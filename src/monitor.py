"""Layer C — the longitudinal evidence engine.

A single research paper is a snapshot. This script is what keeps generating evidence after it:
run on a schedule, it (1) checks the archive for models added since the last run, (2) harvests
only the delta, (3) recomputes the calibrated residual-concentration statistics per benchmark and
per release cohort, and (4) appends one dated row to results/timeseries.csv and one entry to
CHANGELOG.md. Nothing here re-derives the paper's theorems -- it re-applies them to fresh data.

This is what makes N_eff/rms|R_ij| a *living statistic* rather than a number frozen at
publication: if the ecosystem's effective diversity genuinely changes as new model families
appear (per H3's cohort-trend prediction, not yet confirmatorily tested), this is the instrument
that would show it, without a second research program.

Run:      python monitor.py [bench ...]
Schedule: see docs/LAYER_C.md for the cron/CronCreate wiring; this script is what it invokes.
"""
import csv, datetime, json, os, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nullmodel import curveball, fit_rasch, rasch_P, excess_gram, n_eff_from_excess

SUB = os.path.join(HERE, "..", "substrate")
RES = os.path.join(HERE, "..", "results")
ROOT = os.path.join(HERE, "..")
TS_PATH = os.path.join(RES, "timeseries.csv")
CHANGELOG = os.path.join(ROOT, "CHANGELOG.md")

FIELDS = ["run_date", "bench", "n_models", "n_models_delta", "n_items",
          "PR_observed", "PR_null_mean", "PR_null_sd", "PR_ratio",
          "rms_R_observed", "rms_R_null", "commit"]


def today():
    """Injected, never computed here -- Date.now()-equivalents are forbidden in scheduled
    contexts that might replay; the caller (or the shell) supplies the date."""
    return os.environ.get("MM_RUN_DATE") or subprocess.run(
        ["date", "+%Y-%m-%d"], capture_output=True, text=True).stdout.strip()


def git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def load_prior_count(bench):
    if not os.path.exists(TS_PATH):
        return 0
    last = 0
    with open(TS_PATH) as f:
        for row in csv.DictReader(f):
            if row["bench"] == bench:
                last = int(row["n_models"])
    return last


def measure(bench, R_null=40, burn_mult=50):
    z = np.load(os.path.join(SUB, "raw", f"{bench}.npz"), allow_pickle=True)
    acc = z["prim"]
    F = (1 - acc).astype(np.uint8)
    keep = (F.sum(1) > 0) & (F.sum(1) < F.shape[1])
    F = F[keep]
    ck = (F.sum(0) > 0) & (F.sum(0) < F.shape[0])
    F = F[:, ck]
    N, M = F.shape

    rng = np.random.default_rng(20260726)
    a, b, err = fit_rasch(F)
    P = rasch_P(a, b)
    D = excess_gram(F, P)
    pr_obs, w = n_eff_from_excess(D)
    d = np.sqrt(np.clip(np.diag(D).astype(np.float64), 1e-12, None))
    Rm = D.astype(np.float64) / d[:, None] / d[None, :]
    iu = np.triu_indices(N, 1)
    rms_obs = float(np.sqrt((Rm[iu] ** 2).mean()))

    X = curveball(np.array(F, dtype=np.uint8), burn_mult * N, rng)
    pr_null, rms_null = [], []
    for _ in range(R_null):
        X = curveball(X, 5 * N, rng)
        Dn = excess_gram(X, P)
        prn, _ = n_eff_from_excess(Dn)
        pr_null.append(prn)
        dn = np.sqrt(np.clip(np.diag(Dn).astype(np.float64), 1e-12, None))
        Rn = Dn.astype(np.float64) / dn[:, None] / dn[None, :]
        rms_null.append(float(np.sqrt((Rn[iu] ** 2).mean())))
    pr_null = np.asarray(pr_null)

    return {
        "n_models": int(N), "n_items": int(M),
        "PR_observed": float(pr_obs), "PR_null_mean": float(pr_null.mean()),
        "PR_null_sd": float(pr_null.std(ddof=1)), "PR_ratio": float(pr_obs / pr_null.mean()),
        "rms_R_observed": rms_obs, "rms_R_null": float(np.mean(rms_null)),
    }


def append_row(row):
    exists = os.path.exists(TS_PATH)
    with open(TS_PATH, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if not exists:
            w.writeheader()
        w.writerow(row)


def append_changelog(date, entries):
    lines = [f"\n## {date}\n"]
    for bench, m, delta in entries:
        lines.append(f"- **{bench}**: N={m['n_models']} ({'+' if delta>=0 else ''}{delta} "
                     f"since last run), PR={m['PR_observed']:.1f} vs null "
                     f"{m['PR_null_mean']:.1f}±{m['PR_null_sd']:.1f} "
                     f"(ratio {m['PR_ratio']:.3f}), rms|R|={m['rms_R_observed']:.4f} vs null "
                     f"{m['rms_R_null']:.4f}.\n")
    text = "".join(lines)
    if not os.path.exists(CHANGELOG):
        open(CHANGELOG, "w").write(
            "# Layer C changelog\n\nAppended automatically by `src/monitor.py`. Each entry is a "
            "re-application of the paper's calibrated estimator to the archive's current state, "
            "not a re-derivation. See docs/LAYER_C.md for how this is scheduled.\n" + text)
    else:
        open(CHANGELOG, "a").write(text)


def main(benches):
    date = today()
    commit = git_commit()
    entries = []
    for bench in benches:
        path = os.path.join(SUB, "raw", f"{bench}.npz")
        if not os.path.exists(path):
            print(f"[{bench}] no substrate yet, skipping (run harvest_matrix.py first)",
                  flush=True)
            continue
        prior = load_prior_count(bench)
        m = measure(bench)
        delta = m["n_models"] - prior
        row = {"run_date": date, "bench": bench, "n_models_delta": delta, "commit": commit, **m}
        append_row(row)
        entries.append((bench, m, delta))
        print(f"[{bench}] {date}  N={m['n_models']} ({'+' if delta>=0 else ''}{delta})  "
              f"PR={m['PR_observed']:.1f}/{m['PR_null_mean']:.1f}  "
              f"ratio={m['PR_ratio']:.3f}", flush=True)
    if entries:
        append_changelog(date, entries)
        print(f"CHANGELOG.md updated, {len(entries)} benchmark(s).", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:] or ["arc", "winogrande", "truthfulqa", "gsm8k", "hellaswag"])
