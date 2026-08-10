"""Answer the recency objection: does the finding replicate on the v2 (harness-updated) archive?

docs/NEURIPS_BLUEPRINT.md's F8 records the objection this closes: v1's harness snapshots run
2023-07 to 2024-06, and a reviewer could reasonably ask whether the residual-correlation finding
is an artifact of that specific, now-dated evaluation harness rather than a property of the
open-model ecosystem. v2 (src/harvest_v2_arc.py) uses a materially different, newer harness on an
overlapping-but-distinct ARC-Challenge population.

This reuses dedup_sensitivity.stats_for() unchanged -- same Rasch fit, same curveball null
construction (50N burn-in, 5N between draws, 6 replicates), same statistics -- so the v1 and v2
numbers are computed identically and the comparison is not just "two numbers that happened to be
computed somehow."

Run: ./.venv/bin/python src/v2_comparison.py -> results/v2_comparison.json
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from dedup_sensitivity import stats_for  # noqa: E402

SUB = os.path.join(HERE, "..", "substrate", "raw")
RES = os.path.join(HERE, "..", "results")


def main():
    rng = np.random.default_rng(20260810)

    z = np.load(os.path.join(SUB, "arc_v2.npz"), allow_pickle=True)
    F = (1 - z["prim"]).astype(np.uint8)
    print(f"[v2] raw matrix: {F.shape}", flush=True)
    v2 = stats_for(F, rng)
    print(f"[v2]  N={v2['N']} rms {v2['rms_obs']:.4f}/{v2['rms_null']:.4f}="
          f"{v2['rms_ratio']:.2f}x  PR {v2['PR_obs']:.1f}/{v2['PR_null']:.1f}="
          f"{v2['PR_ratio']:.4f}  eig>edge={v2['n_eigen_above_edge']}", flush=True)

    v1 = json.load(open(os.path.join(RES, "dedup_sensitivity.json")))
    v1_arc_full = next(b for b in v1["benchmarks"] if b["bench"] == "arc")["sweep"][0]
    print(f"[v1]  N={v1_arc_full['N']} rms_ratio={v1_arc_full['rms_ratio']:.2f}x "
          f"PR_ratio={v1_arc_full['PR_ratio']:.4f} eig>edge={v1_arc_full['n_eigen_above_edge']}",
          flush=True)

    out = {
        "question": "does the residual-correlation finding replicate on v2's newer harness",
        "v1_arc_full_population": v1_arc_full,
        "v2_arc": v2,
        "v2_n_kept_of_targeted": int(z["models"].shape[0]),
        "rms_ratio_agree_direction": bool(
            (v1_arc_full["rms_ratio"] > 1) == (v2["rms_ratio"] > 1)),
        "PR_ratio_agree_direction": bool(
            (v1_arc_full["PR_ratio"] < 1) == (v2["PR_ratio"] < 1)),
    }
    json.dump(out, open(os.path.join(RES, "v2_comparison.json"), "w"), indent=1)
    print("wrote results/v2_comparison.json")


if __name__ == "__main__":
    main()
