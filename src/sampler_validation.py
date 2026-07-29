"""X6 -- is the curveball sampler actually uniform on the fiber?

WHY THIS MATTERS. "Exact" is the paper's central adjective, and it rests entirely on the claim
that curveball samples the uniform distribution over binary matrices with the observed row and
column margins. Carstens (2015, Phys. Rev. E 91:042812; erratum 94:039902, 2016) proved uniformity
but showed the chain must COUNT FAILED TRADES -- a proposal that cannot be executed still consumes
a step. A sampler that instead resamples until it finds a valid trade has a different transition
kernel and is not uniform.

Implementation note, checked by reading src/nullmodel.py: `curveball` draws all row pairs up front
and `continue`s on a failed trade, so a failure consumes one loop iteration rather than triggering
a resample. That is the correct behaviour. This script tests it empirically rather than by
inspection.

TWO TESTS
  V1. Exhaustive-fiber chi-square. On matrices small enough to enumerate every binary matrix with
      the given margins, run a long chain and chi-square the visit counts against uniform.
  V2. Gelman-Rubin on a real benchmark. Four dispersed chains, monitor the residual-correlation
      rms, report Rhat. Rhat <= 1.01 indicates the chains have mixed.

PRE-REGISTERED KILL CONDITION (written before execution, 2026-07-28)
--------------------------------------------------------------------
KV1. V1 must NOT reject uniformity at p < 0.01 on any test fiber. A rejection means the sampler is
     biased and every null in the paper is wrong; the word "exact" is removed and the numbers are
     recomputed with a validated sampler.
KV2. V2 must give Rhat <= 1.05 on every benchmark at the burn-in actually used in the paper
     (50 trades/N). Otherwise the reported nulls are not converged and burn-in must be increased.

Run: ./.venv/bin/python src/sampler_validation.py -> results/sampler_validation.json
"""
import json, itertools, os, sys
from collections import Counter
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nullmodel import curveball, fit_rasch, rasch_P, excess_gram

SUB = os.path.join(HERE, "..", "substrate", "raw")
RES = os.path.join(HERE, "..", "results")


def enumerate_fiber(r, c):
    """All binary matrices with row sums r and column sums c, by brute force over row patterns."""
    N, M = len(r), len(c)
    rows = [list(itertools.combinations(range(M), int(k))) for k in r]
    out = []

    def rec(i, colsum, acc):
        if i == N:
            if list(colsum) == list(c):
                out.append(np.array(acc, dtype=np.uint8))
            return
        # prune: remaining rows cannot supply more than this many to any column
        rem = N - i
        for pat in rows[i]:
            cs = colsum.copy()
            ok = True
            for j in pat:
                cs[j] += 1
                if cs[j] > c[j]:
                    ok = False
                    break
            if not ok:
                continue
            if any(c[j] - cs[j] > rem - 1 for j in range(M)):
                continue
            row = np.zeros(M, dtype=np.uint8)
            row[list(pat)] = 1
            acc.append(row)
            rec(i + 1, cs, acc)
            acc.pop()

    rec(0, np.zeros(M, dtype=int), [])
    return out


def chi2_p(chi2, df):
    """Survival function of chi-square via a Wilson-Hilferty normal approximation."""
    from math import erfc, sqrt
    if df <= 0:
        return 1.0
    x = (chi2 / df) ** (1.0 / 3.0)
    mu = 1.0 - 2.0 / (9.0 * df)
    sd = sqrt(2.0 / (9.0 * df))
    zscore = (x - mu) / sd
    return 0.5 * erfc(zscore / sqrt(2.0))


def v1_fiber_test(r, c, n_samples, trades_per_sample, seed):
    rng = np.random.default_rng(seed)
    fiber = enumerate_fiber(r, c)
    if len(fiber) < 4:
        return None
    key = {m.tobytes(): i for i, m in enumerate(fiber)}
    F0 = fiber[0]
    counts = Counter()
    X = np.array(F0, dtype=np.uint8)
    X = curveball(X, 500, rng)                       # burn-in
    for _ in range(n_samples):
        X = curveball(X, trades_per_sample, rng)
        counts[key[X.tobytes()]] += 1
    obs = np.array([counts.get(i, 0) for i in range(len(fiber))], dtype=float)
    exp = obs.sum() / len(fiber)
    chi2 = float(((obs - exp) ** 2 / exp).sum())
    df = len(fiber) - 1
    return {"rows": list(map(int, r)), "cols": list(map(int, c)),
            "fiber_size": len(fiber), "n_samples": int(obs.sum()),
            "chi2": chi2, "df": df, "p": chi2_p(chi2, df),
            "min_count": int(obs.min()), "max_count": int(obs.max()),
            "expected": float(exp)}


def v2_gelman_rubin(bench, n_chains=4, n_draws=25, burn_mult=50, thin_mult=5, seed=99):
    z = np.load(os.path.join(SUB, f"{bench}.npz"), allow_pickle=True)
    F = (1 - z["prim"]).astype(np.uint8)
    keep = (F.sum(1) > 0) & (F.sum(1) < F.shape[1])
    F = F[keep]
    ck = (F.sum(0) > 0) & (F.sum(0) < F.shape[0])
    F = F[:, ck]
    N = F.shape[0]
    a, b, _ = fit_rasch(F)
    P = rasch_P(a, b)
    iu = np.triu_indices(N, 1)

    def stat(X):
        D = excess_gram(X, P)
        d = np.sqrt(np.clip(np.diag(D).astype(np.float64), 1e-12, None))
        R = D.astype(np.float64) / d[:, None] / d[None, :]
        return float(np.sqrt((R[iu] ** 2).mean()))

    chains = []
    for ci in range(n_chains):
        rng = np.random.default_rng(seed + 1000 * ci)
        # dispersed starts: different burn-in lengths
        X = curveball(F, (burn_mult + 25 * ci) * N, rng)
        vals = []
        for _ in range(n_draws):
            X = curveball(X, thin_mult * N, rng)
            vals.append(stat(X))
        chains.append(vals)
        print(f"   chain {ci}: mean {np.mean(vals):.5f} sd {np.std(vals, ddof=1):.2e}", flush=True)

    A = np.array(chains)                       # n_chains x n_draws
    m, n = A.shape
    chain_means = A.mean(1)
    B = n * chain_means.var(ddof=1)
    W = A.var(1, ddof=1).mean()
    var_hat = (n - 1) / n * W + B / n
    rhat = float(np.sqrt(var_hat / W)) if W > 0 else float("nan")
    return {"bench": bench, "n_chains": m, "n_draws": n,
            "chain_means": chain_means.tolist(), "W": float(W), "B": float(B),
            "rhat": rhat, "KV2_pass": bool(rhat <= 1.05)}


def main():
    print("V1 -- exhaustive fiber chi-square")
    fibers = [
        ([2, 2, 2, 2], [2, 2, 2, 2]),
        ([3, 2, 2, 1], [2, 2, 2, 2]),
        ([3, 3, 2, 2, 2], [3, 3, 3, 3]),
        ([2, 3, 1, 2, 2], [2, 2, 2, 2, 2]),
    ]
    v1 = []
    for r, c in fibers:
        if sum(r) != sum(c):
            continue
        res = v1_fiber_test(r, c, n_samples=60000, trades_per_sample=8, seed=7)
        if res is None:
            continue
        v1.append(res)
        print(f"   r={res['rows']} c={res['cols']} |fiber|={res['fiber_size']:>5} "
              f"chi2={res['chi2']:8.2f} df={res['df']:>4} p={res['p']:.4f} "
              f"{'ok' if res['p'] >= 0.01 else 'REJECT'}", flush=True)

    print("\nV2 -- Gelman-Rubin across 4 dispersed chains")
    v2 = []
    for bch in ["arc", "winogrande", "truthfulqa", "gsm8k", "hellaswag"]:
        if not os.path.exists(os.path.join(SUB, f"{bch}.npz")):
            continue
        print(f"  [{bch}]", flush=True)
        r = v2_gelman_rubin(bch)
        v2.append(r)
        print(f"   Rhat = {r['rhat']:.5f}  {'PASS' if r['KV2_pass'] else 'FAIL'}", flush=True)

    kv1_fires = any(x["p"] < 0.01 for x in v1)
    kv2_fires = any(not x["KV2_pass"] for x in v2)
    out = {"V1_fiber_tests": v1, "V2_gelman_rubin": v2,
           "KV1_fires": bool(kv1_fires), "KV2_fires": bool(kv2_fires)}
    json.dump(out, open(os.path.join(RES, "sampler_validation.json"), "w"), indent=1)
    print(f"\nKV1 {'FIRES -- sampler is NOT uniform' if kv1_fires else 'survives -- uniformity not rejected'}")
    print(f"KV2 {'FIRES -- chains not converged' if kv2_fires else 'survives -- Rhat within tolerance'}")


if __name__ == "__main__":
    main()
