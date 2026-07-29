"""Does ranking models by ACCURACY -- what every leaderboard and practitioner does -- select for
margin-conditioned redundancy?

MOTIVATION. In the panel experiment, panels built as "top-k by accuracy" showed mean pairwise
conditioned correlation RISING steeply with k (-0.01 at k=3 to +0.31 at k=15) while diversity-built
panels stayed near zero. If that reflects real structure rather than an artifact of selecting a
narrow accuracy band, it is the correctly-measured version of the claim that frontier models are
converging -- and it is actionable: leaderboard-ranked selection concentrates correlated failure.

THE CONFOUND THIS EXPERIMENT EXISTS TO KILL. Taking the top-k by accuracy also takes a NARROW
accuracy band. Any narrow band might mechanically show elevated conditioned correlation, in which
case "the top models are redundant" would be a statement about banding, not about the top.

CONTROL: a sliding accuracy window of FIXED WIDTH swept across the whole accuracy range. If mean
conditioned R is elevated only at the high-accuracy end, the effect is real and specific. If every
narrow window shows the same elevation, the effect is an artifact of band width and the claim dies.

PRE-REGISTERED KILL CONDITION (written before execution, 2026-07-28)
--------------------------------------------------------------------
KR1. Sweep a fixed-width accuracy window across each benchmark. Let rho be the Spearman
     correlation between window-centre accuracy and mean within-window conditioned R. The claim
     SURVIVES only if rho > 0 with the top decile's mean R exceeding the median window's mean R,
     on at least 4 of the 5 benchmarks. Otherwise KR1 FIRES and the claim is dropped.

KR2. Null calibration. The same sweep is run on margin-preserving (curveball) replicates. The
     observed high-accuracy elevation must exceed what the null produces; if the null reproduces
     the same rising profile, the effect is a margin artifact and the claim dies regardless of KR1.

Run: ./.venv/bin/python src/rank_redundancy.py [bench ...] -> results/rank_redundancy.json
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nullmodel import curveball, fit_rasch, rasch_P, excess_gram

SUB = os.path.join(HERE, "..", "substrate", "raw")
RES = os.path.join(HERE, "..", "results")

WINDOW_FRAC = 0.10      # window holds 10% of the models, swept by accuracy rank
N_WINDOWS = 25
N_NULL = 12


def resid_corr(F, P):
    D = excess_gram(F, P)
    d = np.sqrt(np.clip(np.diag(D).astype(np.float64), 1e-12, None))
    R = D.astype(np.float64) / d[:, None] / d[None, :]
    np.fill_diagonal(R, 0.0)
    return R


def window_profile(R, acc_order, n_win, w):
    """Mean pairwise R inside a fixed-width window slid along the accuracy ranking.

    acc_order is model indices sorted by accuracy DESCENDING, so window 0 is the top models.
    """
    N = len(acc_order)
    starts = np.linspace(0, N - w, n_win).astype(int)
    out = []
    for s in starts:
        idx = acc_order[s:s + w]
        ii = np.ix_(idx, idx)
        out.append(float(R[ii].sum() / (w * (w - 1))))
    return starts, np.array(out)


def spearman(x, y):
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    return float(np.corrcoef(rx, ry)[0, 1])


def run(bench, rng):
    z = np.load(os.path.join(SUB, f"{bench}.npz"), allow_pickle=True)
    acc = z["prim"]
    F = (1 - acc).astype(np.uint8)
    keep = (F.sum(1) > 0) & (F.sum(1) < F.shape[1])
    F = F[keep]
    ck = (F.sum(0) > 0) & (F.sum(0) < F.shape[0])
    F = F[:, ck]
    N, M = F.shape

    model_acc = 1.0 - F.mean(1)
    order = np.argsort(-model_acc)          # descending accuracy
    w = max(int(N * WINDOW_FRAC), 10)

    a, b, err = fit_rasch(F)
    P = rasch_P(a, b)
    R = resid_corr(F, P)
    starts, prof = window_profile(R, order, N_WINDOWS, w)
    centre_acc = np.array([model_acc[order[s:s + w]].mean() for s in starts])

    rho = spearman(centre_acc, prof)
    top_R, med_R = float(prof[0]), float(np.median(prof))

    # --- KR2: same sweep under the margin-preserving null -------------------------------
    X = curveball(np.array(F, dtype=np.uint8), 50 * N, rng)
    null_profs = []
    for _ in range(N_NULL):
        X = curveball(X, 5 * N, rng)
        Rn = resid_corr(X, P)
        # null models keep the SAME margins, so the accuracy ordering is unchanged
        _, pn = window_profile(Rn, order, N_WINDOWS, w)
        null_profs.append(pn)
    null_profs = np.array(null_profs)
    null_mean, null_sd = null_profs.mean(0), null_profs.std(0, ddof=1)
    null_rho = float(np.mean([spearman(centre_acc, p) for p in null_profs]))

    z_top = float((top_R - null_mean[0]) / max(null_sd[0], 1e-12))
    excess_prof = (prof - null_mean).tolist()

    return {
        "bench": bench, "N": int(N), "M": int(M), "window": int(w),
        "rasch_fit_err": float(err),
        "window_centre_acc": centre_acc.tolist(),
        "observed_profile": prof.tolist(),
        "null_profile_mean": null_mean.tolist(),
        "null_profile_sd": null_sd.tolist(),
        "excess_profile": excess_prof,
        "spearman_acc_vs_R": rho, "spearman_under_null": null_rho,
        "top_window_R": top_R, "median_window_R": med_R,
        "top_window_z_vs_null": z_top,
        "KR1_bench_pass": bool(rho > 0 and top_R > med_R),
    }


def main(benches):
    rng = np.random.default_rng(20260728)
    res = []
    for bch in benches:
        p = os.path.join(SUB, f"{bch}.npz")
        if not os.path.exists(p):
            print(f"[{bch}] missing substrate, skipping", flush=True)
            continue
        r = run(bch, rng)
        res.append(r)
        print(f"[{bch}] N={r['N']} rho={r['spearman_acc_vs_R']:+.3f} "
              f"(null rho {r['spearman_under_null']:+.3f})  "
              f"top {r['top_window_R']:+.4f} vs median {r['median_window_R']:+.4f}  "
              f"z_top={r['top_window_z_vs_null']:+.1f}  "
              f"{'PASS' if r['KR1_bench_pass'] else 'fail'}", flush=True)

    n_pass = sum(r["KR1_bench_pass"] for r in res)
    out = {"window_frac": WINDOW_FRAC, "n_windows": N_WINDOWS, "n_null": N_NULL,
           "benchmarks": res, "KR1_n_pass": n_pass, "KR1_fires": bool(n_pass < 4)}
    json.dump(out, open(os.path.join(RES, "rank_redundancy.json"), "w"), indent=1)
    print(f"\nKR1 {'FIRES -- claim dropped' if n_pass < 4 else 'survives'} ({n_pass}/{len(res)})")


if __name__ == "__main__":
    main(sys.argv[1:] or ["arc", "winogrande", "truthfulqa", "gsm8k", "hellaswag"])
