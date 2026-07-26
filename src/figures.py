"""Publication figures. Every figure is generated from a results/*.json artifact -- nothing is
drawn from hard-coded numbers, so a figure cannot silently drift from the run that produced it.

Output: figures/fig<N>_<name>.pdf (vector) and .png (preview).
Run: python figures.py
"""
import json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "results")
FIG = os.path.join(HERE, "..", "figures")
os.makedirs(FIG, exist_ok=True)

BENCHES = ["arc", "winogrande", "truthfulqa", "gsm8k"]
NICE = {"arc": "ARC-Challenge", "winogrande": "Winogrande",
        "truthfulqa": "TruthfulQA", "gsm8k": "GSM8K", "hellaswag": "HellaSwag"}
# Okabe-Ito, colourblind-safe
CB = {"obs": "#0072B2", "null": "#D55E00", "grey": "#767676",
      "ok": "#009E73", "warn": "#CC79A7", "y": "#E69F00"}

plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 300, "font.size": 9,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.5,
    "legend.frameon": False, "axes.titlesize": 9.5, "axes.titleweight": "bold",
})


def J(name):
    p = os.path.join(RES, name)
    return json.load(open(p)) if os.path.exists(p) else None


def save(fig, n, name):
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(FIG, f"fig{n}_{name}.{ext}"), bbox_inches="tight")
    plt.close(fig)
    print(f"  fig{n}_{name}", flush=True)


def have(b):
    return J(f"{b}_results.json") is not None


def fig2_closed_form():
    """Proposition 2 validated on real data: measured naive excess vs closed form."""
    bs = [b for b in BENCHES if have(b)]
    fig, ax = plt.subplots(1, 2, figsize=(7.6, 2.9), width_ratios=[1.15, 1])
    fig.subplots_adjust(wspace=0.42)
    xs, ys, res = [], [], []
    for b in bs:
        d = J(f"{b}_results.json")["E0_validation"]
        xs.append(d["naive_excess_closed_form"]); ys.append(d["naive_excess_empirical"])
        res.append(abs(d["residual"]))
    lim = [0, max(xs + ys) * 1.15]
    ax[0].plot(lim, lim, "--", c=CB["grey"], lw=1, label="y = x")
    ax[0].scatter(xs, ys, s=55, c=CB["obs"], zorder=3)
    for b, x, y in zip(bs, xs, ys):
        ax[0].annotate(NICE[b], (x, y), textcoords="offset points", xytext=(7, -3), fontsize=7.5)
    ax[0].set_xlim(lim); ax[0].set_ylim(lim)
    ax[0].set_xlabel("closed form  $[N\\,\\mathrm{Var}_m(f)+\\mathrm{Var}_i(p)-\\bar f(1-\\bar f)]/(N-1)$")
    ax[0].set_ylabel("measured naive excess")
    ax[0].set_title("a  Lemma 2 predicts the reported excess exactly", fontsize=8.8)
    ax[0].legend(loc="upper left")

    ax[1].bar(range(len(bs)), res, color=CB["ok"], width=0.55)
    ax[1].set_yscale("log")
    ax[1].axhline(1e-9, ls="--", c=CB["warn"], lw=1)
    ax[1].text(0.02, 1.4e-9, "kill condition K6 threshold", fontsize=7, color=CB["warn"],
               transform=ax[1].get_yaxis_transform())
    ax[1].set_xticks(range(len(bs)))
    ax[1].set_xticklabels([NICE[b] for b in bs], rotation=20, ha="right", fontsize=7.5)
    ax[1].set_ylabel("|measured $-$ closed form|")
    ax[1].set_ylim(1e-18, 1e-7)
    ax[1].set_title("b  Residuals at machine precision", fontsize=8.8)
    save(fig, 2, "closed_form")


def fig3_decomposition():
    """The reported excess is entirely a marginal artifact."""
    bs = [b for b in BENCHES if have(b)]
    naive = [J(f"{b}_results.json")["E2_decomposition"]["naive_excess_over_independence"] for b in bs]
    resid = [abs(J(f"{b}_results.json")["E2_decomposition"]["residual_mean_excess"]) for b in bs]
    x = np.arange(len(bs))
    fig, ax = plt.subplots(figsize=(5.6, 3.0))
    ax.bar(x - 0.19, naive, 0.36, color=CB["null"], label="reported excess over independence")
    ax.bar(x + 0.19, np.maximum(resid, 1e-18), 0.36, color=CB["obs"],
           label="residual after conditioning on margins")
    for xi, v in zip(x, naive):
        ax.text(xi - 0.19, v + 0.003, f"{v:+.3f}", ha="center", fontsize=7)
    for xi, v in zip(x, resid):
        ax.text(xi + 0.19, 0.004, f"{v:.0e}", ha="center", fontsize=6.5, rotation=90,
                color=CB["obs"])
    ax.set_xticks(x); ax.set_xticklabels([NICE[b] for b in bs], rotation=15, ha="right")
    ax.set_ylabel("mean pairwise co-failure excess")
    ax.set_title("Conditioning on item difficulty removes 100% of the reported excess")
    ax.legend(loc="upper right", fontsize=7.5)
    save(fig, 3, "decomposition")


def fig4_neff():
    """N_eff observed vs the margin-preserving null."""
    src = {}
    for b in BENCHES:
        d = J(f"{b}_null_independent.json")
        if d:
            src[b] = (d["N_eff"]["observed"], d["N_eff"]["null_mean"], d["N_eff"]["null_sd"],
                      d["N"], d["N_eff"]["ratio"])
        elif have(b):
            e = J(f"{b}_results.json")["E3_neff"]
            src[b] = (e["N_eff_participation_conditioned"], e["N_eff_null_mean"],
                      e["N_eff_null_sd"], e["N"], e["N_eff_ratio_obs_over_null"])
    bs = list(src)
    x = np.arange(len(bs))
    w = 0.26
    fig, ax = plt.subplots(figsize=(6.6, 3.4))
    ax.bar(x - w, [src[b][3] for b in bs], w, color=CB["grey"], alpha=0.45,
           label="nominal model count $N$")
    ax.bar(x, [src[b][1] for b in bs], w, yerr=[src[b][2] for b in bs],
           color=CB["null"], capsize=3, ecolor="0.2",
           label="$N_{\\mathrm{eff}}$ under margin-preserving null")
    ax.bar(x + w, [src[b][0] for b in bs], w, color=CB["obs"],
           label="$N_{\\mathrm{eff}}$ observed")
    for xi, b in zip(x, bs):
        ax.text(xi - w, src[b][3] * 1.12, f"{src[b][3]:.0f}", ha="center", fontsize=7,
                color="0.35")
        ax.text(xi, src[b][1] * 1.14, f"{src[b][1]:.0f}", ha="center", fontsize=7,
                color=CB["null"])
        ax.text(xi + w, src[b][0] * 1.16, f"{src[b][0]:.0f}", ha="center", fontsize=8.5,
                color=CB["obs"], fontweight="bold")
        ax.text(xi + w, src[b][0] * 0.55, f"{src[b][4]*100:.1f}%\nof null", ha="center",
                fontsize=6.5, color="white", fontweight="bold", linespacing=0.95)
    ax.set_yscale("log")
    ax.set_xticks(x); ax.set_xticklabels([NICE[b] for b in bs], fontsize=8.5)
    # NB: the participation ratio is N/(1+(N-1)*mean R_ij^2) and does NOT count independent
    # models -- it cannot separate one weak global factor from many tight clusters. Titled and
    # labelled accordingly; see results/RESULTS_DIGEST.md section C2.
    ax.set_ylabel("participation ratio of conditioned excess spectrum")
    ax.set_title("Margin-conditioned residual concentration, against an exact-margin null")
    ax.legend(loc="lower left", bbox_to_anchor=(0.0, 1.06), ncol=1, fontsize=7.2)
    ax.set_ylim(3, 6000)
    save(fig, 4, "neff")


def fig5_dedup():
    """N_eff is not an artifact of near-duplicate models."""
    fig, ax = plt.subplots(figsize=(5.8, 3.1))
    marks = ["o", "s", "^", "D"]
    any_ = False
    for k, b in enumerate(BENCHES):
        d = J(f"{b}_dedup.json")
        if not d:
            continue
        any_ = True
        lv = d["levels"]
        xs, ys = [], []
        for key, r in lv.items():
            xs.append(r["N"]); ys.append(r["N_eff"])
        o = np.argsort(xs)
        ax.plot(np.array(xs)[o], np.array(ys)[o], marks[k] + "-", ms=4.5, lw=1.3,
                label=NICE[b])
    if not any_:
        plt.close(fig); return
    ax.set_xlabel("models retained after removing near-duplicates")
    ax.set_ylabel("$N_{\\mathrm{eff}}$ observed")
    ax.set_title("Removing up to two-thirds of models barely changes $N_{\\mathrm{eff}}$")
    ax.legend(fontsize=7.5)
    save(fig, 5, "dedup")


def fig6_spectrum():
    """Eigenspectrum: raw vs margin-conditioned."""
    d = J("arc_results.json")
    if not d:
        return
    e = d["E3_neff"]
    fig, ax = plt.subplots(figsize=(5.4, 3.0))
    k = np.arange(1, len(e["top10_eigs_raw"]) + 1)
    ax.plot(k, e["top10_eigs_raw"], "o-", c=CB["grey"], ms=4,
            label="raw correlation (unconditioned)")
    ax.plot(k, e["top10_eigs_conditioned"], "s-", c=CB["obs"], ms=4,
            label="margin-conditioned excess")
    ax.set_yscale("log")
    ax.set_xlabel("eigenvalue rank"); ax.set_ylabel("eigenvalue")
    ax.set_title("ARC: the raw spectrum is one giant difficulty factor")
    ax.legend(fontsize=7.5)
    save(fig, 6, "spectrum")


def fig7_convergence():
    """Curveball mixing diagnostic."""
    d = J("arc_results.json")
    if not d:
        return
    tr = d["E7_convergence"]
    x = [r["trades_per_N"] for r in tr]
    T = [r["T"] for r in tr]
    fc = [r["frac_cells_changed"] for r in tr]
    fig, ax = plt.subplots(figsize=(5.4, 3.0))
    ax.plot(x, T, "o-", c=CB["obs"], ms=4, label="statistic $T$")
    ax.axvline(50, ls="--", c=CB["warn"], lw=1)
    ax.text(52, min(T) + 0.05 * (max(T) - min(T)), "burn-in used", fontsize=7, color=CB["warn"])
    ax.set_xscale("symlog"); ax.set_xlabel("curveball trades per model (trades / N)")
    ax.set_ylabel("$T = \\mathrm{Var}_{ij}(C_{ij})$", color=CB["obs"])
    ax.yaxis.set_major_formatter(ScalarFormatter(useMathText=True))
    ax2 = ax.twinx(); ax2.grid(False)
    ax2.plot(x, fc, "s--", c=CB["grey"], ms=3.5, label="fraction of cells changed")
    ax2.set_ylabel("fraction of cells changed", color=CB["grey"])
    ax.set_title("Chain reaches its plateau by ~10 trades/N")
    save(fig, 7, "convergence")


def fig8_controls():
    """Estimator controls."""
    d = J("controls.json")
    if not d:
        return
    keys = [k for k in d if isinstance(d[k], dict) and "SES" in d[k]]
    lbl = {"C1_negative_rasch_generated": "C1 Rasch-generated\n(expect ≈0)",
           "C2_positive_eight_families": "C2 eight families\n(expect ≫0)",
           "C3_positive_exact_clones": "C3 exact clones\n(expect >0)",
           "C4_negative_column_shuffled_real": "C4 shuffled real\n(expect ≈0)"}
    v = [d[k]["SES"] for k in keys]
    col = [CB["ok"] if ("negative" in k) == (abs(d[k]["SES"]) < 2) else CB["warn"] for k in keys]
    fig, ax = plt.subplots(figsize=(5.4, 2.9))
    ax.bar(range(len(keys)), v, color=col, width=0.55)
    ax.axhline(0, c="k", lw=0.8)
    ax.set_xticks(range(len(keys)))
    ax.set_xticklabels([lbl.get(k, k) for k in keys], fontsize=7)
    ax.set_ylabel("SES of $T$ vs null")
    ax.set_title("Estimator recovers known structure and reports none when there is none")
    for i, val in enumerate(v):
        ax.text(i, val + (0.25 if val >= 0 else -0.5), f"{val:+.2f}", ha="center", fontsize=7.5)
    save(fig, 8, "controls")


def fig9_cohort():
    """N_eff / N by release cohort."""
    fig, ax = plt.subplots(figsize=(6.0, 3.1))
    any_ = False
    for b in BENCHES:
        d = J(f"{b}_results.json")
        if not d or not d.get("E4_cohort"):
            continue
        c = d["E4_cohort"]
        if len(c) < 3:
            continue
        any_ = True
        ax.plot([r["cohort"] for r in c], [r["N_eff_over_N"] for r in c], "o-", ms=4,
                lw=1.3, label=NICE[b])
    if not any_:
        plt.close(fig); return
    ax.set_ylabel("$N_{\\mathrm{eff}} / N$ within cohort")
    ax.set_xlabel("release cohort (month of leaderboard snapshot)")
    ax.set_title("Effective independence per release cohort")
    ax.tick_params(axis="x", rotation=45, labelsize=7)
    ax.legend(fontsize=7.5)
    save(fig, 9, "cohort")


if __name__ == "__main__":
    print("generating figures...", flush=True)
    for fn in (fig2_closed_form, fig3_decomposition, fig4_neff, fig5_dedup,
               fig6_spectrum, fig7_convergence, fig8_controls, fig9_cohort):
        try:
            fn()
        except Exception as e:
            print(f"  SKIP {fn.__name__}: {type(e).__name__}: {e}", flush=True)
