"""X5 -- does the exact conditional null buy anything over a trivial baseline?

THE OBJECTION THIS ANSWERS. A reviewer observed that the reported null rms of residual
correlation (0.039) is close to 1/sqrt(M), the naive sampling floor for a correlation estimated
from M binary observations (0.029 for ARC, 0.036 for TruthfulQA, 0.028 for GSM8K), and concluded
that "the elaborate exact null coincides with the naive noise floor, so the machinery buys nothing
empirically." If true, the entire instrument is unnecessary and the paper has no method
contribution. This is the cheapest experiment that can kill the project, so it runs first.

DESIGN. Per benchmark, compute the rms of the margin-conditioned residual correlation under five
reference distributions, all with the SAME conditioning matrix P fitted from the observed data:

  (a) exact fixed-fixed      curveball; both margins preserved                [the paper's null]
  (b) row-margin-only        independently permute each row; row sums kept, column sums destroyed
  (c) column-margin-only     independently permute each column
  (d) iid Bernoulli          matched to the overall cell mean; no margins preserved
  (e) analytic floor         1/sqrt(M-3), the Fisher-z sampling floor

PRE-REGISTERED KILL CONDITION (written before execution, 2026-07-28)
--------------------------------------------------------------------
KN1. The instrument SURVIVES only if the exact null (a) differs from the trivial baselines
     (d) and (e) by a factor of at least 1.25 in rms on a majority of benchmarks. If (a), (d) and
     (e) agree within 25%, the exact conditioning is empirically inert: the paper must say so in
     the abstract and the method contribution is withdrawn.

KN2. Separately, the exact null must differ from the one-sided nulls (b) and (c). If preserving
     BOTH margins gives the same answer as preserving only one, the "jointly sufficient" argument
     has no empirical content on this data.

Run: ./.venv/bin/python src/noise_floor.py [bench ...] -> results/noise_floor.json
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nullmodel import curveball, fit_rasch, rasch_P, excess_gram

SUB = os.path.join(HERE, "..", "substrate", "raw")
RES = os.path.join(HERE, "..", "results")
N_REP = 12


def rms_resid(F, P, iu):
    D = excess_gram(np.ascontiguousarray(F, dtype=np.uint8), P)
    d = np.sqrt(np.clip(np.diag(D).astype(np.float64), 1e-12, None))
    R = D.astype(np.float64) / d[:, None] / d[None, :]
    return float(np.sqrt((R[iu] ** 2).mean()))


def rms_resid_refit(F, iu):
    """Same statistic, but with the Rasch conditioning model refitted to THIS matrix's margins.

    Required for any baseline that does not preserve the observed row margins. `R` normalises by
    sqrt(diag(D)), and D is defined relative to a fitted P; if P carries the observed margins
    while F does not, diag(D) collapses toward zero and R diverges -- an artifact of mismatched
    normalisation, not a property of the baseline. The first version of this script reported
    ratios of order 1e10 for exactly that reason. For the fixed-fixed null the refit is a no-op
    (margins are identical by construction), so this is the self-consistent way to compare all
    five reference distributions on one scale.
    """
    F = np.ascontiguousarray(F, dtype=np.uint8)
    keep = (F.sum(1) > 0) & (F.sum(1) < F.shape[1])
    if keep.sum() < 10:
        return float("nan")
    F = F[keep]
    ck = (F.sum(0) > 0) & (F.sum(0) < F.shape[0])
    F = F[:, ck]
    a, b, _ = fit_rasch(F)
    D = excess_gram(F, rasch_P(a, b))
    d = np.sqrt(np.clip(np.diag(D).astype(np.float64), 1e-12, None))
    R = D.astype(np.float64) / d[:, None] / d[None, :]
    iu2 = np.triu_indices(F.shape[0], 1)
    return float(np.sqrt((R[iu2] ** 2).mean()))


def permute_rows(F, rng):
    X = F.copy()
    for i in range(X.shape[0]):
        rng.shuffle(X[i])
    return X


def permute_cols(F, rng):
    X = F.copy()
    for j in range(X.shape[1]):
        col = X[:, j].copy()
        rng.shuffle(col)
        X[:, j] = col
    return X


def run(bench, rng):
    z = np.load(os.path.join(SUB, f"{bench}.npz"), allow_pickle=True)
    F = (1 - z["prim"]).astype(np.uint8)
    keep = (F.sum(1) > 0) & (F.sum(1) < F.shape[1])
    F = F[keep]
    ck = (F.sum(0) > 0) & (F.sum(0) < F.shape[0])
    F = F[:, ck]
    N, M = F.shape
    iu = np.triu_indices(N, 1)

    a, b, err = fit_rasch(F)
    P = rasch_P(a, b)
    obs = rms_resid(F, P, iu)
    p_bar = float(F.mean())

    out = {"bench": bench, "N": int(N), "M": int(M), "observed_rms": obs,
           "cell_mean": p_bar, "rasch_fit_err": float(err)}

    # (a) exact fixed-fixed
    X = curveball(F, 50 * N, rng)
    vals = []
    for _ in range(N_REP):
        X = curveball(X, 5 * N, rng)
        vals.append(rms_resid(X, P, iu))
    out["a_exact_fixed_fixed"] = {"mean": float(np.mean(vals)), "sd": float(np.std(vals, ddof=1))}

    # (b) row-margin-only, (c) column-margin-only, (d) iid Bernoulli.
    # These destroy one or both observed margins, so the conditioning model is refitted to each
    # replicate; see rms_resid_refit for why reusing the observed P gives meaningless ratios.
    for key, fn in (("b_row_margin_only", permute_rows),
                    ("c_col_margin_only", permute_cols)):
        vals = [rms_resid_refit(fn(F, rng), iu) for _ in range(max(N_REP // 3, 4))]
        out[key] = {"mean": float(np.mean(vals)), "sd": float(np.std(vals, ddof=1)),
                    "refit": True}

    vals = [rms_resid_refit((rng.random((N, M)) < p_bar).astype(np.uint8), iu)
            for _ in range(max(N_REP // 3, 4))]
    out["d_iid_bernoulli"] = {"mean": float(np.mean(vals)), "sd": float(np.std(vals, ddof=1)),
                              "refit": True}

    # (e) analytic Fisher-z floor
    out["e_analytic_floor"] = {"mean": float(1.0 / np.sqrt(M - 3)), "sd": 0.0}

    ex = out["a_exact_fixed_fixed"]["mean"]
    out["ratio_exact_over_iid"] = ex / out["d_iid_bernoulli"]["mean"]
    out["ratio_exact_over_floor"] = ex / out["e_analytic_floor"]["mean"]
    out["ratio_exact_over_rowonly"] = ex / out["b_row_margin_only"]["mean"]
    out["ratio_exact_over_colonly"] = ex / out["c_col_margin_only"]["mean"]
    out["KN1_bench_pass"] = bool(
        max(out["ratio_exact_over_iid"], 1 / out["ratio_exact_over_iid"]) >= 1.25
        or max(out["ratio_exact_over_floor"], 1 / out["ratio_exact_over_floor"]) >= 1.25)
    out["KN2_bench_pass"] = bool(
        max(out["ratio_exact_over_rowonly"], 1 / out["ratio_exact_over_rowonly"]) >= 1.25
        or max(out["ratio_exact_over_colonly"], 1 / out["ratio_exact_over_colonly"]) >= 1.25)
    return out


def main(benches):
    rng = np.random.default_rng(20260728)
    res = []
    for bch in benches:
        if not os.path.exists(os.path.join(SUB, f"{bch}.npz")):
            continue
        r = run(bch, rng)
        res.append(r)
        print(f"[{r['bench']:<11}] obs={r['observed_rms']:.4f} | exact={r['a_exact_fixed_fixed']['mean']:.4f} "
              f"row={r['b_row_margin_only']['mean']:.4f} col={r['c_col_margin_only']['mean']:.4f} "
              f"iid={r['d_iid_bernoulli']['mean']:.4f} floor={r['e_analytic_floor']['mean']:.4f} | "
              f"exact/iid={r['ratio_exact_over_iid']:.2f} exact/floor={r['ratio_exact_over_floor']:.2f} "
              f"{'PASS' if r['KN1_bench_pass'] else 'fail'}", flush=True)

    n1 = sum(r["KN1_bench_pass"] for r in res)
    n2 = sum(r["KN2_bench_pass"] for r in res)
    out = {"n_replicates": N_REP, "benchmarks": res,
           "KN1_n_pass": n1, "KN1_fires": bool(n1 <= len(res) // 2),
           "KN2_n_pass": n2, "KN2_fires": bool(n2 <= len(res) // 2)}
    json.dump(out, open(os.path.join(RES, "noise_floor.json"), "w"), indent=1)
    print(f"\nKN1 {'FIRES -- exact null is empirically inert' if out['KN1_fires'] else 'survives'} "
          f"({n1}/{len(res)})")
    print(f"KN2 {'FIRES -- both-margin conditioning adds nothing over one-margin' if out['KN2_fires'] else 'survives'} "
          f"({n2}/{len(res)})")


if __name__ == "__main__":
    main(sys.argv[1:] or ["arc", "winogrande", "truthfulqa", "gsm8k", "hellaswag"])
