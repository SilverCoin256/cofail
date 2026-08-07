# NeurIPS transformation blueprint

**Date:** 2026-07-28. **Author of this document:** PI-mode analysis, written against the current
manuscript at `paper/main.tex` (commit `5a7905b`).

**Provenance of the evidence below.** Two independent sources.
1. A nine-persona adversarial reviewer simulation. **Six of nine personas completed** (main-track,
   Area Chair, Senior AC, Datasets & Benchmarks, LLM-evaluation, theory). The hostile, systems and
   statistician personas, **all six novelty sweeps, and all 33 verification agents failed on a
   usage quota** and did not run. Section 22 states exactly what that leaves unverified. Nothing
   in this document is presented as verified that was not.
2. Four new experiments I designed and ran here, each with a kill condition written before
   execution: `src/selection_killtest.py`, `src/incremental_validity.py`,
   `src/rank_redundancy.py`, `src/rank_redundancy_control.py`. Full numbers in
   `results/RESULTS_DIGEST.md`.

Where the two sources agree, I say so. Where I could not check something, I mark it
**[UNVERIFIED]**.

---

## 1. Fatal weaknesses

> **Read §1 with the addendum at the end of this file.** Six of its experiments have since been run and four of its findings are superseded — each superseded passage below is struck through in place rather than deleted, so the original audit stays legible as a dated record.

Ranked by how much each raises P(reject), consolidated across six reviewer personas and my own
experiments. "Convergent" means ≥3 personas raised it independently.

**F1. No positive claim survives the paper's own results. (Critical, convergent — 6/6 personas.)**
H1b refuted (K1′), lineage decomposition dropped (K5), participation ratio withdrawn (C4), prior
work vindicated rather than overturned (K7). What remains is one descriptive statistic whose
interpretation the paper itself contests in Limitations. The Area Chair persona put P(reject)=0.91
and named this as the load-bearing objection.

**I tested whether a positive claim could be manufactured from the existing data. Three
candidates, three pre-registered controls, and two of them fired.** This is the single most
important finding in this document, because it means F1 is not a framing problem:

- *Panel selection by conditioned diversity.* KS1 nominally passed (4/6 panel sizes), **KS2
  fired**: conditioned-diversity panels also had higher mean member accuracy at every panel size,
  so the win is confounded with picking better models.
- *Incremental predictive validity.* **KI1 fired, KI2 violated.** Across 5,999 stratified panels,
  mean member accuracy + panel size explains **R² = 0.9928** of ensemble accuracy. Both classical
  diversity measures together add **+0.0017**. The margin-conditioned measure adds **+0.0002**,
  with the *wrong sign*.
- *"Accuracy ranking selects for conditioned redundancy."* KR1 passed 5/5 with a beautiful control
  (null profile flat at ~0.000 across the whole accuracy range while observed rises to +0.67 at
  the top). Then **KD1 fired 3/5**: removing near-duplicates at agreement ≥0.95 collapses the
  gradient on ARC (2.33×→0.86×), TruthfulQA (2.13×→0.94×) and HellaSwag (2.49×→0.35×). It
  survives on GSM8K (6.81×→5.39×, essentially unmoved) and partially on Winogrande.

**F2. The population is not a sample of independent models. (Critical, convergent — 4/6.)**
Reviewers called this "the single most likely confound a reviewer names." **Partly confirmed, partly refuted.** KD1 shows deduplication at 0.95 removes 36–64% of models and *reverses* the accuracy-**gradient** on three of five benchmarks. But X1/X2 (see the addendum) then showed the **population-level** statistics are robust: 14 of 15 statistic–benchmark pairs move by less than 1.5×. The confound is real for the gradient claim and largely answered for the headline measurement. The existing E5 analysis is not a defence — it measures a
global summary, and duplicates pool at the top of the leaderboard, which is exactly where the
gradient lives.

**F3. "Canonical / exact / fit-free" is a category error. (Critical, convergent — 4/6.)** The
fixed-fixed null is canonical *given* the Rasch family, and choosing that family is precisely the
analyst choice Jo et al. call subjective. The paper relocates the subjectivity and calls the
relocation a resolution. Worse, C5 shows the chosen family is inadequate — multi-ability structure
outside Rasch reproduces rms 0.162 of the observed 0.248 — and Limitations concedes it. The
concession is in the paper's own text, so it cannot be rebutted.

**F4. The Narcissus effect. (Critical.)** Conditioning on item margins conditions away a leading
signature of the phenomenon: if models share training data they share *which items are hard*, and
that is encoded in the item margins. Ecology named this failure mode in 1984 — Colwell & Winkler,
"A null model for null models in biogeography," ch. 20 in *Ecological Communities*, Princeton UP,
pp. 344–359 — **in the same literature the paper borrows curveball from, and does not cite it.**
Verified by search. ~~The paper has no power analysis characterising what alternatives its test
can detect.~~ **It does now (X4, see the addendum): power is 1.00 against shared failure modes at planted rms 0.048 and exactly α=0.05 against the shared-difficulty alternative. F4 is now quantified rather than open — which is a stronger position than the objection assumed.**

**F5. C1 is 25-year-old psychometrics. (Critical, convergent — 3/6.)** The exact fixed-margin
conditional Rasch test is standard: Ponocny (2001) *Psychometrika* 66:437–460, Verhelst (2008),
`eRm::NPtest`. **The paper already cites `ponocny2001` and `verhelst2008` in its own
bibliography** — so the objection is not "you missed it," it is "you cited the prior art and then
claimed its content as a contribution."

**F6. C2 attacks a statistic nobody reports, and misses the ML prior art that does. (Critical.)**
Mean pairwise co-failure *is* the **double-fault measure**, catalogued in Kuncheva & Whitaker
(2003) *Machine Learning* 51(2):181–207 among ten diversity measures (verified by search). The
paper's claim that the degeneracy is "not cited in the model-evaluation literature" is false in
the direction that matters at NeurIPS. Separately, Kim et al. report agreement *conditional on
both being wrong*, not the unconditional mean — so the degeneracy theorem does not bite on the
work it is aimed at.

**F7. The null value is the finite-sample noise floor. (Major.)** Reported null rms is 0.039;
1/√M is 0.029 (ARC), 0.036 (TruthfulQA), 0.028 (GSM8K). To reported precision the elaborate exact
null coincides with the naive sampling floor — so the machinery may buy nothing empirically over a
trivial baseline. **This is a checkable arithmetic claim and it should be checked before
submission.** ~~[UNVERIFIED — I did not run this comparison.]~~ **RUN AND REFUTED (X5, see the addendum): the exact null sits at 1.25–2.01× the analytic floor, not on it. This objection does not stand, though the margin is a factor of 1.3–2 rather than an order of magnitude.**

**F8. Data recency and harness heterogeneity. (Major, convergent — 4/6.)** July 2023–June 2024
leaderboard v1: pre-Llama-3.1, pre-Qwen-2.5, pre-reasoning-model. The suite was retired for
saturation and contamination. Worse, **the prior work being corrected used v2, so this is not even
the same population.** The window also spans multiple lm-eval-harness versions and normalisation
conventions, so shared scoring artifacts masquerade as shared behaviour.

**F9. The theorems are one-line identities. (Critical, theory persona.)** C2 is
(Σᵢ Fᵢₘ)² = Σᵢ Fᵢₘ² + Σᵢ≠ⱼ FᵢₘFⱼₘ plus F²=F. C4 is PR = (tr R)²/tr(R²). C6 is definitional.
"Verified empirically to 1e-16" is a floating-point tautology — it verifies that the code
implements arithmetic.

**F10. Artifact compliance. (Critical for D&B track.)** ~~No license, no datasheet~~ (both added 2026-07-28: `LICENSE`, `docs/DATASHEET.md`), no Croissant
metadata, item axis unresolvable (anonymous bit grids), item alignment resting on a 14-model spot
check, tier-2 release redistributes reconstructed ARC gold keys at 99.01% fidelity (a licensing
and contamination hazard with a 1% undocumented label-error rate), and the artifact mutates on a
schedule with no versioning, checksums, or DOI.

**F11. Desk-reject risks. (Administrative but dispositive.)** 12 pages against a 9-page main-track
limit; named GitHub account and personal project page linked from a double-blind submission;
self-hosted pre-registration whose timestamps are author-controlled (git history can be rewritten).

---

## 2. Why NeurIPS would reject today

Six personas, six rejects, P(reject) **0.86–0.91**. The meta-review writes itself: *"The authors
are commendably rigorous, and the paper's own pre-registered tests show that adopting their null
leaves the prior literature's central claim intact. No downstream decision changes. The core
method is a standard psychometric test the paper itself cites. I do not see what a NeurIPS reader
does differently after reading this."*

**With the current core, my estimate of main-track acceptance is 3–6%.** Not because the work is
bad — it is unusually careful — but because NeurIPS scores contribution, not virtue, and after
four self-refutations the contribution ledger is empty. My own three experiments were an attempt
to refill it from the existing data and two of them failed. That is decisive evidence that this
is a scientific problem, not a writing problem.

---

## 3. Required scientific redesign

**Stop asking "how concentrated is the ecosystem?" It is not identifiable from this data and the
paper already proves it cannot answer it.**

Ask instead: **"Is the population that the field runs its correlation analyses on actually a
population of independent models — and what happens to published conclusions if it isn't?"**

That question is (a) answerable with data in hand, (b) already answered *in the affirmative* by my
KD1 result, (c) consequential for a body of published work, and (d) a measurement/audit
contribution, which is what this project actually is.

**The new contribution statement is in §14.** The three assets that survive and carry it:

- **A1. The degeneracy, relocated into ML.** Not "here is an identity" but "the double-fault
  diversity measure of Kuncheva & Whitaker is margin-determined, and here is what that does inside
  the standard diversity-regression framework": coefficients blow up to +316/+275 from
  collinearity, and ΔR² for *all* diversity measures over member accuracy is +0.0017. This is the
  identity made consequential for an ML audience.
- **A2. The instrument.** The exact conditional test, honestly positioned as an application of
  Ponocny (2001) with a *power characterisation* (what it can and cannot detect — the Narcissus
  answer) rather than a canonicality claim.
- **A3. The population result.** Leaderboard model populations are 36–64% redundant at agreement
  ≥0.95, and that redundancy is concentrated at the top, which reverses a strong apparent gradient
  on 3/5 benchmarks. Anyone analysing leaderboard populations must deduplicate first.

**Two findings worth keeping as secondary, both honest negatives with prescriptions:**
- Diversity metrics — classical *or* conditioned — have essentially no incremental value for
  predicting LLM panel accuracy (ΔR² ≤ 0.002 over member accuracy). Prescription: select judges
  and ensemble members by accuracy; diversity engineering is not buying anything at this scale.
  This contradicts widespread folk practice and is backed by 5,999 panels.
- GSM8K is the exception on every axis — its top-decile redundancy survives aggressive dedup
  (6.8×→5.4×) and its PR ratio is the least extreme (0.214 vs 0.028–0.056). Reasoning benchmarks
  may behave structurally differently from multiple-choice ones. Flag as a finding, not a claim.

---

## 4. Required experimental redesign

Keep: E0 (degeneracy check, demoted to a unit test), the curveball machinery, the dedup machinery.
Delete from the paper: C6 variance decomposition (definitional), the PR discovery-and-withdrawal
narrative (compress to two sentences), the "1e-16 on five benchmarks" contribution bullet.

**New experiments, in dependency order. Each carries a pre-registered kill condition.**

| # | Experiment | Kill condition | Status |
|---|---|---|---|
| X1 | **Duplicate census.** Lineage via name parsing + HF config/tokenizer/vocab hashing, not the `base_model` field that failed K5 at 23.3%. Report coverage, cluster sizes, and the accuracy-rank distribution of clusters. | Coverage <60% → report as a bound, not a census | **Not run** |
| X2 | **Dedup sensitivity of every headline number.** Rerun rms, eigenvalue count, PR on 0.99/0.97/0.95/0.90 populations. | Any headline number changes sign or >2× → it is a duplication result, report it as one | Partially done (KD1) |
| X3 | **Null-ladder head-to-head.** One table: rms and eigenvalue count under (a) uniform, (b) accuracy-conditioned, (c) fitted 1PL, (d) exact fixed-fixed, (e) 2PL parametric bootstrap, (f) q-dim MIRT for q=1..6, × 5 benchmarks, with CIs. | If (d) ≈ (a) within CI, the machinery buys nothing — report that | **Not run.** This is the single highest-value missing experiment |
| X4 | **Planted-signal power study.** Inject k correlated model families at controlled strength into real matrices; report detection power of each null. **This is the Narcissus answer** and the only way to characterise what the test can see. | Power <0.5 at realistic strengths → the instrument does not work; withdraw it | **Not run** |
| X5 | **Noise-floor check.** Compare exact-null rms against 1/√(M−3). | If they agree to 2 s.f., say so plainly in the abstract | **Not run.** Cheap; do this first |
| X6 | **Sampler validation.** χ² against complete enumeration on an 8×8 fiber; Gelman–Rubin across ≥4 dispersed chains. | Non-uniform → the word "exact" comes out everywhere | **Not run.** Note: I read `curveball` in `src/nullmodel.py` and it **does** correctly count failed trades (a failed trade consumes a loop iteration rather than resampling), which is the condition Carstens 2015 *Phys. Rev. E* 91:042812 + erratum 94:039902 require. That objection is refutable; the validation is still needed |
| X7 | **v2 replication.** Open LLM Leaderboard v2 archive (4,576 models × BBH/IFEval/MATH/GPQA/MuSR/MMLU-Pro), same $0 column-selective harvest. **This is also the population the prior work actually used.** | Effect vanishes on v2 → the finding is v1-specific; report that | **Not run** |
| X8 | **MMLU subject projection.** MMLU is in the v1 archive and was omitted. Its 57 labelled subjects give externally validated multidimensional structure — project residual eigenvectors onto subject indicators. Decisive for the multi-ability explanation. | Eigenvectors align with subjects → the residual is topic structure, not monoculture | **Not run** |
| X9 | **Contamination stratification.** Split by published contamination flags. | Effect concentrated in contaminated models → report as contamination measurement | **Not run** |
| X10 | **Tier-2 distractor analysis.** Decompose co-failure into same-wrong-option vs different-wrong-option. Correctness-only nulls structurally cannot represent the thing "models make the same mistake" means. | — | Partially done (K7) |

**X3, X4, X5 are the ones that decide whether there is a paper.** X5 is an afternoon.

---

## 5. Required methodological redesign

- Restate the degeneracy correctly: excess in O is identically zero over nulls preserving **item
  (column) margins** — not "any margin-preserving null." Add a worked counterexample with nonzero
  excess under a row-margin-only null. **As stated in the current paper the proposition is too
  broad, and once narrowed it does not bite on Kim et al., who condition on row margins.**
- State the sufficiency proposition formally and scope it: it holds for the **1PL logistic** link
  specifically. Margins are not sufficient under probit or cloglog. "The whole Rasch family" is
  wrong as written.
- Replace "canonical" with "the exact conditional null *within* the 1PL family — the weakest
  estimation-free null," and report sensitivity to family choice as a curve over null richness.
- Report degenerate row/column counts and rerun on trimmed matrices.
- Independent-chain nulls everywhere; the single-chain SES inflation the digest already flags
  makes every reported SES untrustworthy. **Report ratios, not SES.**
- Bootstrap CIs on every headline number including the eigenvalue count. There are currently none.
- Deposit the pre-registration on **OSF with a DOI**. Self-hosted git timestamps are
  author-controlled and a reviewer already flagged this.

---

## 6. Required literature redesign

Current: 28 refs, ~5 ML. Target: ~45 refs, ≥25 ML. Add, minimum:

- **Ensemble diversity:** Kuncheva & Whitaker (2003) — *mandatory*, double-fault is the paper's own
  statistic; Giacinto & Roli (2001).
- **Null-model epistemics:** Colwell & Winkler (1984) — *mandatory*, the Narcissus effect;
  Carstens (2015) + erratum (2016) for curveball uniformity.
- **Psychometrics positioning:** Ponocny (2001), Verhelst (2008), Chen/Diaconis/Holmes/Liu (2005) —
  already partly cited; must be repositioned from background to "this is the method we apply."
- **LLM eval science:** HELM, lm-evaluation-harness, Open LLM Leaderboard v1/v2 construction,
  tinyBenchmarks, Anchor Points, IRT-for-LLM-eval, contamination and saturation literature,
  LLM-as-judge and judge-panel work, model routing / cascades / mixture-of-agents.

**[UNVERIFIED]** — all six novelty sweeps failed on quota. I verified Kuncheva & Whitaker, Colwell
& Winkler, Carstens+erratum, and the v2 archive by direct search. **The rest of the ML citation
list is a specification, not a verified bibliography, and every entry must be checked before it
goes in the paper.** Do not let any citation into the manuscript unread.

---

## 7. Required benchmark redesign

The v1 suite is the wrong substrate: retired, saturated, contaminated, superseded by v2, and not
the population the prior work used. **Harvest v2** (4,576 models × 6 tasks) by the same
column-selective parquet method, plus **MMLU from v1** for X8. Keep v1 as the historical arm so
the paper can report a *change over eras* — which is the one thing a two-era substrate can say
that a one-era substrate cannot, and which Layer C is already built to extend.

---

## 8. Required evaluation redesign

Every claim needs a null-ladder row (X3) and a power number (X4). The paper currently reports
effect sizes against one null with no power characterisation, which is why the Narcissus objection
lands. Report the contrast that carries the claim — **0.248 vs 0.162 (multi-ability generator)**,
not 0.248 vs 0.039 — with CIs on both. In variance terms the honest effect is roughly a third of
the advertised one.

---

## 9. Required artifact redesign

Datasheet (Gebru et al. schema), Croissant metadata, explicit license with the upstream chain
documented, per-benchmark inclusion rules with counts at each filtering stage, resolvable item IDs
(not row indices), Zenodo DOI with checksums, semantic versioning, and a stated maintenance plan.
**Drop the reconstructed ARC gold keys from the public release** — redistributing a 99.01%-fidelity
answer key is both a licensing hazard and a contamination hazard. Ship the recovery *code* instead.

## 10. Required repository redesign

`pip install cofail` with a CLI (`cofail audit --matrix X.npy`) that runs the degeneracy check, the
null ladder, the dedup census, and emits a report. Test suite well beyond the current 3.2 KB,
including the X6 sampler validation as a test. Pin harness versions. Separate the paper's frozen
substrate from Layer C's mutating one — a schedule-mutating artifact with no versioning is
currently a reviewer objection, not a feature.

## 11. Required external validation

Zero third-party attestation exists today. In order of value: OSF pre-registration DOI (removes
the timestamp objection outright); Zenodo artifact DOI; arXiv preprint (`stat.AP`/`stat.ME` needs
no endorsement); contact Jo/Garg/Raghavan and Kim et al. — the K7 result *supports* Kim et al. and
that is a legitimate, and unusually strong, reason to write to them.

## 12. Required reproducibility improvements

Convergence diagnostics as artifacts, not prose. Seeds and environment pinned. Every number in the
paper emitted by a script into a JSON that the LaTeX reads — the digest discipline already exists;
finish it so no number is hand-transcribed. `make paper` from a clean checkout.

---

## 13. Required paper restructuring

9 pages, anonymised, D&B/Evaluations-track framing.

| § | Content | Change |
|---|---|---|
| Abstract | New (§16) | **REWRITE** |
| 1 Intro | Measurement-practice framing; drop the counting question | **REWRITE** |
| 2 Background | Double-fault, Kuncheva & Whitaker, Ponocny, Narcissus | **REBUILD** |
| 3 Degeneracy | Correctly scoped to column margins; counterexample | **MODIFY** |
| 4 Instrument | Application of Ponocny; **power characterisation** | **REBUILD** |
| 5 Substrate | v1 + v2, datasheet, dedup census | **REBUILD** |
| 6 Null ladder (X3) | New | **NEW** |
| 7 Population audit (X1/X2) | The duplication result | **NEW** |
| 8 Consequences | Diversity metrics have no incremental validity | **NEW** |
| 9 Limitations | Keep the honesty; it is the best-written section | **KEEP** |
| Old §6.1–6.8 | Compress 8 subsections to 2 | **DELETE/MERGE** |
| Old C6 | Definitional | **DELETE** |
| AI disclosure | Correct as written | **KEEP** |

---

## 14. New contribution statement

> Agreement-based diversity statistics used throughout LLM evaluation — of which the double-fault
> measure is the canonical instance — are determined by item margins and therefore carry no
> information about model similarity. We give the exact conditional test that removes this
> artifact, characterise what it can and cannot detect, and apply it to 5,800+ models across two
> leaderboard eras. Two consequences follow. First, leaderboard model populations are 36–64%
> redundant and that redundancy concentrates at the top, which reverses an apparent
> accuracy–redundancy gradient on three of five benchmarks — so correlation analyses on
> leaderboard populations must deduplicate first. Second, neither classical nor difficulty-
> conditioned diversity has meaningful incremental value for predicting panel accuracy over member
> accuracy alone (ΔR² ≤ 0.002 over 5,999 panels), so panel construction should optimise accuracy
> and stop paying for diversity engineering.

Against the required tests: original (the relocation into ML + the population audit), useful,
reproducible, general (any model×item matrix), actionable, hard to invalidate (identity + large N
+ pre-registered controls), survives better LLMs (it is a statement about measurement), useful
beyond this dataset, and stronger than "we discovered X."

## 15. Title options

1. *Your Diversity Metric Is Measuring Item Difficulty*
2. *Double-Fault Is Degenerate: Auditing Agreement-Based Diversity in LLM Evaluation*
3. *Leaderboard Populations Are Not Model Populations*
4. *What Survives an Exact Conditional Null? Auditing Correlated Failure Across 5,800 Open Models*

(1) for impact, (3) if X1/X2 come back as strong as KD1 suggests.

## 16. New abstract

> Claims that language models "fail on the same inputs" are usually supported by comparing a
> pairwise agreement or co-failure rate against an independence baseline. We show this comparison
> is uninformative by construction: mean pairwise co-failure — the double-fault measure of the
> ensemble-diversity literature — is a deterministic function of item margins, so its excess over
> any item-margin-preserving null is identically zero. We give the exact conditional test implied
> by Rasch sufficiency, following standard nonparametric Rasch methodology, and — unlike prior
> uses — characterise its power against planted correlated-failure alternatives, including the
> alternatives it provably cannot see. Applying it to N models across two Open LLM Leaderboard
> eras yields two results with immediate consequences for evaluation practice. First, leaderboard
> populations are heavily redundant: removing models agreeing above 0.95 removes 36–64% of the
> population, and because that redundancy concentrates among the highest-accuracy models it
> reverses an apparent accuracy–redundancy gradient on three of five benchmarks. Analyses treating
> leaderboard submissions as independent models are partly measuring duplication. Second, across
> 5,999 sampled panels, mean member accuracy and panel size explain R²=0.993 of majority-vote
> accuracy; classical diversity measures add ΔR²=0.002 and our difficulty-conditioned measure adds
> ΔR²=0.0002. Diversity metrics, corrected or not, do not help panel construction. We release the
> substrate, the audit tool, and a datasheet.

*(N left as a placeholder until X7 fixes the population.)*

## 17. Experiment roadmap

**Phase 0 (1 week, decides whether there is a paper):** X5 noise floor → X6 sampler validation →
X3 null ladder. If X5 shows the exact null equals the 1/√M floor and X3 shows null choice changes
nothing, **stop and reconsider** — that is a fourth kill and the instrument itself is in question.

**Phase 1 (3 weeks):** X1 duplicate census → X2 full dedup sensitivity → X4 power study. These
three produce the paper's central claim.

**Phase 2 (3 weeks):** X7 v2 harvest → X8 MMLU projection → X9 contamination.

**Phase 3 (2 weeks):** artifact compliance (§9–10), OSF/Zenodo DOIs, rewrite.

## 18. Figure roadmap

Every figure must make a conclusion impossible if removed.

| Fig | Question it answers | Fate |
|---|---|---|
| F1 | Does the excess vanish exactly under the correct null? | From `fig2`, **MODIFY** |
| F2 | Does the conclusion depend on the null? (X3 ladder) | **NEW** — the paper's most important figure |
| F3 | What can the test detect? (X4 power curves) | **NEW** — the Narcissus answer |
| F4 | How much of the structure is duplication? (X2) | **NEW** — from KD1 |
| F5 | Do diversity metrics predict panel accuracy? (nested ΔR²) | **NEW** |
| F6 | Does the effect hold in the modern era? (v1 vs v2) | **NEW** |
| old fig3 decomposition | none — definitional | **DELETE** |
| old fig6 spectrum, fig7 convergence | appendix at best | **DEMOTE** |

## 19. Table roadmap

T1 substrate (both eras, with dedup census). T2 the null ladder (X3) — *the* table. T3 dedup
sensitivity. T4 nested regression. T5 power (X4). Kill the current T2/T3.

## 20. Appendix roadmap

A: proofs, correctly scoped. B: sampler validation (X6, incl. 8×8 enumeration + Gelman–Rubin).
C: datasheet. D: harvest and inclusion rules with per-stage counts. E: the full pre-registration
and every fired kill condition, including the three from this session. F: LLM-assistance
disclosure.

## 21. Remaining risks

**R1. Phase 0 kills the instrument (X5/X3).** ~30%. Mitigation: X5 is one afternoon — run it
first, before any writing.
**R2. X4 shows low power against realistic alternatives.** ~40%. This would be a genuinely
important negative result but a much harder sell.
**R3. The v2 harvest is not available in the same form.** ~25%. Mitigation: verify before
committing to Phase 2.
**R4. The duplication result is judged "well known."** ~35%. Mitigation: nobody has quantified it
with a null-calibrated instrument and shown it reverses a published-style gradient — but this must
be checked against literature I could not sweep.
**R5. Single unaffiliated author with disclosed LLM assistance.** Unquantifiable. The disclosure
is correct and should stay; the mitigation is that the derivations must be defensible live.
**R6. Timeline.** NeurIPS 2026 main track closed May 6, 2026. Realistic targets: **NeurIPS 2026
workshop (~Aug 29, 2026)** for the degeneracy + duplication result as a short paper; **ICLR 2027**
or **NeurIPS 2027 D&B** for the full programme.

## 22. Probability assessment

| Scenario | P(accept) | Basis |
|---|---|---|
| Current paper, NeurIPS main track | **3–6%** | 6/6 personas reject at 0.86–0.91; three of my own spine tests failed |
| Current paper, NeurIPS workshop | **45–60%** | Workshops reward exactly this kind of methodological correction; non-archival |
| After §3–13, NeurIPS D&B / Evaluations | **25–35%** | Conditional on Phase 0 surviving and X1/X2/X4 landing |
| After §3–13, NeurIPS main track | **12–18%** | Still no algorithm; measurement papers are a hard sell on the main track |
| After §3–13, ICLR 2027 | **20–30%** | Broader tolerance for evaluation-science work |

**Recommendation.** Target **D&B / Evaluations**, not main track. Submit the degeneracy +
duplication result to a **NeurIPS 2026 workshop by Aug 29** — that is four weeks away, it is
non-archival so it does not burn the full paper, and it converts this work into an external
credential on the current timeline.

**What this document does not know.** All six novelty sweeps and all 33 verification agents failed
on a usage quota. The four papers I verified myself by direct search are Kuncheva & Whitaker 2003,
Colwell & Winkler 1984, Carstens 2015 + erratum, and the Open LLM Leaderboard v2 archive. **The
novelty of the redesigned contribution in §14 has not been checked against the literature.** That
sweep must be run before any of this is executed — if the duplication result is already published,
§3 changes again.

---

# ADDENDUM — Phase 0 and Phase 1 executed (2026-07-28, same day)

The blueprint above was written before any of its own experiments were run. Six of them have now
been run. **The picture improved substantially, and §3 and §22 should be read subject to this.**

## What was run, and what it found

| # | Experiment | Result |
|---|---|---|
| X5 | Noise-floor ladder | **PASS.** The exact null sits at 1.25–2.01× the analytic 1/√(M−3) floor, not on it. The reviewer objection is refuted. *But* column-margin conditioning alone reproduces the both-margin null to within 6%, so item margins do essentially all the work. |
| X6 | Sampler validation | **PASS.** χ² against complete enumeration on four fibres (to size 1,170) does not reject uniformity (p = 0.05–0.73); Gelman–Rubin R̂ = 0.98–1.03 on all five benchmarks. "Exact" is now earned. |
| X1/X2 | Duplication audit | **14 of 15 statistic–benchmark pairs robust.** Removing 36–64% of each population moves the headline ratios ≤1.46×. Only HellaSwag's PR ratio is duplication-driven (2.44×). |
| X4 | Power study | **PASS, plus the Narcissus answer.** Power 1.00 against shared failure modes at planted rms 0.048 (real data: 0.099–0.294); copying detected from c ≥ 0.1; and power **exactly 0.05 = α** against the shared-difficulty alternative, because that alternative *is* the null. |
| X3 | Null ladder | Permutation rungs (R0–R3) usable and reported. The fitted rungs (2PL, MIRT) are **not** — see below. |
| — | Dimensionality (q*) | **RETRACTED.** Three fitting attempts disagreed; the third revealed that with free per-item loadings, q=1 is 2PL, not Rasch, so the ladder counted from the wrong baseline. Left open for an established IRT package. |

## The consequence for §3

**F2 (the duplication confound) is now largely answered rather than conceded**, which was the
single most-cited objection across all six reviewer personas. F4 (Narcissus) is now *quantified*
rather than merely admitted — and quantifying a blind spot exactly is a stronger scientific
position than not knowing it. The instrument objections behind F5 and part of F9 are answered by
X6.

The redesign in §3 should therefore be revised: the paper does **not** need to retreat entirely to
a duplication audit. It has a defensible measurement plus a characterised instrument. The correct
framing is now:

> Mean co-failure is the double-fault diversity measure and is margin-determined. Here is the
> exact conditional test, here is a validated sampler, here is exactly what the test can and
> cannot detect, and here is what survives on 1,228–1,373 models across five benchmarks —
> including after 36–64% of each population is removed as near-duplicate.

## One thing found that was not on the list

**A number in the paper traced to no executed run.** The manuscript reported the ARC null as
0.0389 and an abstract claim of a "sixfold excess." No artifact in `results/` produces 0.0389;
four independent estimates give 0.0445–0.0449, and the correct ratio is 5.5×. Fixed in three
places and recorded in `results/RESULTS_DIGEST.md`. Most likely a scope mix — 0.039 is close to the
cross-benchmark *mean* null (0.0398), paired with ARC's benchmark-specific observed value. It is
the kind of defect a hostile reviewer finds, and it was found by cross-checking the paper against
newly computed values rather than by any of the planned experiments.

## Revised probability assessment

| Scenario | Before | **After Phase 0/1** | Why |
|---|---|---|---|
| NeurIPS main track, as-is | 3–6% | **6–10%** | Still no capability claim, still 14 pages, still v1 data |
| NeurIPS workshop | 45–60% | **60–70%** | The instrument is now validated and the leading confound answered |
| NeurIPS D&B / Evaluations after §9–13 | 25–35% | **35–45%** | Datasheet and LICENSE now exist; power characterisation is exactly what that track rewards |
| ICLR 2027 | 20–30% | **25–35%** | Same reasoning, broader tolerance |

## What remains, in priority order

1. **The dimensionality question** — the paper's central identification issue, still open. Needs
   R `mirt` or `py-irt`, not a bespoke optimiser.
2. **The novelty sweep** — still never run (quota). Nothing in §14's contribution statement has
   been checked against the literature.
3. **X7 v2 replication**, X8 MMLU subject projection, X9 contamination — all unrun.
4. Cut to 9 pages and anonymise; deposit the pre-registration on OSF and the artifact on Zenodo.
5. Fill in the upstream license table in `docs/DATASHEET.md` and withhold the reconstructed ARC
   answer key from any public release.

## X7 feasibility check — the v2 replication is NOT a drop-in repeat of the v1 harvest

The blueprint above assumed the v2 leaderboard could be harvested by the same $0
column-selective parquet trick that made v1 free. **Checked directly, and it cannot.**

The v2 archive exists and is reachable, under a different naming convention
(`open-llm-leaderboard/<org>__<model>-details`, versus v1's
`open-llm-leaderboard-old/details_<org>__<model>`). But v2 stores per-sample outcomes as
**JSON, not parquet**, so there is no column to read selectively — the whole file must come down.

Measured on `meta-llama__Meta-Llama-3-70B-Instruct-details`: 120 sample files totalling
**1,107 MB for one model** across three snapshots, i.e. ~369 MB per model per snapshot. MMLU-Pro
alone is **403 MB per model per snapshot**. Extrapolated to a 1,000-model population that is
roughly **369 GB**, against the ~1.4 KB per model per benchmark that v1 cost.

**Consequences for the roadmap.**
- A full six-task, 1,000-model v2 replication is not feasible on a personal connection, and any
  plan that assumes otherwise will fail in week one of Phase 2.
- A scoped version is feasible and should replace it: **ARC-Challenge in v2 is 9.4 MB per model
  per snapshot**, so ~300 models is ~2.8 GB. GPQA (198 items) is smaller still. That is enough to
  answer the recency objection on one task with a matched comparison against the v1 arm.
- **Drop MMLU-Pro from any harvest plan** unless a parquet mirror is found.
- Revised §17 Phase 2: replicate on v2 ARC-Challenge and GPQA at ~300 models, not all six tasks at
  full population.

This is recorded because the cheapest way to lose a month is to plan around a harvest method that
does not transfer, and the check took ten minutes.

## Novelty sweep — closed (2026-07-31)

Every prior attempt at the three remaining sweeps (`judge-panels`, `monoculture-2026`,
`tools-packages`) went through the Workflow/Agent subagent path and failed three separate times on
three separate quota mechanisms: weekly limit, then session limit, then session limit again. **The
fix was not to keep retrying that path — it was to use WebSearch/WebFetch directly from the main
agent, which was available the entire time and does not share the subagent quota.** Two searches
and two full-PDF reads later, the gap is closed. Full detail in
`docs/PRIOR_ART_LEDGER.md` §"Novelty sweep, completed by direct search"; summary here.

**Two verified hits, both read from the primary PDF** (not a fetched summary — a WebFetch summary
of the Kohli paper earlier in this project fabricated details on inspection, so this discipline was
non-negotiable):

1. **Kim, D. (2026), arXiv:2607.20768, "Are Diversity Metrics Measuring Diversity?"** — posted six
   days before this project's active work. Independently finds diversity measures (including
   double-fault, the same statistic our Lemma 1 covers) are rank-deficient with mean accuracy and
   contribute only a modest residual to LLM-ensemble majority-vote gain, using an exact algebraic
   identity and partial-correlation capability controls — no margin-preserving null. **Narrows
   Claim 6** (our incremental-validity finding) to "independently corroborated by different
   machinery," not novel. Does not touch Claims 1–5, 7, 8.
2. **Sha & Zhao (2026), arXiv:2603.29357, "BenchScope"** — counts effective independent
   *benchmarks* (not models) using the same participation-ratio statistic we withdraw as a model
   count, and reaches the identical caution ("screening statistic, not a literal factor count")
   independently. Orthogonal axis, no exact null. Corroborates rather than threatens §6.1.

Both are now cited in `paper/main.tex` and `paper/workshop.tex`, with the incremental-validity and
participation-ratio passages reworded to present the overlap explicitly rather than let a reviewer
find it unaided. Both papers recompile clean, zero undefined citations.

**Revised assessment.** The blueprint's §14 contribution statement survives this sweep intact:
nothing found kills Claims 1–5, 7, or 8, and the two genuine overlaps (6, and the PR-caution framing
around 7) were already the paper's most hedged claims — being independently corroborated rather
than solitary is a strengthening, not a weakening, provided the paper cites the overlap honestly,
which it now does. The residual novelty risk is what a *further* sweep of the areas actually
searched (judge-panel construction beyond Kohli/Kim, monoculture literature since mid-2026, an
exhaustive GitHub/PyPI trawl) might still find — those queries returned only secondary context
(other papers' related-work sections, leaderboard redundancy figures) that was not independently
verified and is recorded as leads, not claims, in the ledger.

## X7 correction — v2 access is gated, not just large (2026-08-07)

The X7 feasibility check above measured **file size only** (via API metadata) and concluded the v2
replication was a size/bandwidth problem. Attempting the actual harvest, after the user authorized
the scoped ~2.8GB download, surfaced a second, more fundamental blocker that the size-only check
never touched: **v2 `-details` datasets are gated** (`api.dataset_info(...).gated == "auto"`),
returning `401 GatedRepoError` on every content request. v1 (`open-llm-leaderboard-old`) is
`gated: False` and worked anonymously all session, which is why this was never surfaced before now.

`gated: "auto"` typically means any authenticated HuggingFace account that accepts the dataset's
terms gets automatic access — this is not a high-friction manual-review gate — but it still
requires (a) an HF account, (b) accepting terms on the `open-llm-leaderboard` org's datasets, and
(c) an access token supplied to the harvest environment. None of that was disclosed when the user
approved the download, because the check that informed the ask never exercised real content
access, only `list_repo_files`/size metadata (which apparently doesn't require the same auth).

**Correction to the record, not just an update:** the "Consequences for the roadmap" section above
is still right about scope (ARC-Challenge + GPQA, ~300 models, drop MMLU-Pro) but understated the
blocker. This is now flagged as an open decision for the user rather than executed unprompted:
supplying an HF access token is not equivalent to a password or financial credential, but it is a
new requirement beyond what was approved, discovered only after the ask, so it goes back to the
user rather than being assumed.

`src/harvest_v2_arc.py` is written and ready (scoped to n_models, checkpointed every 10 models,
same rate-limiter as the v1 harvesters) but has not run past the gating wall. Its field-name
parsing for v2's `samples_leaderboard_arc_challenge_*.json` records (`acc`/`acc_norm` vs
`predictions`/`target` fallback) is also **unverified against a real record** — the one real file
this session touched (`01-ai__Yi-34B`) failed at the auth step before parsing could be tested, so
that logic should be treated as untested until a real file is successfully read.

## v2 ungated-mirror check — negative result, recorded (2026-08-07)

Before accepting the HF-auth blocker as final, checked whether any ungated mirror of v2 per-item
data exists. Two candidates found and inspected directly (both genuinely `gated: False`):
`open-llm-leaderboard/results` (per-model `results_*.json`, ~120 KB each) and
`open-llm-leaderboard/contents` (single parquet, 4,576 rows). **Both are aggregate-only** — the
`contents` parquet's columns are per-benchmark summary scores (IFEval, BBH, MATH Lvl 5, GPQA,
MUSR, MMLU-PRO), and each `results_*.json`'s `results` key holds aggregate metric dicts, not
per-item correctness. Neither contains the per-item detail the co-failure analysis needs; that
lives only in the gated `<model>-details` repos' `samples_*.json` files. The HF-auth blocker
stands; there is no ungated workaround.

## GitHub release prepared as a draft, not published (2026-08-07)

`gh release create v1.0.0 --draft` run to reduce the Zenodo-activation step to one click. Verified
`isDraft: true` via `gh release view`: draft releases are private to repo collaborators, are not
included in the public releases feed, and do not trigger Zenodo's release webhook, so nothing was
published or made publicly visible. The user's remaining action is exactly one click ("Publish
release") once they've toggled the repo on at zenodo.org — everything else that can be prepared
without their account credentials now is.
