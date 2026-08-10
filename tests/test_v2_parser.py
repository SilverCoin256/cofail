"""Unit tests for the v2 samples parser, built against the harness's real record schema.

The v2 harvest is blocked on HuggingFace auth, so no real `samples_*.json` has ever been parsed
by this project. That is exactly why these tests exist: the parser was written by guessing field
names, and a guess that is never exercised is a bug waiting for the moment the token arrives.

The record shape here is copied from lm-evaluation-harness's own construction in
`lm_eval/evaluator.py`:

    example = {"doc_id":..., "doc":..., "target":..., "arguments":..., "resps":...,
               "filtered_resps":..., "filter":..., "metrics": [...], ...}
    example.update(metrics)      # acc / acc_norm land at top level as floats

Each test below pins a defect the original parser actually had. The first one is the serious
one: it would have silently corrupted the correctness matrix in the direction that flatters the
paper's headline finding.
"""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

pytest.importorskip("numpy")
harvest_v2_arc = pytest.importorskip(
    "harvest_v2_arc", reason="requires huggingface_hub (harvest extra)")
extract_correctness = harvest_v2_arc.extract_correctness
SampleParseError = harvest_v2_arc.SampleParseError


def record(doc_id, acc=None, acc_norm=None, target=0, filt="none", **extra):
    """One logged sample in the harness's schema."""
    r = {
        "doc_id": doc_id,
        "doc": {"answerKey": "A"},
        "target": target,
        "arguments": [["ctx", "cont"]],
        "resps": [["-1.0", "False"]],
        "filtered_resps": ["-1.0"],
        "filter": filt,
        "metrics": [m for m, v in (("acc", acc), ("acc_norm", acc_norm)) if v is not None],
    }
    if acc is not None:
        r["acc"] = acc
    if acc_norm is not None:
        r["acc_norm"] = acc_norm
    r.update(extra)
    return r


def write(tmp_path, rows, name="samples.json"):
    p = tmp_path / name
    p.write_text(json.dumps(rows))
    return str(p)


def test_acc_zero_is_not_silently_replaced_by_acc_norm(tmp_path):
    """THE severe one. `r.get("acc") or r.get("acc_norm")` returns acc_norm when acc == 0.0,
    because 0.0 is falsy -- so every item the model failed under acc but passed under acc_norm
    was recorded as CORRECT. That inflates accuracy and deflates co-failure, biasing the study's
    headline toward 'models are more independent than they are'."""
    rows = [
        record(0, acc=0.0, acc_norm=1.0),   # wrong under acc, right under acc_norm
        record(1, acc=1.0, acc_norm=1.0),
        record(2, acc=0.0, acc_norm=0.0),
    ]
    got, metric = extract_correctness(write(tmp_path, rows))
    assert metric == "acc", "acc must win the preference order when present on every record"
    assert got == [False, True, False], (
        "item 0 is wrong under acc; returning True means the 0.0-is-falsy bug is back"
    )


def test_target_index_zero_does_not_fall_through(tmp_path):
    """`r.get("target") or ...` discards a gold label of 0, which is a valid ARC answer index."""
    rows = [record(0, acc=1.0, target=0), record(1, acc=0.0, target=0)]
    got, _ = extract_correctness(write(tmp_path, rows))
    assert got == [True, False]


def test_multiple_filters_do_not_duplicate_items(tmp_path):
    """The harness loops over filters OUTSIDE the doc loop, so k filters emit k records per doc.
    Reading in file order would return k copies of every item, interleaved."""
    rows = []
    for filt in ("none", "strict-match"):
        for doc_id, acc in enumerate([1.0, 0.0, 1.0]):
            rows.append(record(doc_id, acc=acc, filt=filt))
    got, _ = extract_correctness(write(tmp_path, rows))
    assert len(got) == 3, f"expected 3 items after collapsing filters, got {len(got)}"
    assert got == [True, False, True]


def test_items_are_ordered_by_doc_id_not_file_order(tmp_path):
    """Item identity comes from doc_id. File order is not guaranteed and must not be trusted."""
    rows = [record(2, acc=1.0), record(0, acc=0.0), record(1, acc=1.0)]
    got, _ = extract_correctness(write(tmp_path, rows))
    assert got == [False, True, True], "records must be sorted by doc_id before use"


def test_metric_is_chosen_once_per_file_not_per_record(tmp_path):
    """If acc is missing from even one record, the whole file falls back to acc_norm -- rather
    than mixing acc on some items with acc_norm on others."""
    rows = [record(0, acc=1.0, acc_norm=0.0), record(1, acc_norm=1.0)]
    got, metric = extract_correctness(write(tmp_path, rows))
    assert metric == "acc_norm", "a metric absent on any record cannot be the file's metric"
    assert got == [False, True]


def test_missing_metrics_raises_rather_than_guessing(tmp_path):
    rows = [record(0), record(1)]
    with pytest.raises(SampleParseError, match="no metric"):
        extract_correctness(write(tmp_path, rows))


def test_missing_doc_id_raises(tmp_path):
    rows = [record(0, acc=1.0), record(1, acc=1.0)]
    del rows[1]["doc_id"]
    with pytest.raises(SampleParseError, match="doc_id"):
        extract_correctness(write(tmp_path, rows))


def test_gappy_doc_ids_raise_rather_than_silently_shortening(tmp_path):
    """Missing items would otherwise produce a shorter vector that still looks well-formed, and
    a shorter vector silently misaligns this model's row against every other model's."""
    rows = [record(0, acc=1.0), record(2, acc=1.0)]
    with pytest.raises(SampleParseError, match="0..n-1|missing"):
        extract_correctness(write(tmp_path, rows))


def test_duplicate_doc_id_within_one_filter_raises(tmp_path):
    rows = [record(0, acc=1.0), record(0, acc=0.0), record(1, acc=1.0)]
    with pytest.raises(SampleParseError, match="duplicate"):
        extract_correctness(write(tmp_path, rows))


def test_samples_key_wrapper_is_accepted(tmp_path):
    """Some dumps wrap the list under a "samples" key rather than being a bare list."""
    rows = [record(0, acc=1.0), record(1, acc=0.0)]
    p = tmp_path / "wrapped.json"
    p.write_text(json.dumps({"samples": rows}))
    got, _ = extract_correctness(str(p))
    assert got == [True, False]


def test_empty_file_raises(tmp_path):
    with pytest.raises(SampleParseError):
        extract_correctness(write(tmp_path, []))


def write_jsonl(tmp_path, rows, name="samples.json"):
    """Real archive files use this format despite the .json extension -- see below."""
    p = tmp_path / name
    p.write_text("\n".join(json.dumps(r) for r in rows))
    return str(p)


def test_jsonl_despite_json_extension_is_parsed(tmp_path):
    """The real archive schema, found only once a real file could be downloaded (2026-08-10):
    every sample file is JSON Lines -- one JSON object per line -- despite ending in `.json`,
    not the single JSON array/object every test above (and the original implementation) assumed.
    Confirmed directly on a 1,172-line real ARC-Challenge file; json.load() on the whole file
    raises 'Extra data' at the start of line 2, which crashed 22/300 models before this fix, with
    the other 278 rejected for lacking an ARC-Challenge file at all (a real, separate fact about
    the archive -- see list_models()'s docstring)."""
    rows = [record(0, acc=1.0), record(1, acc=0.0), record(2, acc=1.0)]
    got, metric = extract_correctness(write_jsonl(tmp_path, rows))
    assert metric == "acc"
    assert got == [True, False, True]


def test_single_json_document_still_works_alongside_jsonl(tmp_path):
    """The fix tries a single json.load() first and only falls back to JSON Lines on failure --
    confirming it doesn't regress the format every other test in this file uses."""
    rows = [record(0, acc=1.0), record(1, acc=0.0)]
    got, _ = extract_correctness(write(tmp_path, rows))
    assert got == [True, False]


def test_genuinely_malformed_file_raises_not_silently_empty(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json at all")
    with pytest.raises(SampleParseError, match="neither a single JSON document nor JSON Lines"):
        extract_correctness(str(p))
