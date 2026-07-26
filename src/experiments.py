"""Confirmatory analysis. Every number this file prints is written to results/ as JSON so
that each figure and table in the manuscript traces to an executed run.

Experiment map (see PREREGISTRATION.md, incl. AMENDMENT 1 and 2):
  E0  pipeline validation / kill condition K6 : measured naive excess vs closed form
  E1  H1b : T = Var_{i<j}(C_ij) against the fixed-fixed null (primary confirmatory test)
  E2  decomposition : how much reported "excess" is marginal artifact vs residual structure
  E3  H3  : N_eff under two independent definitions, on the margin-conditioned excess
  E4  H3  : N_eff / N by release cohort
  E7  K4  : curveball convergence diagnostics
Run:  python experiments.py [bench ...]
"""
import json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nullmodel import (curveball, margins_ok, mean_cofail, naive_excess_closed_form,
                       naive_excess_empirical, gram, var_cofail, fit_rasch, rasch_P,
                       excess_gram, n_eff_from_excess, n_eff_variance_inflation)

SUB = os.path.join(HERE, "..", "substrate", "raw")
RES = os.path.join(HERE, "..", "results")
os.makedirs(RES, exist_ok=True)

R_SAMPLES = int(os.environ.get("MM_R", "500"))     # null replicates
BURN_MULT = 50                                      # burn-in trades = BURN_MULT * N
THIN_MULT = 5                                       # trades between retained samples


def load(bench, min_models=50):
    z = np.load(os.path.join(SUB, f"{bench}.npz"), allow_pickle=True)
    acc = z["prim"]
    models = np.array([str(m) for m in z["models"]])
    dates = np.array([str(d) for d in z["dates"]])
    F = (1 - acc).astype(np.uint8)                  # FAILURE matrix
    keep = (F.sum(1) > 0) & (F.sum(1) < F.shape[1]) # drop degenerate rows
    F, models, dates = F[keep], models[keep], dates[keep]
    ck = (F.sum(0) > 0) & (F.sum(0) < F.shape[0])   # drop items nobody/everybody fails
    return F[:, ck], models, dates, ck


def e0_validation(F):
    """K6: the measured naive excess must equal the Proposition 2 closed form."""
    emp = naive_excess_empirical(F)
    cf = naive_excess_closed_form(F)
    return {"naive_excess_empirical": emp, "naive_excess_closed_form": cf,
            "residual": emp - cf, "K6_pass": bool(abs(emp - cf) < 1e-9)}


def null_chain(F, R, rng, stat_fns, burn_mult=BURN_MULT, thin_mult=THIN_MULT, trace_every=0):
    """One curveball chain: burn in, then retain R samples, computing each statistic on each."""
    N = F.shape[0]
    X = np.array(F, dtype=np.uint8)
    X = curveball(X, burn_mult * N, rng)
    out = {k: [] for k in stat_fns}
    trace = []
    for r in range(R):
        X = curveball(X, thin_mult * N, rng)
        for k, fn in stat_fns.items():
            out[k].append(fn(X))
        if trace_every and r % trace_every == 0:
            trace.append({"sample": r, **{k: out[k][-1] for k in out}})
    return {k: np.asarray(v, float) for k, v in out.items()}, trace, X


def e1_structure(F, rng, R=R_SAMPLES):
    """H1b primary test: dispersion of pairwise co-failure vs the fixed-fixed null."""
    G = gram(F)
    T_obs = var_cofail(F, G)
    mu_obs = mean_cofail(F)
    stats = {"T": lambda X: var_cofail(X), "mu": mean_cofail}
    t0 = time.time()
    draws, trace, Xlast = null_chain(F, R, rng, stats, trace_every=max(1, R // 40))
    Tn, mun = draws["T"], draws["mu"]
    sd = Tn.std(ddof=1)
    ses = (T_obs - Tn.mean()) / sd if sd > 0 else float("nan")
    p_hi = (1 + (Tn >= T_obs).sum()) / (1 + len(Tn))
    return {
        "T_observed": T_obs, "T_null_mean": float(Tn.mean()), "T_null_sd": float(sd),
        "SES": float(ses), "p_one_sided_greater": float(p_hi),
        "ratio_obs_over_null": float(T_obs / Tn.mean()) if Tn.mean() else None,
        "mean_cofail_observed": mu_obs,
        "mean_cofail_null_mean": float(mun.mean()),
        "mean_cofail_null_sd": float(mun.std(ddof=1)),
        "prop1_max_abs_dev": float(np.abs(mun - mu_obs).max()),
        "margins_preserved": margins_ok(F, Xlast),
        "R": int(R), "seconds": time.time() - t0,
    }, trace


def e2_decomposition(F, e1):
    """How much of the reported 'excess' survives conditioning on the margins."""
    naive = naive_excess_empirical(F)
    return {
        "naive_excess_over_independence": naive,
        "explained_by_margins": naive,          # Prop 1: the whole mean-level excess
        "residual_mean_excess": e1["mean_cofail_observed"] - e1["mean_cofail_null_mean"],
        "pct_of_mean_excess_that_is_artifact":
            100.0 * (1 - abs(e1["mean_cofail_observed"] - e1["mean_cofail_null_mean"]) / abs(naive))
            if naive else None,
    }


def e3_neff(F, rng, R_neff=60):
    """N_eff on the MARGIN-CONDITIONED excess, CALIBRATED AGAINST THE NULL.

    An uncalibrated N_eff would repeat precisely the error this paper identifies: a number
    that looks like evidence of concentration but is in fact whatever the margins force.
    The null replicates share F's margins exactly, so the Rasch fit is identical for all of
    them and is computed once.
    """
    a, b, err = fit_rasch(F)
    P = rasch_P(a, b)
    D = excess_gram(F, P)
    ne_part, w = n_eff_from_excess(D)
    ne_vi, rbar = n_eff_variance_inflation(F)
    N = F.shape[0]
    from nullmodel import eig_spectrum, n_eff_participation
    w_raw = eig_spectrum(F)

    X = curveball(np.array(F, dtype=np.uint8), BURN_MULT * N, rng)
    null_ne = []
    for _ in range(R_neff):
        X = curveball(X, THIN_MULT * N, rng)
        ne_r, _ = n_eff_from_excess(excess_gram(X, P))
        null_ne.append(ne_r)
    null_ne = np.asarray(null_ne, float)
    sd = null_ne.std(ddof=1)
    return {
        "N": int(N), "rasch_margin_error": err,
        "N_eff_participation_conditioned": ne_part,
        "N_eff_null_mean": float(null_ne.mean()), "N_eff_null_sd": float(sd),
        "N_eff_SES": float((ne_part - null_ne.mean()) / sd) if sd > 0 else float("nan"),
        "N_eff_ratio_obs_over_null": float(ne_part / null_ne.mean()),
        "N_eff_null_R": int(R_neff),
        "N_eff_variance_inflation_raw": ne_vi, "mean_pairwise_corr_raw": rbar,
        "N_eff_participation_raw_UNCONDITIONED": n_eff_participation(w_raw),
        "N_eff_over_N_conditioned": ne_part / N,
        "top10_eigs_conditioned": [float(x) for x in w[:10]],
        "top10_eigs_raw": [float(x) for x in w_raw[:10]],
    }


def e4_cohort(F, dates, min_n=60):
    """N_eff / N by release cohort (H3 consolidation claim)."""
    q = np.array([d[:7] if len(d) >= 7 else "" for d in dates])
    out = []
    for c in sorted(set(q)):
        if not c:
            continue
        idx = np.flatnonzero(q == c)
        if idx.size < min_n:
            continue
        Fc = F[idx]
        ck = (Fc.sum(0) > 0) & (Fc.sum(0) < Fc.shape[0])
        Fc = Fc[:, ck]
        if Fc.shape[1] < 50:
            continue
        a, b, _ = fit_rasch(Fc)
        D = excess_gram(Fc, rasch_P(a, b))
        ne, _ = n_eff_from_excess(D)
        out.append({"cohort": c, "n_models": int(idx.size),
                    "N_eff": ne, "N_eff_over_N": ne / idx.size})
    return out


def e7_convergence(F, rng, checkpoints=(1, 2, 5, 10, 20, 50, 100, 200)):
    """K4: does the chain mix? Track the statistic and the distance from the observed matrix."""
    N = F.shape[0]
    X = np.array(F, dtype=np.uint8)
    T0 = var_cofail(F)
    rows = [{"trades_per_N": 0, "T": T0, "frac_cells_changed": 0.0}]
    prev = 0
    for c in checkpoints:
        X = curveball(X, (c - prev) * N, rng)
        prev = c
        rows.append({"trades_per_N": int(c), "T": var_cofail(X),
                     "frac_cells_changed": float((X != F).mean()),
                     "margins_ok": margins_ok(F, X)})
    return rows


def run(bench, seed=20260726):
    rng = np.random.default_rng(seed)
    F, models, dates, _ = load(bench)
    N, M = F.shape
    print(f"\n===== {bench}: N={N} models x M={M} items, failure density {F.mean():.4f} =====",
          flush=True)
    out = {"bench": bench, "N": int(N), "M": int(M), "failure_density": float(F.mean()),
           "seed": seed}

    out["E0_validation"] = e0_validation(F)
    print(f"  E0 K6 {'PASS' if out['E0_validation']['K6_pass'] else 'FAIL'}: "
          f"empirical={out['E0_validation']['naive_excess_empirical']:.9f} "
          f"closed_form={out['E0_validation']['naive_excess_closed_form']:.9f} "
          f"resid={out['E0_validation']['residual']:.2e}", flush=True)

    e1, trace = e1_structure(F, rng)
    out["E1_structure"], out["E1_trace"] = e1, trace
    print(f"  E1 T_obs={e1['T_observed']:.6e} null={e1['T_null_mean']:.6e} "
          f"SES={e1['SES']:.2f} p={e1['p_one_sided_greater']:.4g} "
          f"ratio={e1['ratio_obs_over_null']:.3f} ({e1['seconds']:.0f}s)", flush=True)
    print(f"  E1 Prop1 check: mean co-failure max |null - obs| = "
          f"{e1['prop1_max_abs_dev']:.2e}  margins_ok={e1['margins_preserved']}", flush=True)

    out["E2_decomposition"] = e2_decomposition(F, e1)
    print(f"  E2 naive excess={out['E2_decomposition']['naive_excess_over_independence']:+.6f} "
          f"residual after conditioning={out['E2_decomposition']['residual_mean_excess']:+.2e}",
          flush=True)

    out["E3_neff"] = e3_neff(F, rng)
    e3 = out["E3_neff"]
    print(f"  E3 N={N}  N_eff(conditioned)={e3['N_eff_participation_conditioned']:.1f}  "
          f"null={e3['N_eff_null_mean']:.1f}+-{e3['N_eff_null_sd']:.1f}  "
          f"SES={e3['N_eff_SES']:.2f}  ratio={e3['N_eff_ratio_obs_over_null']:.3f}  "
          f"[raw,unconditioned={e3['N_eff_participation_raw_UNCONDITIONED']:.1f}]", flush=True)

    out["E4_cohort"] = e4_cohort(F, dates)
    print(f"  E4 cohorts with >=60 models: {len(out['E4_cohort'])}", flush=True)

    out["E7_convergence"] = e7_convergence(F, rng)
    print(f"  E7 mixing: frac cells changed at 200 trades/N = "
          f"{out['E7_convergence'][-1]['frac_cells_changed']:.3f}", flush=True)

    json.dump(out, open(os.path.join(RES, f"{bench}_results.json"), "w"), indent=1)
    return out


if __name__ == "__main__":
    for b in (sys.argv[1:] or ["arc"]):
        run(b)
