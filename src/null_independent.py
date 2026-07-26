"""Re-estimate the null distributions using INDEPENDENT chains.

The first confirmatory run drew null replicates by thinning a single curveball chain. Those
draws are autocorrelated, which underestimates the null SD and inflates |SES|. The point
estimates and ratios are unaffected, but the significance statements are not trustworthy until
this is redone properly.

Fix: R independent chains, each started from the observed matrix and burned in separately, one
sample retained per chain. The E7 trace justifies the burn-in -- the statistic plateaus by
about 10 trades/N and is flat out to 200 trades/N -- so 50 trades/N per chain is ample.

Both the single-chain and independent-chain SDs are reported so the size of the correction is
visible rather than quietly absorbed.

Run: python null_independent.py [bench ...]  ->  results/<bench>_null_independent.json
"""
import json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nullmodel import (curveball, margins_ok, var_cofail, fit_rasch, rasch_P,
                       excess_gram, n_eff_from_excess)
from experiments import load

RES = os.path.join(HERE, "..", "results")
BURN = 50           # trades per N, per independent chain
R_T = int(os.environ.get("MM_RT", "200"))
R_NEFF = int(os.environ.get("MM_RNEFF", "60"))


def autocorr(x, lag=1):
    x = np.asarray(x, float)
    x = x - x.mean()
    d = (x * x).sum()
    return float((x[:-lag] * x[lag:]).sum() / d) if d > 0 else float("nan")


def run(bench, seed=20260726):
    rng = np.random.default_rng(seed + 1)
    F, models, dates, _ = load(bench)
    N = F.shape[0]
    F8 = np.array(F, dtype=np.uint8)
    print(f"\n===== {bench}: independent-chain null, N={N} =====", flush=True)

    # ---- T, independent chains
    t0 = time.time()
    T_obs = var_cofail(F)
    Ti = []
    ok = True
    for r in range(R_T):
        X = curveball(F8, BURN * N, rng)
        if r == 0:
            ok = margins_ok(F, X)
        Ti.append(var_cofail(X))
    Ti = np.asarray(Ti)
    sd_i = Ti.std(ddof=1)

    # ---- T, single chain (for comparison with the original run)
    Ts, X = [], curveball(F8, BURN * N, rng)
    for _ in range(R_T):
        X = curveball(X, 5 * N, rng)
        Ts.append(var_cofail(X))
    Ts = np.asarray(Ts)
    sd_s = Ts.std(ddof=1)

    out = {
        "bench": bench, "N": int(N), "M": int(F.shape[1]), "burn_trades_per_N": BURN,
        "margins_preserved": bool(ok),
        "T": {
            "observed": float(T_obs),
            "independent": {"mean": float(Ti.mean()), "sd": float(sd_i), "R": R_T,
                            "SES": float((T_obs - Ti.mean()) / sd_i),
                            "ratio": float(T_obs / Ti.mean()),
                            "lag1_autocorr": autocorr(Ti)},
            "single_chain": {"mean": float(Ts.mean()), "sd": float(sd_s), "R": R_T,
                             "SES": float((T_obs - Ts.mean()) / sd_s),
                             "lag1_autocorr": autocorr(Ts)},
            "sd_inflation_factor": float(sd_i / sd_s) if sd_s else None,
        },
    }
    print(f"  T obs={T_obs:.5e}", flush=True)
    print(f"    independent : null={Ti.mean():.5e} sd={sd_i:.2e} SES={out['T']['independent']['SES']:+.2f} "
          f"lag1={out['T']['independent']['lag1_autocorr']:+.3f}", flush=True)
    print(f"    single-chain: null={Ts.mean():.5e} sd={sd_s:.2e} SES={out['T']['single_chain']['SES']:+.2f} "
          f"lag1={out['T']['single_chain']['lag1_autocorr']:+.3f}", flush=True)
    print(f"    null SD is {out['T']['sd_inflation_factor']:.2f}x larger with independent chains",
          flush=True)

    # ---- N_eff, independent chains (Rasch fit is shared: null replicates have identical margins)
    a, b, err = fit_rasch(F)
    P = rasch_P(a, b)
    ne_obs, w = n_eff_from_excess(excess_gram(F, P))
    Ni = []
    for _ in range(R_NEFF):
        X = curveball(F8, BURN * N, rng)
        Ni.append(n_eff_from_excess(excess_gram(X, P))[0])
    Ni = np.asarray(Ni)
    sdn = Ni.std(ddof=1)
    out["N_eff"] = {
        "observed": float(ne_obs), "null_mean": float(Ni.mean()), "null_sd": float(sdn),
        "SES": float((ne_obs - Ni.mean()) / sdn), "ratio": float(ne_obs / Ni.mean()),
        "R": R_NEFF, "lag1_autocorr": autocorr(Ni), "rasch_margin_error": err,
    }
    print(f"  N_eff obs={ne_obs:.1f} null={Ni.mean():.1f}+-{sdn:.1f} "
          f"SES={out['N_eff']['SES']:+.1f} ratio={out['N_eff']['ratio']:.3f} "
          f"lag1={out['N_eff']['lag1_autocorr']:+.3f}", flush=True)
    out["seconds"] = time.time() - t0
    json.dump(out, open(os.path.join(RES, f"{bench}_null_independent.json"), "w"), indent=1)
    return out


if __name__ == "__main__":
    for b in (sys.argv[1:] or ["arc"]):
        run(b)
