"""W3 -- is the mean-level degeneracy decision-relevant, or only an identity?

Pre-registered in docs/PREREG_WORKSHOP_EXPERIMENTS.md (KW5/KW6) before this ran.

The EvoRobust short paper argues mean-level diversity metrics are degenerate and that margin
calibration fixes them. That is proved as an identity and shown observationally, but an identity
does not by itself demonstrate that any decision changes. This constructs two suites with KNOWN
ground truth, in the shape of a red-teaming evaluation where F[i,m]=1 means "probe m succeeded
against member i", and asks which metrics get the ordering right.

  Suite A -- genuinely diverse: members fail conditionally independently given the item; probe
             potency strongly heterogeneous, sd(logit) = 2.0.
  Suite B -- shared failure modes: members drawn in 5 clusters with shared modes; probe potency
             nearly homogeneous, sd(logit) = 0.15.

Ground truth: A is the diverse suite. A metric "gets it right" if it scores A as more diverse.

Run: python src/w3_diversity_decision.py -> results/w3_diversity_decision.json
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nullmodel import curveball, fit_rasch, rasch_P, excess_gram, mean_cofail

RES = os.path.join(HERE, "..", "results")

N_MEM, N_ITEM = 200, 500
N_NULL = 20
BURN, THIN = 50, 5
SEED = 20260903


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def suite_diverse(rng, n=N_MEM, m=N_ITEM, sd_item=2.0):
    """Conditionally independent given the item; strongly heterogeneous probe potency."""
    beta = rng.normal(0.0, sd_item, m)         # probe potency
    alpha = rng.normal(0.0, 0.6, n)            # member susceptibility
    return (rng.random((n, m)) < sigmoid(alpha[:, None] + beta[None, :])).astype(np.uint8)


def suite_shared_modes(rng, n=N_MEM, m=N_ITEM, g=5, sd_item=0.15, load=1.6):
    """Members in g clusters sharing failure modes; probe potency nearly homogeneous."""
    beta = rng.normal(0.0, sd_item, m)
    alpha = rng.normal(0.0, 0.6, n)
    grp = rng.integers(0, g, n)
    mode = rng.normal(0.0, 1.0, (g, m))        # each cluster's shared failure profile
    lin = alpha[:, None] + beta[None, :] + load * mode[grp]
    return (rng.random((n, m)) < sigmoid(lin)).astype(np.uint8)


def naive_metrics(F):
    N, M = F.shape
    p = F.mean(1)
    O = mean_cofail(F)
    # mean pairwise disagreement over ordered pairs = 2*pbar - 2*O   (Lemma 1)
    G = (F.astype(np.float64) @ F.astype(np.float64).T) / M
    iu = np.triu_indices(N, 1)
    disagree = float(((p[:, None] + p[None, :] - 2 * G)[iu]).mean())
    return {"double_fault_mean_cofail": float(O),
            "mean_pairwise_disagreement": disagree,
            "identity_check_2pbar_minus_2O": float(2 * p.mean() - 2 * O)}


def calibrated_metrics(F, rng):
    N, M = F.shape
    iu = np.triu_indices(N, 1)
    a, b, err = fit_rasch(F)
    P = rasch_P(a, b)

    def measure(X):
        D = excess_gram(np.ascontiguousarray(X, dtype=np.uint8), P)
        d = np.sqrt(np.clip(np.diag(D).astype(np.float64), 1e-12, None))
        R = D.astype(np.float64) / d[:, None] / d[None, :]
        w = np.linalg.eigvalsh(R)[::-1]
        return float(np.sqrt((R[iu] ** 2).mean())), w

    rms_o, w_o = measure(F)
    X = curveball(F, BURN * N, rng)
    rms_n, edges = [], []
    for _ in range(N_NULL):
        X = curveball(X, THIN * N, rng)
        r, w = measure(X)
        rms_n.append(r); edges.append(float(w[0]))
    edge = float(np.mean(edges))
    return {"rms_R_obs": rms_o, "rms_R_null": float(np.mean(rms_n)),
            "rms_ratio": float(rms_o / np.mean(rms_n)),
            "null_spectral_edge": edge, "n_eigen_above_edge": int((w_o > edge).sum()),
            "rasch_margin_error": float(err)}


def main():
    rng = np.random.default_rng(SEED)
    A = suite_diverse(rng)
    B = suite_shared_modes(rng)
    out = {"seed": SEED, "n_members": N_MEM, "n_items": N_ITEM, "n_null": N_NULL, "suites": {}}
    for name, F, truth in (("A_genuinely_diverse", A, "diverse"),
                           ("B_shared_failure_modes", B, "not_diverse")):
        keep = (F.sum(1) > 0) & (F.sum(1) < F.shape[1]); Fk = F[keep]
        ck = (Fk.sum(0) > 0) & (Fk.sum(0) < Fk.shape[0]); Fk = Fk[:, ck]
        d = {"ground_truth": truth, "N": int(Fk.shape[0]), "M": int(Fk.shape[1])}
        d.update(naive_metrics(Fk))
        d.update(calibrated_metrics(Fk, rng))
        out["suites"][name] = d
        print(f"{name}: double-fault={d['double_fault_mean_cofail']:.4f} "
              f"disagreement={d['mean_pairwise_disagreement']:.4f} "
              f"rms ratio={d['rms_ratio']:.2f}x dims>edge={d['n_eigen_above_edge']}", flush=True)

    a, b = out["suites"]["A_genuinely_diverse"], out["suites"]["B_shared_failure_modes"]
    # naive reading: HIGHER disagreement (or LOWER double-fault) = "more diverse"
    naive_says_A_more_diverse = bool(a["mean_pairwise_disagreement"] > b["mean_pairwise_disagreement"])
    naive_df_says_A_more_diverse = bool(a["double_fault_mean_cofail"] < b["double_fault_mean_cofail"])
    # calibrated reading: LOWER excess over the exact null = more diverse
    calib_says_A_more_diverse = bool(a["rms_ratio"] < b["rms_ratio"])
    out["verdict"] = {
        "naive_disagreement_correct": naive_says_A_more_diverse,
        "naive_double_fault_correct": naive_df_says_A_more_diverse,
        "calibrated_correct": calib_says_A_more_diverse,
        "KW5_degeneracy_is_decision_relevant": bool(
            not naive_says_A_more_diverse or not naive_df_says_A_more_diverse),
        "KW6_correction_fails": bool(not calib_says_A_more_diverse),
    }
    json.dump(out, open(os.path.join(RES, "w3_diversity_decision.json"), "w"), indent=1)
    print("\nverdict:", json.dumps(out["verdict"], indent=1))
    if out["verdict"]["KW6_correction_fails"]:
        print("KW6 FIRED: the calibrated statistic also gets the ordering wrong.")
    elif not out["verdict"]["KW5_degeneracy_is_decision_relevant"]:
        print("KW5 FIRED: naive metrics get the ordering right; degeneracy not decision-relevant here.")
    else:
        print("Naive metrics invert the true ordering; the calibrated statistic recovers it.")


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# Appended after the 2x2 objection: the headline comparison varies TWO factors at
# once (difficulty heterogeneity AND shared modes), which is the point -- that is
# what makes the naive metric fail -- but a reviewer is entitled to ask which
# factor does the work. This grid crosses them.
def grid(rng):
    cells = {}
    for het, sd in (("heterogeneous", 2.0), ("homogeneous", 0.15)):
        for shared, load in (("independent", 0.0), ("shared_modes", 1.6)):
            F = (suite_diverse(rng, sd_item=sd) if load == 0.0
                 else suite_shared_modes(rng, sd_item=sd, load=load))
            keep = (F.sum(1) > 0) & (F.sum(1) < F.shape[1]); F = F[keep]
            ck = (F.sum(0) > 0) & (F.sum(0) < F.shape[0]); F = F[:, ck]
            d = {"difficulty": het, "structure": shared}
            d.update(naive_metrics(F)); d.update(calibrated_metrics(F, rng))
            cells[f"{het}|{shared}"] = d
            print(f"  {het:<14} {shared:<12} double-fault={d['double_fault_mean_cofail']:.4f} "
                  f"disagreement={d['mean_pairwise_disagreement']:.4f} "
                  f"rms ratio={d['rms_ratio']:.2f}x dims>edge={d['n_eigen_above_edge']}", flush=True)
    return cells


if __name__ == "__main__" and "--grid" in sys.argv:
    rng2 = np.random.default_rng(SEED + 7)
    print("2x2 grid: difficulty heterogeneity x shared failure modes")
    cells = grid(rng2)
    path = os.path.join(RES, "w3_diversity_decision.json")
    out = json.load(open(path))
    out["grid_2x2"] = cells
    # within each difficulty regime, does the naive metric rank independent as more diverse?
    ver = {}
    for het in ("heterogeneous", "homogeneous"):
        ind, sh = cells[f"{het}|independent"], cells[f"{het}|shared_modes"]
        ver[het] = {
            "naive_disagreement_correct": bool(ind["mean_pairwise_disagreement"]
                                               > sh["mean_pairwise_disagreement"]),
            "naive_double_fault_correct": bool(ind["double_fault_mean_cofail"]
                                               < sh["double_fault_mean_cofail"]),
            "calibrated_correct": bool(ind["rms_ratio"] < sh["rms_ratio"]),
        }
    out["grid_verdict"] = ver
    json.dump(out, open(path, "w"), indent=1)
    print("\ngrid verdict:", json.dumps(ver, indent=1))
