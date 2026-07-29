"""CONTROL for the rank-redundancy finding: is top-of-leaderboard redundancy just duplicate
fine-tunes of the same base model?

THE ATTACK THIS ANSWERS. rank_redundancy.py shows mean margin-conditioned residual correlation is
2.1-6.8x higher in the top accuracy decile than at the median, with a flat (~0.000) profile under
the margin-preserving null on all five benchmarks. The first thing a reviewer will say is: the top
of an open leaderboard is full of near-identical fine-tunes of whatever base model was strongest
that month, so of course they agree. The paper's existing dedup analysis is GLOBAL; it does not
address concentration specifically at the top, which is exactly where duplicates would pool.

DESIGN. Re-run the identical accuracy-window sweep on progressively deduplicated populations:
drop one member of every pair whose raw agreement exceeds a threshold, sweeping the threshold from
0.99 (exact clones only) down to 0.90 (aggressive). The Rasch fit and the conditioned correlation
are recomputed from scratch on each surviving population, so nothing is carried over.

PRE-REGISTERED KILL CONDITION (written before execution, 2026-07-28)
--------------------------------------------------------------------
KD1. The finding SURVIVES only if, at the aggressive 0.95 threshold, the top-window conditioned R
     remains at least 1.5x the median-window value on at least 4 of 5 benchmarks. If deduplication
     collapses the gradient, the effect is a duplicate-fine-tune artifact and the central positive
     claim must be withdrawn.

Run: ./.venv/bin/python src/rank_redundancy_control.py -> results/rank_redundancy_control.json
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nullmodel import fit_rasch, rasch_P, excess_gram
from rank_redundancy import resid_corr, window_profile, spearman, WINDOW_FRAC, N_WINDOWS

SUB = os.path.join(HERE, "..", "substrate", "raw")
RES = os.path.join(HERE, "..", "results")

THRESHOLDS = [1.01, 0.99, 0.97, 0.95, 0.90]     # 1.01 = keep everything (baseline)


def dedup_keep(A, thresh):
    """Greedy: walk models in descending accuracy, keep a model unless it agrees with an
    already-kept model at or above `thresh`. Keeping the more accurate member is the choice a
    practitioner would make, and is the conservative one here -- it retains the top of the
    leaderboard, which is the region under test."""
    N, M = A.shape
    acc = A.mean(1)
    order = np.argsort(-acc)
    kept = []
    Ak = A.astype(np.float32)
    for i in order:
        if not kept:
            kept.append(int(i))
            continue
        K = np.array(kept)
        agree = (Ak[i] @ Ak[K].T + (1 - Ak[i]) @ (1 - Ak[K]).T) / M
        if agree.max() < thresh:
            kept.append(int(i))
    return np.array(sorted(kept))


def run(bench):
    z = np.load(os.path.join(SUB, f"{bench}.npz"), allow_pickle=True)
    acc_raw = z["prim"]
    F0 = (1 - acc_raw).astype(np.uint8)
    keep = (F0.sum(1) > 0) & (F0.sum(1) < F0.shape[1])
    F0 = F0[keep]
    ck = (F0.sum(0) > 0) & (F0.sum(0) < F0.shape[0])
    F0 = F0[:, ck]
    A0 = (1 - F0).astype(np.float32)

    rows = []
    for th in THRESHOLDS:
        idx = np.arange(A0.shape[0]) if th > 1.0 else dedup_keep(A0, th)
        F = F0[idx]
        cc = (F.sum(0) > 0) & (F.sum(0) < F.shape[0])
        F = F[:, cc]
        rk = (F.sum(1) > 0) & (F.sum(1) < F.shape[1])
        F = F[rk]
        N = F.shape[0]
        if N < 120:
            continue
        model_acc = 1.0 - F.mean(1)
        order = np.argsort(-model_acc)
        w = max(int(N * WINDOW_FRAC), 10)
        a, b, _ = fit_rasch(F)
        R = resid_corr(F, rasch_P(a, b))
        _, prof = window_profile(R, order, N_WINDOWS, w)
        centre = np.array([model_acc[order[s:s + w]].mean()
                           for s in np.linspace(0, N - w, N_WINDOWS).astype(int)])
        top, med = float(prof[0]), float(np.median(prof))
        rows.append({
            "threshold": th, "N_kept": int(N), "N_removed": int(A0.shape[0] - N),
            "top_window_R": top, "median_window_R": med,
            "ratio": float(top / med) if abs(med) > 1e-9 else float("nan"),
            "spearman": spearman(centre, prof),
        })
        print(f"  thr={th:<5} N={N:>5} (-{A0.shape[0]-N:>4})  top={top:+.4f} "
              f"med={med:+.4f}  ratio={rows[-1]['ratio']:>6.2f}x  rho={rows[-1]['spearman']:+.3f}",
              flush=True)
    return rows


def main(benches):
    out = {}
    for bch in benches:
        if not os.path.exists(os.path.join(SUB, f"{bch}.npz")):
            continue
        print(f"[{bch}]", flush=True)
        out[bch] = run(bch)

    # KD1 evaluated at the 0.95 threshold
    passes = {}
    for bch, rows in out.items():
        r = next((x for x in rows if x["threshold"] == 0.95), None)
        passes[bch] = bool(r and np.isfinite(r["ratio"]) and r["ratio"] >= 1.5)
    n_pass = sum(passes.values())
    res = {"thresholds": THRESHOLDS, "per_bench": out,
           "KD1_pass_at_0.95": passes, "KD1_n_pass": n_pass,
           "KD1_fires": bool(n_pass < 4)}
    json.dump(res, open(os.path.join(RES, "rank_redundancy_control.json"), "w"), indent=1)
    print(f"\nKD1 {'FIRES -- duplicate artifact, claim withdrawn' if n_pass < 4 else 'survives'} "
          f"({n_pass}/{len(out)} benchmarks keep ratio >= 1.5 after 0.95 dedup)")


if __name__ == "__main__":
    main(sys.argv[1:] or ["arc", "winogrande", "truthfulqa", "gsm8k", "hellaswag"])
