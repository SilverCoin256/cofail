# Results digest — every number below was produced by an executed run

Generated 2026-07-26. Regenerate with `python src/experiments.py <bench>`, `src/controls.py`,
`src/dedup.py`. Raw JSON in this directory. Nothing here is estimated, rounded from memory,
or carried over from an earlier draft.

## Substrate

| benchmark | models | items | mean accuracy | snapshots | cohorts |
|---|---|---|---|---|---|
| ARC-Challenge | 1362 | 1165 | 0.527 | 2023-07 … 2024-06 | 12 |
| Winogrande | 1361 | 1267 | 0.734 | 2023-09 … 2024-06 | 10 |
| TruthfulQA (mc1) | 1334 | 786 | 0.368 | 2023-07 … 2024-06 | 12 |
| GSM8K | 1228 | 1319 | 0.348 | 2023-09 … 2024-06 | 10 |
| HellaSwag | 1362 | 9404 | 0.581 | 2023-07 … 2024-06 | 12 |

Harvested from `open-llm-leaderboard-old` at **$0 compute cost** by reading only the metric
column of each parquet (1.4 KB out of a 63 MB file for HellaSwag). Item identity is the row
index, licensed by a row-order verification (14/14 sampled models identical across
Jul 2023 – May 2024 and all three harness schema generations) plus a row-count guard on every
read. Total rejected: ARC 0, GSM8K 0, Winogrande few, TruthfulQA 22.

## E0 / kill condition K6 — Proposition 2 holds exactly on real data

Measured naive excess vs. the closed form `[N·Var_m(f) + Var_i(p) − f̄(1−f̄)]/(N−1)`:

| benchmark | measured naive excess | closed form | residual |
|---|---|---|---|
| ARC | +0.113180719 | +0.113180719 | −2.78e-17 |
| Winogrande | +0.057265401 | +0.057265401 | −1.39e-17 |
| TruthfulQA | +0.115767366 | +0.115767366 | +1.39e-17 |
| GSM8K | +0.042311309 | +0.042311309 | +7.63e-17 |

**K6 PASS on all four.** The identity is exact to machine precision on real data.

## E1 / Proposition 1 — the mean-level "excess" is 100% a marginal artifact

Over 400 curveball replicates per benchmark, with both margins exactly preserved
(`margins_ok = True` everywhere), the maximum absolute deviation of mean co-failure from its
observed value is **0.00e+00** in every benchmark. Residual mean excess after conditioning:

| benchmark | naive excess reported | residual after margin conditioning |
|---|---|---|
| ARC | +0.113181 | +5.55e-17 |
| Winogrande | +0.057265 | +2.78e-17 |
| TruthfulQA | +0.115767 | −1.11e-16 |
| GSM8K | +0.042311 | +0.00e+00 |

## E1 / H1b — the pre-registered dispersion statistic: **REFUTED (K1′ fires)**

`T = Var over model pairs of C_ij`, against its fixed-fixed null:

| benchmark | T observed | T null | SES | ratio | direction |
|---|---|---|---|---|---|
| ARC | 7.6396e-3 | 8.3300e-3 | −70.11 | 0.917 | below null |
| Winogrande | 1.3101e-3 | 2.3220e-3 | −145.76 | 0.564 | below null |
| TruthfulQA | 1.2774e-2 | 1.1638e-2 | **+77.93** | 1.098 | above null |
| GSM8K | 4.5763e-2 | 4.6228e-2 | −39.36 | 0.990 | below null |

Only 1 of 4 lies above the null. **K1′ fires: H1b is refuted and is reported as refuted.**
The sign is inconsistent across benchmarks, so `T` does not support a claim in either
direction and is reported as an uninformative statistic, not as a negative finding.

## E3 / H3 — N_eff, null-calibrated: the finding that survives

Participation ratio of the eigenspectrum of the margin-conditioned excess matrix
`D = (F Fᵀ − P Pᵀ)/M`, with `P` the fitted Rasch/maximum-entropy margin model
(margins matched to ≤ 5.7e-13), calibrated against curveball replicates sharing the margins:

| benchmark | N | N_eff observed | N_eff null | SES | ratio | raw (unconditioned) |
|---|---|---|---|---|---|---|
| ARC | 1362 | **23.6** | 449.6 ± 3.3 | −130.28 | 0.052 | 1.9 |
| Winogrande | 1361 | **20.1** | 494.0 ± 3.4 | −141.25 | 0.041 | 3.6 |
| TruthfulQA | 1334 | **17.4** | 309.7 ± 2.3 | −126.42 | 0.056 | 1.5 |
| GSM8K | 1228 | **118.6** | 553.3 ± 2.5 | −175.19 | 0.214 | 2.1 |

Consistent in sign and large in all four. The raw unconditioned column shows why conditioning
is essential: uncalibrated it reads 1.5–3.6, which is not a finding but the shared
item-difficulty eigenvalue.

Eigenvalue diagnostic (ARC): eigenvalues sum to N = 1362 as required; 91.35% of spectral mass
is positive, 8.65% negative (110 negative eigenvalues, minimum −139.85). The participation
ratio is insensitive to how negatives are handled — **clipped 23.6, absolute 23.5, raw 16.0**.

## E5 — the N_eff collapse is **not** a near-duplicate artifact

ARC pairwise agreement: mean 0.7282, p99 0.9382, max 1.0000 (exact duplicates do exist).
Only 272 of 926,841 pairs agree at ≥0.99 and 5,403 at ≥0.95.

| ARC threshold | models kept | removed | N_eff | null | ratio |
|---|---|---|---|---|---|
| full | 1362 | 0 | 23.6 | 449.6 | 0.052 |
| ≥0.99 | 1251 | 111 | 24.0 | 439.4 | 0.055 |
| ≥0.97 | 1067 | 295 | 25.4 | 418.5 | 0.061 |
| ≥0.95 | 877 | 485 | 26.0 | 391.6 | 0.066 |
| ≥0.90 | 462 | 900 | 29.0 | 289.3 | 0.100 |

Winogrande behaves identically (20.1 → 26.6 after removing 474 models). **Removing two-thirds
of the models moves observed N_eff by ~5.** Redundant members are not what is driving it.

## Estimator controls (`results/controls.json`)

| control | construction | expected | SES | ratio |
|---|---|---|---|---|
| C1 negative | matrix drawn from a Rasch margin model | ≈ 0 | +0.05 | 1.0001 |
| C2 positive | 8 latent model families sharing failure modes | ≫ 0 | +6.75 | 1.0151 |
| C3 positive | half the models exact clones | > 0 | +2.64 | 1.0042 |
| C4 negative | column-shuffled real ARC | ≈ 0 | −1.33 | 0.9803 |

Sign convention and detection ability both verified before any real-data claim was made.

## E7 — curveball convergence

Both margins exactly preserved at every checkpoint. At 200 trades/N, 18.5–25.1% of cells have
changed (ARC 20.2%, Winogrande 25.1%, TruthfulQA 18.5%, GSM8K 22.2%). Burn-in used is
50 trades/N with 5 trades/N thinning.

**Open issue, flagged not hidden:** null replicates are drawn from a single chain and are
therefore autocorrelated, so the null SD is likely underestimated and the reported SES
magnitudes correspondingly inflated. The *signs* and the *ratios* — which carry the
substantive claims — are unaffected. Independent-chain re-estimation is a pending fix.

## Simulation result behind Proposition 3 (not yet run on real responses)

Models erring **conditionally independently** given the item, with heterogeneous per-item
distractor attractiveness: observed P(same wrong | both wrong) = 0.5567 against a uniform
baseline of 0.3333 → apparent excess **+0.2233**, while excess over the composition-preserving
null = **−1.1e-16** (null SD 1.1e-16 over 12 replicates). A constructive counterexample:
independent models, large apparent error correlation.

## Status of every pre-registered kill condition

| condition | status |
|---|---|
| K1′ (dispersion T above null in ≥2 of 3) | **FIRED — H1b refuted, reported as such** |
| K2 (lineage signal) | not yet run — pending base_model harvest |
| K3 (cohort trend in N_eff/N) | E4 computed, 7–8 cohorts per benchmark; trend not yet tested |
| K4 (chain convergence) | partially satisfied; single-chain autocorrelation outstanding |
| K5 (base_model coverage ≥40%) | not yet run |
| K6 (closed form matches measurement) | **PASS on all four benchmarks** |
| K7 (accuracy–agreement slope survives conditioning) | not yet run — needs tier-2 responses |

*This table is the state as of the first confirmatory run and is left unedited as a dated
record. It is superseded twice below: by "C5. Pre-registered gate outcomes, final" and then by
"Final kill-condition status". Read the last one.*

---

# CORRECTIONS after adversarial review (2026-07-26, later same day)

An adversarial verification workflow returned a verdict of **fatal** on parts of the framing
above. Where the reviewer made a checkable claim, I re-ran it myself. Three corrections stand,
and the sections above should be read subject to them.

## C1. The three "Propositions" are prior art

Verified and accepted. See `docs/PRIOR_ART_LEDGER.md`.
- Mean-co-failure degeneracy = **Schluter's V-ratio**, stated explicitly in Gotelli (2000,
  *Ecology* 81:2606) and Gotelli & Ulrich (2012, *Oikos* 121:171).
- The closed form = **Cronbach's α / KR-20**. I verified `naive_excess == α_N · Var_m(f_m)`
  myself: residual ≤ 6.9e-17 across five synthetic shapes, −4.2e-17 on real ARC, α_N = 0.99928.
- The multi-category form = **Fleiss (1971)** observed agreement.

They are retained as an attributed translation table, not as contributions.

## C2. The participation ratio does NOT count independent models — claim withdrawn

Verified on real ARC: `PR = N/(1 + (N−1)·mean R_ij²)` gives **16.0449** computed either way, so
the eigendecomposition adds nothing and PR is a monotone transform of mean squared residual
correlation. It cannot distinguish one weak global factor from many tight clusters.

The "≈1,300 models behave like 20–24 independent ones" headline is **withdrawn**. Replaced with
the primitive quantities, which do discriminate (ARC):

| diagnostic | observed | null | interpretation |
|---|---|---|---|
| rms \|R_ij\| | **0.2483** | 0.0389 | 6.4× excess residual correlation |
| λ₁²/Σλ² | **0.540** | — | one-factor ≈0.99, clone blocks ≈0.10 |
| PR after deflating λ₁ | **46.8** | — | one-factor would give ≈N=1362 |
| eigenvalues > null edge (28.7) | **5** | — | five real residual dimensions |

## C3. Misspecification controls — what else produces the effect

Each row is a simulated population with **no clusters, no clones, no shared lineage**.

| generating process | PR/PR_null | rms \|R\| | λ₁²/Σλ² | dims > edge |
|---|---|---|---|---|
| 1PL, correctly specified | 1.001 | 0.065 | 0.105 | 1 |
| 2PL, sd(log a)=0.35 | 0.966 | 0.068 | 0.119 | 1 |
| 2PL, sd(log a)=0.60 | 0.862 | 0.076 | 0.167 | 1 |
| two ability dimensions | 0.230 | 0.162 | 0.457 | 3 |
| 20 exact clone clusters | 0.112 | 0.234 | 0.102 | 19 |
| **real ARC** | **0.052** | **0.248** | **0.540** | **5** |

- Discrimination heterogeneity **cannot** explain the observation (rms ≤0.076 vs 0.248).
- A low-dimensional multi-ability structure explains much of it.
- Real ARC's signature matches the multidimensional case (λ₁² 0.540 vs 0.457), **not** the clone
  case (0.102). Conclusion restated as: residual structure of ~5 dimensions whose signature is
  additional latent ability dimensions, not duplicated models.

## C4. Objections raised and answered by evidence

- **Chain autocorrelation inflates SES.** Answered: independent chains give null SD ratios
  0.96–1.02 vs single-chain, lag-1 autocorrelation −0.14 to +0.07 across four benchmarks; a
  2000-trades/N burn-in gives ARC N_eff null 450.8 vs 449.3 at 50 trades/N (0.3% change).
- **T below null contradicts the spectral result.** Answered exactly. Var(E) is identical for
  observation and null (measured difference **0.000e+00**). With C = E + D:
  Var(D) = 6.253e-4 vs null 2.127e-5 (**SES +1613**, 29×), while Cov(E,D) = −6.494e-4 vs
  −2.1e-6 (corr −0.285 vs −0.005). The negative covariance outweighs the excess variance, which
  is why Var(C) reads below null. The arithmetic closes.
- **Duplicate models.** Answered before submission: removing 900 of 1362 ARC models moves the
  observed statistic by ~5.

## C5. Pre-registered gate outcomes, final

| condition | outcome |
|---|---|
| K1′ dispersion T above null in ≥2 of 3 | **FIRED — H1b refuted**, reported as refuted |
| K5 base_model coverage ≥40% | **FAILED — 23.3%** (317/1362; 315 repos no longer retrievable) → lineage contribution **dropped** |
| K6 closed form matches measurement | **PASS**, all five benchmarks, residual ≤7.6e-17 |
| K4 chain convergence | **PASS** (plateau by 10 trades/N; 40× burn-in changes null 0.3%) |
| K2, K3 | not run — K2 blocked by K5 |
| K7 | **FIRED** — tier-2 responses harvested and run 2026-07-26; H4 refuted |

## C6. Still outstanding

- ~~HellaSwag harvest paused at 100/1362~~ — **completed 2026-07-26**; see the fifth-benchmark
  section at the end of this file.
- ~~Tier-2 response harvest (Proposition 3 / H4 on real responses) written but not run.~~ —
  **run 2026-07-26**; K7 fired, H4 refuted. See the K7 section.
- Deep robustness suite (dedup, misspecification controls, exact variance reconciliation) is run
  on the primary four benchmarks only, not on HellaSwag. Stated as such in the paper.
- Prior-art sweep angles and the venue-verification agent died on a session limit; the venue
  shortlist below rests on my own verified searches, not on the workflow.

---

# Tier-2 real-response result (2026-07-26, same day, after corrections)

600-model ARC subsample, responses reconstructed from per-choice log-likelihoods.
Gold-recovery validation: agreement among correct models on shared items = **1.0000**
(1144/1172 items); recovered gold reproduces each model's own reported accuracy on **99.01%**
of cells.

**Proposition 3 on real data:** observed P(same wrong | both wrong) = 0.7299 vs uniform
baseline 0.25 (apparent excess +0.4799, matching the "big number" the prior-art baseline would
report) — but excess over the **composition-preserving null** = **+0.1293** (null sd 3.1e-4).
Unlike the synthetic counterexample (which nets ~0 by construction), real ARC responses show a
genuine, non-degenerate excess over composition alone. This is a different, honest finding from
the simulation and is reported as such.

**H4 / K7 — the pre-registered test of whether this rescues Kim et al.'s claim: it does not.**
Slope of agreement-when-both-wrong vs. mean pair accuracy: raw +0.5851 [+0.5770, +0.5938],
conditioned on the composition-preserving null +0.5141 [+0.5059, +0.5224]. Attenuation = **12.1%**.
**K7 fires: H4 refuted, meaning the critique does NOT apply here — Kim et al.'s specific
comparative claim (more accurate models → more correlated errors) is robust to this
conditioning**, and is reported as such, per the pre-registration's advance commitment to report
this outcome as prominently as the alternative.

Mean-level excess is separately near zero (0.7332 observed vs 0.7324 conditional-independence
expectation, +0.00085) — the two results are compatible: mean-level agreement is explained by
conditioning, the accuracy-agreement *slope* is not. These are different statistics.

## Final kill-condition status

| condition | outcome |
|---|---|
| K1′ | FIRED — H1b refuted |
| K5 | FAILED — 23.3% coverage, lineage dropped |
| K6 | PASS, all five benchmarks |
| K7 | **FIRED — H4 refuted; prior-art claim reported as robust** |
| K2, K3, K4 | not applicable (K2 blocked by K5) / satisfied (K4, via burn-in + independent-chain checks) |

---

# Fifth benchmark: HellaSwag (2026-07-26, same day, after HellaSwag harvest completed)

Harvest: 1362 models, 10042 items, 0 rejected, 111.9 min (largest file size of the five).

| check | result |
|---|---|
| K6 (closed form) | PASS — empirical 0.148717716, closed form 0.148717716, residual −5.55e-17 |
| E1 T (independent-chain) | T_obs 5.098e-3 vs null 5.085e-3, SES +10.6, ratio 1.002 — **above** null |
| E3 N_eff (independent-chain) | obs 27.3 vs null 958.0±3.2, ratio 0.028 — most extreme of all five |
| E7 mixing | plateaus by 5–10 trades/N, flat to 200 (9.8% cells changed, lower than others but consistent) |

Sign tally for T across all five is now 3 below / 2 above (ARC, Winogrande, GSM8K below;
TruthfulQA, HellaSwag above) — reconfirms K1′ (inconsistent sign, H1b refuted) rather than
changing the verdict. PR ratio (0.028) is the smallest of the five, i.e. the strongest
concentration signal, consistent in direction with the other four.

Deep robustness suite (dedup, misspecification controls, exact variance reconciliation) was
run on the primary four only; HellaSwag is added as a fifth confirmatory point with the same
core pipeline (E0–E7, independent-chain nulls), not the full robustness battery. The paper
states this scope distinction explicitly rather than implying uniform depth across all five.

All paper tables, figures, and abstract language updated from "four" to "five benchmarks."
Recompiled clean, 12 pages, zero LaTeX errors, verified by rendering the changed pages.
