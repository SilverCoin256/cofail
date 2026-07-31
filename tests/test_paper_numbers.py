"""Every number in the submission paper must trace to an executed run.

The project states that as a discipline; this enforces it. It exists because a null value of
0.0389 sat in the manuscript for some time and traced to no artifact in results/ -- it was found
by cross-checking against freshly computed values, not by any planned check. A test is cheaper
than the next such discovery.

Scope: paper/workshop.tex, the submission candidate. It quotes a small, fixed set of figures, so
an exact string match against the JSON artifacts is both possible and meaningful. main.tex quotes
many more numbers from older runs and is not covered here; extending this to it is worthwhile but
would need those runs re-emitted as artifacts first.
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
