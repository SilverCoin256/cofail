"""Figure for the ATTRIB paper: family separation in the residual eigenspace.

Left: models projected on the top two eigenvectors of the margin-conditioned residual correlation
matrix, coloured by base family. Right: the same projection computed on a curveball replicate of
the same matrix (the exact conditional null), which preserves both margins and therefore destroys
any real association between behaviour and family. The right panel is what the left panel would
look like if the pipeline were manufacturing the structure.

Run: python src/w1_figure.py -> figures/fig_w1_family.pdf
"""
import json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
# NeurIPS requires PDFs contain only Type 1 or embedded TrueType fonts; matplotlib's
# default PDF backend emits Type 3, which the formatting instructions reject.
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nullmodel import curveball
from dedup_sensitivity import family_of
from w1_family_signal import residual_eigvecs, TOP_FAMILIES, SEED

SUB = os.path.join(HERE, "..", "substrate", "raw")
FIG = os.path.join(HERE, "..", "figures")
RES = os.path.join(HERE, "..", "results")
COLORS = {"mistral": "#d95f02", "llama-2": "#1b9e77", "llama-3": "#7570b3",
          "qwen": "#e7298a", "mixtral": "#66a61e"}


def pinned_substrate(bench):
    """Return a path to the exact snapshot the W1 analysis ran on.

    The archive is live and src/monitor.py commits new harvests, so substrate/raw/{bench}.npz
    drifts. Drawing the figure from whatever happens to be checked out would show a different
    population from the one the paper reports -- which happened once and is why this exists.
    If the working file does not match the pinned hash, recover the pinned blob from git.
    """
    import hashlib, subprocess, tempfile
    art = os.path.join(RES, "w1_family_signal.json")
    want = json.load(open(art))["substrate_snapshot"]
    live = os.path.join(SUB, f"{bench}.npz")
    have = hashlib.sha256(open(live, "rb").read()).hexdigest()
    if have == want["sha256"]:
        print(f"[{bench}] working substrate matches the pinned snapshot", flush=True)
        return live
    blob = want.get("git_blob")
    if not blob:
        raise SystemExit(f"substrate drifted from the pin and no git blob is recorded in {art}")
    out = os.path.join(tempfile.gettempdir(), f"pinned_{blob[:12]}_{bench}.npz")
    if not os.path.exists(out):
        with open(out, "wb") as f:
            subprocess.run(["git", "cat-file", "blob", blob], cwd=os.path.join(HERE, ".."),
                           stdout=f, check=True)
    got = hashlib.sha256(open(out, "rb").read()).hexdigest()
    if got != want["sha256"]:
        raise SystemExit(f"recovered blob hashes {got[:16]}, expected {want['sha256'][:16]}")
    print(f"[{bench}] working substrate has drifted ({have[:12]}); "
          f"drawing from the pinned snapshot {got[:12]} instead", flush=True)
    return out


def main(bench="arc"):
    rng = np.random.default_rng(SEED)
    z = np.load(pinned_substrate(bench), allow_pickle=True)
    models = np.array([str(m) for m in z["models"]])
    F = (1 - z["prim"]).astype(np.uint8)
    keep = (F.sum(1) > 0) & (F.sum(1) < F.shape[1]); F, models = F[keep], models[keep]
    ck = (F.sum(0) > 0) & (F.sum(0) < F.shape[0]); F = F[:, ck]

    fams = np.array([family_of(m) for m in models])
    from collections import Counter
    counts = Counter(f for f in fams if f != "unattributed")
    keep_f = [f for f, _ in counts.most_common(TOP_FAMILIES)]
    sel = np.isin(fams, keep_f)

    V, _, _, _, _, _ = residual_eigvecs(F, 6, rng)
    Xn = curveball(F, 50 * F.shape[0], rng)
    Vn, _, _, _, _, _ = residual_eigvecs(Xn, 6, rng)

    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.3), sharex=False, sharey=False)
    for ax, W, title in ((axes[0], V, "observed: margin-conditioned residual"),
                         (axes[1], Vn, "exact conditional null (curveball replicate)")):
        Z = W[sel, :2]
        Z = (Z - Z.mean(0)) / (Z.std(0) + 1e-12)
        for f in keep_f:
            m = fams[sel] == f
            ax.scatter(Z[m, 0], Z[m, 1], s=7, alpha=0.65, linewidths=0,
                       c=COLORS[f], label=f"{f} ({m.sum()})")
        ax.set_title(title, fontsize=9)
        ax.set_xlabel("eigenvector 1 (standardised loading)", fontsize=8)
        ax.tick_params(labelsize=7)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    axes[0].set_ylabel("eigenvector 2", fontsize=8)
    axes[0].legend(fontsize=6.5, frameon=False, markerscale=1.8, loc="best", handletextpad=0.2)
    fig.tight_layout()
    out = os.path.join(FIG, "fig_w1_family.pdf")
    fig.savefig(out, bbox_inches="tight")
    fig.savefig(out.replace(".pdf", ".png"), dpi=180, bbox_inches="tight")
    print("wrote", out)


if __name__ == "__main__":
    main()
