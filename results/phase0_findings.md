# Phase 0 — Feasibility Spike: FINDINGS (executed, not assumed)
All results below were produced by running code against live public data. Reproduce with `src/spike_harmonize.py`.

## Gate: does the data substrate exist and is it usable? — **PASS**

| Check | Result | Evidence |
|---|---|---|
| Per-item eval logs public? | **YES**, ungated | `open-llm-leaderboard-old/details_*` returns `gated:false, private:false`; ~398 in one API page, 998+ matching `details` overall |
| Per-item correctness present? | **YES** | parquet columns include `acc`, `acc_norm`, `gold`, `predictions`, `choices`; ARC-Challenge = 1,172 rows/model |
| Scale | ~2,000+ models × 6 v1 benchmarks | archive listing |
| Cost | **$0**, no GPU, no inference | pure download + pandas |
| Current-leaderboard details (IFEval/BBH/MATH/GPQA/MuSR/MMLU-Pro) | **GATED (HTTP 401)** | treated as extension, not dependency |

## Risk that nearly killed the project — and its resolution
**Discovered:** item identifiers are **not** stable across harness versions. Snapshots from ~Jul 19 2023 store `example` as a dataset ID (`Mercury_SC_410971`); later snapshots (Jul 24 2023+) store `example` as the **question text**. A naive ID join across 6 models produced **intersection = 0** — which would have made the model×item matrix unbuildable.

**Resolved:** harmonizing on a normalized *question-text hash* (whitespace-collapsed, lowercased, MD5) instead of IDs. Cross-scheme join verified:

```
A keys=1170  B keys=1170  INTERSECTION=1170  overlap=100.0%
```

This is strictly more robust than ID-joining (works across harness versions and benchmarks) and is now **fixed in the pre-registration** as the harmonization rule.

**Note for the write-up:** this bug is worth reporting. Any prior work that joined these logs on `example` without checking scheme drift would silently drop or mis-align items — a small methodological contribution in its own right.

## Pilot signal (2 models, ARC-Challenge, 1,170 harmonized items)
```
acc(Quokka_2.7b) = 0.281      acc(Quokka_590m) = 0.186
RAW co-failure          = 0.6590
Independence prediction = 0.5849
Naive "excess"          = +0.0741
```
The +0.074 is *exactly the kind of number the monoculture literature reports*. The project's central claim is that most or all of it is **forced by item difficulty**, and the margin-preserving null is what tests that. **Nothing here yet supports H1** — a naive independence baseline is precisely the confounded comparison this work replaces.

## What Phase 0 does NOT establish
- Whether excess survives the margin-preserving null (that is H1, unrun).
- Whether `base_model` lineage coverage is sufficient (§29 step 5, unrun).
- Whether curveball randomization mixes on matrices of this shape (Phase 2).

## Verdict
Gates 2 (feasibility) and 7 (reproducibility) are **empirically passed**. The highest-risk assumption (item alignment) was **tested and initially failed**, then solved. Proceed to Phase 1.
