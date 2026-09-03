# Pre-registration — three workshop-paper experiments

Written **before** any of the three scripts below was executed. Commit history is the dating
evidence. Each workshop short paper proposed work it had not done; this document specifies that
work, and the condition under which each experiment returns a negative result that must be
reported as such.

Population for W1 and W2: the current substrate, i.e. the 2026-08-09 harvest
(ARC-Challenge, N = 3,762 models after degeneracy filtering, M = 1,169 items). This is **not** the
N = 1,362 population of the journal manuscript's headline tables, which came from an earlier,
partial harvest of the same archive and is not reproducible from the current substrate. Every
number produced here must be labelled with N = 3,762 and must not be presented as if it were
computed on the manuscript's population. The headline statistics for this exact population are
already on record in `results/timeseries.csv` (row `2026-08-09,arc`): PR ratio 0.0449,
rms |R| 0.2437 observed against 0.0453 null.

---

## W1 (ATTRIB) — does the residual spectrum carry model-family information?

`src/w1_family_signal.py` -> `results/w1_family_signal.json`

The ATTRIB short paper asks: do the leading residual eigenvectors of the margin-conditioned
co-failure matrix separate, even loosely, models of different declared base family? The paper
currently poses this as an open question. This experiment answers it.

**Design.** Fit the Rasch mean field to the ARC failure matrix, form the residual correlation
matrix R, take the top-k eigenvectors (k = number of eigenvalues above the exact null's spectral
edge). Label models by base family using the existing name-string matcher
(`dedup_sensitivity.family_of`), which is a coarse lower bound on relatedness and not lineage
ground truth. Restrict to models attributable to one of the five largest named families. Test
statistic: leave-one-out 5-nearest-neighbour classification accuracy of family label in the
standardised k-dimensional loading space.

**Three reference distributions**, all required:
1. *Label permutation* (1,000 draws): family labels shuffled, pipeline otherwise identical. This
   is the primary null.
2. *Exact conditional null*: the entire pipeline re-run on a curveball replicate of F, with real
   family labels. Under the exact null the eigenvectors cannot carry family information, so this
   must land at chance. It is the calibration check that the pipeline is not manufacturing signal.
3. *Majority-class rate*: the accuracy of always predicting the largest family.

**KW1 (kill condition).** If observed LOO accuracy does not exceed the 95th percentile of the
label-permutation null, the finding is **no detectable family signal**, and the ATTRIB paper must
report the negative result — the residual structure does not carry recoverable provenance
information at this granularity — rather than restating the question as open.

**KW2 (duplicate-artifact kill condition).** Family separation is uninteresting if it is driven by
near-duplicate submissions inside a family. The whole experiment is therefore repeated on the
population deduplicated at pairwise agreement 0.95. If accuracy falls to the permutation null
after deduplication, the signal must be reported as a duplicate artifact, not a provenance signal.

**KW3 (calibration kill condition).** If reference distribution 2 (curveball replicate, real
labels) does *not* land at chance, the pipeline is manufacturing signal and no result from it may
be reported at all.

---

## W2 (E-values) — a sequential monitor on the real arrival stream

`src/w2_sequential_evalue.py` -> `results/w2_sequential_evalue.json`

The E-values short paper argues the exact conditional null is the right fixed-sample primitive for
an anytime-valid monitor, states that averaging calibrated e-values is valid across a
pre-specified set of looks, and says no monitor has been built. This experiment builds the
fixed-set-of-looks version and tests it against a null stream.

**Design.** Order ARC models by leaderboard submission date. Take monthly looks
t = 1..T over the accumulating population. At each look compute rms |R_ij| on the population to
date, and a Monte Carlo p-value against R = 40 curveball replicates drawn for that population,
p_t = (1 + #{null >= obs}) / (R + 1). Calibrate each to an e-value by the standard calibrator
e_t = kappa * p_t^(kappa - 1) with kappa = 0.5, and report the running arithmetic mean of e_t,
which is a valid e-value under arbitrary dependence between looks (Vovk & Wang 2021) — the
dependence here is severe, since the populations are nested.

**Control arm (required).** The identical pipeline where the observed matrix at each look is
replaced by a curveball draw from that look's own exact null. This is a stream in which the null
is true by construction.

**KW4 (kill condition).** If the control arm's merged e-value exceeds 20 at any look, the
construction is invalid as implemented and must be reported as failing rather than presented as a
monitor.

**Stated in advance:** the real-data p-values are expected to hit the Monte Carlo floor
1/(R+1), because the effect size on record is enormous (SES < -100). The merged e-value is
therefore expected to saturate at the calibrator's maximum for p = 1/41. That is a ceiling of the
Monte Carlo resolution, not unbounded evidence, and the paper must say so in those words rather
than quoting a large number as if it were a likelihood ratio.

---

## W3 (EvoRobust) — is the degeneracy decision-relevant?

`src/w3_diversity_decision.py` -> `results/w3_diversity_decision.json`

The EvoRobust short paper argues that mean-level diversity and coverage metrics are degenerate and
that margin calibration fixes them, but demonstrates this only as an identity plus an observational
study. This experiment tests whether the degeneracy actually reverses a decision.

**Design.** Two synthetic suites, each 200 members x 500 test cases, in the shape of a red-teaming
evaluation where "failure" is "the probe succeeded against this member":
- **Suite A, genuinely diverse:** members fail conditionally independently given the item; item
  difficulty (probe potency) strongly heterogeneous, sd(logit difficulty) = 2.0.
- **Suite B, shared failure modes:** members drawn in 5 clusters with shared failure modes; item
  difficulty homogeneous, sd(logit difficulty) = 0.15.
Ground truth: A is the diverse suite, B is not. Compute for each: mean double-fault, mean pairwise
disagreement, and the calibrated statistics (rms |R| against its own exact null, and eigenvalues
above the null edge).

**KW5 (kill condition).** If the naive mean-level metrics do **not** rank A as less diverse than B
— i.e. if they get the ordering right — the degeneracy is not decision-relevant in this regime and
the EvoRobust paper must say so and drop the governance claim to a much weaker one.

**KW6.** If the calibrated statistics also get the ordering wrong, the proposed correction does not
work and must not be recommended.

Both suites are generated from a fixed seed recorded in the artifact.
