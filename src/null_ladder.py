"""X3 -- the null ladder. Does the conclusion depend on which null you choose, and at what rung
does the observed excess disappear?

This is the experiment the paper's whole argument presupposes and never runs. Jo, Garg & Raghavan
argue monoculture inference is null-dependent; the paper replies that one rung of the ladder is
canonical. Neither side has published the ladder itself. Here it is.

FIXED STATISTIC, VARYING NULL. The statistic is held constant throughout: rms over model pairs of
the margin-conditioned residual correlation, where the conditioning matrix is a 1PL Rasch fit to
whichever matrix is being measured. Only the null DISTRIBUTION changes between rungs. This isolates
the effect of null choice, which is the quantity in dispute.

RUNGS (increasing richness; each is fitted to the observed data, then sampled from)
  R0 iid Bernoulli        one global rate; conditions on nothing
  R1 row margins only     model accuracy preserved, item difficulty destroyed
  R2 column margins only  item difficulty preserved, model accuracy destroyed
  R3 exact fixed-fixed    both margins; the paper's null (curveball)
  R4 2PL                  per-item discrimination as well as difficulty
  R5..R8 MIRT q=2,3,4,5   q-dimensional compensatory latent ability

PRE-REGISTERED KILL CONDITION (written before execution, 2026-07-28)
--------------------------------------------------------------------
KL1. If the observed statistic lies inside the R3 null band, the paper has no effect at its own
     null and everything collapses. (Not expected -- prior runs put it far outside -- but stated
     so the ladder is a real test rather than a demonstration.)
KL2. The paper's substantive claim requires that the excess SURVIVE the richest rung tested. If
     the observed rms falls inside the MIRT-q band for some q <= 5, then the honest conclusion is
     "the data are q-dimensional IRT", not "the ecosystem is concentrated", and the paper must say
     so as its headline rather than in Limitations.
KL3. If R3 gives materially the same answer as R1 or R2 alone, the "jointly sufficient" argument
     has no empirical content and the canonicality framing is dropped.

Run: ./.venv/bin/python src/null_ladder.py [bench ...] -> results/null_ladder.json
"""
import json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nullmodel import curveball, fit_rasch, rasch_P, excess_gram

SUB = os.path.join(HERE, "..", "substrate", "raw")
RES = os.path.join(HERE, "..", "results")
N_REP = 8
MIRT_Q = [2, 3, 4, 5]


def trim(F):
    F = np.ascontiguousarray(F, dtype=np.uint8)
    keep = (F.sum(1) > 0) & (F.sum(1) < F.shape[1])
    F = F[keep]
    ck = (F.sum(0) > 0) & (F.sum(0) < F.shape[0])
    return F[:, ck]


def stat_rms(F):
    """rms residual correlation, with the 1PL conditioning refitted to F itself."""
    F = trim(F)
    if F.shape[0] < 10:
        return float("nan")
    a, b, _ = fit_rasch(F)
    D = excess_gram(F, rasch_P(a, b))
    d = np.sqrt(np.clip(np.diag(D).astype(np.float64), 1e-12, None))
    R = D.astype(np.float64) / d[:, None] / d[None, :]
    iu = np.triu_indices(F.shape[0], 1)
    return float(np.sqrt((R[iu] ** 2).mean()))


# ------------------------------------------------------------------ null families

def fit_2pl(F, iters=250, lr=0.5):
    """P_im = sigmoid(alpha_m * (theta_i - beta_m)), fitted by projected gradient ascent on the
    Bernoulli log-likelihood. alpha is kept positive by optimising log-alpha. float32 for the same
    memory reason as fit_mirt."""
    N, M = F.shape
    Y = F.astype(np.float32)
    theta = np.zeros(N)
    beta = np.zeros(M)
    la = np.zeros(M)
    for t in range(iters):
        alpha = np.exp(la)
        Z = alpha[None, :] * (theta[:, None] - beta[None, :])
        P = 1.0 / (1.0 + np.exp(-Z))
        E = Y - P
        g_theta = (E * alpha[None, :]).sum(1) / M
        g_beta = -(E * alpha[None, :]).sum(0) / N
        g_la = (E * Z).sum(0) / N
        theta += lr * g_theta * M / max(M, 1) * 4
        beta += lr * g_beta * 4
        la += lr * g_la * 0.5
        la = np.clip(la, -1.5, 1.5)
        theta -= theta.mean()
    alpha = np.exp(la)
    return 1.0 / (1.0 + np.exp(-(alpha[None, :] * (theta[:, None] - beta[None, :]))))


def fit_mirt(F, q, iters=400, lr=0.35, seed=0):
    """P_im = sigmoid(theta_i . a_m + b_m), q-dimensional compensatory MIRT, full-batch gradient
    ascent. float32 throughout: at 1362 x 9404 a single float64 temporary is 102 MB and the naive
    version allocated several per iteration, which OOM-killed the first run on HellaSwag."""
    rng = np.random.default_rng(seed)
    N, M = F.shape
    Y = F.astype(np.float32)
    m = np.clip(Y.mean(0), 1e-3, 1 - 1e-3)
    b = np.log(m / (1 - m)).astype(np.float32)
    th = rng.normal(0, 0.1, (N, q)).astype(np.float32)
    A = rng.normal(0, 0.1, (M, q)).astype(np.float32)
    E = np.empty_like(Y)
    for t in range(iters):
        np.matmul(th, A.T, out=E)
        E += b[None, :]
        np.negative(E, out=E)
        np.exp(E, out=E)
        E += 1.0
        np.reciprocal(E, out=E)      # E now holds P
        np.subtract(Y, E, out=E)     # E now holds the residual
        th += (lr * 8 / M) * (E @ A)
        A += (lr * 8 / N) * (E.T @ th)
        b += (lr * 4) * E.mean(0)
        th -= th.mean(0, keepdims=True)
    np.matmul(th, A.T, out=E)
    E += b[None, :]
    np.negative(E, out=E)
    np.exp(E, out=E)
    E += 1.0
    np.reciprocal(E, out=E)
    return E


def sample_bernoulli(P, rng):
    return (rng.random(P.shape) < P).astype(np.uint8)


def permute_rows(F, rng):
    X = F.copy()
    for i in range(X.shape[0]):
        rng.shuffle(X[i])
    return X


def permute_cols(F, rng):
    X = F.copy()
    for j in range(X.shape[1]):
        c = X[:, j].copy()
        rng.shuffle(c)
        X[:, j] = c
    return X


# ------------------------------------------------------------------ driver

def run(bench, rng):
    z = np.load(os.path.join(SUB, f"{bench}.npz"), allow_pickle=True)
    F = trim((1 - z["prim"]).astype(np.uint8))
    N, M = F.shape
    obs = stat_rms(F)
    print(f"[{bench}] N={N} M={M} observed rms = {obs:.4f}", flush=True)

    rungs = {}

    def record(name, vals, note=""):
        v = np.asarray([x for x in vals if np.isfinite(x)], dtype=float)
        if v.size == 0:
            rungs[name] = {"mean": float("nan"), "sd": float("nan"), "n": 0, "note": note}
            return
        lo, hi = np.percentile(v, [2.5, 97.5]) if v.size >= 4 else (v.min(), v.max())
        rungs[name] = {"mean": float(v.mean()), "sd": float(v.std(ddof=1) if v.size > 1 else 0.0),
                       "ci95": [float(lo), float(hi)], "n": int(v.size),
                       "excess_ratio": float(obs / v.mean()) if v.mean() > 0 else float("nan"),
                       "observed_inside_band": bool(v.min() <= obs <= v.max()), "note": note}
        print(f"   {name:<22} null {v.mean():.4f} +-{v.std(ddof=1) if v.size>1 else 0:.4f}  "
              f"obs/null = {obs/v.mean():>7.2f}x  "
              f"{'OBS INSIDE BAND' if rungs[name]['observed_inside_band'] else ''}", flush=True)

    p_bar = float(F.mean())
    record("R0_iid_bernoulli",
           [stat_rms(sample_bernoulli(np.full((N, M), p_bar), rng)) for _ in range(4)])
    record("R1_row_margins_only", [stat_rms(permute_rows(F, rng)) for _ in range(4)])
    record("R2_col_margins_only", [stat_rms(permute_cols(F, rng)) for _ in range(4)])

    X = curveball(F, 50 * N, rng)
    vals = []
    for _ in range(N_REP):
        X = curveball(X, 5 * N, rng)
        vals.append(stat_rms(X))
    record("R3_exact_fixed_fixed", vals, "the paper's null")

    t0 = time.time()
    P2 = fit_2pl(F)
    record("R4_2pl", [stat_rms(sample_bernoulli(P2, rng)) for _ in range(4)],
           f"2PL fit {time.time()-t0:.0f}s")

    for q in MIRT_Q:
        t0 = time.time()
        Pq = fit_mirt(F, q, seed=q)
        record(f"R{4+q}_mirt_q{q}", [stat_rms(sample_bernoulli(Pq, rng)) for _ in range(4)],
               f"MIRT q={q} fit {time.time()-t0:.0f}s")

    inside = [k for k, v in rungs.items() if v.get("observed_inside_band")]
    return {"bench": bench, "N": int(N), "M": int(M), "observed_rms": obs,
            "rungs": rungs, "rungs_containing_observed": inside}


def main(benches):
    rng = np.random.default_rng(20260728)
    res = []
    path = os.path.join(RES, "null_ladder.json")
    for bch in benches:
        if not os.path.exists(os.path.join(SUB, f"{bch}.npz")):
            continue
        try:
            res.append(run(bch, rng))
        except Exception as e:                       # one benchmark must not lose the others
            print(f"[{bch}] FAILED: {type(e).__name__}: {e}", flush=True)
            res.append({"bench": bch, "error": f"{type(e).__name__}: {e}",
                        "rungs": {}, "rungs_containing_observed": []})
        # write after every benchmark; the first run of this script died on the largest matrix
        # and lost all prior work because results were only serialised at the end
        json.dump({"partial": True, "benchmarks": res}, open(path, "w"), indent=1)

    kl1 = any("R3_exact_fixed_fixed" in r["rungs_containing_observed"] for r in res)
    kl2 = any(any(k.startswith("R") and "mirt" in k for k in r["rungs_containing_observed"])
              for r in res)
    out = {"n_replicates": N_REP, "mirt_q": MIRT_Q, "benchmarks": res,
           "KL1_fires": bool(kl1), "KL2_fires": bool(kl2)}
    json.dump(out, open(os.path.join(RES, "null_ladder.json"), "w"), indent=1)
    print(f"\nKL1 {'FIRES -- no effect at the paper own null' if kl1 else 'survives'}")
    print(f"KL2 {'FIRES -- a MIRT rung explains the observed value' if kl2 else 'survives'}")
    for r in res:
        if r["rungs_containing_observed"]:
            print(f"  [{r['bench']}] observed lies inside: {', '.join(r['rungs_containing_observed'])}")


if __name__ == "__main__":
    main(sys.argv[1:] or ["arc", "winogrande", "truthfulqa", "gsm8k", "hellaswag"])
