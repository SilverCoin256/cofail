"""Every number in the three NeurIPS workshop papers must trace to an executed run.

Same discipline as tests/test_paper_numbers.py, applied to the workshop short papers. It exists
because the first drafts of these three papers contained figures that traced to nothing: two
per-benchmark rms ratios quoted as 4.6x and 4.1x appeared in no artifact (the real values are 6.6x
and 5.1x), and a deduplication claim quoted the wrong threshold and the wrong outcome. Those were
caught by hand. This makes the check automatic.

Also enforces the submission constraints that would cause a desk reject rather than a bad review:
page limits and blinding, checked on the RENDERED pdf, not the source.
"""
import csv
import json
import os
import re
import shutil
import subprocess

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
WS = os.path.join(ROOT, "paper", "workshops")
RES = os.path.join(ROOT, "results")

PAPERS = {"e-values": 4.0, "attrib": 6.0, "evorobust": 4.0}
BLINDING = {"e-values": "single", "attrib": "double", "evorobust": "double"}


def art(name):
    with open(os.path.join(RES, name)) as f:
        return json.load(f)


def tex(venue):
    with open(os.path.join(WS, venue, "main.tex")) as f:
        return f.read()


def rendered(venue):
    pdf = os.path.join(WS, venue, "main.pdf")
    if not os.path.exists(pdf) or shutil.which("pdftotext") is None:
        pytest.skip(f"{venue}/main.pdf not built or pdftotext unavailable")
    out = subprocess.run(["pdftotext", "-layout", pdf, "-"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        pytest.skip("pdftotext failed")
    return out.stdout


# --------------------------------------------------------------------------
# W1 -- the ATTRIB family-signal result
# --------------------------------------------------------------------------

def test_attrib_headline_accuracy_traces_to_w1():
    w1 = art("w1_family_signal.json")
    real = w1["arms"]["real_full"]
    t = tex("attrib")
    assert f"{real['loo_knn_accuracy']:.3f}" == "0.807"
    assert "0.807" in t
    assert f"{real['perm_mean']:.3f}" == "0.287" and "0.287" in t
    assert f"{real['perm_sd']:.3f}" == "0.017" and "0.017" in t
    assert f"{real['majority_class_rate']:.3f}" == "0.382" and "0.382" in t
    assert real["n_models_labelled"] == 916 and "916" in t
    assert real["N"] == 3762 and "3{,}762" in t


def test_attrib_control_arms_trace_to_artifacts():
    w1, c = art("w1_family_signal.json"), art("w1_controls.json")
    t = tex("attrib")
    pairs = [
        (w1["arms"]["curveball_replicate"]["loo_knn_accuracy"], "0.318"),
        (w1["arms"]["dedup_0.95"]["loo_knn_accuracy"], "0.787"),
        (c["A_accuracy_only"]["acc"], "0.432"),
        (c["A2_accuracy_regressed_out"]["acc"], "0.809"),
        (c["B_raw_correlation"]["acc"], "0.760"),
        (c["C_dedup_0.90"]["acc"], "0.551"),
    ]
    for value, printed in pairs:
        assert f"{value:.3f}" == printed, f"{value} != {printed}"
        assert printed in t, f"{printed} missing from attrib/main.tex"


def test_attrib_family_counts_match_the_census():
    w1 = art("w1_family_signal.json")
    counts = w1["arms"]["real_full"]["family_counts"]
    t = tex("attrib")
    assert sum(counts.values()) == w1["arms"]["real_full"]["n_models_labelled"]
    for fam, n in counts.items():
        assert str(n) in t, f"family count {fam}={n} missing from the paper"


def test_attrib_k5_coverage_traces_to_the_gate():
    k5 = art("k5_gate.json")
    t = tex("attrib")
    assert abs(k5["coverage"] - 0.233) < 0.0005
    assert "23.3" in t
    assert str(k5["models_with_declared_parent"]) == "317" and "317" in t
    assert str(k5["errors"]) == "315" and "315" in t
    assert int(k5["K5_threshold"] * 100) == 40 and "40\\%" in t


def test_attrib_kill_conditions_all_passed():
    v = art("w1_family_signal.json")["verdict"]
    assert v["KW3_null_arm_at_chance"], "KW3 fired: pipeline manufactures signal; nothing reportable"
    assert v["KW1_signal_detected"], "KW1 fired: the paper must report a negative result"
    assert v["KW2_survives_dedup"], "KW2 fired: signal is a duplicate artifact"


def test_attrib_states_the_negative_control_results():
    """The two findings that cut against the strongest reading must stay in the paper."""
    t = tex("attrib")
    assert "0.760" in t and "conditioning" in t.lower()
    assert "0.551" in t


# --------------------------------------------------------------------------
# W2 -- the E-values sequential monitor
# --------------------------------------------------------------------------

def test_evalues_monitor_numbers_trace_to_w2():
    w2 = art("w2_sequential_evalue.json")
    t = tex("e-values")
    assert w2["n_looks"] == 12 and "twelve" in t
    assert w2["real_stream"][0]["N"] == 241 and "241" in t
    assert w2["real_stream"][-1]["N"] == 3762 and "3{,}762" in t
    assert abs(w2["e_value_ceiling_at_mc_floor"] - 3.202) < 0.001 and "3.20" in t
    assert abs(w2["mc_p_floor"] - 1 / 41) < 1e-9 and "1/41" in t
    assert abs(w2["final_merged_e_control"] - 0.902) < 0.001 and "0.90" in t
    assert abs(w2["max_merged_e_control"] - 1.165) < 0.001 and "1.17" in t


def test_evalues_monitor_table_rows_match_the_stream():
    w2 = art("w2_sequential_evalue.json")
    t = tex("e-values")
    by_month = {r["month"]: r for r in w2["real_stream"]}
    ctrl = {c["month"]: c for c in w2["null_stream_control"]}
    for month in ("2023-07", "2023-11", "2024-01", "2024-03", "2024-06"):
        r = by_month[month]
        assert month in t, f"{month} row missing"
        assert f"{r['ratio']:.2f}" in t, f"ratio {r['ratio']:.2f} for {month} not in paper"
        assert f"{ctrl[month]['e_merged_running_mean']:.2f}" in t


def test_evalues_control_stream_did_not_accumulate_evidence():
    w2 = art("w2_sequential_evalue.json")
    assert not w2["KW4_control_exceeds_20"], "KW4 fired: the monitor is invalid as implemented"
    assert w2["max_merged_e_control"] < 2.0


def test_evalues_real_stream_is_reported_as_a_resolution_ceiling():
    """Every real look sits at the MC floor, so the paper must not present 3.20 as evidence."""
    w2 = art("w2_sequential_evalue.json")
    assert all(abs(r["p"] - w2["mc_p_floor"]) < 1e-9 for r in w2["real_stream"])
    t = tex("e-values")
    assert "ceiling" in t.lower()
    assert "not a likelihood ratio" in t or "resolution" in t.lower()


def test_evalues_p_range_of_the_control_arm_matches():
    w2 = art("w2_sequential_evalue.json")
    ps = [c["p"] for c in w2["null_stream_control"]]
    t = tex("e-values")
    assert f"{min(ps):.3f}" == "0.049" and "0.049" in t
    assert f"{max(ps):.3f}" == "0.951" and "0.951" in t


# --------------------------------------------------------------------------
# W3 -- the EvoRobust decision-relevance grid
# --------------------------------------------------------------------------

def test_evorobust_grid_traces_to_w3():
    w3 = art("w3_diversity_decision.json")
    t = tex("evorobust")
    for key, cell in w3["grid_2x2"].items():
        for field, fmt in (("double_fault_mean_cofail", "{:.4f}"),
                           ("mean_pairwise_disagreement", "{:.4f}")):
            printed = fmt.format(cell[field])
            assert printed in t, f"{key} {field}={printed} missing from evorobust/main.tex"
        assert f"{cell['rms_ratio']:.2f}" in t
        assert str(cell["n_eigen_above_edge"]) in t


def test_evorobust_grid_verdict_supports_the_claims():
    """The paper claims double-fault is wrong in BOTH regimes and disagreement only in one."""
    v = art("w3_diversity_decision.json")["grid_verdict"]
    assert v["heterogeneous"]["naive_double_fault_correct"] is False
    assert v["homogeneous"]["naive_double_fault_correct"] is False
    assert v["heterogeneous"]["naive_disagreement_correct"] is False
    assert v["homogeneous"]["naive_disagreement_correct"] is True
    assert v["heterogeneous"]["calibrated_correct"] is True
    assert v["homogeneous"]["calibrated_correct"] is True


def test_evorobust_kill_conditions():
    v = art("w3_diversity_decision.json")["verdict"]
    assert v["KW5_degeneracy_is_decision_relevant"], "KW5 fired: governance claim must be withdrawn"
    assert not v["KW6_correction_fails"], "KW6 fired: the correction does not work"


def test_disagreement_identity_holds_numerically():
    """The EvoRobust lemma extends Lemma 1 to disagreement: mean disagreement = 2*pbar - 2*O.

    Asserted as a test because it is a proposition in a submitted paper.
    """
    w3 = art("w3_diversity_decision.json")
    for name, s in w3["suites"].items():
        assert abs(s["mean_pairwise_disagreement"] - s["identity_check_2pbar_minus_2O"]) < 1e-12, name

    rng = np.random.default_rng(11)
    for _ in range(5):
        n, m = 60, 90
        F = (rng.random((n, m)) < rng.uniform(0.2, 0.8, (1, m))).astype(np.uint8)
        p = F.mean(1)
        G = (F.astype(float) @ F.astype(float).T) / m
        iu = np.triu_indices(n, 1)
        disagree = (p[:, None] + p[None, :] - 2 * G)[iu].mean()
        c = F.sum(0).astype(float)
        O = ((c * c - c).sum()) / (m * n * (n - 1))
        assert abs(disagree - (2 * p.mean() - 2 * O)) < 1e-10


# --------------------------------------------------------------------------
# Shared figures across the three papers
# --------------------------------------------------------------------------

def test_shared_rms_ratios_match_the_timeseries():
    """The 2.9x-11.9x range quoted in all three papers must come from the frozen run."""
    with open(os.path.join(RES, "timeseries.csv")) as f:
        rows = [r for r in csv.DictReader(f) if r["run_date"] == "2026-07-26"]
    ratios = {r["bench"]: float(r["rms_R_observed"]) / float(r["rms_R_null"]) for r in rows}
    assert f"{min(ratios.values()):.1f}" == "2.9"
    assert f"{max(ratios.values()):.1f}" == "11.9"
    for venue in PAPERS:
        t = tex(venue)
        if "2.9" in t or "11.9" in t:
            assert "2.9" in t and "11.9" in t, f"{venue} quotes half the range"


def test_per_benchmark_ratios_in_tables_match_the_timeseries():
    with open(os.path.join(RES, "timeseries.csv")) as f:
        rows = [r for r in csv.DictReader(f) if r["run_date"] == "2026-07-26"]
    for r in rows:
        ratio = float(r["rms_R_observed"]) / float(r["rms_R_null"])
        for venue in ("e-values", "evorobust"):
            t = tex(venue)
            assert f"${ratio:.1f}\\times$" in t, \
                f"{venue}: {r['bench']} ratio {ratio:.1f}x not in the table"


def test_no_retired_ratio_values_reappear():
    """4.6x and 4.1x were in the first drafts and trace to no artifact."""
    for venue in PAPERS:
        t = tex(venue)
        assert "$4.6\\times$" not in t, f"{venue} resurrected the untraceable 4.6x"
        assert "$4.1\\times$ its null" not in t, f"{venue} resurrected the untraceable 4.1x"


def test_neff_nulls_match_the_independent_chain_runs():
    for bench, label in (("arc", "ARC-Challenge"), ("winogrande", "Winogrande"),
                         ("truthfulqa", "TruthfulQA"), ("gsm8k", "GSM8K"),
                         ("hellaswag", "HellaSwag")):
        a = art(f"{bench}_null_independent.json")["N_eff"]
        for venue in ("e-values", "evorobust"):
            t = tex(venue)
            assert f"{a['null_mean']:.1f}" in t, f"{venue}: {bench} null mean missing"
            assert f"{a['observed']:.1f}" in t, f"{venue}: {bench} observed PR missing"


# --------------------------------------------------------------------------
# Submission constraints, checked on the rendered artifact
# --------------------------------------------------------------------------

@pytest.mark.parametrize("venue,limit", sorted(PAPERS.items()))
def test_content_pages_within_venue_limit(venue, limit):
    text = rendered(venue)
    pages = text.split("\f")
    for i, p in enumerate(pages):
        if "References" in p:
            lines = p.split("\n")
            n = next(k for k, l in enumerate(lines) if "References" in l)
            content = i + n / max(len(lines), 1)
            assert content <= limit, f"{venue}: {content:.2f} content pages exceeds {limit}"
            return
    pytest.fail(f"{venue}: no References heading found")


@pytest.mark.parametrize("venue", sorted(BLINDING))
def test_blinding_is_correct_in_the_rendered_pdf(venue):
    text = rendered(venue)
    if BLINDING[venue] == "double":
        assert not re.search(r"Shaurya|Gupta|shauryaguptaa8|SilverCoin256", text, re.I), \
            f"{venue} is double-blind but leaks the author's identity"
        assert "Anonymous Author" in text
    else:
        assert "Shaurya Gupta" in text, f"{venue} is single-blind and must name the author"


@pytest.mark.parametrize("venue", sorted(PAPERS))
def test_workshop_title_is_declared(venue):
    """Both \\title and \\workshoptitle are required by the NeurIPS workshop template."""
    t = tex(venue)
    assert "\\workshoptitle{" in t and "\\title{" in t


# --------------------------------------------------------------------------
# Substrate drift
# --------------------------------------------------------------------------

def test_experiment_artifacts_pin_their_input_snapshot():
    """W1/W2 ran on a snapshot of an archive that is still growing.

    src/monitor.py commits new harvests on a schedule -- one landed the same day these
    experiments ran and took ARC from N=3,762 to N=4,562. An experiment whose input file has
    changed underneath it is only reproducible if it names the snapshot it used, so every
    artifact must carry one and the paper must not call that snapshot "current".
    """
    for name in ("w1_family_signal.json", "w1_controls.json", "w2_sequential_evalue.json"):
        snap = art(name).get("substrate_snapshot")
        assert snap, f"{name} does not record which substrate snapshot it ran on"
        assert len(snap["sha256"]) == 64, f"{name} snapshot hash is malformed"


def test_papers_do_not_claim_the_snapshot_is_current():
    """'The current harvest' silently goes stale the next time the monitor runs."""
    for venue in PAPERS:
        t = tex(venue)
        assert "current harvest" not in t.lower(), \
            f"{venue} calls its snapshot 'current'; pin it by hash instead"


def test_attrib_states_the_snapshot_is_pinned():
    t = tex("attrib")
    snap = art("w1_family_signal.json")["substrate_snapshot"]
    assert snap["sha256"].startswith("79d2490e")
    assert "79d2490e" in t, "attrib must name the snapshot hash its numbers came from"
