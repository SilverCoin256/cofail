"""W1 controls -- adversarial checks on the family-signal result before it is reported.

The headline (LOO 5-NN family accuracy 0.81 against a 0.29 permutation null) is a large effect,
and the project's standing rule is that a large effect is first a suspected bug. These are the
confounds a reviewer would name, each run as its own arm:

  A. accuracy-only        -- does raw model accuracy alone predict family that well? If so the
                             eigenvectors may just be re-encoding the row margin that conditioning
                             is supposed to have removed.
  B. raw-correlation      -- do the UNCONDITIONED correlation eigenvectors do just as well? If so,
                             the margin conditioning is not what is buying the signal.
  C. dedup 0.90           -- a stricter duplicate filter than the 0.95 used in the main run.
  D. per-family recall    -- is one large family carrying the whole result?
  E. k sensitivity        -- accuracy as a function of how many eigenvectors are used.

Run: python src/w1_controls.py [bench] -> results/w1_controls.json
"""
import json, os, sys
from collections import Counter
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nullmodel import curveball, fit_rasch, rasch_P, excess_gram
from dedup_sensitivity import family_of, dedup_keep
from w1_family_signal import residual_eigvecs, loo_knn_accuracy, TOP_FAMILIES, KNN, SEED

SUB = os.path.join(HERE, "..", "substrate", "raw")
RES = os.path.join(HERE, "..", "results")


def labelled(models, fams=None):
    f = np.array([family_of(m) for m in models])
    counts = Counter(x for x in f if x != "unattributed")
    keep = fams or [k for k, _ in counts.most_common(TOP_FAMILIES)]
    sel = np.isin(f, keep)
    return sel, f[sel], keep


def perm_ref(Z, y, rng, n=500):
    p = np.array([loo_knn_accuracy(Z, rng.permutation(y)) for _ in range(n)])
    return float(p.mean()), float(np.percentile(p, 95))


def std(Z):
    return (Z - Z.mean(0)) / (Z.std(0) + 1e-12)


def main(bench="arc"):
    rng = np.random.default_rng(SEED + 1)
    z = np.load(os.path.join(SUB, f"{bench}.npz"), allow_pickle=True)
    models = np.array([str(m) for m in z["models"]])
    F = (1 - z["prim"]).astype(np.uint8)
    keep = (F.sum(1) > 0) & (F.sum(1) < F.shape[1]); F, models = F[keep], models[keep]
    ck = (F.sum(0) > 0) & (F.sum(0) < F.shape[0]); F = F[:, ck]
    N, M = F.shape
    out = {"bench": bench, "N": int(N), "M": int(M), "seed": SEED + 1}

    V, w, edge, k, _, P = residual_eigvecs(F, 6, rng)
    k = max(k, 2)
    sel, y, keep_f = labelled(models)
    Zres = std(V[sel, :k])
    acc_res = loo_knn_accuracy(Zres, y)
    pm, p95 = perm_ref(Zres, y, rng)
    out["main"] = {"k": int(k), "acc": acc_res, "perm_mean": pm, "perm_p95": p95,
                   "n_labelled": int(sel.sum()), "families": keep_f}

    # --- A. accuracy-only ------------------------------------------------------
    acc_vec = std((1 - F).mean(1)[sel][:, None])
    a_acc = loo_knn_accuracy(acc_vec, y)
    a_pm, a_p95 = perm_ref(acc_vec, y, rng)
    out["A_accuracy_only"] = {"acc": a_acc, "perm_mean": a_pm, "perm_p95": a_p95,
                              "beats_perm": bool(a_acc > a_p95)}

    # A2. residual eigenvectors AFTER regressing model accuracy out of each loading
    x = (1 - F).mean(1)[sel]; x = (x - x.mean()) / (x.std() + 1e-12)
    Zadj = Zres - np.outer(x, (x @ Zres) / (x @ x))
    a2 = loo_knn_accuracy(std(Zadj), y)
    a2_pm, a2_p95 = perm_ref(std(Zadj), y, rng)
    out["A2_accuracy_regressed_out"] = {"acc": a2, "perm_mean": a2_pm, "perm_p95": a2_p95,
                                        "beats_perm": bool(a2 > a2_p95)}

    # --- B. raw (unconditioned) correlation eigenvectors ------------------------
    Fc = F.astype(np.float64)
    Fc = Fc - Fc.mean(1, keepdims=True)
    Craw = (Fc @ Fc.T) / M
    d = np.sqrt(np.clip(np.diag(Craw), 1e-12, None))
    Rraw = Craw / d[:, None] / d[None, :]
    wr, Vr = np.linalg.eigh(Rraw); Vr = Vr[:, ::-1]
    Zraw = std(Vr[sel, :k])
    b_acc = loo_knn_accuracy(Zraw, y)
    b_pm, b_p95 = perm_ref(Zraw, y, rng)
    out["B_raw_correlation"] = {"acc": b_acc, "perm_mean": b_pm, "perm_p95": b_p95,
                                "beats_perm": bool(b_acc > b_p95)}

    # --- C. dedup 0.90 ---------------------------------------------------------
    idx = dedup_keep((1 - F).astype(np.float32), 0.90)
    Vd, wd, ed, kd, _, _ = residual_eigvecs(F[idx], 6, rng)
    kd = max(kd, 2)
    seld, yd, _ = labelled(models[idx], keep_f)
    Zd = std(Vd[seld, :kd])
    c_acc = loo_knn_accuracy(Zd, yd)
    c_pm, c_p95 = perm_ref(Zd, yd, rng)
    out["C_dedup_0.90"] = {"N": int(len(idx)), "k": int(kd), "n_labelled": int(seld.sum()),
                           "acc": c_acc, "perm_mean": c_pm, "perm_p95": c_p95,
                           "beats_perm": bool(c_acc > c_p95)}

    # --- D. per-family recall --------------------------------------------------
    n = len(y)
    d2 = ((Zres[:, None, :] - Zres[None, :, :]) ** 2).sum(-1); np.fill_diagonal(d2, np.inf)
    nn = np.argsort(d2, axis=1)[:, :KNN]
    pred = np.array([Counter(y[r]).most_common(1)[0][0] for r in nn])
    out["D_per_family_recall"] = {
        f: {"n": int((y == f).sum()), "recall": float((pred[y == f] == f).mean())}
        for f in keep_f}

    # --- E. k sensitivity ------------------------------------------------------
    out["E_k_sensitivity"] = {
        str(kk): float(loo_knn_accuracy(std(V[sel, :kk]), y)) for kk in (1, 2, 3, 4, 6, 10, 20)}

    json.dump(out, open(os.path.join(RES, "w1_controls.json"), "w"), indent=1)
    m = out["main"]
    print(f"main   k={m['k']} n={m['n_labelled']} acc={m['acc']:.4f} perm={m['perm_mean']:.4f}")
    print(f"A  accuracy-only          acc={a_acc:.4f} perm={a_pm:.4f}  beats={out['A_accuracy_only']['beats_perm']}")
    print(f"A2 accuracy regressed out acc={a2:.4f} perm={a2_pm:.4f}  beats={out['A2_accuracy_regressed_out']['beats_perm']}")
    print(f"B  raw correlation        acc={b_acc:.4f} perm={b_pm:.4f}  beats={out['B_raw_correlation']['beats_perm']}")
    print(f"C  dedup 0.90 (N={len(idx)})   acc={c_acc:.4f} perm={c_pm:.4f}  beats={out['C_dedup_0.90']['beats_perm']}")
    print("D  per-family recall:", {k_: round(v['recall'], 3) for k_, v in out["D_per_family_recall"].items()})
    print("E  k sensitivity:", {k_: round(v, 3) for k_, v in out["E_k_sensitivity"].items()})


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "arc")
