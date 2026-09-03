"""W1 -- does the margin-conditioned residual spectrum carry model-family information?

Pre-registered in docs/PREREG_WORKSHOP_EXPERIMENTS.md (KW1/KW2/KW3) before this ran.

The ATTRIB short paper poses this as an open question. This answers it: take the top-k
eigenvectors of the residual correlation matrix R (k = number of eigenvalues above the exact
null's spectral edge), label models by base family with the coarse name-string matcher, and ask
whether family is recoverable from the loadings.

Run: python src/w1_family_signal.py [bench] -> results/w1_family_signal.json
"""
import json, os, sys
from collections import Counter
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nullmodel import curveball, fit_rasch, rasch_P, excess_gram
from dedup_sensitivity import family_of, dedup_keep

SUB = os.path.join(HERE, "..", "substrate", "raw")
RES = os.path.join(HERE, "..", "results")

N_PERM = 1000
N_EDGE_NULL = 6      # curveball replicates used to locate the null spectral edge
KNN = 5
TOP_FAMILIES = 5
SEED = 20260903


def residual_eigvecs(F, n_edge_null, rng):
    """Top eigenvectors of R, and how many eigenvalues clear the exact null's spectral edge."""
    N, M = F.shape
    a, b, err = fit_rasch(F)
    P = rasch_P(a, b)

    def R_of(X):
        D = excess_gram(np.ascontiguousarray(X, dtype=np.uint8), P)
        d = np.sqrt(np.clip(np.diag(D).astype(np.float64), 1e-12, None))
        return D.astype(np.float64) / d[:, None] / d[None, :]

    R = R_of(F)
    w, V = np.linalg.eigh(R)
    w, V = w[::-1], V[:, ::-1]

    X = curveball(F, 50 * N, rng)
    edges = []
    for _ in range(n_edge_null):
        X = curveball(X, 5 * N, rng)
        edges.append(float(np.linalg.eigvalsh(R_of(X))[-1]))
    edge = float(np.mean(edges))
    k = int((w > edge).sum())
    return V, w, edge, k, float(err), P


def loo_knn_accuracy(Z, y, k=KNN):
    """Leave-one-out k-NN accuracy in standardised loading space, Euclidean."""
    n = len(y)
    d2 = ((Z[:, None, :] - Z[None, :, :]) ** 2).sum(-1)
    np.fill_diagonal(d2, np.inf)
    nn = np.argsort(d2, axis=1)[:, :k]
    pred = np.array([Counter(y[row]).most_common(1)[0][0] for row in nn])
    return float((pred == y).mean())


def evaluate(F, models, tag, rng, n_perm=N_PERM):
    V, w, edge, k, fit_err, P = residual_eigvecs(F, N_EDGE_NULL, rng)
    k = max(k, 2)
    fams = np.array([family_of(m) for m in models])
    counts = Counter(f for f in fams if f != "unattributed")
    keep_f = [f for f, _ in counts.most_common(TOP_FAMILIES)]
    sel = np.isin(fams, keep_f)
    y = fams[sel]
    Z = V[sel, :k]
    Z = (Z - Z.mean(0)) / (Z.std(0) + 1e-12)

    acc = loo_knn_accuracy(Z, y)
    perm = np.empty(n_perm)
    for i in range(n_perm):
        perm[i] = loo_knn_accuracy(Z, rng.permutation(y))
    maj = float(Counter(y).most_common(1)[0][1] / len(y))
    p_emp = float((1 + (perm >= acc).sum()) / (n_perm + 1))

    out = {
        "tag": tag, "N": int(F.shape[0]), "M": int(F.shape[1]),
        "rasch_margin_error": fit_err,
        "n_eigen_above_edge": int((w > edge).sum()), "k_used": int(k),
        "null_spectral_edge": edge,
        "families_used": keep_f, "n_models_labelled": int(sel.sum()),
        "family_counts": {f: int(counts[f]) for f in keep_f},
        "loo_knn_accuracy": acc,
        "perm_mean": float(perm.mean()), "perm_sd": float(perm.std()),
        "perm_p95": float(np.percentile(perm, 95)),
        "perm_max": float(perm.max()),
        "p_permutation": p_emp,
        "majority_class_rate": maj,
        "excess_over_perm_mean": float(acc - perm.mean()),
        "KW1_signal_detected": bool(acc > np.percentile(perm, 95)),
    }
    return out, sel, y, k


def main(bench="arc"):
    rng = np.random.default_rng(SEED)
    z = np.load(os.path.join(SUB, f"{bench}.npz"), allow_pickle=True)
    models = np.array([str(m) for m in z["models"]])
    F = (1 - z["prim"]).astype(np.uint8)
    keep = (F.sum(1) > 0) & (F.sum(1) < F.shape[1])
    F, models = F[keep], models[keep]
    ck = (F.sum(0) > 0) & (F.sum(0) < F.shape[0])
    F = F[:, ck]
    print(f"[{bench}] population N={F.shape[0]} M={F.shape[1]}", flush=True)

    # --- arm 1: real data, real labels (primary, KW1)
    real, sel, y, k = evaluate(F, models, "real_full", rng)
    print(f"  REAL   k={real['k_used']} n_labelled={real['n_models_labelled']} "
          f"acc={real['loo_knn_accuracy']:.4f} perm={real['perm_mean']:.4f}"
          f"+-{real['perm_sd']:.4f} p95={real['perm_p95']:.4f} "
          f"majority={real['majority_class_rate']:.4f} p={real['p_permutation']:.4f}", flush=True)

    # --- arm 2: exact-null calibration (KW3) -- curveball replicate, real labels
    Xn = curveball(F, 50 * F.shape[0], rng)
    null_arm, _, _, _ = evaluate(Xn, models, "curveball_replicate", rng, n_perm=300)
    print(f"  NULL   acc={null_arm['loo_knn_accuracy']:.4f} "
          f"perm={null_arm['perm_mean']:.4f} p={null_arm['p_permutation']:.4f}", flush=True)

    # --- arm 3: deduplicated at 0.95 (KW2)
    A = (1 - F).astype(np.float32)
    idx = dedup_keep(A, 0.95)
    dd, _, _, _ = evaluate(F[idx], models[idx], "dedup_0.95", rng, n_perm=500)
    print(f"  DEDUP  N={dd['N']} acc={dd['loo_knn_accuracy']:.4f} "
          f"perm={dd['perm_mean']:.4f} p={dd['p_permutation']:.4f}", flush=True)

    verdict = {
        "KW1_signal_detected": real["KW1_signal_detected"],
        "KW2_survives_dedup": bool(dd["KW1_signal_detected"]),
        "KW3_null_arm_at_chance": bool(not null_arm["KW1_signal_detected"]),
    }
    verdict["reportable"] = bool(verdict["KW3_null_arm_at_chance"])
    out = {"bench": bench, "seed": SEED, "n_perm": N_PERM, "knn": KNN,
           "arms": {"real_full": real, "curveball_replicate": null_arm, "dedup_0.95": dd},
           "verdict": verdict}
    json.dump(out, open(os.path.join(RES, "w1_family_signal.json"), "w"), indent=1)
    print("\nVERDICT:", json.dumps(verdict), flush=True)
    if not verdict["KW3_null_arm_at_chance"]:
        print("KW3 FIRED: pipeline manufactures signal under the exact null. Nothing reportable.")
    elif not verdict["KW1_signal_detected"]:
        print("KW1 FIRED: no detectable family signal. Report the negative result.")
    elif not verdict["KW2_survives_dedup"]:
        print("KW2 FIRED: family signal is a near-duplicate artifact.")
    else:
        print("Family signal detected, survives deduplication, null arm at chance.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "arc")
