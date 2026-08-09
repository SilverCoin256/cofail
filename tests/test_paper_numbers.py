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


def test_main_spectral_diagnostics_trace_to_an_artifact(main_tex):
    """The discriminating spectral diagnostics must trace to JSON, not only to the digest.

    lambda_1^2/sum(lambda^2), the deflated participation ratio, and the positive-mass fraction
    are the statistics the paper offers *in place of* the withdrawn 'effective number of models'
    claim, so they carry real weight. They were quoted in main.tex and recorded in
    RESULTS_DIGEST.md but emitted by no run; src/spectral_diagnostics.py now emits them and this
    asserts the paper matches. Recomputed on the paper-era 1,362-model matrix, not the live
    substrate, which Layer C keeps growing.
    """
    d = load("spectral_diagnostics.json")["arc"]
    assert d["N"] == 1362 and d["M"] == 1165, (
        "spectral_diagnostics.json must be computed on the paper-era ARC snapshot; "
        f"got N={d['N']}, M={d['M']}"
    )
    assert f"{d['lambda1_sq_over_sum_sq']:.3f}" in main_tex
    assert f"{d['pr_deflated_leading']:.1f}" in main_tex
    assert f"{d['frac_spectral_mass_positive'] * 100:.2f}" in main_tex
    assert f"{d['pr_clipped']:.1f}" in main_tex
    assert f"{d['pr_absolute']:.1f}" in main_tex
    assert d["pr_identity_matches_raw"], (
        "the paper's algebraic claim is that PR = N/(1+(N-1)*mean R^2) exactly; "
        "the run says otherwise"
    )


def test_cross_benchmark_ratio_range_is_rounded_correctly(main_tex, tex):
    """The headline cross-benchmark excess range must round the artifact correctly.

    Both papers said '2.9-11.9x'; the artifact says 2.848 and 11.842, which round to 2.8 and
    11.8. Rounding a headline range outward in both directions overstates the finding at both
    ends, so this pins it to the run.
    """
    ratios = [b["sweep"][0]["rms_ratio"] for b in load("dedup_sensitivity.json")["benchmarks"]]
    lo, hi = f"{min(ratios):.1f}", f"{max(ratios):.1f}"
    for name, body in (("main.tex", main_tex), ("workshop.tex", tex)):
        assert lo in body and hi in body, (
            f"{name} must state the cross-benchmark excess range as {lo}-{hi}x"
        )


def test_dedup_discard_range_matches_the_sweep(main_tex, tex):
    """The '0.95-dedup discards X-Y% of each population' range must bound all five benchmarks.

    Both papers said 36-64%. The sweep says GSM8K drops 20.8% and Winogrande 34.3%, so the low
    end was wrong on two of five -- and workshop.tex's own table already printed 21% for GSM8K,
    contradicting its abstract two pages earlier.
    """
    fracs = []
    for b in load("dedup_sensitivity.json")["benchmarks"]:
        full = [s for s in b["sweep"] if s["threshold"] == 1.01][0]
        d95 = [s for s in b["sweep"] if s["threshold"] == 0.95][0]
        fracs.append(d95["n_removed"] / full["N"] * 100.0)
    lo, hi = f"{min(fracs):.0f}", f"{max(fracs):.0f}"
    for name, body in (("main.tex", main_tex), ("workshop.tex", tex)):
        assert f"${lo}$--${hi}\\%$" in body, (
            f"{name} must state the 0.95-dedup discard range as {lo}-{hi}%"
        )


def test_model_count_range_traces_to_the_runs(main_tex, tex):
    """The headline population range must equal the actual per-benchmark N values.

    Both papers advertised '1,228-1,373 models per benchmark' in their abstracts. No artifact
    contains 1,373 as a value at all -- the true maximum is ARC/HellaSwag at 1,362. This is the
    same failure mode as the 0.0389 null: a headline number that traced to nothing.
    """
    import glob
    ns = []
    for f in sorted(glob.glob(os.path.join(RES, "*_results.json"))):
        ns.append(json.load(open(f))["N"])
    lo = f"{min(ns):,}".replace(",", "{,}")
    hi = f"{max(ns):,}".replace(",", "{,}")
    for name, body in (("main.tex", main_tex), ("workshop.tex", tex)):
        assert f"${lo}$--${hi}$" in body, (
            f"{name} must state the population range as {lo}-{hi}"
        )
        # reject every spelling: the math form, the plain-text form (a section heading used
        # "1,228--1,373" outside math mode and survived the first fix), and the bare digits
        for bad in ("1{,}373", "1,373", "1373"):
            assert bad not in body, f"{name} still contains the untraceable count 1,373 as {bad!r}"


def test_substrate_is_strictly_binary():
    """Outcome matrices must contain only 0/1. A non-binary cell means the harvest read the
    wrong column or a metric that is not accuracy, and every downstream statistic -- co-failure,
    the Rasch fit, the residual spectrum -- silently assumes binarity.

    Cheap to check, and it is the integrity property that the v2 parser's falsy-`or` bug would
    NOT have violated: that bug produced valid 0/1 values that were simply the wrong ones. So
    this test is a floor, not a proof of correctness.
    """
    np = pytest.importorskip("numpy")
    raw = os.path.join(ROOT, "substrate", "raw")
    if not os.path.isdir(raw):
        pytest.skip("substrate not present")
    checked = 0
    for bench in ("arc", "winogrande", "truthfulqa", "gsm8k", "hellaswag"):
        p = os.path.join(raw, f"{bench}.npz")
        if not os.path.exists(p):
            continue
        prim = np.load(p, allow_pickle=True)["prim"]
        bad = np.unique(prim[~np.isin(prim, (0, 1))])
        assert bad.size == 0, f"{bench}.npz has non-binary values: {bad[:5]}"
        checked += 1
    assert checked, "no substrate matrices found to check"
