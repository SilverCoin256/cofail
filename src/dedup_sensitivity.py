"""X1/X2 -- the duplication audit. How much of every headline number is duplicate models?

This is the central experiment of the redesigned paper. The Open LLM Leaderboard v1 population is
dominated by fine-tunes, LoRA merges, DPO variants and quantizations of a handful of base
checkpoints. Every reviewer persona that read the manuscript named this as the leading confound,
and KD1 (src/rank_redundancy_control.py) already showed it destroys the top-of-leaderboard
redundancy gradient on three of five benchmarks. This script asks the same question of EVERY
statistic the paper reports, not just that one.

X1 -- a name-based family census. The pre-registered `base_model` route failed at 23.3% coverage
(K5), so lineage is attributed here from the model ID string, which is available for 100% of the
population. This is coarser than a config hash and is reported as a LOWER BOUND on relatedness,
never as a lineage ground truth.

X2 -- dedup sensitivity. Every headline statistic recomputed on populations deduplicated at
agreement thresholds 0.99 / 0.97 / 0.95 / 0.90, with the Rasch fit and the null redrawn from
scratch each time.

PRE-REGISTERED KILL CONDITION (written before execution, 2026-07-28)
--------------------------------------------------------------------
KX1. A statistic is DUPLICATION-DRIVEN if its observed/null ratio moves by more than 2x between
     the full population and the 0.95-deduplicated population. Any such statistic must be reported
     in the paper as a measurement of population redundancy, not of ecosystem concentration.
KX2. If ALL headline statistics are duplication-driven, the paper's entire empirical section is a
     duplication audit and must be retitled as one.
KX3. If NONE are, the duplication objection is answered and the original framing survives.

Run: ./.venv/bin/python src/dedup_sensitivity.py [bench ...] -> results/dedup_sensitivity.json
"""
import json, os, re, sys
from collections import Counter
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nullmodel import curveball, fit_rasch, rasch_P, excess_gram, n_eff_from_excess

SUB = os.path.join(HERE, "..", "substrate", "raw")
RES = os.path.join(HERE, "..", "results")
THRESHOLDS = [1.01, 0.99, 0.97, 0.95, 0.90]
N_NULL = 6

# Base-family patterns, longest/most specific first. Deliberately coarse: this is a lower bound
# on relatedness, not a lineage claim.
FAMILIES = [
    ("llama-3", r"llama[-_ ]?3"), ("llama-2", r"llama[-_ ]?2"), ("codellama", r"code[-_]?llama"),
    ("mistral", r"mistral"), ("mixtral", r"mixtral"), ("qwen", r"qwen"), ("yi", r"\byi[-_]"),
    ("falcon", r"falcon"), ("mpt", r"\bmpt[-_]"), ("pythia", r"pythia"), ("gpt-neox", r"neox"),
    ("gpt-j", r"gpt[-_]?j"), ("gpt2", r"gpt2"), ("bloom", r"bloom"), ("opt", r"\bopt[-_]\d"),
    ("phi", r"\bphi[-_]?\d"), ("gemma", r"gemma"), ("solar", r"solar"), ("zephyr", r"zephyr"),
    ("vicuna", r"vicuna"), ("openchat", r"openchat"), ("tinyllama", r"tinyllama"),
    ("stablelm", r"stablelm"), ("deepseek", r"deepseek"), ("olmo", r"olmo"),
]
MERGE_HINT = re.compile(r"merge|slerp|dare|ties|frankenstein|moe|lazymergekit|slice", re.I)


def family_of(model_id):
    s = model_id.lower()
    for name, pat in FAMILIES:
        if re.search(pat, s):
            return name
    return "unattributed"


def census(models):
    fams = [family_of(str(m)) for m in models]
    c = Counter(fams)
    merges = sum(1 for m in models if MERGE_HINT.search(str(m)))
    attributed = len(models) - c.get("unattributed", 0)
    return {
        "n_models": len(models), "n_attributed": int(attributed),
        "attribution_rate": float(attributed / len(models)),
        "n_merge_named": int(merges),
        "families": dict(c.most_common()),
        "top5_share": float(sum(n for f, n in c.most_common(6) if f != "unattributed") / len(models)),
    }


def dedup_keep(A, thresh):
    """Keep the more accurate member of any pair agreeing at or above `thresh`."""
    N, M = A.shape
    order = np.argsort(-A.mean(1))
    kept = []
    for i in order:
        if not kept:
            kept.append(int(i))
            continue
        K = np.array(kept)
        ag = (A[i] @ A[K].T + (1 - A[i]) @ (1 - A[K]).T) / M
        if ag.max() < thresh:
            kept.append(int(i))
    return np.array(sorted(kept))


def stats_for(F, rng):
    """Every headline statistic, with the null redrawn for this exact population."""
    keep = (F.sum(1) > 0) & (F.sum(1) < F.shape[1])
    F = F[keep]
    ck = (F.sum(0) > 0) & (F.sum(0) < F.shape[0])
    F = F[:, ck]
    N, M = F.shape
    iu = np.triu_indices(N, 1)
    a, b, _ = fit_rasch(F)
    P = rasch_P(a, b)

    def measure(X):
        D = excess_gram(np.ascontiguousarray(X, dtype=np.uint8), P)
        pr, w = n_eff_from_excess(D)
        d = np.sqrt(np.clip(np.diag(D).astype(np.float64), 1e-12, None))
        R = D.astype(np.float64) / d[:, None] / d[None, :]
        return float(np.sqrt((R[iu] ** 2).mean())), float(pr), np.sort(w)[::-1]

    rms_o, pr_o, w_o = measure(F)
    X = curveball(F, 50 * N, rng)
    rms_n, pr_n, edges = [], [], []
    for _ in range(N_NULL):
        X = curveball(X, 5 * N, rng)
        r, p, w = measure(X)
        rms_n.append(r); pr_n.append(p); edges.append(float(w[0]))
    edge = float(np.mean(edges))
    n_above = int((w_o > edge).sum())
    return {
        "N": int(N), "M": int(M),
        "rms_obs": rms_o, "rms_null": float(np.mean(rms_n)),
        "rms_ratio": float(rms_o / np.mean(rms_n)),
        "PR_obs": pr_o, "PR_null": float(np.mean(pr_n)),
        "PR_ratio": float(pr_o / np.mean(pr_n)),
        "null_spectral_edge": edge, "n_eigen_above_edge": n_above,
    }


def run(bench, rng):
    z = np.load(os.path.join(SUB, f"{bench}.npz"), allow_pickle=True)
    models = [str(m) for m in z["models"]]
    F0 = (1 - z["prim"]).astype(np.uint8)
    keep = (F0.sum(1) > 0) & (F0.sum(1) < F0.shape[1])
    F0, models = F0[keep], [m for m, k in zip(models, keep) if k]
    ck = (F0.sum(0) > 0) & (F0.sum(0) < F0.shape[0])
    F0 = F0[:, ck]
    A0 = (1 - F0).astype(np.float32)

    cen = census(models)
    print(f"[{bench}] census: {cen['n_models']} models, "
          f"{cen['attribution_rate']*100:.0f}% attributed to a named base family, "
          f"{cen['n_merge_named']} merge-named, top-5 families = {cen['top5_share']*100:.0f}%",
          flush=True)

    rows = []
    for th in THRESHOLDS:
        idx = np.arange(A0.shape[0]) if th > 1.0 else dedup_keep(A0, th)
        s = stats_for(F0[idx], rng)
        s["threshold"] = th
        s["n_removed"] = int(A0.shape[0] - len(idx))
        rows.append(s)
        print(f"   thr={th:<5} N={s['N']:>5} (-{s['n_removed']:>4})  "
              f"rms {s['rms_obs']:.4f}/{s['rms_null']:.4f}={s['rms_ratio']:>6.2f}x   "
              f"PR {s['PR_obs']:>7.1f}/{s['PR_null']:>6.1f}={s['PR_ratio']:.4f}   "
              f"eig>edge={s['n_eigen_above_edge']}", flush=True)

    full = rows[0]
    at95 = next(r for r in rows if r["threshold"] == 0.95)
    verdict = {}
    for key in ("rms_ratio", "PR_ratio"):
        a_, b_ = full[key], at95[key]
        mv = max(a_ / b_, b_ / a_) if min(a_, b_) > 0 else float("inf")
        verdict[key] = {"full": a_, "at_0.95": b_, "move_factor": float(mv),
                        "duplication_driven": bool(mv > 2.0)}
    verdict["n_eigen_above_edge"] = {
        "full": full["n_eigen_above_edge"], "at_0.95": at95["n_eigen_above_edge"],
        "duplication_driven": bool(
            full["n_eigen_above_edge"] > 0 and
            max(full["n_eigen_above_edge"] / max(at95["n_eigen_above_edge"], 1),
                max(at95["n_eigen_above_edge"], 1) / full["n_eigen_above_edge"]) > 2.0)}
    return {"bench": bench, "census": cen, "sweep": rows, "KX1_verdict": verdict}


def main(benches):
    rng = np.random.default_rng(20260728)
    res = []
    for bch in benches:
        if not os.path.exists(os.path.join(SUB, f"{bch}.npz")):
            continue
        res.append(run(bch, rng))

    flags = [(r["bench"], k, v["duplication_driven"])
             for r in res for k, v in r["KX1_verdict"].items()]
    n_driven = sum(1 for _, _, d in flags if d)
    out = {"thresholds": THRESHOLDS, "n_null": N_NULL, "benchmarks": res,
           "n_statistic_bench_pairs": len(flags), "n_duplication_driven": n_driven,
           "KX2_all_driven": bool(n_driven == len(flags)),
           "KX3_none_driven": bool(n_driven == 0)}
    json.dump(out, open(os.path.join(RES, "dedup_sensitivity.json"), "w"), indent=1)
    print(f"\n{n_driven}/{len(flags)} statistic-benchmark pairs are duplication-driven "
          f"(ratio moves >2x by the 0.95 threshold)")
    for b, k, d in flags:
        if d:
            print(f"   DUPLICATION-DRIVEN: {b} / {k}")
    if out["KX3_none_driven"]:
        print("KX3: no statistic is duplication-driven -- the objection is answered")
    elif out["KX2_all_driven"]:
        print("KX2: every statistic is duplication-driven -- the paper is a duplication audit")


if __name__ == "__main__":
    main(sys.argv[1:] or ["arc", "winogrande", "truthfulqa", "gsm8k", "hellaswag"])
