# Pre-Registration — Excess Co-Failure and Effective Model Count
**Committed before any confirmatory run.** No exemplar in the reference set pre-registers; this is one of the axes on which this project is designed to dominate. Amendments must be appended with dates, never silently edited.

Status: Phase 0 (feasibility) COMPLETE — see `results/phase0_findings.md`. Phases 1+ not yet run.

## Hypotheses
- **H1 (existence).** Pairwise co-failure among open models exceeds the expectation of a null that preserves each model's accuracy (row margins) and each item's difficulty (column margins) exactly. Predicted: mean standardized effect size (SES) > 0, CI excluding 0, surviving BH-FDR across benchmarks.
- **H2 (structure).** Excess co-failure is concentrated along declared model lineage. Predicted: phylogenetic signal in the excess matrix significantly exceeds a lineage-label-permutation null.
- **H3 (consequence).** The effective number of independent models N_eff is far below the nominal count N, and N_eff/N declines across release cohorts.

## Pre-declared kill conditions
- **K1.** If mean SES is not CI-separated from 0 in ≥2 of 3 primary benchmarks, H1 is refuted → report the **negative result**: reported monoculture is an artifact of marginals. This outcome is publishable and will be published rather than reframed.
- **K2.** If phylogenetic signal does not exceed the permutation null, H2 is refuted → Contribution 3 is reported as null; lineage is not the mechanism.
- **K3.** If N_eff/N shows no cohort trend, H3's consolidation claim is dropped (the level claim may still stand).
- **K4.** If randomization chains fail convergence diagnostics, the estimator is invalid → no H1 claim may be made until fixed.
- **K5.** If `base_model` coverage < 40% of the analysed models, Contribution 3 is dropped rather than estimated on a biased subset.

## Primary analysis (fixed in advance)
- Primary benchmarks: ARC-Challenge, HellaSwag, MMLU (aggregated across subjects). Secondary: TruthfulQA, Winogrande, GSM8K.
- Null: fixed-fixed (row- and column-margin preserving) randomization via curveball/swap, R ≥ 1000 after burn-in, with convergence diagnostics reported.
- Primary statistic: SES_ij = (observed co-failure − null mean) / null SD, aggregated to a benchmark-level mean with two-way (item and model) bootstrap CIs.
- Multiplicity: Benjamini–Hochberg across the benchmark × statistic family.
- N_eff: reported under **two** independent definitions (participation ratio of the excess-correlation eigenspectrum; variance-inflation formulation). A claim is made only if both agree in direction.
- Secondary null (robustness, not primary): fixed-equiprobable.

## What would make me wrong
The single most likely way this project is wrong: the entire raw excess (e.g. the +0.074 observed in the Phase-0 pilot) is absorbed by the margin-preserving null, leaving SES ≈ 0. I commit in advance to reporting that as the headline if it occurs.

## Scope limits declared in advance
Claims cover the *evaluated open-model ecosystem* on multiple-choice-style benchmarks, not deployed proprietary systems. No claim about real-world hiring/screening outcomes will be made from this data; the societal framing is motivation, not a measured outcome.

## Analyst-degrees-of-freedom controls (original)
Item harmonization rule (whitespace-normalized, lowercased question-text MD5 — validated at 100% overlap in Phase 0), model inclusion rule (has ≥1 primary benchmark with parseable per-item outcomes), and snapshot rule (latest snapshot per model) are fixed here and may not be changed after seeing confirmatory results.

---

# AMENDMENT 1 — 2026-07-26
**Status when written: Phase 1 harvest in progress; NO confirmatory statistic has been computed on real data. This amendment is registered before the confirmatory run, not after seeing its result.**

## Reason for amendment
While implementing the margin-preserving null (Phase 2), a derivation showed that **H1, as originally stated, is refuted analytically rather than empirically**. The original H1 predicted that mean pairwise co-failure would exceed its expectation under a null preserving row and column margins. That expectation is not merely close to the observed value — it is *identically equal* to it, by construction.

### Proposition 1 (mean co-failure is a function of item margins alone)
For a binary failure matrix `F ∈ {0,1}^(N×M)` with item failure counts `c_m = Σ_i F_im`, the mean pairwise co-failure over ordered pairs `i ≠ j` is

```
O = (1 / (M·N·(N−1))) · Σ_m ( c_m² − c_m )
```

which depends on the column margins alone and not at all on the row margins or on any structure in `F`.

**Corollary 1.1.** Any randomization that preserves column margins exactly — including the fixed-fixed / curveball null specified as this study's primary null — leaves `O` invariant with exactly zero variance. The standardized effect size for `O` is therefore `0/0`, undefined. *Verified numerically: curveball resampling reproduces `O` to a difference of exactly 0.00e+00 while preserving both margins.*

### Proposition 2 (the naive "excess" is exactly a difficulty-dispersion artifact)
Against the independence baseline `I = (1/(N(N−1)))·[(Σ_i p_i)² − Σ_i p_i²]`, with `p_i` the model failure rate, `f_m = c_m/N` the item failure rate, and `f̄` its mean:

```
O − I  =  [ N·Var_m(f_m)  +  Var_i(p_i)  −  f̄(1 − f̄) ] / (N − 1)
```

This is an exact finite-`N` identity, **verified to machine precision (residual ≤ 1.1e-16) across five matrix shapes** spanning N ∈ [40, 5000], M ∈ [250, 1172]. As `N → ∞` it converges to `Var_m(f_m)`. The reported "excess co-failure" of the monoculture literature is therefore, to leading order, *the cross-item variance in difficulty* — a quantity that is present in any item set with heterogeneous difficulty, including one where every model fails independently.

## Consequences for the hypotheses
- **H1 is replaced, not rescued.** It splits into:
  - **H1a (analytic, now settled).** Mean excess co-failure over a margin-preserving null is identically zero, and the naive excess equals the closed form above. This is a derivation with numerical verification; it is *not* an empirical hypothesis and no p-value attaches to it. Its empirical component is the calibration check below.
  - **H1b (structural, the new confirmatory test).** Correlated failure, if present, must appear at **second order**: in the *dispersion and eigenstructure* of the pairwise co-failure distribution, which Proposition 1 does not pin. Pre-declared primary statistic: `T = Var_{i<j}(C_ij)`, compared against its fixed-fixed null distribution, reported as SES with two-way bootstrap CIs and BH-FDR across benchmarks.
- **H2 and H3 are unchanged.** Both were always second-order/structural claims and are unaffected by Proposition 1. N_eff, resting on the eigenspectrum, is likewise not pinned by margins.

## New pre-declared kill conditions
- **K1′ (replaces K1).** If `T` is not CI-separated above its null in ≥2 of 3 primary benchmarks, H1b is refuted → the headline becomes the **negative structural result**: after conditioning on marginals, the open-model ecosystem shows no detectable excess co-failure structure, and *all* reported monoculture is a marginal artifact. This will be published as the finding, not reframed.
- **K6 (new, calibration check on H1a).** On the real harvested matrices, the measured naive excess must match the closed form of Proposition 2 to within 1e-9. If it does not, the derivation or the pipeline is wrong and **no claim of either kind may be made** until the discrepancy is resolved.

## Why this is not post-hoc flexibility
Three points, stated so a reviewer can check them: (i) the amendment **strengthens** the null and **removes** the study's most headline-friendly available claim rather than protecting it; (ii) it is a derivation verified to machine precision, not a specification chosen because it fit; (iii) it is recorded before any confirmatory statistic was computed on the harvested data, and the git history of this file evidences the ordering. The original H1 text above is left intact rather than edited, per this document's own amendment rule.

---

# AMENDMENT 2 — 2026-07-26
**Status when written: Phase 1 harvest of the binary outcome matrices in progress; no confirmatory statistic computed on real data. Registered before the confirmatory run.**

## Reason
A prior-art sweep located Wu, Hardt et al. (arXiv:2506.07962), "Correlated Errors in Large Language Models" (349 LLMs x 12,032 HuggingFace items; 71 LLMs x 14,042 Helm items; 20 LLMs on resume screening). Its primary statistic is the **agreement rate conditional on both models being wrong**, compared against a **uniform-random baseline** (1/3 for Helm's 3 distractors, 0.127 for the mixed HuggingFace set). The authors state their conditioning is designed "to reduce confounding based on model accuracy"; they do **not** adjust for item difficulty or for per-item distractor attractiveness.

This is the same class of confound Proposition 1 formalises, but for a multi-category statistic. The pre-registration is therefore extended rather than redirected.

## Proposition 3 (multi-category agreement is pinned by per-item response composition)
Let `R_im ∈ {0,…,K}` be model *i*'s response to item *m*, and let `n_mk` be the number of models giving response *k* to item *m*. The mean pairwise agreement over ordered pairs, restricted to any response subset (e.g. "both wrong"), is

```
A = Σ_m Σ_k n_mk(n_mk − 1)  /  Σ_m n_m(n_m − 1)
```

a function of the per-item response **composition** alone. Any null preserving that composition — e.g. permuting response labels within each item — leaves `A` exactly invariant.

**Verified numerically.** In a simulation where every model draws its wrong answer *conditionally independently* given the item, from a shared per-item distractor-attractiveness distribution:
- observed P(same wrong | both wrong) = **0.5567**
- uniform baseline of the kind used in prior work = **0.3333**
- apparent "excess" = **+0.2233**
- excess over the composition-preserving null = **−1.1e-16**, null SD **1.1e-16** across 12 replicates.

That is a **constructive counterexample**: models with conditionally independent errors exhibit a large apparent error correlation under a uniform baseline. Non-uniform distractor attractiveness alone is sufficient to produce the reported effect.

## New hypothesis (confirmatory, to be tested on real data)
- **H4.** The prior-art comparative claim — that larger / more accurate models have *more* correlated errors — does not survive margin conditioning. Mechanism to test: more accurate models fail only on a smaller, harder, more selected item subset, where distractor attractiveness is more concentrated, which inflates composition-driven agreement independently of any shared behaviour.
  - **Predicted if H4 true:** the accuracy–agreement slope is strongly attenuated (or vanishes) when agreement is measured as excess over the composition-preserving null.
  - **K7 (kill condition).** If the accuracy–agreement slope survives margin conditioning with CI excluding zero, H4 is refuted and I will report that the prior-art comparative finding is **robust** to this critique. That outcome will be reported as prominently as the alternative.

## Scope and fairness constraints (binding on the write-up)
1. The critique applies to the *interpretation of the baseline*, not to the correctness of the prior work's measurements. Their reported numbers are not in question; what is in question is what a uniform baseline licenses.
2. Their accuracy conditioning ("both wrong") is a genuine and acknowledged control and must be described as such.
3. Their stated limitation — that current metrics "treat incorrect answers identically" — must be quoted, since it is adjacent to this critique and shows the authors flagged metric limitations themselves.
4. No claim that prior authors erred in data collection or analysis execution. The claim is that a class of baselines is uninformative.

## Data requirement added
Testing Proposition 3 on real data requires **responses**, not just correctness. The archive's `predictions` (per-choice log-likelihoods) and `gold` columns permit reconstruction of each model's chosen answer at roughly 60x the bytes of the `acc` column. This is therefore run as a **second tier** on a subsample of models, with the binary analysis (Propositions 1–2) remaining the full-scale primary.
