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
index, licensed by a row-order verification (149/149 readable models of a 150-model sample
identical; see the 2026-07-28 audit section. Originally 14/14 sampled models identical across
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

---

# NeurIPS redesign: three pre-registered tests of a "positive capability" spine (2026-07-28)

The NeurIPS brief requires a contribution of the form "because we discovered X, researchers can
now do Y." Three candidate Y's were specified with kill conditions written BEFORE execution and
tested in order. All three controls are recorded here including the two that fired.

## KS1/KS2 — panel selection by conditioned diversity (`src/selection_killtest.py`)

Leakage guard: all selection statistics on a SEL item half, majority-vote accuracy on a disjoint
EVAL half. 600-model ARC response tensor, 8 item-split seeds, panel sizes {3,5,7,9,11,15}.

| k | cond-div vote | naive-div vote | top-acc vote | paired diff [95% CI] |
|---|---|---|---|---|
| 3 | 0.7714 | 0.7509 | 0.8066 | +0.0205 [+0.0022,+0.0422] |
| 5 | 0.7802 | 0.7745 | 0.7987 | +0.0057 [−0.0011,+0.0133] |
| 7 | 0.7725 | 0.7616 | 0.7649 | +0.0109 [+0.0039,+0.0188] |
| 9 | 0.7710 | 0.7557 | 0.7472 | +0.0153 [+0.0083,+0.0229] |
| 11 | 0.7649 | 0.7559 | 0.7430 | +0.0090 [+0.0033,+0.0149] |
| 15 | 0.7555 | 0.7502 | 0.7358 | +0.0052 [−0.0002,+0.0111] |

**KS1 nominally passes (4/6). KS2 FIRES.** Conditioned-diversity panels have higher mean member
accuracy at *every* panel size (e.g. 0.7426 vs 0.7309 at k=3), so the vote win is confounded with
simply selecting better models. This experiment cannot establish the claim and is retained only
as a record. Note also that `top-acc` beats both diversity strategies at k=3,5 and loses at
k=7..15 — a crossover, not a clean win for diversity.

## KI1/KI2 — incremental predictive validity (`src/incremental_validity.py`)

The design the ensemble-diversity literature actually uses (Kuncheva & Whitaker 2003,
*Machine Learning* 51(2):181–207): sample panels, regress ensemble accuracy on diversity
statistics, ask what survives controlling for member accuracy. 5,999 panels, stratified over
accuracy bands so member accuracy varies enough to be controlled.

| nested model | R² | ΔR² | F |
|---|---|---|---|
| M0: mean member accuracy + panel size | 0.9928 | — | — |
| M1: + disagreement + double-fault | 0.9945 | +0.0017 | 923.7 |
| M2: + margin-conditioned R | 0.9947 | **+0.0002** | 219.5 |

**KI1 FIRES and KI2 is violated.** The conditioned measure adds ΔR² = +0.0002 — significant at
n≈6000 but practically nil — and enters with a *positive* coefficient, the wrong sign for the
proposed mechanism. Member accuracy plus panel size alone explains 99.28% of ensemble-accuracy
variance. The "better diversity metric → better ensembles" spine is dead.

Independent corroboration of Lemma 1: standardised OLS coefficients blow up to member_acc=+316.2
and double_fault=+275.4, the signature of near-perfect collinearity between double-fault and the
margins — which is exactly what Lemma 1 predicts, now visible inside the canonical ML
diversity-regression framework rather than only as an identity.

## KR1/KD1 — does accuracy ranking select for conditioned redundancy? (`src/rank_redundancy.py`, `..._control.py`)

Fixed-width accuracy window (10% of models) swept across the accuracy range; the sweep controls
the obvious confound that *any* narrow band might show elevated correlation.

| bench | ρ(window accuracy, mean R) | ρ under margin-preserving null | top window R | median | ratio |
|---|---|---|---|---|---|
| ARC | +0.837 | −0.047 | +0.502 | +0.215 | 2.33× |
| Winogrande | +0.920 | +0.150 | +0.674 | +0.299 | 2.25× |
| TruthfulQA | +0.823 | +0.003 | +0.510 | +0.239 | 2.13× |
| GSM8K | +0.635 | −0.034 | +0.163 | +0.024 | 6.81× |
| HellaSwag | +0.562 | +0.081 | +0.462 | +0.186 | 2.49× |

**KR1 survives 5/5**: the null profile is flat at ~0.000 across the whole accuracy range while the
observed profile rises steeply toward the top. Not a banding artifact and not a margin artifact.

**KD1 FIRES (2/5).** Re-running the identical sweep after removing near-duplicate models
(agreement ≥ 0.95, recomputing the Rasch fit from scratch each time) collapses the gradient on
three benchmarks:

| bench | ratio @ no dedup | @0.99 | @0.97 | @0.95 | @0.90 | KD1 |
|---|---|---|---|---|---|---|
| ARC | 2.33× | 2.19× | 1.55× | 0.86× | 0.78× | fail |
| Winogrande | 2.25× | 1.83× | 1.54× | 1.66× | 1.55× | pass |
| TruthfulQA | 2.13× | 1.88× | 1.36× | 0.94× | 0.06× | fail |
| GSM8K | 6.81× | 4.62× | 6.00× | 5.39× | 5.43× | pass |
| HellaSwag | 2.49× | 2.00× | 0.54× | 0.35× | 0.28× | fail |

Top-of-leaderboard conditioned redundancy is **substantially a duplicate-fine-tune artifact** on
ARC, TruthfulQA and HellaSwag. It survives aggressive deduplication only on GSM8K (essentially
unmoved, 6.8×→5.4×) and partially on Winogrande. The general claim is refuted as stated.

## What these three tests establish

Every candidate positive capability died under its own pre-registered control. That is itself the
finding: the residual structure this project measures does not convert into a downstream selection
advantage, and the one striking population-level gradient is mostly duplication. The reusable
results are (a) the degeneracy, now demonstrated inside the ML diversity-regression framework,
(b) the null-calibrated instrument, and (c) the evidence that leaderboard model populations must
be deduplicated before any correlation analysis — 36–64% of models removed at the 0.95 threshold.

### Reconciling KD1 with E5 (they are not in conflict)

E5 above reports that removing two-thirds of the models moves *global* N_eff by only ~5, and
concludes the concentration is not a duplicate artifact. KD1 reports that the same deduplication
destroys the *top-decile-versus-median* redundancy gradient on three benchmarks. Both are correct
and they are different statistics: duplicates are not spread uniformly over the accuracy range,
they pool at the top of the leaderboard, so removing them barely moves a population-wide summary
while sharply flattening a profile measured *along* the accuracy axis. E5's conclusion stands as
stated (global concentration is not duplication) and must not be extended to the gradient claim.

---

# Phase 0 of the NeurIPS redesign (2026-07-28)

## X5 / KN1, KN2 — does the exact conditional null buy anything? (`src/noise_floor.py`)

A reviewer objected that the reported null rms (~0.039) is close to 1/sqrt(M), so "the elaborate
exact null coincides with the naive noise floor and the machinery buys nothing." This is the
cheapest experiment that could kill the project, so it ran first.

rms of margin-conditioned residual correlation under five reference distributions. The Rasch
conditioning model is **refitted to each replicate** — see the note below.

| bench | observed | R3 exact fixed-fixed | row-margin only | col-margin only | iid Bernoulli | 1/sqrt(M−3) |
|---|---|---|---|---|---|---|
| ARC | 0.2483 | 0.0446 | 0.0293 | 0.0445 | 0.0293 | 0.0293 |
| Winogrande | 0.2691 | 0.0409 | 0.0281 | 0.0397 | 0.0282 | 0.0281 |
| TruthfulQA | 0.2942 | 0.0584 | 0.0357 | 0.0578 | 0.0357 | 0.0357 |
| GSM8K | 0.0987 | 0.0345 | 0.0276 | 0.0326 | 0.0276 | 0.0276 |
| HellaSwag | 0.2457 | 0.0207 | 0.0103 | 0.0191 | 0.0103 | 0.0103 |

**KN1 survives 5/5. The reviewer objection is refuted:** the exact null sits at 1.25–2.01× the
analytic floor, not at it. But the margin is a factor of 1.3–2, not an order of magnitude, and the
paper should report the floor alongside the null rather than let a reader assume a larger gap.

**A finding this experiment was not designed to produce, and which qualifies the paper's central
argument.** Column-margin-only conditioning reproduces the exact both-margin null almost exactly —
0.0445 vs 0.0446 on ARC, 0.0578 vs 0.0584 on TruthfulQA, within 6% on all five. Meanwhile
row-margin-only conditioning lands exactly on the iid/analytic floor on every benchmark. So
**essentially all of the conditioning work is done by the item margins; the model-ability margins
are nearly inert for this statistic.** That is consistent with Lemma 1, which is a statement about
item margins alone, but it means the "jointly sufficient statistics" framing overstates what is
empirically load-bearing. KN2 as coded compares against the *larger* of the two one-sided
discrepancies and therefore passes on the row comparison; the honest reading of the column
comparison is that it nearly fails. Reported here rather than resolved in the framing's favour.

**Correctness note.** The first version of this script reused the observed-data Rasch fit `P` to
normalise every baseline, and reported ratios of order 1e10 for the column-only and iid arms.
That was an artifact, not a result: `R` normalises by sqrt(diag(D)), and when the baseline
destroys the row margins that `P` encodes, diag(D) collapses toward zero. Fixed by refitting the
conditioning model to each replicate (`rms_resid_refit`); the table above is the corrected run.

## X6 / KV1, KV2 — is the curveball sampler actually uniform? (`src/sampler_validation.py`)

"Exact" is the paper's central adjective and rested on assertion. Carstens (2015, *Phys. Rev. E*
91:042812; erratum 94:039902, 2016) proved curveball converges to the uniform distribution on the
fiber **provided failed trades are counted** — a proposal that cannot execute must still consume a
step. Reading `src/nullmodel.py`: the implementation draws all row pairs up front and `continue`s
on failure, so a failure consumes one loop iteration rather than triggering a resample. That is
the required behaviour. Tested rather than asserted:

**V1 — exhaustive-fiber chi-square.** Every binary matrix with the given margins enumerated, then
60,000 thinned draws chi-squared against uniform.

| row margins | col margins | fiber size | χ² | df | p | verdict |
|---|---|---|---|---|---|---|
| 2,2,2,2 | 2,2,2,2 | 90 | 111.64 | 89 | 0.053 | not rejected |
| 3,2,2,1 | 2,2,2,2 | 48 | 53.84 | 47 | 0.229 | not rejected |
| 3,3,2,2,2 | 3,3,3,3 | 204 | 190.42 | 203 | 0.727 | not rejected |
| 2,3,1,2,2 | 2,2,2,2,2 | 1170 | 1219.43 | 1169 | 0.149 | not rejected |

**V2 — Gelman–Rubin, 4 dispersed chains, at the burn-in the paper actually uses (50 trades/N).**

| bench | R̂ |
|---|---|
| ARC | 0.9882 |
| Winogrande | 1.0300 |
| TruthfulQA | 0.9894 |
| GSM8K | 0.9807 |
| HellaSwag | 1.0272 |

**KV1 and KV2 both survive.** Uniformity is not rejected on any fiber up to size 1,170, and all
five benchmarks mix at the burn-in in use. The "exact is an unverified adjective" objection is
answered, and this also closes the single-chain concern flagged under E7 — the multi-chain SDs
here (2e-4 to 6e-4) are the honest ones to quote.

## CORRECTION — an untraceable null value in the paper (found 2026-07-28)

The manuscript reported `rms|R_ij| = 0.2483 against 0.0389 under the null` (Section 6.4) and, in
the abstract, `0.248 against 0.039 --- a sixfold excess`. **The value 0.0389 traces to no executed
run.** A search of every artifact in `results/` finds no such number in any file that predates
today; the only near-matches in the repository are values generated by experiments written today
(`dedup_sensitivity.json` Winogrande@0.97, `noise_floor.json` Winogrande column-only).

Four independent estimates of the ARC exact-null rms agree:

| source | draws | value |
|---|---|---|
| `sampler_validation.json`, 4 dispersed chains | 100 | 0.04491 |
| `timeseries.csv` | 40 | 0.04490 |
| `noise_floor.json` | 12 | 0.0446 |
| `dedup_sensitivity.json` | 6 | 0.0445 |

The correct ARC ratio is therefore **0.2483 / 0.0449 = 5.5x, not sixfold.** Most likely origin of
the error: 0.039 is close to the *mean null across the five benchmarks* (0.0398), which was paired
with ARC's *benchmark-specific* observed value — a scope mix, not a fabrication, but the paper
states that every number traces to an executed run and this one did not.

Fixed in `paper/main.tex` at three places (abstract, Section 6.4, Section 6.5 summary). The
abstract now reports the ARC-specific ratio, the cross-benchmark range (2.9x GSM8K to 11.9x
HellaSwag), and the deduplication robustness. Recorded here rather than silently amended.

## X1/X2 — the duplication audit (`src/dedup_sensitivity.py`)

Every headline statistic recomputed on populations deduplicated at agreement thresholds
0.99/0.97/0.95/0.90, with the Rasch fit and the null redrawn from scratch each time. **KX1: a
statistic is duplication-driven if its observed/null ratio moves more than 2x by the 0.95
threshold.**

| bench | models removed @0.95 | rms ratio full → @0.95 | PR ratio full → @0.95 | eigen>edge full → @0.95 |
|---|---|---|---|---|
| ARC | 491 (36%) | 5.58 → 5.44 (1.03×) | 0.0520 → 0.0666 (1.28×) | 6 → 6 |
| Winogrande | 467 (34%) | 6.58 → 6.18 (1.06×) | 0.0408 → 0.0597 (1.46×) | 5 → 5 |
| TruthfulQA | 535 (40%) | 5.06 → 4.64 (1.09×) | 0.0561 → 0.0763 (1.36×) | 5 → 4 |
| GSM8K | 256 (21%) | 2.85 → 3.10 (1.09×) | 0.2145 → 0.1987 (1.08×) | 4 → 4 |
| HellaSwag | 870 (64%) | 11.84 → 13.45 (1.14×) | 0.0285 → 0.0697 (**2.44×**) | 12 → 8 |

**14 of 15 statistic-benchmark pairs are robust.** The single exception is HellaSwag's PR ratio.
This is the strongest single result of the redesign work: the concentration finding survives
removing 36–64% of each population, which answers the objection every reviewer persona named as
the leading confound. It also sharpens KD1 — the *population-level* concentration is not
duplication, while the *gradient along the accuracy axis* is. Both are true and they are
different statistics.

**Family census (X1), reported as a lower bound.** Name-string attribution reaches only ~35% of
model ids on every benchmark, with ~125 models per benchmark carrying merge-related names and the
top five named families covering ~25%. This is coarser than a config hash and is **not** lineage
ground truth; it is reported to show that the `base_model` field failing at 23.3% (K5) was not
the only weak attribution route available.

## X4 / KP1–KP3 — what the test can and cannot detect (`src/power_study.py`)

Planted structure at controlled strength, 400 models x 700 items, 20 datasets per condition,
one-sided test at alpha = 0.05. Calibration check: the null conditions (s=0, c=0) reject at
0.017 against a nominal 0.05, so the threshold is if anything slightly conservative.

**Alternative A — shared failure modes** (g latent groups, per-item offset of magnitude s):

| s | power (g=4) | power (g=8) | planted rms |
|---|---|---|---|
| 0.00 | 0.05 | 0.00 | 0.047 |
| 0.15 | 0.05 | 0.10 | 0.047 |
| 0.30 | 0.25 | 0.15 | 0.047 |
| 0.50 | **1.00** | **1.00** | 0.048–0.050 |
| 0.80 | 1.00 | 1.00 | 0.056–0.062 |
| 1.20 | 1.00 | 1.00 | 0.075–0.092 |

**KP1 passes.** Full power is reached at a planted rms of **0.048** — far below the 0.099–0.294
seen on real data. The test is not underpowered in the regime it is applied in.

**Alternative C — partial copying of a reference model:** power 0.00 at c=0, **0.65 at c=0.05**,
**1.00 from c=0.10 onward.** **KP3: copying is detected from c ≥ 0.1.** The instrument is highly
sensitive to duplication, which is the right property given the population is 36–64% redundant.

**Alternative B — shared item difficulty only: power = 0.05, exactly the nominal alpha.**

**This is the Narcissus effect, quantified.** Colwell & Winkler (1984) warned that a null
conditioning on statistics into which the process of interest has leaked will absorb that process.
Here the warning is exact rather than rhetorical: against the alternative "every model finds the
same items hard, differing only in overall ability" — arguably the strongest form of monoculture —
the test has **zero power by construction**, because that alternative *is* the null. Per KP2 this
belongs in the abstract, not in Limitations. The instrument measures departures from a shared
difficulty profile; it cannot measure the shared difficulty profile itself.

## RETRACTED — the "q* latent dimensions" estimate (`src/dimensionality.py`)

An estimate of how many latent ability dimensions reproduce the residual correlation was
attempted, on held-out items, and **is not reported as a result.** Three independent fitting
attempts disagreed materially about the same quantity:

| attempt | 2PL-equivalent synthetic rms (ARC) |
|---|---|
| `null_ladder.py` R4 rung | 0.109 |
| `dimensionality.py`, first parameterisation | 0.062 |
| `dimensionality.py`, after the gradient-scaling fix | 0.177 / 0.214 depending on lr |

Three defects were found, in order:
1. float32 overflow in the null-ladder MIRT, which returned rms > 1 for Winogrande q=2,3,4. An
   rms of correlations cannot exceed 1, so those rungs were discarded.
2. Missing gradient normalisation, making theta updates ~M times too large; every fit diverged.
3. **A specification error that invalidates the ladder's labelling.** In this parameterisation
   `q=1` allows a free per-item loading, so it is a **2PL**, not the Rasch model. The built-in
   calibration — q=1 must reproduce the Rasch null of ~0.045 — therefore fails by construction,
   and the reported q* was counting from the wrong baseline.

Two genuinely different approaches having failed, this stops here rather than continuing to tune a
bespoke optimiser. **The dimensionality question remains open** and should be answered with an
established IRT implementation (R `mirt`, or `py-irt`) rather than hand-rolled gradient ascent.
The earlier in-sample impression that 2–4 dimensions suffice is *suggestive only* and must not be
cited until refitted. What survives from this line of work is the permutation-based rungs of the
ladder (R0–R3), which involve no optimiser at all and are reported above under X5.

## Row-order audit, widened (2026-07-28) — `src/audit_roworder.py`

The single assumption the whole substrate rests on is that item identity is the row index. The
release cited a 14-model spot check and pointed at `src/audit_roworder.py` as the evidence —
**and that script was not in the repository**, so the claim was unverifiable from the release.
The script now exists and the sample is an order of magnitude larger.

Method: 150 ARC models sampled *evenly across the snapshot date range* (2023-07-18 – 2024-05-30)
rather than alphabetically, because the failure mode being audited is schema drift over time.
Item identity is normalised to a question-text hash — gen A reads `query`, gen B/C read `example`,
since gen A's `example` holds a dataset id, which is exactly the mismatch that produced an empty
intersection in Phase 0. A model is aligned iff its full hash sequence equals the reference's,
position by position.

| quantity | value |
|---|---|
| models checked | **149** of 150 (1 unreadable, transient network error) |
| row-order identical to reference | **149 / 149 — zero mismatches** |
| items | 1,172 |
| schema generations covered | 28 gen-A (`query`), 121 gen-B/C (`example`) |
| reference model | `details_AlekseyKorshuk__chatml-pyg-v1` (gen A) |

Artifact: `results/audit_roworder_arc.json`.

**This remains a sample of ~1,400 models, not a proof**, and every document that cites it now says
so. Note the direction of the risk: an undetected misalignment makes a model's row look
independent of every other, biasing correlation estimates *toward zero* — toward the null. So this
failure mode would understate the paper's headline rather than manufacture it.

### Row-order audit extended to all five benchmarks (2026-07-28)

The ARC audit above was initially the only one run, while the item-identity claim covers all five
benchmarks. Extended:

| benchmark | models checked | row-order identical | items | schema generations in sample |
|---|---|---|---|---|
| ARC | 149 (of 150; 1 unreadable) | **149 / 149** | 1,172 | 28 gen-A, 121 gen-B/C |
| TruthfulQA | 60 | **60 / 60** | 817 | 60 gen-B/C |
| GSM8K | 60 | **60 / 60** | 1,319 | 60 gen-B/C |
| Winogrande | 40 | **40 / 40** | 1,267 | 40 gen-B/C |
| HellaSwag | 15 | **15 / 15** | 10,042 | 3 gen-A, 12 gen-B/C |

**Zero mismatches anywhere.** Artifacts: `results/audit_roworder_<bench>.json`.

**Three caveats, all of which matter.**
1. This is ~330 models of ~1,400. It raises confidence; it is not a proof.
2. **Only ARC and HellaSwag sample both identity-column schema generations.** The other three drew
   entirely from gen-B/C, so they do not independently exercise the cross-generation drift that
   produced an empty intersection in Phase 0 — that hazard is tested by ARC and HellaSwag only.
3. HellaSwag's sample is the smallest at 15, because it reads 10,042 question texts per model
   and repeated attempts at N≥25 were terminated by the environment before completing. The
   committed artifact is `complete: true, audit_ran: true` and spans both schema generations.
   Reproduce with `python src/audit_roworder.py hellaswag 15`.

Direction of the residual risk, unchanged: an undetected misalignment makes one model's row look
independent of every other, biasing correlation estimates *toward zero*. This failure mode would
understate the paper's headline, not manufacture it.
