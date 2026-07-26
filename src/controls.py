"""Positive and negative controls for the estimator.

The confirmatory run reports a large NEGATIVE effect on real data (observed dispersion of
pairwise co-failure below the margin-preserving null). A result that size is more likely an
implementation error than a discovery, so the estimator is validated on matrices whose
structure is known by construction before any real-data claim is made.

  C1 negative : matrix drawn FROM a Rasch margin model. The Rasch sufficient statistics are
                the margins, so conditional on them the law is uniform over the margin class
                -- exactly the curveball target. Expect SES ~ 0.
  C2 positive : eight latent model families sharing failure modes. Expect SES >> 0.
  C3 positive : half the models are exact clones of the other half. Expect SES > 0.
  C4 negative : column-shuffled real data (destroys model-side structure, keeps item
                difficulty). Expect SES ~ 0 on real margins.

Run: python controls.py   ->  results/controls.json
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nullmodel import curveball, var_cofail
RES = os.path.join(HERE, "..", "results")
os.makedirs(RES, exist_ok=True)


def ses(F, rng, R=120, burn=50, thin=5):
    N = F.shape[0]
    T = var_cofail(F)
    X = curveball(np.array(F, dtype=np.uint8), burn * N, rng)
    v = []
    for _ in range(R):
        X = curveball(X, thin * N, rng)
        v.append(var_cofail(X))
    v = np.asarray(v)
    sd = v.std(ddof=1)
    return {"T_observed": float(T), "T_null_mean": float(v.mean()), "T_null_sd": float(sd),
            "SES": float((T - v.mean()) / sd) if sd > 0 else float("nan"),
            "ratio": float(T / v.mean()), "R": R}


def main(N=500, M=900, seed=0):
    rng = np.random.default_rng(seed)
    out = {"N": N, "M": M, "seed": seed}

    a = rng.normal(0, 1.2, N)
    b = rng.normal(0, 1.5, M)
    P = 1 / (1 + np.exp(-(a[:, None] + b[None, :])))
    F1 = (rng.random((N, M)) < P).astype(np.uint8)
    out["C1_negative_rasch_generated"] = ses(F1, rng)

    fam = rng.integers(0, 8, N)
    sh = rng.normal(0, 1.6, (8, M))
    P2 = 1 / (1 + np.exp(-(a[:, None] + b[None, :] + sh[fam])))
    out["C2_positive_eight_families"] = ses((rng.random((N, M)) < P2).astype(np.uint8), rng)

    F3 = F1.copy()
    F3[N // 2:] = F3[:N // 2]
    out["C3_positive_exact_clones"] = ses(F3, rng)

    try:
        z = np.load(os.path.join(HERE, "..", "substrate", "raw", "arc.npz"), allow_pickle=True)
        Fr = (1 - z["prim"]).astype(np.uint8)
        Fs = np.stack([Fr[rng.permutation(Fr.shape[0]), m] for m in range(Fr.shape[1])], axis=1)
        out["C4_negative_column_shuffled_real"] = ses(Fs, rng, R=60)
    except Exception as e:
        out["C4_negative_column_shuffled_real"] = {"error": f"{type(e).__name__}: {e}"}

    json.dump(out, open(os.path.join(RES, "controls.json"), "w"), indent=1)
    for k, v in out.items():
        if isinstance(v, dict) and "SES" in v:
            print(f"  {k:38s} SES={v['SES']:+8.2f}  ratio={v['ratio']:.4f}")
    return out


if __name__ == "__main__":
    main()
