"""KILL-TEST: does margin-conditioned diversity actually BUY anything downstream?

The proposed NeurIPS spine is: "the standard diversity/agreement metric is degenerate, here is
the exact fit-free correction, and USING the correction changes a decision you would actually
make." The decision chosen is panel/ensemble construction: pick k models out of a pool, take a
majority vote, measure accuracy.

If margin-conditioned selection does not beat naive-diversity selection at matched accuracy,
there is no capability, and the spine is dead. That must be findable in one run, before any
paper is restructured around it.

PRE-REGISTERED KILL CONDITION (written before execution, 2026-07-28)
--------------------------------------------------------------------
KS1. Let d(k) = acc[acc-gated + cond-div] - acc[acc-gated + naive-div] at panel size k,
     paired within each item-split seed. The spine SURVIVES only if the 95% bootstrap CI of
     mean d(k) over seeds excludes zero on the positive side for at least 4 of the 6 panel
     sizes k in {3,5,7,9,11,15}. Otherwise KS1 FIRES: conditioned diversity does not improve
     panel construction, and the blueprint must find a different Monday-morning consequence
     (candidates: judge-panel effective size, eval-set design, benchmark reliability).

KS2. Guard against the trivial confound: if `acc-gated + cond-div` wins only because it happens
     to select HIGHER MEAN ACCURACY members than `acc-gated + naive-div`, the win is not about
     diversity. Report mean member accuracy per strategy. If the cond-div panels have higher
     mean member accuracy AND the accuracy gap explains the vote gap, KS2 fires.

LEAKAGE GUARD: every selection statistic (accuracy, disagreement, Rasch fit, residual
correlation) is computed on the SEL item half ONLY. Majority-vote accuracy is measured on the
disjoint EVAL half. Selecting models on the same items you score them on would manufacture the
result; that is the single most likely way this experiment could lie.

Run: python src/selection_killtest.py [n_seeds]  ->  results/selection_killtest.json
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from nullmodel import fit_rasch, rasch_P, excess_gram
from harvest_responses import recover_gold, SENTINEL

SUB = os.path.join(HERE, "..", "substrate", "raw")
RES = os.path.join(HERE, "..", "results")

PANEL_SIZES = [3, 5, 7, 9, 11, 15]
ACC_GATE = 100          # accuracy-gated strategies diversify within the top-100 models
STRATEGIES = ["random", "top-acc", "gated-naive-div", "gated-cond-div",
              "pure-naive-div", "pure-cond-div"]


def majority_vote(choice, gold, subset, rng):
    """Mode of the panel's chosen options per item; ties broken uniformly at random.

    Items where a panel member is unparseable (SENTINEL) still vote with the members that
    parsed. Items with no recovered gold are excluded by the caller.
    """
    sub = choice[subset]                      # k x M
    M = sub.shape[1]
    K = int(sub.max()) + 1
    if K < 1:
        return np.zeros(M, dtype=bool)
    # counts[c, m] = how many panel members chose option c on item m
    counts = np.zeros((K, M), dtype=np.int16)
    for c in range(K):
        counts[c] = (sub == c).sum(0)
    best = counts.max(0)
    # random tie-break among the argmax options
    tie = (counts == best[None, :])
    r = rng.random((K, M)) * tie
    pick = r.argmax(0)
    voted_nothing = best == 0
    correct = (pick == gold) & ~voted_nothing
    return correct


def greedy_diverse(score_matrix, pool, k, seed_idx, minimize):
    """Greedy panel growth. score_matrix is a pool x pool pairwise similarity/agreement.

    minimize=True  -> add the model with the lowest mean similarity to the current panel
    minimize=False -> add the model with the highest mean value (used for disagreement)
    """
    chosen = [seed_idx]
    remaining = [i for i in range(len(pool)) if i != seed_idx]
    while len(chosen) < k and remaining:
        sub = score_matrix[np.ix_(remaining, chosen)].mean(1)
        j = int(sub.argmin() if minimize else sub.argmax())
        chosen.append(remaining.pop(j))
    return [pool[i] for i in chosen]


def run_seed(choice, acc, gold, seed):
    rng = np.random.default_rng(seed)
    N, M = choice.shape
    have_gold = gold != SENTINEL
    items = np.where(have_gold)[0]
    rng.shuffle(items)
    half = len(items) // 2
    sel_items, eval_items = np.sort(items[:half]), np.sort(items[half:])

    A_sel = acc[:, sel_items]                       # N x M_sel correctness
    model_acc = A_sel.mean(1)

    # ---- selection statistics, SEL half only -------------------------------------------
    F = (1 - A_sel).astype(np.uint8)                # failure matrix
    keep = (F.sum(1) > 0) & (F.sum(1) < F.shape[1])
    idx_keep = np.where(keep)[0]
    Fk = F[keep]
    ck = (Fk.sum(0) > 0) & (Fk.sum(0) < Fk.shape[0])
    Fk = Fk[:, ck]

    a, b, _ = fit_rasch(Fk)
    P = rasch_P(a, b)
    D = excess_gram(Fk, P)
    d = np.sqrt(np.clip(np.diag(D).astype(np.float64), 1e-12, None))
    R = D.astype(np.float64) / d[:, None] / d[None, :]     # conditioned residual correlation
    np.fill_diagonal(R, 0.0)

    # naive (unconditioned) pairwise DISAGREEMENT on raw correctness -- what people actually use
    Ak = A_sel[idx_keep]
    agree = (Ak @ Ak.T + (1 - Ak) @ (1 - Ak).T) / Ak.shape[1]
    disagree = 1.0 - agree
    np.fill_diagonal(disagree, 0.0)

    acc_k = model_acc[idx_keep]
    order = np.argsort(-acc_k)
    gate = order[:ACC_GATE]

    out = {}
    for k in PANEL_SIZES:
        panels = {}
        panels["random"] = rng.choice(idx_keep, size=k, replace=False).tolist()
        panels["top-acc"] = idx_keep[order[:k]].tolist()

        # accuracy-gated: same candidate pool, same seed member -> isolates the METRIC
        seed_local = int(gate[0])
        gate_pool = gate.tolist()
        gpos = {m: i for i, m in enumerate(gate_pool)}
        Rg = R[np.ix_(gate_pool, gate_pool)]
        Dg = disagree[np.ix_(gate_pool, gate_pool)]
        panels["gated-cond-div"] = [idx_keep[gate_pool[i]] for i in
                                    greedy_diverse(Rg, list(range(len(gate_pool))), k,
                                                   gpos[seed_local], minimize=True)]
        panels["gated-naive-div"] = [idx_keep[gate_pool[i]] for i in
                                     greedy_diverse(Dg, list(range(len(gate_pool))), k,
                                                    gpos[seed_local], minimize=False)]

        # ungated versions, to show whether accuracy gating is doing the work
        allp = list(range(len(idx_keep)))
        panels["pure-cond-div"] = [idx_keep[i] for i in
                                   greedy_diverse(R, allp, k, int(order[0]), minimize=True)]
        panels["pure-naive-div"] = [idx_keep[i] for i in
                                    greedy_diverse(disagree, allp, k, int(order[0]),
                                                   minimize=False)]

        res = {}
        for name, subset in panels.items():
            subset = list(map(int, subset))
            corr = majority_vote(choice[:, eval_items], gold[eval_items], subset, rng)
            res[name] = {
                "vote_acc": float(corr.mean()),
                "mean_member_acc_sel": float(model_acc[subset].mean()),
                "mean_member_acc_eval": float(acc[np.ix_(subset, eval_items)].mean()),
                "mean_pair_R": float(R[np.ix_([list(idx_keep).index(s) for s in subset],
                                              [list(idx_keep).index(s) for s in subset])].mean()),
            }
        out[k] = res
    return out


def main(n_seeds=8):
    z = np.load(os.path.join(SUB, "arc_resp.npz"), allow_pickle=True)
    choice, acc = z["choice"], z["acc"]
    gold, agree_rate, n_rec = recover_gold(choice, acc)
    print(f"gold recovered on {n_rec}/{choice.shape[1]} items, "
          f"agreement among correct models {agree_rate:.4f}", flush=True)

    per_seed = []
    for s in range(n_seeds):
        r = run_seed(choice, acc, gold, 20260728 + s)
        per_seed.append(r)
        line = "  ".join(f"k={k}:" + ",".join(
            f"{n[:4]}={r[k][n]['vote_acc']:.4f}" for n in ("gated-cond-div", "gated-naive-div"))
            for k in PANEL_SIZES)
        print(f"[seed {s}] {line}", flush=True)

    # ---- paired bootstrap on the decisive contrast ---------------------------------------
    rng = np.random.default_rng(7)
    summary, verdict = {}, {}
    for k in PANEL_SIZES:
        d = np.array([per_seed[s][k]["gated-cond-div"]["vote_acc"]
                      - per_seed[s][k]["gated-naive-div"]["vote_acc"] for s in range(n_seeds)])
        bs = np.array([rng.choice(d, size=len(d), replace=True).mean() for _ in range(20000)])
        lo, hi = np.percentile(bs, [2.5, 97.5])
        summary[k] = {
            "mean_diff": float(d.mean()), "ci95": [float(lo), float(hi)],
            "excludes_zero_positive": bool(lo > 0),
            "per_strategy": {n: {
                "vote_acc_mean": float(np.mean([per_seed[s][k][n]["vote_acc"]
                                                for s in range(n_seeds)])),
                "member_acc_eval_mean": float(np.mean([per_seed[s][k][n]["mean_member_acc_eval"]
                                                       for s in range(n_seeds)])),
                "mean_pair_R": float(np.mean([per_seed[s][k][n]["mean_pair_R"]
                                              for s in range(n_seeds)])),
            } for n in STRATEGIES},
        }
        verdict[k] = summary[k]["excludes_zero_positive"]

    n_pass = sum(verdict.values())
    ks1_fires = n_pass < 4
    # KS2: does the winner simply hold more accurate members?
    ks2_flags = {k: (summary[k]["per_strategy"]["gated-cond-div"]["member_acc_eval_mean"]
                     > summary[k]["per_strategy"]["gated-naive-div"]["member_acc_eval_mean"])
                 for k in PANEL_SIZES}

    out = {
        "n_seeds": n_seeds, "panel_sizes": PANEL_SIZES, "acc_gate": ACC_GATE,
        "gold_recovery": {"n_items": int(n_rec), "agreement": float(agree_rate)},
        "summary": {str(k): v for k, v in summary.items()},
        "KS1_fires": bool(ks1_fires), "KS1_n_panel_sizes_positive": int(n_pass),
        "KS2_member_acc_higher_for_cond": {str(k): bool(v) for k, v in ks2_flags.items()},
    }
    os.makedirs(RES, exist_ok=True)
    json.dump(out, open(os.path.join(RES, "selection_killtest.json"), "w"), indent=1)

    print("\n=== VERDICT ===")
    for k in PANEL_SIZES:
        s = summary[k]
        print(f"k={k:2d}  cond {s['per_strategy']['gated-cond-div']['vote_acc_mean']:.4f}  "
              f"naive {s['per_strategy']['gated-naive-div']['vote_acc_mean']:.4f}  "
              f"top-acc {s['per_strategy']['top-acc']['vote_acc_mean']:.4f}  "
              f"diff {s['mean_diff']:+.4f} CI[{s['ci95'][0]:+.4f},{s['ci95'][1]:+.4f}]  "
              f"{'PASS' if verdict[k] else 'ns'}")
    print(f"\nKS1 {'FIRES -- spine refuted' if ks1_fires else 'survives'} "
          f"({n_pass}/6 panel sizes positive)")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8)
