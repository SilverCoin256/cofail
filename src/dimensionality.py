"""How many latent ability dimensions does it take to explain the residual correlation?

This is the identification question the paper concedes in Limitations and never answers. The
partial null-ladder run (src/null_ladder.py) suggested the answer is small -- a 2-to-4 dimensional
compensatory MIRT reproduced the observed residual-correlation rms almost exactly -- but that run
had two defects that make its numbers unusable:

  1. NUMERICAL DIVERGENCE. Unclipped logits overflowed in float32, and Winogrande's q=2,3,4 fits
     returned rms > 1, which is impossible for a correlation. Fixed here by clipping the logit and
     monitoring the log-likelihood, with divergence reported rather than silently returned.
  2. NO HELD-OUT EVALUATION. The MIRT was fitted to the same matrix whose residual correlation it
     was then asked to reproduce. A sufficiently flexible low-rank model reproduces any second-
     order statistic in-sample, so an in-sample match is not evidence that q dimensions suffice.

HELD-OUT DESIGN. Items are split 50/50.
  - Fit the q-dimensional model on TRAIN items -> person abilities theta (N x q).
  - Freeze theta. Fit only the item parameters on TEST items.
  - Generate synthetic TEST-item data from the frozen-theta model, and compare its residual
    correlation rms against the observed rms ON THE SAME TEST ITEMS.
A model that only memorised train items cannot match on test items, so a match here is evidence
about dimensionality rather than about flexibility. Held-out Bernoulli log-likelihood on test
items is reported alongside, as the standard model-selection criterion.

PRE-REGISTERED KILL CONDITION (written before execution, 2026-07-28)
--------------------------------------------------------------------
KQ1. Let q* be the smallest q whose held-out synthetic rms falls within 10% of the observed
     held-out rms. If q* <= 5 on a majority of benchmarks, the observed residual correlation is
     explained by a low-dimensional ability structure, and the paper's headline must become
     "open-model failure needs about q* ability dimensions, not one" rather than any statement
     about ecosystem concentration or monoculture.
KQ2. Held-out log-likelihood must improve from q=1 to q=q*. If it does not, the extra dimensions
     are not real structure and KQ1's match is an artifact.

Run: ./.venv/bin/python src/dimensionality.py [bench ...] -> results/dimensionality.json
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nullmodel import fit_rasch, rasch_P, excess_gram

SUB = os.path.join(HERE, "..", "substrate", "raw")
RES = os.path.join(HERE, "..", "results")
QS = [1, 2, 3, 4, 5, 6]
CLIP = 30.0


def sigmoid(Z):
    np.clip(Z, -CLIP, CLIP, out=Z)
    return 1.0 / (1.0 + np.exp(-Z))


def rms_resid(F):
    """rms residual correlation with the 1PL conditioning refitted to F -- the paper's statistic."""
    F = np.ascontiguousarray(F, dtype=np.uint8)
    keep = (F.sum(1) > 0) & (F.sum(1) < F.shape[1])
    F = F[keep]
    ck = (F.sum(0) > 0) & (F.sum(0) < F.shape[0])
    F = F[:, ck]
    if F.shape[0] < 10 or F.shape[1] < 10:
        return float("nan")
    a, b, _ = fit_rasch(F)
    D = excess_gram(F, rasch_P(a, b))
    d = np.sqrt(np.clip(np.diag(D).astype(np.float64), 1e-12, None))
    R = D.astype(np.float64) / d[:, None] / d[None, :]
    iu = np.triu_indices(F.shape[0], 1)
    return float(np.sqrt((R[iu] ** 2).mean()))


def loglik(Y, P):
    P = np.clip(P, 1e-6, 1 - 1e-6)
    return float((Y * np.log(P) + (1 - Y) * np.log(1 - P)).mean())


def fit_theta_and_items(Y, q, iters=800, lr=4.0, seed=0):
    """Joint fit of theta (N x q), item loadings A (M x q) and intercepts b (M,).

    Gradients are normalised by the dimension being summed over -- these are gradients of the MEAN
    log-likelihood, not the sum. The first version omitted this, so a single theta update was of
    order M times too large and every fit diverged to NaN on every benchmark.
    """
    rng = np.random.default_rng(seed)
    N, M = Y.shape
    m = np.clip(Y.mean(0), 1e-3, 1 - 1e-3)
    b = np.log(m / (1 - m))
    th = rng.normal(0, 0.05, (N, q))
    A = rng.normal(0, 0.05, (M, q))
    best, best_state = -np.inf, (th.copy(), A.copy(), b.copy())
    for t in range(iters):
        P = sigmoid(th @ A.T + b[None, :])
        E = Y - P
        th += lr * (E @ A) / M
        A += lr * (E.T @ th) / N
        b += lr * E.mean(0)
        th -= th.mean(0, keepdims=True)
        np.clip(th, -1e6, 1e6, out=th)                 # keep th**2 below the float64 overflow
        s = np.sqrt((th ** 2).mean() + 1e-12)          # identification: fix the theta scale
        th /= s
        A *= s
        if t % 50 == 49:
            ll = loglik(Y, sigmoid(th @ A.T + b[None, :]))
            if not np.isfinite(ll):
                break
            if ll > best:
                best, best_state = ll, (th.copy(), A.copy(), b.copy())
    return best_state


def fit_items_given_theta(Y, th, iters=600, lr=4.0, seed=1):
    """Item parameters for held-out items with abilities frozen. Same gradient scaling."""
    rng = np.random.default_rng(seed)
    N, M = Y.shape
    q = th.shape[1]
    m = np.clip(Y.mean(0), 1e-3, 1 - 1e-3)
    b = np.log(m / (1 - m))
    A = rng.normal(0, 0.05, (M, q))
    for _ in range(iters):
        P = sigmoid(th @ A.T + b[None, :])
        E = Y - P
        A += lr * (E.T @ th) / N
        b += lr * E.mean(0)
    return A, b


def run(bench, rng):
    z = np.load(os.path.join(SUB, f"{bench}.npz"), allow_pickle=True)
    F = (1 - z["prim"]).astype(np.uint8)
    keep = (F.sum(1) > 0) & (F.sum(1) < F.shape[1])
    F = F[keep]
    ck = (F.sum(0) > 0) & (F.sum(0) < F.shape[0])
    F = F[:, ck]
    N, M = F.shape

    idx = rng.permutation(M)
    tr, te = np.sort(idx[: M // 2]), np.sort(idx[M // 2:])
    Ytr = F[:, tr].astype(np.float64)
    Yte = F[:, te].astype(np.float64)
    obs_te = rms_resid(F[:, te])
    print(f"[{bench}] N={N} M={M} (train {len(tr)} / test {len(te)} items)  "
          f"observed held-out rms = {obs_te:.4f}", flush=True)

    rows = []
    for q in QS:
        th, _, _ = fit_theta_and_items(Ytr, q, seed=q)
        A_te, b_te = fit_items_given_theta(Yte, th, seed=100 + q)
        P_te = sigmoid(th @ A_te.T + b_te[None, :])
        ll = loglik(Yte, P_te)
        if not np.isfinite(ll):
            print(f"   q={q}: DIVERGED", flush=True)
            rows.append({"q": q, "diverged": True})
            continue
        syn = [rms_resid((rng.random(P_te.shape) < P_te).astype(np.uint8)) for _ in range(4)]
        syn_m = float(np.mean(syn))
        rel = abs(syn_m - obs_te) / obs_te
        rows.append({"q": q, "diverged": False, "heldout_loglik": ll,
                     "synthetic_rms_mean": syn_m, "synthetic_rms_sd": float(np.std(syn, ddof=1)),
                     "rel_gap_to_observed": float(rel), "within_10pct": bool(rel <= 0.10)})
        print(f"   q={q}: held-out LL={ll:.5f}  synthetic rms={syn_m:.4f}  "
              f"gap={rel*100:5.1f}%  {'MATCH' if rel <= 0.10 else ''}", flush=True)

    ok = [r for r in rows if not r.get("diverged") and r.get("within_10pct")]
    qstar = min((r["q"] for r in ok), default=None)
    lls = {r["q"]: r["heldout_loglik"] for r in rows if not r.get("diverged")}
    kq2 = bool(qstar is not None and 1 in lls and lls.get(qstar, -1e9) > lls[1])
    return {"bench": bench, "N": int(N), "M": int(M),
            "n_train_items": int(len(tr)), "n_test_items": int(len(te)),
            "observed_heldout_rms": obs_te, "by_q": rows,
            "q_star": qstar, "KQ2_loglik_improves": kq2}


def main(benches):
    rng = np.random.default_rng(20260728)
    res = []
    path = os.path.join(RES, "dimensionality.json")
    for bch in benches:
        if not os.path.exists(os.path.join(SUB, f"{bch}.npz")):
            continue
        try:
            res.append(run(bch, rng))
        except Exception as e:
            print(f"[{bch}] FAILED: {type(e).__name__}: {e}", flush=True)
            res.append({"bench": bch, "error": f"{type(e).__name__}: {e}"})
        json.dump({"partial": True, "q_values": QS, "benchmarks": res}, open(path, "w"), indent=1)

    qs = [r.get("q_star") for r in res if r.get("q_star") is not None]
    kq1 = bool(len(qs) > len(res) / 2 and all(q <= 5 for q in qs))
    out = {"q_values": QS, "benchmarks": res, "q_stars": qs,
           "KQ1_low_dimensional_explanation": kq1,
           "KQ2_all_loglik_improve": bool(all(r.get("KQ2_loglik_improves")
                                              for r in res if "q_star" in r))}
    json.dump(out, open(path, "w"), indent=1)
    print(f"\nq* per benchmark: "
          f"{ {r['bench']: r.get('q_star') for r in res if 'bench' in r} }")
    print(f"KQ1 {'CONFIRMED -- a low-dimensional ability structure explains the residual'
                 if kq1 else 'not confirmed'}")
    print(f"KQ2 held-out log-likelihood improves over q=1: {out['KQ2_all_loglik_improve']}")


if __name__ == "__main__":
    main(sys.argv[1:] or ["arc", "winogrande", "truthfulqa", "gsm8k", "hellaswag"])
