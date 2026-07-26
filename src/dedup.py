"""E5 -- is the N_eff collapse just near-duplicate models?

The archive is full of merges, re-uploads and light fine-tunes. If N_eff collapses only because
many rows of F are near-identical, the finding is about leaderboard hygiene, not about the
ecosystem. This tests that directly: cluster models by agreement on the item set, keep one
representative per cluster, and recompute the null-calibrated N_eff on the deduplicated matrix.

Reported at several thresholds so the conclusion cannot rest on one arbitrary cutoff.

Run: python dedup.py [bench ...]   ->  results/<bench>_dedup.json
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nullmodel import curveball, fit_rasch, rasch_P, excess_gram, n_eff_from_excess
from experiments import load, BURN_MULT, THIN_MULT

RES = os.path.join(HERE, "..", "results")
os.makedirs(RES, exist_ok=True)


def agreement_matrix(F, block=512):
    """Fraction of items on which each pair of models gives the SAME outcome."""
    X = np.ascontiguousarray(F, dtype=np.float32)
    N, M = X.shape
    Y = 1.0 - X
    A = np.empty((N, N), dtype=np.float32)
    for s in range(0, N, block):
        e = min(s + block, N)
        A[s:e] = (X[s:e] @ X.T + Y[s:e] @ Y.T) / M
    return A


def cluster_reps(A, thresh):
    """Greedy single-link-ish clustering: a model joins an existing cluster if it agrees with
    that cluster's representative at >= thresh. Returns indices of representatives."""
    N = A.shape[0]
    order = np.argsort(-A.sum(1))          # most central first, deterministic
    reps, taken = [], np.zeros(N, dtype=bool)
    for i in order:
        if taken[i]:
            continue
        reps.append(int(i))
        taken |= (A[i] >= thresh)
        taken[i] = True
    return sorted(reps)


def neff_calibrated(F, rng, R=40):
    a, b, err = fit_rasch(F)
    P = rasch_P(a, b)
    obs, _ = n_eff_from_excess(excess_gram(F, P))
    N = F.shape[0]
    X = curveball(np.array(F, dtype=np.uint8), BURN_MULT * N, rng)
    v = []
    for _ in range(R):
        X = curveball(X, THIN_MULT * N, rng)
        v.append(n_eff_from_excess(excess_gram(X, P))[0])
    v = np.asarray(v)
    sd = v.std(ddof=1)
    return {"N": int(N), "N_eff": float(obs), "null_mean": float(v.mean()),
            "null_sd": float(sd), "SES": float((obs - v.mean()) / sd) if sd else float("nan"),
            "ratio": float(obs / v.mean()), "rasch_margin_error": err, "R": R}


def run(bench, seed=20260726):
    rng = np.random.default_rng(seed)
    F, models, dates, _ = load(bench)
    A = agreement_matrix(F)
    iu = np.triu_indices(F.shape[0], 1)
    off = A[iu]
    out = {"bench": bench, "N_full": int(F.shape[0]), "M": int(F.shape[1]),
           "agreement_mean": float(off.mean()), "agreement_p99": float(np.quantile(off, 0.99)),
           "agreement_max": float(off.max()),
           "pairs_above_0.99": int((off >= 0.99).sum()),
           "pairs_above_0.95": int((off >= 0.95).sum()),
           "n_pairs": int(off.size), "levels": {}}
    print(f"\n===== {bench} dedup =====", flush=True)
    print(f"  pairwise agreement: mean {off.mean():.4f}  p99 {np.quantile(off,0.99):.4f} "
          f"max {off.max():.4f}", flush=True)
    print(f"  identical-ish pairs: >=0.99 {(off>=0.99).sum()}  >=0.95 {(off>=0.95).sum()} "
          f"of {off.size}", flush=True)

    out["levels"]["full"] = neff_calibrated(F, rng)
    r = out["levels"]["full"]
    print(f"  full   N={r['N']:5d}  N_eff={r['N_eff']:7.1f}  null={r['null_mean']:7.1f}"
          f"  ratio={r['ratio']:.3f}", flush=True)

    for th in (0.99, 0.97, 0.95, 0.90):
        reps = cluster_reps(A, th)
        if len(reps) < 100:
            print(f"  thr={th}: only {len(reps)} representatives, skipped", flush=True)
            continue
        Fd = F[reps]
        ck = (Fd.sum(0) > 0) & (Fd.sum(0) < Fd.shape[0])
        Fd = Fd[:, ck]
        r = neff_calibrated(Fd, rng)
        r["threshold"] = th
        r["n_removed"] = int(F.shape[0] - len(reps))
        out["levels"][f"dedup_{th}"] = r
        print(f"  thr={th}  N={r['N']:5d} (-{r['n_removed']:4d})  N_eff={r['N_eff']:7.1f}"
              f"  null={r['null_mean']:7.1f}  ratio={r['ratio']:.3f}  SES={r['SES']:.1f}",
              flush=True)

    json.dump(out, open(os.path.join(RES, f"{bench}_dedup.json"), "w"), indent=1)
    return out


if __name__ == "__main__":
    for b in (sys.argv[1:] or ["arc"]):
        run(b)
