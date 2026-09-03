"""W2 -- a sequential monitor on the real model-arrival stream, with a null-stream control.

Pre-registered in docs/PREREG_WORKSHOP_EXPERIMENTS.md (KW4) before this ran.

The E-values short paper argues the exact conditional null is the right fixed-sample primitive for
an anytime-valid monitor and says no monitor has been built. This builds the fixed-set-of-looks
version: monthly looks over the accumulating ARC population, a Monte Carlo p-value against that
look's own exact conditional null, the standard calibrator p -> kappa p^(kappa-1), and the running
arithmetic mean of the calibrated e-values, which is a valid e-value under arbitrary dependence
(the looks here are nested and so strongly dependent).

Run: python src/w2_sequential_evalue.py [bench] -> results/w2_sequential_evalue.json
"""
import json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nullmodel import curveball, fit_rasch, rasch_P, excess_gram

SUB = os.path.join(HERE, "..", "substrate", "raw")
RES = os.path.join(HERE, "..", "results")

R_NULL = 40          # curveball replicates per look -> Monte Carlo p-value floor 1/41
KAPPA = 0.5          # calibrator e = kappa * p^(kappa-1)
BURN, THIN = 50, 5   # trades per model
SEED = 20260903
MIN_N = 100



def substrate_fingerprint(path):
    """Content hash of the input matrix file, recorded in every artifact.

    The archive grows and src/monitor.py commits new harvests, so an experiment is only
    reproducible if it names the snapshot it ran on. This is that name.
    """
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return {"file": os.path.relpath(path), "sha256": h.hexdigest()}

def rms_resid(F, P, iu):
    D = excess_gram(np.ascontiguousarray(F, dtype=np.uint8), P)
    d = np.sqrt(np.clip(np.diag(D).astype(np.float64), 1e-12, None))
    R = D.astype(np.float64) / d[:, None] / d[None, :]
    return float(np.sqrt((R[iu] ** 2).mean()))


def one_look(F, rng, observed=None):
    """Monte Carlo p-value for rms|R| against this population's own exact conditional null."""
    N = F.shape[0]
    iu = np.triu_indices(N, 1)
    a, b, err = fit_rasch(F)
    P = rasch_P(a, b)
    obs = rms_resid(F if observed is None else observed, P, iu)
    X = curveball(F, BURN * N, rng)
    nulls = []
    for _ in range(R_NULL):
        X = curveball(X, THIN * N, rng)
        nulls.append(rms_resid(X, P, iu))
    nulls = np.array(nulls)
    p = float((1 + (nulls >= obs).sum()) / (R_NULL + 1))
    return {"obs": obs, "null_mean": float(nulls.mean()), "null_sd": float(nulls.std()),
            "p": p, "ratio": float(obs / nulls.mean()), "margin_err": float(err)}


def calibrate(p, kappa=KAPPA):
    return float(kappa * p ** (kappa - 1.0))


def main(bench="arc"):
    rng = np.random.default_rng(SEED)
    z = np.load(os.path.join(SUB, f"{bench}.npz"), allow_pickle=True)
    dates = np.array([str(d) for d in z["dates"]])
    F = (1 - z["prim"]).astype(np.uint8)
    keep = (F.sum(1) > 0) & (F.sum(1) < F.shape[1]); F, dates = F[keep], dates[keep]
    ck = (F.sum(0) > 0) & (F.sum(0) < F.shape[0]); F = F[:, ck]
    months = sorted(set(d[:7] for d in dates if len(d) >= 7))

    real, ctrl = [], []
    e_real, e_ctrl = [], []
    for mth in months:
        m = np.array([d[:7] <= mth for d in dates])
        if m.sum() < MIN_N:
            continue
        Fc = F[m]
        kk = (Fc.sum(1) > 0) & (Fc.sum(1) < Fc.shape[1]); Fc = Fc[kk]
        cc = (Fc.sum(0) > 0) & (Fc.sum(0) < Fc.shape[0]); Fc = Fc[:, cc]
        if Fc.shape[0] < MIN_N:
            continue
        t0 = time.time()

        r = one_look(Fc, rng)
        r.update(month=mth, N=int(Fc.shape[0]), M=int(Fc.shape[1]))
        e_real.append(calibrate(r["p"]))
        r["e_value"] = e_real[-1]
        r["e_merged_running_mean"] = float(np.mean(e_real))
        real.append(r)

        # control: a stream where the null is true by construction
        a, b, _ = fit_rasch(Fc)
        Xobs = curveball(Fc, BURN * Fc.shape[0], rng)
        c = one_look(Fc, rng, observed=Xobs)
        c.update(month=mth, N=int(Fc.shape[0]))
        e_ctrl.append(calibrate(c["p"]))
        c["e_value"] = e_ctrl[-1]
        c["e_merged_running_mean"] = float(np.mean(e_ctrl))
        ctrl.append(c)

        print(f"  {mth} N={r['N']:>5}  real p={r['p']:.4f} ratio={r['ratio']:>5.2f}x "
              f"e={r['e_value']:>6.2f} merged={r['e_merged_running_mean']:>6.2f} | "
              f"ctrl p={c['p']:.4f} e={c['e_value']:.2f} merged={c['e_merged_running_mean']:.2f}"
              f"  [{time.time()-t0:.0f}s]", flush=True)

    e_floor = calibrate(1.0 / (R_NULL + 1))
    ctrl_max = max(x["e_merged_running_mean"] for x in ctrl) if ctrl else 0.0
    out = {"bench": bench, "seed": SEED, "R_null": R_NULL, "kappa": KAPPA,
           "substrate_snapshot": substrate_fingerprint(os.path.join(SUB, f"{bench}.npz")),
           "mc_p_floor": 1.0 / (R_NULL + 1), "e_value_ceiling_at_mc_floor": e_floor,
           "n_looks": len(real), "real_stream": real, "null_stream_control": ctrl,
           "final_merged_e_real": real[-1]["e_merged_running_mean"] if real else None,
           "final_merged_e_control": ctrl[-1]["e_merged_running_mean"] if ctrl else None,
           "max_merged_e_control": ctrl_max,
           "KW4_control_exceeds_20": bool(ctrl_max > 20.0)}
    json.dump(out, open(os.path.join(RES, "w2_sequential_evalue.json"), "w"), indent=1)
    print(f"\nlooks={len(real)}  merged e (real)={out['final_merged_e_real']:.2f}  "
          f"merged e (control)={out['final_merged_e_control']:.2f}  "
          f"control max={ctrl_max:.2f}  e-ceiling at MC floor={e_floor:.2f}")
    print("KW4 FIRED — control stream accumulated evidence; construction invalid."
          if out["KW4_control_exceeds_20"] else
          "KW4 not fired — control stream stays near 1, as a valid e-value must.")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "arc")
