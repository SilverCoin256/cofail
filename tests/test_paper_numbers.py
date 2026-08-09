"""Every number in the submission paper must trace to an executed run.

The project states that as a discipline; this enforces it. It exists because a null value of
0.0389 sat in the manuscript for some time and traced to no artifact in results/ -- it was found
by cross-checking against freshly computed values, not by any planned check. A test is cheaper
than the next such discovery.

Scope: paper/workshop.tex in full, since the submission candidate quotes a small fixed set of
figures. paper/main.tex is covered only for the figures produced by the 2026-07-28 robustness runs
(sampler validation, power study, noise floor, deduplication) -- those have artifacts to check
against. Its older numbers come from runs that predate this discipline and are not yet re-emitted
as JSON; that gap is real and is stated here rather than hidden by a passing test.
"""
import json
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
RES = os.path.join(ROOT, "results")
TEX = os.path.join(ROOT, "paper", "workshop.tex")

NICE = {"arc": "ARC-Challenge", "winogrande": "Winogrande", "truthfulqa": "TruthfulQA",
        "gsm8k": "GSM8K", "hellaswag": "HellaSwag"}


def load(name):
    p = os.path.join(RES, name)
    if not os.path.exists(p):
        pytest.skip(f"{name} not present; run the corresponding experiment")
    return json.load(open(p))


@pytest.fixture(scope="module")
def tex():
    if not os.path.exists(TEX):
        pytest.skip("paper/workshop.tex not present")
    return open(TEX).read()


def test_per_benchmark_figures_match_dedup_sensitivity(tex):
    """Observed rms, its ratio to the null, % of models removed at 0.95, and the dimension count."""
    d = load("dedup_sensitivity.json")
    missing = []
    for b in d["benchmarks"]:
        full = b["sweep"][0]
        at95 = next(s for s in b["sweep"] if s["threshold"] == 0.95)
        pct = round(100 * at95["n_removed"] / full["N"])
        want = {
            "rms": f"${full['rms_obs']:.4f}$",
            "ratio": f"${full['rms_ratio']:.2f}\\times$",
            "pct_removed": f"${pct}\\%$",
            "dims": f"${full['n_eigen_above_edge']}$",
        }
        for k, s in want.items():
            if s not in tex:
                missing.append(f"{NICE[b['bench']]}/{k}: {s}")
    assert not missing, "workshop.tex does not contain these artifact values: " + "; ".join(missing)


def test_incremental_validity_figures(tex):
    d = load("incremental_validity.json")["models"]
    for s in (f"{d['M0_member_acc_plus_size']['r2']:.4f}",
              f"{d['M1_plus_classical_diversity']['delta_r2_vs_M0']:.4f}",
              f"{d['M2_plus_conditioned_R']['delta_r2_vs_M1']:.4f}"):
        assert s in tex, f"missing incremental-validity figure {s}"


def test_power_study_figures(tex):
    d = load("power_study.json")
    assert f"{d['KP1_min_rms_at_power_0.8']:.3f}" in tex, "missing the planted rms at power 0.8"
    assert f"${d['KP3_copy_detection_threshold']}$" in tex, "missing the copy-detection threshold"
    # the blind spot must be stated as equal to alpha, not merely as a small number
    assert d["KP2_blind_spot_power"] == d["alpha"], (
        "power against the shared-difficulty alternative is no longer exactly alpha; the paper's "
        "central claim about the blind spot must be re-checked, not just re-worded")


def test_sampler_validation_figures(tex):
    d = load("sampler_validation.json")
    for t in d["V1_fiber_tests"]:
        assert str(t["fiber_size"]) in tex, f"missing enumerated fibre size {t['fiber_size']}"
    rhats = [x["rhat"] for x in d["V2_gelman_rubin"]]
    assert f"{min(rhats):.2f}" in tex and f"{max(rhats):.2f}" in tex, "Rhat range not quoted"
    assert all(r <= 1.05 for r in rhats), "a chain no longer mixes; the paper claims all do"


def test_no_untraceable_null_value(tex):
    """Regression guard for the specific defect that motivated this file."""
    assert "0.0389" not in tex, (
        "0.0389 is back in the paper. It traced to no executed run; the ARC exact-null rms is "
        "~0.0449 across four independent estimates."
    )


# --- paper/main.tex: only the figures that have artifacts from the 2026-07-28 runs ------------

MAIN = os.path.join(ROOT, "paper", "main.tex")


@pytest.fixture(scope="module")
def main_tex():
    if not os.path.exists(MAIN):
        pytest.skip("paper/main.tex not present")
    return open(MAIN).read()


def test_main_sampler_validation_figures(main_tex):
    d = load("sampler_validation.json")
    for t in d["V1_fiber_tests"]:
        assert str(t["fiber_size"]) in main_tex, f"missing enumerated fibre size {t['fiber_size']}"
    rhats = [x["rhat"] for x in d["V2_gelman_rubin"]]
    assert f"{min(rhats):.2f}" in main_tex and f"{max(rhats):.2f}" in main_tex


def test_main_power_and_noise_floor_figures(main_tex):
    ps = load("power_study.json")
    assert f"{ps['KP1_min_rms_at_power_0.8']:.3f}" in main_tex
    assert f"{ps['calibration_false_positive_rate']:.3f}" in main_tex, (
        "the null-condition false-positive rate is quoted as evidence the test is calibrated; "
        "it must match the run"
    )
    arc = load("noise_floor.json")["benchmarks"][0]
    assert arc["bench"] == "arc"
    for key in ("a_exact_fixed_fixed", "c_col_margin_only", "e_analytic_floor"):
        v = f"{arc[key]['mean']:.4f}"
        assert v in main_tex, f"missing noise-floor value {key}={v}"


def test_main_quotes_the_corrected_arc_null(main_tex):
    """The correction that motivated this file, asserted on the full paper too."""
    assert "0.0389" not in main_tex
    arc_chains = [x for r in load("sampler_validation.json")["V2_gelman_rubin"]
                  if r["bench"] == "arc" for x in r["chain_means"]]
    pooled = sum(arc_chains) / len(arc_chains)
    assert f"{pooled:.4f}" in main_tex, (
        f"main.tex should quote the ARC exact-null rms as {pooled:.4f}, the pooled mean of the "
        "four dispersed chains"
    )


def test_item_margin_only_gap_is_stated_as_the_max_not_a_smaller_number(main_tex, tex):
    """Both papers claim item-margin-only conditioning reproduces the both-margin null
    'to within X%'. X must bound the WORST benchmark, not a convenient one.

    This exists because the papers said 6% while HellaSwag's actual gap is 8.3% and GSM8K's
    is 6.05% -- a claim that was false on two of five benchmarks, found by checking the
    per-benchmark ratios rather than the ARC row the sentence quotes.
    """
    ratios = [b["ratio_exact_over_colonly"] for b in load("noise_floor.json")["benchmarks"]]
    worst_pct = (max(ratios) - 1.0) * 100.0
    stated = f"{worst_pct:.1f}\\%"
    for name, body in (("main.tex", main_tex), ("workshop.tex", tex)):
        assert stated in body, (
            f"{name} must bound the item-margin-only gap by the worst benchmark "
            f"({stated}); a smaller figure understates it"
        )
