"""Harvest ARC-Challenge from the Open LLM Leaderboard v2 archive.

Why this exists and why it is scoped the way it is: v2 stores per-sample outcomes as JSON, not
parquet, so there is no column-selective read the way v1 allowed -- the whole per-item file must
come down. Measured directly (docs/NEURIPS_BLUEPRINT.md, X7 feasibility check): ARC-Challenge in
v2 is ~9.4 MB per model per snapshot, so a full six-task replication is infeasible (~369 GB for
1,000 models) but a single-task, ~300-model replication is a bounded, explicitly authorized
~2.8 GB download -- authorized by the user 2026-08-07, not started unprompted.

For each model, only the LATEST snapshot's ARC-Challenge sample file is fetched, and only the
fields needed for a binary correctness matrix (predicted answer index, gold index) are kept in
memory -- the raw JSON is not retained after parsing, only the parsed correctness bit per item.

Run: ./.venv/bin/python src/harvest_v2_arc.py [n_models_to_keep]
(n_models is a target KEPT count, not an attempt budget -- see main()'s docstring.)

Status as of 2026-08-10: unblocked. The HF auth blocker (v2 details datasets are gated) was
resolved by accepting the account-level gate on the open-llm-leaderboard collection, which
propagates across all ~4,500 repos in it -- confirmed directly, not assumed (curl 200 on three
unrelated repos plus an actual file download, before the first real run). That first real run
then found two further bugs no amount of reading could have, since v2 had never been fetched
before: a rejection-handler typo that crashed the whole run on its first reject, and every
sample file being JSON Lines despite its `.json` extension. Both are fixed and documented at
their call sites; see docs/NEURIPS_BLUEPRINT.md for the full sequence.
"""
import json, os, re, sys, time

# huggingface_hub, numpy and the rate limiter are imported lazily inside the functions that
# actually reach the network. extract_correctness() is pure JSON parsing, and keeping it
# importable without the "harvest" extra is what lets tests/test_v2_parser.py exercise it on any
# interpreter -- which matters here more than usual, because the v2 datasets are gated and this
# parser has never seen a real file. Its unit tests are the only thing standing between a
# field-name mistake and a silently corrupted matrix.
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

SUB = os.path.join(HERE, "..", "substrate")
RAW = os.path.join(SUB, "raw")

SAMPLE_RE = re.compile(r"^(?P<model>.+)/samples_leaderboard_arc_challenge_(?P<ts>[\d\-T.]+)\.json$")


def list_models(cache_hours=24):
    """Discover ALL `-details` dataset repos, not just the ones with an ARC-Challenge file --
    that can only be known by listing each repo's own files, which main() does per-candidate.
    Cached, since listing all ~4,500 dataset names is itself a non-trivial number of API calls.

    No n_models truncation here (2026-08-10 fix): the leaderboard switched to a different task
    suite (BBH/GPQA/IFEval/MATH/MMLU-Pro/MUSR) partway through v2's life, and on an alphabetical
    sample of the archive only ~7% of models had an ARC-Challenge file at all (22/300, measured
    directly). Truncating the *candidate* list to the target kept-count, as the original version
    did, produced 0 kept models out of 300 attempted. main() now scans this full list and stops
    once it has kept enough -- see its docstring for why that is still within the ~2.8 GB
    authorization despite scanning far more than 300 candidates."""
    from huggingface_hub import HfApi
    cache_path = os.path.join(SUB, "v2_model_list_cache.json")
    if os.path.exists(cache_path) and (time.time() - os.path.getmtime(cache_path)) < cache_hours * 3600:
        return json.load(open(cache_path))
    api = HfApi()
    ids = sorted(d.id for d in api.list_datasets(author="open-llm-leaderboard", limit=None)
                 if d.id.endswith("-details"))
    json.dump(ids, open(cache_path, "w"))
    return ids


def latest_arc_sample_file(model_id):
    """Return the repo-relative path of the most recent ARC-Challenge samples file, or None."""
    from huggingface_hub import HfApi
    api = HfApi()
    files = api.list_repo_files(model_id, repo_type="dataset")
    hits = []
    for f in files:
        m = SAMPLE_RE.match(f)
        if m and m.group("model") == model_id.split("/")[-1].replace("-details", ""):
            hits.append((m.group("ts"), f))
    if not hits:
        # fall back: any file matching the benchmark name, timestamp parse best-effort
        hits = [(f.rsplit("_", 1)[-1].replace(".json", ""), f) for f in files
                if "samples_leaderboard_arc_challenge" in f]
    if not hits:
        return None
    hits.sort(key=lambda t: t[0])
    return hits[-1][1]


class SampleParseError(ValueError):
    """A v2 samples file could not be parsed unambiguously. Reject the model, never guess."""


def extract_correctness(path, metric_preference=("acc", "acc_norm")):
    """Parse a v2 samples_* file into (correctness list ordered by doc_id, metric name used).

    Written against the actual record schema emitted by lm-evaluation-harness, which builds each
    logged sample as::

        example = {"doc_id":..., "doc":..., "target":..., "arguments":..., "resps":...,
                   "filtered_resps":..., "filter":..., "metrics": [...], ...}
        example.update(metrics)          # <- acc / acc_norm land at TOP LEVEL, as floats

    Three properties of that schema drive this implementation, and an earlier version of this
    function got all three wrong. None of them could have been caught by reading the file we
    could not download; all three are visible in the harness source.

    1. `metrics` is a LIST OF METRIC NAMES, not a mapping of values. The values are top-level.

    2. Metric lookup must use `is not None`, never `or`. `acc` is a float that is legitimately
       0.0 when the model got the item wrong, and `0.0 or <acc_norm>` silently returns acc_norm
       -- so every item a model failed on `acc` but passed on `acc_norm` would have been recorded
       as CORRECT. That single bug would have inflated measured accuracy and, worse, deflated
       measured co-failure, biasing the headline result toward "more independent than they are".
       The same bug applied to `target`, where answer index 0 is a valid gold label.

    3. The harness loops `for filter_key in ...` OUTSIDE the document loop, so a task with k
       filters emits k records per document. Concatenating them in file order yields k copies of
       every item, interleaved by filter. Item identity therefore comes from `doc_id`, and a
       single filter must be chosen deterministically. This is strictly better than v1's
       position-based identity, which needed a 334-model audit (src/audit_roworder.py) to license.

    The metric is chosen ONCE PER FILE from `metric_preference`, not per record: mixing `acc` on
    one model with `acc_norm` on another would make the co-failure matrix incoherent, since the
    two disagree on a substantial fraction of ARC items.

    Raises SampleParseError rather than returning a partially-guessed vector.

    A fourth property, found only once a real file could be downloaded (2026-08-10): despite the
    `.json` extension, files in the archive are JSON Lines -- one JSON object per line, not a
    single array or object -- confirmed on a 1,172-line real ARC-Challenge file. `json.load()` on
    the whole file raises `JSONDecodeError: Extra data` at the start of line 2, which is exactly
    what an all-attempts-crash run surfaced on 22/300 sampled models before this fix. Detected by
    attempting a single `json.load()` first (some dumps genuinely are one JSON document) and
    falling back to one `json.loads()` per line on that specific failure, rather than assuming
    either format.
    """
    with open(path) as fh:
        text = fh.read()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        try:
            data = [json.loads(line) for line in text.splitlines() if line.strip()]
        except json.JSONDecodeError as e:
            raise SampleParseError(f"neither a single JSON document nor JSON Lines: {e}") from e

    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = data.get("samples")
        if rows is None:
            rows = [v for v in data.values() if isinstance(v, dict)]
    else:
        raise SampleParseError(f"unexpected top-level type {type(data).__name__}")
    if not rows:
        raise SampleParseError("no sample records found")

    # one metric for the whole file, present on every record
    metric = next((m for m in metric_preference
                   if all(r.get(m) is not None for r in rows)), None)
    if metric is None:
        have = sorted({k for r in rows[:5] for k in r})
        raise SampleParseError(
            f"no metric in {metric_preference} present on every record; keys seen: {have[:12]}")

    # collapse to one record per doc_id, keeping a single deterministic filter
    filters = sorted({str(r.get("filter", "")) for r in rows})
    chosen = filters[0]
    by_doc = {}
    for r in rows:
        if str(r.get("filter", "")) != chosen:
            continue
        doc_id = r.get("doc_id")
        if doc_id is None:
            raise SampleParseError("record has no doc_id; item identity is not recoverable")
        if doc_id in by_doc:
            raise SampleParseError(
                f"duplicate doc_id {doc_id} within filter {chosen!r}; cannot order items")
        by_doc[doc_id] = r

    if not by_doc:
        raise SampleParseError(f"no records for chosen filter {chosen!r}")

    order = sorted(by_doc)
    if order != list(range(len(order))):
        raise SampleParseError(
            f"doc_id set is not 0..n-1 (min={order[0]}, max={order[-1]}, n={len(order)}); "
            "items may be missing")

    return [bool(round(float(by_doc[d][metric]))) for d in order], metric


def main(n_models=300):
    """n_models is a TARGET KEPT COUNT, not an attempt budget (2026-08-10 fix -- see
    list_models()'s docstring for why the original attempt-budget semantics kept 0/300).
    Scans the full candidate list and stops once that many models have been kept, or the
    candidates run out. Still bounded to the ~2.8 GB the user authorized 2026-08-07: a model
    lacking an ARC-Challenge file is rejected from its file listing alone, with no download, and
    that rejection is the overwhelmingly common case (~93% on the measured sample), so the
    number of actual ~9.4 MB downloads stays close to n_models regardless of how many
    no-file candidates are scanned to find them."""
    import numpy as np
    from huggingface_hub import hf_hub_download
    from huggingface_hub.utils import EntryNotFoundError, HfHubHTTPError
    from ratelimit import LIMITER, is_429

    os.makedirs(RAW, exist_ok=True)
    candidates = list_models()
    print(f"[v2-arc] scanning up to {len(candidates)} candidates for {n_models} kept models "
          f"(scoped, user-authorized 2026-08-07)", flush=True)

    rows, kept_models, rejects = [], [], []
    n_items_ref = metric_ref = None
    t0 = time.time()
    total_bytes = 0
    i = -1  # in case candidates is empty, so the summary below doesn't reference an unset name

    for i, mid in enumerate(candidates):
        if len(kept_models) >= n_models:
            print(f"[v2-arc] reached target of {n_models} kept models "
                  f"after scanning {i}/{len(candidates)} candidates", flush=True)
            break
        try:
            LIMITER.acquire()
            rel = latest_arc_sample_file(mid)
            if rel is None:
                rejects.append({"model": mid, "reason": "no ARC-Challenge samples file"})
                continue
            local = hf_hub_download(mid, rel, repo_type="dataset")
            total_bytes += os.path.getsize(local)
            correctness, metric = extract_correctness(local)
            if n_items_ref is None:
                n_items_ref, metric_ref = len(correctness), metric
            if len(correctness) != n_items_ref:
                rejects.append({"model": mid, "reason": "length mismatch",
                                "n": len(correctness), "expected": n_items_ref})
                continue
            # a model scored on a different metric is not comparable to the rest of the
            # population; keeping it would silently mix acc and acc_norm within one matrix
            if metric != metric_ref:
                rejects.append({"model": mid, "reason": "metric mismatch",
                                "metric": metric, "expected": metric_ref})
                continue
            rows.append(correctness)
            kept_models.append(mid)
        except SampleParseError as e:
            rejects.append({"model": mid, "reason": f"parse: {str(e)[:120]}"})
        except (EntryNotFoundError, HfHubHTTPError) as e:
            if is_429(e):
                LIMITER.hit_429(e)
            rejects.append({"model": mid, "reason": f"{type(e).__name__}: {str(e)[:100]}"})
        except Exception as e:
            rejects.append({"model": mid, "reason": f"{type(e).__name__}: {str(e)[:100]}"})

        if (i + 1) % 10 == 0:
            gb = total_bytes / 1e9
            print(f"  {i+1}/{len(candidates)} scanned  kept={len(kept_models)} target={n_models} "
                  f"rejected={len(rejects)}  {gb:.2f} GB downloaded  {time.time()-t0:.0f}s elapsed",
                  flush=True)
            # checkpoint every 10 models so a long-running, rate-limited harvest over ~300
            # models can't lose everything to a single failure late in the run
            if rows:
                arr = np.array(rows, dtype=np.uint8)
                np.savez_compressed(os.path.join(RAW, "arc_v2.npz"), prim=arr,
                                    models=np.array(kept_models, dtype=object))
                json.dump(rejects, open(os.path.join(SUB, "v2_arc_rejects.json"), "w"))

    arr = np.array(rows, dtype=np.uint8) if rows else np.zeros((0, 0), dtype=np.uint8)
    np.savez_compressed(os.path.join(RAW, "arc_v2.npz"), prim=arr,
                        models=np.array(kept_models, dtype=object))
    json.dump(rejects, open(os.path.join(SUB, "v2_arc_rejects.json"), "w"), indent=1)
    json.dump({"n_target": n_models, "n_scanned": min(i + 1, len(candidates)),
              "n_candidates": len(candidates), "n_kept": len(kept_models),
              "n_rejected": len(rejects), "n_items": n_items_ref,
              "total_bytes_downloaded": total_bytes, "seconds_elapsed": time.time() - t0},
             open(os.path.join(SUB, "v2_arc_manifest.json"), "w"), indent=1)

    print(f"\n[v2-arc] done: {len(kept_models)}/{n_models} kept "
          f"(scanned {min(i + 1, len(candidates))} of {len(candidates)} candidates), "
          f"{len(rejects)} rejected, "
          f"{n_items_ref} items, {total_bytes/1e9:.2f} GB, {time.time()-t0:.0f}s")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    main(n)
