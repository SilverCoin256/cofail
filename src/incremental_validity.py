"""DECISIVE TEST: does margin-conditioned diversity have INCREMENTAL predictive validity for
ensemble accuracy, over and above member accuracy and the naive diversity measure?

WHY THIS REPLACES selection_killtest.py
---------------------------------------
The selection experiment nominally passed KS1 (conditioned-diversity panels beat naive-diversity
panels at 4/6 sizes) but FIRED KS2: the conditioned panels also had higher mean member accuracy
at every single size, so the vote-accuracy win is confounded with simply picking better models.
That experiment therefore cannot establish the claim, and is retained only as a record.

This is the design the ensemble-diversity literature actually uses (Kuncheva & Whitaker 2003,
Machine Learning 51(2):181-207, regress ensemble accuracy on diversity measures): sample many
panels, measure ensemble accuracy, and ask what each diversity statistic explains AFTER the
member-accuracy effect is removed.

The comparison is between two diversity statistics computed on the SAME panels:
  - DISAGREEMENT: mean pairwise raw disagreement. One of Kuncheva & Whitaker's ten measures.
  - DOUBLE-FAULT:  mean pairwise co-failure. Also one of their ten -- and the exact quantity the
                   paper's Lemma 1 proves is a deterministic function of item margins.
  - COND-R:        mean pairwise margin-conditioned residual correlation (this work).

PRE-REGISTERED KILL CONDITION (written before execution, 2026-07-28)
--------------------------------------------------------------------
KI1. Fit nested OLS models predicting panel vote accuracy on held-out items:
       M0: ~ mean_member_acc + panel_size
       M1: M0 + disagreement + double_fault      (the classical diversity measures)
       M2: M1 + cond_R                           (this work's measure)
     The claim SURVIVES only if the partial F-test of M2 over M1 is significant at p<0.001 AND
     delta-R^2(M2 - M1) >= 0.01. Otherwise KI1 FIRES: the conditioned measure adds nothing the
     classical measures do not already provide, and the "better diversity metric" spine is dead.

KI2. Sign check. cond_R must enter with a NEGATIVE coefficient (more conditioned redundancy ->
     worse ensemble). A significant POSITIVE coefficient refutes the mechanism even if KI1 passes.

KI3. Degeneracy corroboration, independent of the above. Lemma 1 predicts double_fault is a
     function of item margins alone and so should carry NO panel-level information about which
     models were chosen once member accuracy is controlled. Report its partial contribution.

LEAKAGE GUARD: all panel predictors (member accuracy, all three diversity statistics, the Rasch
fit) are computed on the SEL item half. Vote accuracy is measured on the disjoint EVAL half.

Run: ./.venv/bin/python src/incremental_validity.py [n_panels]
  -> results/incremental_validity.json
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nullmodel import fit_rasch, rasch_P, excess_gram
from harvest_responses import recover_gold, SENTINEL

SUB = os.path.join(HERE, "..", "substrate", "raw")
RES = os.path.join(HERE, "..", "results")

PANEL_SIZES = [3, 5, 7, 9, 11, 15, 21]


def majority_vote_acc(choice_eval, gold_eval, subset, rng):
    sub = choice_eval[subset]
    K = max(int(sub.max()) + 1, 1)
    counts = np.zeros((K, sub.shape[1]), dtype=np.int16)
    for c in range(K):
        counts[c] = (sub == c).sum(0)
    best = counts.max(0)
    tie = counts == best[None, :]
    pick = (rng.random(counts.shape) * tie).argmax(0)
    return float(((pick == gold_eval) & (best > 0)).mean())


def ols(X, y):
    """Return (beta, r2, resid). X already includes an intercept column."""
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    ss_res = float(resid @ resid)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    return beta, 1.0 - ss_res / ss_tot, ss_res


def partial_F(ss_full, ss_red, df_full, n, q):
    """F for adding q parameters: ((SSred - SSfull)/q) / (SSfull/df_full)."""
    return ((ss_red - ss_full) / q) / (ss_full / df_full)


def main(n_panels=6000, seed=20260728):
    rng = np.random.default_rng(seed)
    z = np.load(os.path.join(SUB, "arc_resp.npz"), allow_pickle=True)
    choice, acc = z["choice"], z["acc"]
    gold, agree_rate, n_rec = recover_gold(choice, acc)
    print(f"gold on {n_rec} items (agreement {agree_rate:.4f})", flush=True)

    items = np.where(gold != SENTINEL)[0]
    rng.shuffle(items)
    half = len(items) // 2
    sel_items, eval_items = np.sort(items[:half]), np.sort(items[half:])

    A = acc[:, sel_items]
    model_acc = A.mean(1)

    F = (1 - A).astype(np.uint8)
    keep = (F.sum(1) > 0) & (F.sum(1) < F.shape[1])
    idx = np.where(keep)[0]
    Fk = F[keep]
    ck = (Fk.sum(0) > 0) & (Fk.sum(0) < Fk.shape[0])
    Fk = Fk[:, ck]
    print(f"selection half: {Fk.shape[0]} models x {Fk.shape[1]} items", flush=True)

    a, b, err = fit_rasch(Fk)
    P = rasch_P(a, b)
    D = excess_gram(Fk, P)
    d = np.sqrt(np.clip(np.diag(D).astype(np.float64), 1e-12, None))
    R = D.astype(np.float64) / d[:, None] / d[None, :]
    np.fill_diagonal(R, 0.0)

    Ak = A[idx]
    agree = (Ak @ Ak.T + (1 - Ak) @ (1 - Ak).T) / Ak.shape[1]
    disagree = 1.0 - agree
    np.fill_diagonal(disagree, 0.0)
    # double-fault: fraction of items BOTH get wrong -- Kuncheva & Whitaker's measure,
    # and exactly the quantity Lemma 1 proves is margin-determined
    Fd = (1 - Ak)
    dfault = (Fd @ Fd.T) / Ak.shape[1]
    np.fill_diagonal(dfault, 0.0)

    acc_k = model_acc[idx]
    ce, ge = choice[:, eval_items], gold[eval_items]

    rows = []
    n_per = n_panels // len(PANEL_SIZES)
    for k in PANEL_SIZES:
        for _ in range(n_per):
            # stratified: draw a random accuracy band, then a panel inside it, so member
            # accuracy VARIES enough to be controlled for rather than being near-constant
            lo = rng.uniform(0.0, 0.75)
            band = np.where((acc_k >= lo) & (acc_k <= lo + 0.25))[0]
            if len(band) < k:
                band = np.arange(len(idx))
            pick = rng.choice(band, size=k, replace=False)
            sub_global = idx[pick]
            ii = np.ix_(pick, pick)
            m = k * (k - 1)
            rows.append((
                k,
                float(acc_k[pick].mean()),
                float(R[ii].sum() / m),
                float(disagree[ii].sum() / m),
                float(dfault[ii].sum() / m),
                majority_vote_acc(ce, ge, sub_global.tolist(), rng),
            ))

    arr = np.array(rows, dtype=np.float64)
    ksz, macc, condR, disag, dfl, vote = (arr[:, i] for i in range(6))
    n = len(arr)
    one = np.ones(n)

    def zs(v):
        return (v - v.mean()) / v.std()

    # standardised predictors so coefficients are comparable in effect-size units
    X0 = np.column_stack([one, zs(macc), zs(ksz)])
    X1 = np.column_stack([X0, zs(disag), zs(dfl)])
    X2 = np.column_stack([X1, zs(condR)])

    b0, r2_0, ss0 = ols(X0, vote)
    b1, r2_1, ss1 = ols(X1, vote)
    b2, r2_2, ss2 = ols(X2, vote)

    F_1_0 = partial_F(ss1, ss0, n - X1.shape[1], n, 2)
    F_2_1 = partial_F(ss2, ss1, n - X2.shape[1], n, 1)

    # also: cond_R added to M0 directly (without the classical measures), for reference
    X0R = np.column_stack([X0, zs(condR)])
    b0R, r2_0R, ss0R = ols(X0R, vote)
    F_0R_0 = partial_F(ss0R, ss0, n - X0R.shape[1], n, 1)

    # KI3: double-fault alone over M0
    X0D = np.column_stack([X0, zs(dfl)])
    _, r2_0D, ss0D = ols(X0D, vote)
    F_0D_0 = partial_F(ss0D, ss0, n - X0D.shape[1], n, 1)

    d_r2 = r2_2 - r2_1
    from math import erf, sqrt
    # crude two-sided p from F with df1=1 (F = t^2): p = erfc(|t|/sqrt2)
    t_2_1 = sqrt(max(F_2_1, 0.0))
    p_2_1 = 1.0 - erf(t_2_1 / sqrt(2.0))

    ki1 = (p_2_1 < 1e-3) and (d_r2 >= 0.01)
    ki2 = b2[-1] < 0

    out = {
        "n_panels": n, "panel_sizes": PANEL_SIZES,
        "sel_items": int(len(sel_items)), "eval_items": int(len(eval_items)),
        "rasch_fit_err": float(err),
        "models": {
            "M0_member_acc_plus_size": {"r2": r2_0},
            "M1_plus_classical_diversity": {"r2": r2_1, "delta_r2_vs_M0": r2_1 - r2_0,
                                            "F": float(F_1_0)},
            "M2_plus_conditioned_R": {"r2": r2_2, "delta_r2_vs_M1": d_r2,
                                      "F": float(F_2_1), "p_approx": float(p_2_1)},
            "M0_plus_conditioned_R_only": {"r2": r2_0R, "delta_r2_vs_M0": r2_0R - r2_0,
                                           "F": float(F_0R_0)},
            "M0_plus_double_fault_only": {"r2": r2_0D, "delta_r2_vs_M0": r2_0D - r2_0,
                                          "F": float(F_0D_0)},
        },
        "standardised_coefficients_M2": {
            "intercept": float(b2[0]), "member_acc": float(b2[1]), "panel_size": float(b2[2]),
            "disagreement": float(b2[3]), "double_fault": float(b2[4]), "cond_R": float(b2[5]),
        },
        "correlations_with_vote_acc": {
            "member_acc": float(np.corrcoef(macc, vote)[0, 1]),
            "disagreement": float(np.corrcoef(disag, vote)[0, 1]),
            "double_fault": float(np.corrcoef(dfl, vote)[0, 1]),
            "cond_R": float(np.corrcoef(condR, vote)[0, 1]),
        },
        "KI1_survives": bool(ki1), "KI2_sign_ok": bool(ki2),
        "KI1_fires": bool(not ki1),
    }
    json.dump(out, open(os.path.join(RES, "incremental_validity.json"), "w"), indent=1)

    print(f"\nn={n} panels")
    print(f"M0  member_acc + size                 R2 = {r2_0:.4f}")
    print(f"M1  + disagreement + double_fault     R2 = {r2_1:.4f}  (dR2 {r2_1-r2_0:+.4f}, F {F_1_0:.1f})")
    print(f"M2  + cond_R                          R2 = {r2_2:.4f}  (dR2 {d_r2:+.4f}, F {F_2_1:.1f}, p~{p_2_1:.2e})")
    print(f"    [ref] M0 + cond_R only            R2 = {r2_0R:.4f}  (dR2 {r2_0R-r2_0:+.4f})")
    print(f"    [KI3] M0 + double_fault only      R2 = {r2_0D:.4f}  (dR2 {r2_0D-r2_0:+.4f}, F {F_0D_0:.1f})")
    print("\nstandardised betas (M2):",
          " ".join(f"{k}={v:+.4f}" for k, v in out["standardised_coefficients_M2"].items()
                   if k != "intercept"))
    print(f"\nKI1 {'FIRES -- conditioned measure adds nothing' if not ki1 else 'survives'} "
          f"(dR2 {d_r2:+.4f}, need >= 0.01 and p < 1e-3)")
    print(f"KI2 sign {'ok (negative)' if ki2 else 'VIOLATED (positive)'}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 6000)
