"""Reconcile the two headline results, and test the reviewer's alternative explanation.

An adversarial review raised an algebraic objection that, if correct, invalidates the N_eff
claim. Because the null preserves margins exactly, the fitted Rasch matrix P -- and hence the
expected co-failure E = PP^T/M -- is IDENTICAL for the observation and every null replicate.
And because the conditioned matrix R has unit diagonal, tr(R) = N exactly, so

    N_eff = N^2 / ||R||_F^2 = N^2 / (N + sum_{i!=j} R_ij^2)

meaning N_eff far BELOW null is algebraically equivalent to mean R_ij^2 far ABOVE null: the
margin-conditioned excess correlations are large. But the pre-registered statistic T said
Var(C_ij) is BELOW null. Writing C = E + D with E fixed:

    Var(C) = Var(E) + 2 Cov(E, D) + Var(D)

Var(E) is identical for observation and null. So Var(C) below null while Var(D) is above null
forces Cov(E, D) to be strongly negative in the real data -- pairs the margin model predicts
will co-fail most actually co-fail relatively less. That is either a real structural finding or
Rasch misfit, and the two must be told apart before anything is claimed.

This script measures every term for the observation and the null, so the reconciliation is
arithmetic rather than argument.

Run: python reconcile.py [bench ...]  ->  results/<bench>_reconcile.json
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nullmodel import curveball, fit_rasch, rasch_P, gram, n_eff_from_excess
from experiments import load

RES = os.path.join(HERE, "..", "results")
os.makedirs(RES, exist_ok=True)


def terms(F, P, M):
    """Return the variance decomposition over unordered model pairs."""
    N = F.shape[0]
    iu = np.triu_indices(N, 1)
    C = (gram(F).astype(np.float64)) / M
    E = (np.ascontiguousarray(P, np.float32) @ np.ascontiguousarray(P, np.float32).T).astype(np.float64) / M
    D = C - E
    c, e, d = C[iu], E[iu], D[iu]
    dd = np.sqrt(np.clip(np.diag(D), 1e-12, None))
    R = D / dd[:, None] / dd[None, :]
    return {
        "var_C": float(c.var()), "var_E": float(e.var()), "var_D": float(d.var()),
        "cov_E_D": float(np.cov(e, d)[0, 1]), "mean_D": float(d.mean()),
        "mean_R2_offdiag": float((R[iu] ** 2).mean()),
        "corr_E_D": float(np.corrcoef(e, d)[0, 1]),
    }


def run(bench, R=30, burn=50, long_burn=2000, seed=20260726):
    rng = np.random.default_rng(seed + 7)
    F, _, _, _ = load(bench)
    N, M = F.shape
    F8 = np.array(F, np.uint8)
    a, b, err = fit_rasch(F)
    P = rasch_P(a, b)
    print(f"\n===== {bench} reconciliation  N={N} M={M} =====", flush=True)

    obs = terms(F, P, M)
    nulls = []
    for _ in range(R):
        X = curveball(F8, burn * N, rng)
        nulls.append(terms(X, P, M))
    keys = list(obs)
    nm = {k: float(np.mean([n[k] for n in nulls])) for k in keys}
    ns = {k: float(np.std([n[k] for n in nulls], ddof=1)) for k in keys}

    print(f"  {'term':22s} {'observed':>13s} {'null mean':>13s} {'null sd':>11s} {'SES':>9s}")
    for k in keys:
        ses = (obs[k] - nm[k]) / ns[k] if ns[k] > 0 else float("nan")
        print(f"  {k:22s} {obs[k]:13.6e} {nm[k]:13.6e} {ns[k]:11.3e} {ses:9.2f}", flush=True)

    # Reviewer's key check: is Var(E) really identical across observation and null?
    print(f"\n  Var(E) identical obs vs null?  |diff| = {abs(obs['var_E']-nm['var_E']):.3e}"
          f"  (must be ~0 since margins are preserved)", flush=True)

    # Long burn-in: is 50 trades/N enough, or is the null under-mixed?
    Xl = curveball(F8, long_burn * N, rng)
    lt = terms(Xl, P, M)
    nel, _ = n_eff_from_excess((gram(Xl).astype(np.float32) -
                                (np.ascontiguousarray(P, np.float32) @
                                 np.ascontiguousarray(P, np.float32).T)) / M)
    neo, _ = n_eff_from_excess((gram(F).astype(np.float32) -
                                (np.ascontiguousarray(P, np.float32) @
                                 np.ascontiguousarray(P, np.float32).T)) / M)
    print(f"\n  burn-in check: N_eff of a {long_burn}-trades/N replicate = {nel:.1f}"
          f"   vs {burn}-trades/N null mean, observed = {neo:.1f}", flush=True)

    out = {"bench": bench, "N": int(N), "M": int(M), "rasch_margin_error": err,
           "observed": obs, "null_mean": nm, "null_sd": ns,
           "SES": {k: ((obs[k] - nm[k]) / ns[k] if ns[k] > 0 else None) for k in keys},
           "long_burn_trades_per_N": long_burn,
           "long_burn_terms": lt, "long_burn_neff": float(nel),
           "observed_neff": float(neo), "R": R}
    json.dump(out, open(os.path.join(RES, f"{bench}_reconcile.json"), "w"), indent=1)
    return out


if __name__ == "__main__":
    for b in (sys.argv[1:] or ["arc"]):
        run(b)
