# Cover letter — Computational Statistics submission

Ready to paste into Editorial Manager's cover-letter field at submission
(https://www.editorialmanager.com/cost/). Editor-in-Chief: Prof. Philippe Vieu (Toulouse
Mathematics Institute, Université Toulouse III).

---

Dear Prof. Vieu,

I am submitting my manuscript, "How Many Independent Models Does an Open-Model Ecosystem
Contain? Evidence at the Exact Conditional Null," for consideration as a research article in
Computational Statistics.

The paper addresses a measurement problem in a growing empirical literature on correlated
failure between machine learning models: pairwise co-failure rates are routinely compared
against an independence baseline, and a recent paper (Jo, Garg, and Raghavan, 2026) showed this
comparison is highly sensitive to the assumed null, concluding that the choice is subjective. I
show that one null is canonical rather than arbitrary. The row and column margins of a
model-by-item outcome matrix are the jointly sufficient statistics of the Rasch family, so the
uniform distribution over margin-matched matrices is the unique exact, fit-free conditional null
for that entire family — it requires no fitting, no penalty, and no identification convention. I
apply this null at scale (1,228-1,362 open models per benchmark, across five benchmarks) and
report what survives: the commonly reported mean-level "excess" co-failure is a deterministic
function of item difficulty and vanishes identically under this null (a degeneracy I trace to
independent, unconnected proofs in ecology, psychometrics, and inter-rater reliability), while a
genuine second-order residual correlation of 2.8-11.8x the null remains, is robust to removing
near-duplicate models, and is shown not to be an "effective number of independent models" by an
explicit algebraic argument.

I believe the paper is a good fit for the journal's stated interest in computational method
alongside methodological diagnostics: the randomisation estimator is validated against direct
enumeration on small fibres and characterised for detection power (including an explicit,
by-construction blind spot) rather than merely applied, and the full pipeline — harvest, curveball
sampler, Rasch fit, spectral diagnostics — is released as an installable package
(`cofail`) with every reported number traced to a committed, executed-run artifact.

The study was pre-registered before the confirmatory analysis, with dated amendments recorded
before any confirmatory statistic was computed (deposited at https://osf.io/cmh7q/, with the
underlying commit history providing independent dating). One pre-registered hypothesis was
refuted by its own kill condition and is reported as refuted rather than reinterpreted; a
separate pre-registered test aimed at a specific published claim in prior work came back
supporting that claim, and is reported as such. All code, the harmonised substrate, and every
results artifact are archived at https://doi.org/10.5281/zenodo.21860005.

This manuscript is original, has not been published previously, and is not under consideration
elsewhere. It contains no material requiring third-party copyright permission. I have no
competing interests to declare, and the work received no external funding. A large language
model (Claude, Anthropic) was used as a coding and analysis assistant, as disclosed in the
manuscript's Reproducibility section, in line with COPE guidance that AI tools cannot be authors.

Thank you for your consideration.

Sincerely,
Shaurya Gupta
shauryaguptaa8@gmail.com

---

## Notes for submission (not part of the letter)

- Suggested reviewers: none identified yet. The guidelines note the corresponding author "must
  provide an institutional email address for each suggested reviewer, or... other means of
  verifying identity" if suggesting any — optional, can leave blank.
- Editorial Manager will ask to classify the submission type (e.g. "Original Paper"/"Original
  Research"); pick that, not a short communication/note track.
- Have ready at submission time: `paper/main.tex`, `paper/sn-jnl.cls`, `paper/sn-mathphys-ay.bst`,
  and every `figures/*.pdf` the manuscript includes, all in one flat upload (no subfolders, per
  the guidelines) — plus the compiled `paper/main.pdf` for the system's own PDF conversion check.
- ORCID: not currently on file for the author; the submission form will offer to create/link one
  during the process if desired — optional per the guidelines ("if available").
