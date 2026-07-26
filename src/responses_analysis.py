"""Proposition 3 and H4 on real model RESPONSES (not just correctness).

Two nulls are needed here and they do different jobs.

1. Composition-preserving permutation (permute response labels within each item).
   Proposition 3 says the agreement statistic is EXACTLY invariant under this, so the null is
   degenerate -- zero variance. That is the proof, demonstrated on real data; it is not a
   calibration.

2. Conditional-independence expectation. For item m let q_mk be the share of WRONG models
   choosing distractor k. If models err independently given the item, the chance two wrong
   models coincide on item m is sum_k q_mk^2. Averaging over the items where both are wrong
   gives a per-pair expectation that already absorbs item-level distractor attractiveness.
   The excess over THIS is what can carry information, and it is what H4 is tested on.

H4: the prior-art comparative claim (more accurate models have more correlated errors) does not
survive conditioning. K7 kills H4 if the slope survives with a CI excluding zero.

Run: python responses_analysis.py [bench]  ->  results/<bench>_responses.json
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from harvest_responses import recover_gold, SENTINEL

SUB = os.path.join(HERE, "..", "substrate", "raw")
RES = os.path.join(HERE, "..", "results")
os.makedirs(RES, exist_ok=True)


def pair_stats(choice, wrong, K, pairs):
    """For each sampled pair: observed agreement-when-both-wrong and its
    conditional-independence expectation."""
    M = choice.shape[1]
    # per-item distractor shares among wrong models
    q2 = np.zeros(M)                       # sum_k q_mk^2
    for m in range(M):
        w = choice[wrong[:, m], m]
        w = w[w >= 0]
        if w.size < 2:
            q2[m] = np.nan
            continue
        _, c = np.unique(w, return_counts=True)
        p = c / c.sum()
        q2[m] = (p * p).sum()
    obs, exp, nboth = [], [], []
    for i, j in pairs:
        both = wrong[i] & wrong[j] & (choice[i] >= 0) & (choice[j] >= 0) & ~np.isnan(q2)
        n = int(both.sum())
        if n < 20:
            obs.append(np.nan); exp.append(np.nan); nboth.append(n); continue
        obs.append(float((choice[i][both] == choice[j][both]).mean()))
        exp.append(float(q2[both].mean()))
        nboth.append(n)
    return np.array(obs), np.array(exp), np.array(nboth), q2


def perm_within_item(choice, rng):
    X = choice.copy()
    for m in range(X.shape[1]):
        col = X[:, m].copy()
        rng.shuffle(col)
        X[:, m] = col
    return X


def global_agreement(choice, wrong):
    """Population statistic A = sum_m sum_k n_mk(n_mk-1) / sum_m n_m(n_m-1) over wrong models."""
    num = den = 0
    for m in range(choice.shape[1]):
        w = choice[wrong[:, m], m]
        w = w[w >= 0]
        if w.size < 2:
            continue
        _, c = np.unique(w, return_counts=True)
        num += int((c * (c - 1)).sum())
        den += int(w.size * (w.size - 1))
    return num / den if den else float("nan")


def main(bench="arc", n_pairs=40000, seed=20260726):
    rng = np.random.default_rng(seed)
    z = np.load(os.path.join(SUB, f"{bench}_resp.npz"), allow_pickle=True)
    choice, acc, nch = z["choice"], z["acc"], z["nchoice"]
    models = [str(m) for m in z["models"]]
    N, M = choice.shape
    print(f"{bench}: {N} models x {M} items", flush=True)

    gold, agree_rate, n_rec = recover_gold(choice, acc)
    ok_items = gold >= 0
    print(f"  gold recovered for {n_rec}/{M} items; agreement among correct models "
          f"= {agree_rate:.4f}", flush=True)

    # validation: does the recovered gold reproduce each model's reported acc?
    pred_correct = (choice[:, ok_items] == gold[ok_items][None, :])
    rep = acc[:, ok_items] == 1
    valid = float((pred_correct == rep).mean())
    print(f"  recovered gold reproduces reported acc on {valid:.4%} of model-item cells",
          flush=True)

    choice = choice[:, ok_items]
    accg = acc[:, ok_items]
    wrong = (accg == 0) & (choice >= 0)
    K = int(np.nanmax(nch)) if nch.size else 4

    A_obs = global_agreement(choice, wrong)
    uni = 1.0 / max(K - 1, 1)
    perms = []
    for _ in range(8):
        Xp = perm_within_item(choice, rng)
        wp = wrong  # composition of RESPONSES is what is permuted
        perms.append(global_agreement(Xp, wp))
    perms = np.array(perms)

    idx = rng.integers(0, choice.shape[0], size=(n_pairs, 2))
    idx = idx[idx[:, 0] != idx[:, 1]]
    obs, exp, nboth, q2 = pair_stats(choice, wrong, K, idx)
    m = ~np.isnan(obs)
    obs, exp, nboth = obs[m], exp[m], nboth[m]
    idx = idx[m]

    p_correct = accg.mean(1)
    pair_acc = (p_correct[idx[:, 0]] + p_correct[idx[:, 1]]) / 2
    raw_excess = obs - uni
    cond_excess = obs - exp

    def slope(x, y, B=400):
        b = np.polyfit(x, y, 1)[0]
        bs = [np.polyfit(x[s], y[s], 1)[0]
              for s in (rng.integers(0, len(x), len(x)) for _ in range(B))]
        lo, hi = np.percentile(bs, [2.5, 97.5])
        return float(b), float(lo), float(hi)

    s_raw = slope(pair_acc, raw_excess)
    s_cond = slope(pair_acc, cond_excess)
    attn = 1 - abs(s_cond[0]) / abs(s_raw[0]) if s_raw[0] else None
    k7 = not (s_cond[1] > 0 or s_cond[2] < 0)   # H4 survives if conditioned CI includes 0

    out = {
        "bench": bench, "N": int(N), "M_used": int(ok_items.sum()), "K_max": K,
        "gold_recovery": {"items_recovered": int(n_rec),
                          "agreement_among_correct_models": agree_rate,
                          "reproduces_reported_acc_frac": valid},
        "proposition3": {
            "observed_agreement_both_wrong": A_obs,
            "uniform_baseline": uni,
            "apparent_excess_vs_uniform": A_obs - uni,
            "composition_permutation_null_mean": float(perms.mean()),
            "composition_permutation_null_sd": float(perms.std(ddof=1)),
            "excess_over_composition_null": float(A_obs - perms.mean()),
            "n_perm": int(perms.size),
        },
        "H4": {
            "n_pairs": int(len(obs)),
            "mean_observed_agreement": float(obs.mean()),
            "mean_conditional_independence_expectation": float(exp.mean()),
            "mean_excess_over_conditional_independence": float(cond_excess.mean()),
            "slope_raw_excess_vs_accuracy": {"beta": s_raw[0], "ci95": [s_raw[1], s_raw[2]]},
            "slope_conditioned_excess_vs_accuracy": {"beta": s_cond[0], "ci95": [s_cond[1], s_cond[2]]},
            "attenuation": attn,
            "K7_H4_supported": bool(k7),
        },
    }
    p3 = out["proposition3"]
    print(f"  PROP 3  observed A={p3['observed_agreement_both_wrong']:.4f}  "
          f"uniform={uni:.4f}  apparent excess={p3['apparent_excess_vs_uniform']:+.4f}",
          flush=True)
    print(f"          composition-null mean={p3['composition_permutation_null_mean']:.4f} "
          f"sd={p3['composition_permutation_null_sd']:.2e}  "
          f"excess over null={p3['excess_over_composition_null']:+.2e}", flush=True)
    h = out["H4"]
    print(f"  H4      mean observed agreement={h['mean_observed_agreement']:.4f}  "
          f"cond-indep expectation={h['mean_conditional_independence_expectation']:.4f}  "
          f"excess={h['mean_excess_over_conditional_independence']:+.4f}", flush=True)
    print(f"          slope vs accuracy: raw {s_raw[0]:+.4f} [{s_raw[1]:+.4f},{s_raw[2]:+.4f}]  "
          f"conditioned {s_cond[0]:+.4f} [{s_cond[1]:+.4f},{s_cond[2]:+.4f}]", flush=True)
    print(f"          attenuation={attn:.1%}  -> H4 {'SUPPORTED' if k7 else 'REFUTED (K7 fires)'}",
          flush=True)
    json.dump(out, open(os.path.join(RES, f"{bench}_responses.json"), "w"), indent=1)
    return out


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "arc")
