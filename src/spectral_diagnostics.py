"""Emit the spectral diagnostics the paper quotes, as a JSON artifact.

Written 2026-08-08. These four numbers -- lambda_1^2/sum(lambda^2), the participation ratio after
deflating the leading eigenvector, the fraction of spectral mass that is positive, and the
participation ratio under three treatments of negative eigenvalues -- were quoted in
paper/main.tex (Sections "Why these numbers are not an effective number of models" and
"Functional choice") and recorded in results/RESULTS_DIGEST.md, but traced to no JSON file. The
paper states that "each number traces to a JSON file emitted by an executed run"; that was true of
every other headline figure and not of these. This script closes the gap by recomputing them from
the committed substrate rather than trusting the digest.

The discriminating diagnostics matter because the participation ratio alone cannot separate one
weak global factor from many tight clusters (that is the paper's own negative result); these are
the statistics that can.

Run: ./.venv/bin/python src/spectral_diagnostics.py [bench ...]
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nullmodel import excess_gram, fit_rasch, rasch_P  # noqa: E402

ROOT = os.path.join(HERE, "..")
RAW = os.path.join(ROOT, "substrate", "raw")
RES = os.path.join(ROOT, "results")


def load_matrix(bench, path=None):
    """Load a benchmark's failure matrix.

    `path` overrides the live substrate file. That override matters: Layer C keeps harvesting, so
    substrate/raw/arc.npz grows over time (1,362 models at the paper's snapshot, 2,162 after the
    2026-08-07 harvest delta). Reproducing a published figure therefore requires the paper-era
    matrix, which is recoverable from git:
        git cat-file -p <paper-era-commit>:substrate/raw/arc.npz > /tmp/arc_paper_era.npz
    (use `git cat-file`, not `git show` -- the latter can mangle binary through a pager/filter).
    """
    z = np.load(path or os.path.join(RAW, f"{bench}.npz"), allow_pickle=True)
    P = np.asarray(z["prim"], dtype=np.uint8)
    # failure matrix: 1 = model failed the item
    F = (1 - P).astype(np.float32)
    # drop degenerate rows/columns exactly as the main analysis does
    keep_i = (F.sum(1) > 0) & (F.sum(1) < F.shape[1])
    F = F[keep_i]
    keep_m = (F.sum(0) > 0) & (F.sum(0) < F.shape[0])
    F = F[:, keep_m]
    return F


def diagnostics(F):
    N, M = F.shape
    a, b, margin_err = fit_rasch(F)
    P = rasch_P(a, b)
    D = excess_gram(F, P)

    d = np.sqrt(np.clip(np.diag(D).astype(np.float64), 1e-9, None))
    R = D.astype(np.float64) / d[:, None] / d[None, :]
    np.fill_diagonal(R, 1.0)

    w = np.linalg.eigvalsh(R)[::-1]
    wp = np.clip(w, 0.0, None)

    def pr(x):
        return float(x.sum() ** 2 / (x * x).sum())

    # participation ratio under three treatments of negative eigenvalues
    pr_clipped = pr(wp)
    pr_absolute = pr(np.abs(w))
    pr_raw = pr(w)

    # share of the leading eigenvalue in total squared spectral mass:
    # ~0.99 for a single global factor, ~0.10 for many equal-size clone blocks
    lam1_sq_share = float(w[0] ** 2 / (w * w).sum())

    # participation ratio after deflating the leading eigenvector -- if the structure were one
    # weak global factor, removing it would send this to ~N
    w_deflated = w[1:]
    pr_deflated = pr(np.clip(w_deflated, 0.0, None))

    frac_positive_mass = float(wp.sum() / np.abs(w).sum())

    # the identity the paper uses to argue PR counts nothing:  PR = N/(1+(N-1)*mean R_ij^2)
    off = ~np.eye(N, dtype=bool)
    mean_r2_offdiag = float((R[off] ** 2).mean())
    pr_identity = float(N / (1.0 + (N - 1) * mean_r2_offdiag))

    return {
        "N": int(N),
        "M": int(M),
        "rasch_margin_error": margin_err,
        "lambda1_sq_over_sum_sq": lam1_sq_share,
        "pr_deflated_leading": pr_deflated,
        "pr_clipped": pr_clipped,
        "pr_absolute": pr_absolute,
        "pr_raw": pr_raw,
        "frac_spectral_mass_positive": frac_positive_mass,
        "mean_R2_offdiag": mean_r2_offdiag,
        "pr_from_identity": pr_identity,
        "pr_identity_matches_raw": bool(abs(pr_identity - pr_raw) < 1e-3),
        "lambda_top10": [float(x) for x in w[:10]],
    }


if __name__ == "__main__":
    # optional: MM_MATRIX=<path.npz> to score a specific snapshot instead of the live substrate
    override = os.environ.get("MM_MATRIX") or None
    out = {}
    for bench in (sys.argv[1:] or ["arc"]):
        F = load_matrix(bench, override)
        print(f"[{bench}] matrix {F.shape}, fitting Rasch and eigendecomposing", flush=True)
        out[bench] = diagnostics(F)
        for k, v in out[bench].items():
            if k != "lambda_top10":
                print(f"  {k} = {v}")
    path = os.path.join(RES, "spectral_diagnostics.json")
    json.dump(out, open(path, "w"), indent=1)
    print(f"wrote {path}")
