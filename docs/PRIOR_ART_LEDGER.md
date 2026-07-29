# Prior-art ledger — what is mine, what is not

Written after an adversarial novelty review returned a verdict of **fatal** on the original
framing. Three results this project had called Propositions are prior art in other fields. Two
of the three I re-verified myself before accepting the finding; the third is settled by a
verbatim quotation. This document is the honest accounting, and the paper is written from it.

## Claims that are NOT novel

### 1. "Mean pairwise co-failure depends only on the item margins" — **known since 1984/2000**

This is Schluter's V-ratio degeneracy, transposed.

- Schluter, D. (1984). A variance test for detecting species associations. *Ecology*
  65:998–1005. V = Var(column sums) / Σ row variances; the null is stated as "the sum of the
  covariances is zero", so V is a monotone reparametrisation of mean pairwise co-occurrence
  covariance.
- Gotelli, N.J. (2000). Null model analysis of species co-occurrence patterns. *Ecology*
  81(9):2606–2621, p. 2612: *"The V ratio was not used in this analysis because retaining row
  and column totals as in SIM9 does not ever change the index, so all of the null matrices
  would have the same V ratio as the original matrix."* Tables 4, 6, 7 print `n.a.` for every
  V-ratio × SIM9 cell. SIM9 is the Connor–Simberloff fixed-fixed swap, direct ancestor of
  curveball.
- Gotelli, N.J. & Ulrich, W. (2012). Statistical challenges in null model analysis. *Oikos*
  121:171–180, p. 173: *"this metric is calculated entirely from row and column totals of the
  observed matrix, so null model algorithms that are conditioned on these totals cannot be used
  with the V-ratio."* They extend the warning to Sørensen, Simpson, Morisita and NODF.

**Status: not a contribution.** Cited and attributed. What remains is that the LLM-evaluation
literature has not received this result, and the transposition (models in the species role) has
not been stated there.

### 2. "Exact identity for the excess over an independence baseline" — **is Cronbach's α / KR-20**

Claimed identity: `O − I = [N·Var_m(f) + Var_i(p) − f̄(1−f̄)]/(N−1)`.

The reviewer asserted this reduces to `O − I = α_N · Var_m(f_m)`, with α_N Cronbach's alpha
computed with the N **models** in the item role. **I verified this myself** rather than accept
it: residual ≤ 6.9e-17 across five synthetic shapes (N ∈ [25, 1200], M ∈ [45, 900]) and
−4.16e-17 on the real ARC matrix, where α_N = 0.99928.

- Kuder, G.F. & Richardson, M.W. (1937). *Psychometrika* 2:151–160.
- Cronbach, L.J. (1951). *Psychometrika* 16:297–334.
- Asymptotic limit Cov = Var(latent p) is the de Finetti / beta-binomial overdispersion
  identity; Yule (1903), *Biometrika* 2:121–134, is the classical warning about association
  induced by mixing heterogeneous strata.

**Status: not new mathematics.** Retained as a two-line lemma in the α form, attributed. The
reduction is a cleaner statement than the original and is worth keeping as exposition.

### 3. "Multi-category agreement is pinned by per-item response composition" — **is Fleiss 1971**

`Σ_k n_mk(n_mk−1) / n(n−1)` is verbatim Fleiss's observed agreement `P̄`.

- Fleiss, J.L. (1971). Measuring nominal scale agreement among many raters. *Psychological
  Bulletin* 76:378–382.
- Equivalently Simpson (1949) concentration / 1 − Hurlbert (1971) PIE.
- The simulation result (conditional independence + heterogeneous distractor attractiveness ⇒
  apparent excess over 1/(K−1)) is the founding premise of answer-copying detection: Wollack
  (1997), *Applied Psychological Measurement* 21:307–320, built ω on the nominal response model
  precisely because indices ignoring option-level heterogeneity "yielded substantially inflated
  Type I error rates"; van der Linden & Sotaridona (2006), *JEBS* 31:283–304, give the exact
  conditional version.

**Status: not a contribution as mathematics.** Retained as a cited restatement.

### 4. The null itself is not new, and the equivalence matters

Row and column sums are jointly sufficient for the Rasch model, so the ecologists' fixed-fixed
null **is** the psychometricians' Rasch conditional null: Rasch (1960); Andersen (1973)
*Psychometrika* 38:123–140; Besag & Clifford (1989) *Biometrika* 76:633–642; Ponocny (2001)
*Psychometrika* 66:437–460; Verhelst (2008); Miller & Harrison (2013) *Ann. Statist.*; Strona
et al. (2014) *Nat. Commun.* 5:4114; Carstens & Horadam (2015) for curveball uniformity.
Ponocny's T11 in R/eRm is close kin to our T (L1 vs L2, item-pairs vs model-pairs).

### 5. N_eff's components are all borrowed

- Participation ratio + removal of a dominant shared mode: Laloux et al. (1999) *PRL* 83:1467;
  Plerou et al. (1999, 2002). Their "market mode" is our shared item-difficulty eigenvalue.
- "Effective number of independent variables from a correlation eigenspectrum" is M_eff in
  statistical genetics: Cheverud (2001); Nyholt (2004); Li & Ji (2005).
- Eigen-decomposition of Rasch residuals is standard: Linacre (1998); Smith (2002).
- `D = FFᵀ − PPᵀ` is the excess matrix of the network-backbone literature: Neal (2014); Neal,
  Domagalski & Sagan (2021) *Sci. Rep.* 11:23929 (FDSM vs SDSM).

### 6. The empirical debunk is partly anticipated

Jo, N., Garg, N. & Raghavan, M. (2026). **The Subjectivity of Monoculture**, arXiv:2602.24086,
27 Feb 2026. HELM MMLU (14,042 items × 72 models) and the HuggingFace Open LLM Leaderboard
(11,994 items × 451 models) — the same archive. They fit a parametric IRT null
`p_ij = Φ(aᵢᵀθⱼ + bᵢ)` by penalised gradient ascent and report residual correlations
"substantially attenuated" once item difficulty is modelled, "some even flipping from strongly
positive to slightly negative" — anticipating the direction of our `T < null` result. Their
Theorem 1: any distribution on {0,1}^m is a mixture of conditionally independent Bernoullis.
Their Proposition 2: excess is monotone decreasing in null expressiveness.

**This is the most important piece of prior art and must be cited prominently.**

## What remains genuinely novel

Stated so a referee can check each one.

1. **An answer to their open question.** Jo et al. conclude that monoculture inference is
   *subjective* because null choice is subjective, and state explicitly that their "framework
   does not prescribe which null is right". The margin-preserving null is not an arbitrary rung
   on their expressiveness ladder: because the margins are the Rasch sufficient statistics, the
   uniform distribution over margin-matched matrices is the **unique exact, fit-free conditional
   null for the entire Rasch family** — no gradient ascent, no ℓ2 penalties, no identification
   or whitening choices, no estimated parameters. It is a canonical, non-subjective stopping
   point that a fitted IRT null cannot claim. Nobody has reported the answer there for LLM
   benchmarks.

2. **A reconciliation that is not obvious and is new.** Two summary statistics point opposite
   ways, and the decomposition explains why. Because the null preserves margins exactly, the
   fitted `P`, and hence `E = PPᵀ/M`, is *identical* for the observation and every replicate,
   so `Var(E)` cancels exactly (measured difference: 0.000e+00). Writing `C = E + D`:
   `Var(C) = Var(E) + 2Cov(E,D) + Var(D)`. On ARC, `Var(D)` is **29× the null**
   (6.25e-4 vs 2.13e-5, SES +1613) while `Cov(E,D)` is strongly negative
   (−6.49e-4, corr −0.285, vs ≈0 under the null). The negative covariance outweighs the excess
   variance, which is *why* the dispersion statistic reads below null while the eigenstructure
   reads 20× concentrated. Both are true simultaneously and the arithmetic closes.

3. **Scale and robustness.** 1,228–1,373 models per benchmark across four (five with HellaSwag)
   benchmarks, versus 451 (Jo et al.), 349 (Kim et al.), 72 (HELM). Deduplication-controlled:
   removing two-thirds of models moves `N_eff` by ~5.

4. **A released substrate and estimator** harvested at zero inference cost, with the harness
   schema drift and item-identity pitfalls documented and guarded.

## Consequences applied to the paper

- Propositions 1–3 are demoted to a cited **translation table** (V-ratio ≡ Cronbach's α ≡
  Fleiss's P̄), presented as a bridge between three literatures that have each derived it
  independently and none of which the LLM-evaluation literature cites. Stated as a bridge, it
  costs nothing and buys credibility.
- The contribution sentence becomes: *whether LLM error correlation exceeds what item difficulty
  and model ability jointly force has only been tested against fitted parametric nulls; we test
  it at the exact conditional null that Rasch sufficiency singles out, and find no excess at the
  mean, none at the dispersion level, but a 20–25× concentration in the residual eigenspectrum.*
- Every borrowed component of N_eff is cited, and alternative effective-dimension estimators are
  reported so the conclusion does not rest on the participation-ratio functional.

## Objections that were raised and are answered by evidence

- **"Chain autocorrelation inflates every SES."** Answered. Independent chains give null SD
  ratios 0.96–1.02 versus single-chain thinning, lag-1 autocorrelation −0.14 to +0.07 across
  four benchmarks. A 2000-trades/N burn-in gives ARC `N_eff` null 450.8 versus 449.6 at 50
  trades/N — a 40× longer burn-in moves it 0.3%.
- **"N_eff collapse is duplicate models."** Answered, and it was run before submission, not
  after: removing 900 of 1362 ARC models moves `N_eff` 23.6 → 29.0.
- **"Var(C) below null contradicts N_eff far below null."** Answered by the decomposition above;
  the reviewer's algebra was correct and it resolves rather than refutes.

---

## Kohli (2026), "Nine Judges, Two Effective Votes" — arXiv:2605.29800, 28 May 2026

Found 2026-07-28 while running the novelty check by hand, after the automated sweeps failed on a
quota. **Verified by reading the paper directly**, not from a search summary — a first-pass
automated summary of this paper asserted that it used a both-margin-preserving permutation, a
participation ratio, and a degeneracy result about item margins. **All three were wrong.** Recorded
here as a caution: the leading-question failure mode of automated summarisation is exactly how a
false novelty kill, or a false all-clear, enters a prior-art ledger.

**What it actually does** (Sections 3.3–3.5 of that paper):
- Nulls: (a) a permutation stratified by human-entropy bin that shuffles each judge's error vector
  independently, preserving per-judge error rates and coarse difficulty structure; (b) a Condorcet
  null simulated from fitted per-judge, per-bin 3×3 confusion matrices. **Neither preserves the
  item margins exactly, and both estimate a nuisance model.**
- Statistic: the **Kish design effect** `n_eff = k/(1+(k−1)·φ̄)` over mean pairwise phi, with
  `n_eff^eigen = k/λ_max` as a robustness check. **Not** a participation ratio.
- Scale: 9 judges, 7 families, 1,000 items, ChaosNLI (MNLI/SNLI/AlphaNLI) + RewardBench, with 100
  human annotations per item.
- **No degeneracy theorem.** Nothing corresponding to our Lemma 1.

**Effect on our claims.**
- C1 (exact fit-free conditional null): **survives.** Their nulls are fitted or stratified, which
  is the class of choice our argument is aimed at.
- C2 (the degeneracy of mean co-failure): **survives.** They do not state or use it.
- C3 (calibrated measurement at scale): **survives**, and the scale gap is ~150×.
- C4 (the withdrawn "effective number of models"): **this is the interesting one.** Their headline
  statistic has the same algebraic form as the participation-ratio identity that made us withdraw
  ours — Kish uses mean φ where PR uses mean φ². So our negative result is not merely a
  self-correction; it bears directly on the headline number of a paper published two months ago.
  That is now stated in Related Work.

**Net:** not a novelty kill. It is a same-question, different-machinery neighbour that the paper
must cite and position against, and it converts C4 from a confession into a contribution.

## Novelty sweep, done by hand (2026-07-28)

The automated sweeps died on a usage quota. What follows was searched and read directly. It is
**partial** — it covers the areas most likely to contain a kill, not all six planned sweeps.

### IRT-based benchmark compression — the nearest *consumer* of our object

An active literature fits item-response models to model-by-item matrices to shrink benchmarks:
tinyBenchmarks (Polo et al., arXiv:2402.14992 — IRT trained on the evaluation results of **319
models**, ~100 items sufficing for MMLU), Anchor Points (multidimensional IRT with anchor-item
calibration), "Lost in Benchmarks?" / PSN-IRT (arXiv:2505.15055), Fluid Benchmarking and adaptive
testing (arXiv:2511.04689), Growing Pains (arXiv:2604.12843), Efficient Safety Benchmarking via
IRT (arXiv:2606.20626), Scales++ (arXiv:2510.26384).

**Does not kill anything.** None of these tests the adequacy of its own latent dimensionality with
a fit-free null; they assume a parameterisation and estimate within it. **But it is the strongest
"so what" available**, and it is now in the paper: our dimensionality estimate is a statement about
whether the assumption these methods rest on holds, measured on a model population roughly 4×
larger than the 319 used to fit tinyBenchmarks. Care taken not to assert which specific papers use
unidimensional versus multidimensional IRT — Anchor Points is explicitly multidimensional.

### Fixed-fixed / configuration nulls outside ecology

Searched for applications to model-by-item evaluation matrices in ML. Found only the ecology and
network-science lineage already cited (Strona et al. 2014; Carstens 2015 + erratum; configuration
models with fixed degree sequences), plus *Non-Uniform Sampling of Fixed Margin Binary Matrices*
(arXiv:2007.15043), which is relevant to the sampler-validity discussion and supports our decision
to validate the sampler by enumeration rather than assertion.

**No evidence anyone has applied the fixed-fixed null to model-by-item evaluation matrices.** This
is a negative search result and therefore weak evidence — absence of a hit is not proof of absence.

### Still unrun

Three of the six planned sweeps were never executed: LLM-judge/panel construction beyond Kohli
(2026), the algorithmic-monoculture literature since mid-2026, and a systematic search of
GitHub/PyPI for an existing package computing these statistics. **The novelty of the contribution
statement is therefore still not fully verified**, and this ledger should not be cited as if it were.
