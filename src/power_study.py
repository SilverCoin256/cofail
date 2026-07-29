"""X4 -- what can the exact conditional test actually detect?

THE OBJECTION. Colwell & Winkler (1984, "A null model for null models in biogeography", ch. 20 in
*Ecological Communities: Conceptual Issues and the Evidence*, Princeton UP, 344-359) named the
Narcissus effect: a null model that conditions on statistics into which the process of interest
has already leaked will absorb that process and report nothing. If open models share training data
they share WHICH ITEMS ARE HARD -- and that is precisely what the item margins encode. Conditioning
on item margins may therefore condition away a leading signature of monoculture by construction.

The paper reports effect sizes against one null and never characterises the null's blind spots.
This script does. It plants known structure at controlled strength and measures detection power.

THREE PLANTED ALTERNATIVES
  A. Shared failure modes. g latent groups, each with its own per-item offset of magnitude s.
     Models within a group fail together beyond what ability and difficulty predict.
     Expectation: detectable, with power rising in s. This is the alternative the test is for.
  B. Shared difficulty only. Every model draws from the SAME item-difficulty profile, differing
     only in ability. This is the strongest form of "all models find the same things hard".
     Expectation: power = the nominal false-positive rate, BY CONSTRUCTION -- alternative B *is*
     the null. Reported to quantify the Narcissus blind spot rather than to discover it.
  C. Partial copying. Each model copies a reference model's response with probability c, else
     answers per its own Rasch draw. Interpolates from the null (c=0) to exact clones (c=1).
     Expectation: a detection threshold in c; the question is where it sits.

PRE-REGISTERED KILL CONDITION (written before execution, 2026-07-28)
--------------------------------------------------------------------
KP1. The instrument is USABLE only if power against alternative A reaches >= 0.8 at a strength
     that produces a residual-correlation rms no larger than the value observed on real data
     (0.10-0.29). If it takes implausibly strong planted structure to reach 0.8, the test is
     underpowered for the regime it is applied in and the paper must say so.
KP2. Power against alternative B must be reported as the blind spot it is, in the abstract, not
     in Limitations. This is not a pass/fail condition -- it is a disclosure requirement, recorded
     here so it cannot be quietly dropped later.
KP3. The detection threshold in c for alternative C must be reported. If the test only detects
     copying above c = 0.5, it cannot see realistic fine-tune relatedness and the paper's
     population-level claims must be scoped accordingly.

Run: ./.venv/bin/python src/power_study.py -> results/power_study.json
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nullmodel import curveball, fit_rasch, rasch_P, excess_gram

RES = os.path.join(HERE, "..", "results")
N, M = 400, 700           # tractable but realistic aspect ratio
N_TRIALS = 20             # planted datasets per condition
N_NULL = 15               # curveball replicates per dataset
ALPHA = 0.05

# Threshold estimation. The first version took the empirical 0.95 quantile of 10 null replicates,
# which interpolates between the 9th and 10th order statistics and is far too noisy: the s=0 and
# c=0 conditions -- which ARE the null and must therefore reject at the nominal rate -- came out at
# power 0.20, i.e. a false-positive rate four times alpha. That was an artifact of the estimator,
# not anti-conservatism of the test. The null distribution of the rms statistic is tight and close
# to normal, so a parametric threshold from the same replicates is far more stable at this budget.
# The s=0 and c=0 rows are retained as the calibration check on this choice.
Z_ALPHA = 1.6449          # one-sided normal quantile at ALPHA = 0.05


def rms_stat(F):
    F = np.ascontiguousarray(F, dtype=np.uint8)
    keep = (F.sum(1) > 0) & (F.sum(1) < F.shape[1])
    F = F[keep]
    ck = (F.sum(0) > 0) & (F.sum(0) < F.shape[0])
    F = F[:, ck]
    if F.shape[0] < 10:
        return float("nan"), None
    a, b, _ = fit_rasch(F)
    D = excess_gram(F, rasch_P(a, b))
    d = np.sqrt(np.clip(np.diag(D).astype(np.float64), 1e-12, None))
    R = D.astype(np.float64) / d[:, None] / d[None, :]
    iu = np.triu_indices(F.shape[0], 1)
    return float(np.sqrt((R[iu] ** 2).mean())), F


def detect(F, rng):
    """One-sided test at ALPHA: is the observed rms above the null's upper quantile?"""
    obs, Ft = rms_stat(F)
    if Ft is None or not np.isfinite(obs):
        return None
    Nn = Ft.shape[0]
    X = curveball(Ft, 40 * Nn, rng)
    vals = []
    for _ in range(N_NULL):
        X = curveball(X, 5 * Nn, rng)
        v, _ = rms_stat(X)
        vals.append(v)
    vals = np.asarray(vals)
    thresh = float(vals.mean() + Z_ALPHA * vals.std(ddof=1))
    return {"obs": obs, "null_mean": float(vals.mean()), "null_sd": float(vals.std(ddof=1)),
            "thresh": thresh, "detected": bool(obs > thresh)}


def base_params(rng):
    theta = rng.normal(0, 1.2, N)
    beta = rng.normal(0, 1.5, M)
    return theta, beta


def gen_A(rng, g, s):
    theta, beta = base_params(rng)
    grp = rng.integers(0, g, N)
    shared = rng.normal(0, 1.0, (g, M))
    Z = theta[:, None] - beta[None, :] + s * shared[grp]
    return (rng.random((N, M)) < 1 / (1 + np.exp(-Z))).astype(np.uint8)


def gen_B(rng):
    """Shared difficulty only: identical item difficulties, ability varies. This IS the null."""
    theta, beta = base_params(rng)
    Z = theta[:, None] - beta[None, :]
    return (rng.random((N, M)) < 1 / (1 + np.exp(-Z))).astype(np.uint8)


def gen_C(rng, c):
    theta, beta = base_params(rng)
    P = 1 / (1 + np.exp(-(theta[:, None] - beta[None, :])))
    F = (rng.random((N, M)) < P).astype(np.uint8)
    ref = F[0].copy()
    copy_mask = rng.random((N, M)) < c
    F = np.where(copy_mask, ref[None, :], F).astype(np.uint8)
    return F


def power_for(gen, label, rng):
    det, obss = [], []
    for _ in range(N_TRIALS):
        F = gen(rng)
        r = detect(F, rng)
        if r is None:
            continue
        det.append(r["detected"])
        obss.append(r["obs"])
    p = float(np.mean(det)) if det else float("nan")
    print(f"   {label:<34} power={p:.2f}  mean rms={np.mean(obss):.4f}  (n={len(det)})",
          flush=True)
    return {"condition": label, "power": p, "n_trials": len(det),
            "mean_observed_rms": float(np.mean(obss)) if obss else float("nan")}


def main():
    rng = np.random.default_rng(20260728)
    out = {"N": N, "M": M, "n_trials": N_TRIALS, "n_null": N_NULL, "alpha": ALPHA}

    print("Alternative A -- shared failure modes (the alternative the test is designed for)")
    A = []
    for g in (4, 8):
        for s in (0.0, 0.15, 0.3, 0.5, 0.8, 1.2):
            A.append({**power_for(lambda r, g=g, s=s: gen_A(r, g, s),
                                  f"A g={g} s={s}", rng), "g": g, "s": s})
    out["alt_A_shared_failure_modes"] = A

    print("\nAlternative B -- shared item difficulty only (the Narcissus blind spot)")
    out["alt_B_shared_difficulty"] = power_for(lambda r: gen_B(r),
                                               "B (identical difficulty profile)", rng)

    print("\nAlternative C -- partial copying of a reference model")
    C = []
    for c in (0.0, 0.05, 0.1, 0.2, 0.35, 0.5):
        C.append({**power_for(lambda r, c=c: gen_C(r, c), f"C c={c}", rng), "c": c})
    out["alt_C_partial_copying"] = C

    # KP1: smallest planted rms at which power >= 0.8 for alternative A
    hits = [a for a in A if a["power"] >= 0.8]
    kp1_rms = min((a["mean_observed_rms"] for a in hits), default=None)
    out["KP1_min_rms_at_power_0.8"] = kp1_rms
    out["KP1_usable"] = bool(kp1_rms is not None and kp1_rms <= 0.29)
    thr = [c for c in C if c["power"] >= 0.8]
    out["KP3_copy_detection_threshold"] = (min(c["c"] for c in thr) if thr else None)
    out["KP2_blind_spot_power"] = out["alt_B_shared_difficulty"]["power"]

    # Calibration check: the s=0 and c=0 conditions are draws from the null, so their "power" is
    # the empirical false-positive rate and must sit near ALPHA. If it does not, the threshold
    # estimator is miscalibrated and every power number above is suspect.
    fp = [a["power"] for a in A if a["s"] == 0.0] + [c["power"] for c in C if c["c"] == 0.0]
    out["calibration_false_positive_rate"] = float(np.mean(fp))
    out["calibration_ok"] = bool(abs(np.mean(fp) - ALPHA) <= 0.10)
    print(f"\ncalibration: empirical false-positive rate at the null conditions = "
          f"{np.mean(fp):.3f} (nominal {ALPHA}) -> "
          f"{'ok' if out['calibration_ok'] else 'MISCALIBRATED, power numbers unreliable'}")

    json.dump(out, open(os.path.join(RES, "power_study.json"), "w"), indent=1)
    print(f"\nKP1: power>=0.8 for alternative A first reached at planted rms "
          f"{kp1_rms if kp1_rms is not None else 'NEVER'} "
          f"(real data sits at 0.10-0.29) -> {'usable' if out['KP1_usable'] else 'UNDERPOWERED'}")
    print(f"KP2: power against the shared-difficulty alternative = "
          f"{out['KP2_blind_spot_power']:.2f} (nominal alpha = {ALPHA}) -- the blind spot")
    print(f"KP3: copying detected from c >= {out['KP3_copy_detection_threshold']}")


if __name__ == "__main__":
    main()
