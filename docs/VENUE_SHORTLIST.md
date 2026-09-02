# Target venue shortlist

**Status — 2026-09-02: journal track is now the sole active plan.** This document was originally
written for a Q2 statistics journal, then partly superseded on 2026-08-07 when the project added a
parallel NeurIPS 2026 workshop track (`paper/workshop.tex`, `docs/NEURIPS_BLUEPRINT.md`). That
window has since closed: the two best-fit workshops found on the NeurIPS 2026 announcement
(`TAI-Eval` and `JUDGe 2026`, both https://blog.neurips.cc/.../announcing-the-neurips-2026-workshops/)
share an August 29, 2026 (AoE) deadline, checked directly against their CFP pages, and today is
September 2 — four days past it. `paper/workshop.tex` is left as-is, unconverted, as a ready
starting point for either workshop's 2027 cycle rather than reworked for a deadline that no longer
exists.

**The journal analysis below is unaffected and is now the only track being executed.** Everything
in this document was already correct for it and needed no re-verification from the pivot.

**Format decision, 2026-09-02.** `paper/main.tex` has been converted from a standalone
`article`-class document to Springer Nature's official `sn-jnl` template
(`sn-mathphys-ay` citation style, matching this journal's author-year requirement exactly), per
explicit user choice over keeping the simpler original class. The conversion needed the class file
and one `.bst`, both now committed alongside `main.tex` (`paper/sn-jnl.cls`,
`paper/sn-mathphys-ay.bst`) per the submission guidelines' "no subfolders" rule. Every one of the
document's `\citep`/`\citet` calls, and the entire hand-typed bibliography, needed zero changes —
the `sn-mathphys-ay` option loads `natbib[authoryear]` internally, and a manually-written
`thebibliography` block is orthogonal to whichever `.bst` the class nominally sets. Full 20-page
visual re-review after conversion found zero regressions from the class swap itself, but caught
two real, pre-existing bugs in the source figures (a clipped axis label in `fig_misspec.pdf`, and
a literal unrendered `\ref{fig:misspec}` string baked into `fig_residual_summary.pdf` — see
`src/svg_figures.py` fix and `git log`) that had been sitting in the paper undetected regardless of
document class.

**Remaining before submission:** none on the manuscript itself — the title page now reads
"Mumbai, India" (filled 2026-09-02). Only the Editorial Manager account/submission step remains,
and that requires the author directly (account creation and credential entry are outside what this
assistant will do).

The "before submitting" checklist at the bottom is now stale in one place: the tier-2 response
analysis it lists as outstanding was run on 2026-07-26 (kill condition K7 fired; see
`results/RESULTS_DIGEST.md`). Struck through below rather than deleted.

**Provenance caveat.** The workflow agent tasked with verifying venues died on a session limit,
so this rests on my own searches, and only the two ranked entries below were verified against a
citable source. Everything marked *unverified* needs checking before submission. Scimago blocks
automated fetching, so quartiles come from secondary aggregators and should be confirmed on
scimagojr.com by hand.

## Binding constraints

1. **Scimago Q2 or better** in a relevant category.
2. **No article processing charge on at least one route.** The author has no budget. Hybrid
   journals whose *subscription* route is free of charge qualify; fully open-access journals
   charging an APC do not, absent a documented waiver for unfunded authors.
3. Scope must accept a **methodological-correction paper**: a degeneracy identity, a
   randomisation estimator, a large empirical study, and a withdrawn claim.

## 1. Computational Statistics (Springer) — **primary**

- **Quartile:** SJR 0.524, **Q2** (2025); best quartile Q2 (2024).
- **APC:** hybrid. Authors may choose the **subscription route, for which no APC applies**;
  open-access route is £2,290 / \$3,190 / €2,590.
- **Scope fit: strong.** "An international journal fostering applications and methodological
  research in computational statistics and data science, emphasizing the contribution to and
  influence of computing on statistics and vice versa." A margin-preserving randomisation
  estimator with MCMC convergence diagnostics, a closed-form identity, and a released software
  package sits squarely inside this. The journal also publishes software articles, which suits
  the `cofail` package.
- **Why first:** it is the only candidate where the quartile *and* a zero-cost route are both
  confirmed, and where the paper's actual content — computational method plus diagnostics — is
  the journal's stated centre rather than an awkward fit.

## 2. Statistical Analysis and Data Mining: An ASA Data Science Journal (Wiley) — **backup**

- **Quartile:** SJR **Q2**. JCR is volatile (reported 3.6/Q1 for 2025 and 1.1/Q3 in the 2026
  release) — flag this, since a Q2 requirement met on SJR but not JCR may matter depending on
  whose definition is used.
- **APC:** open-access route \$4,150 — **not viable**; the subscription route carries no charge.
- **Scope fit: strong.** Statistical and machine-learning methodology plus high-impact
  applications, with stated interest in "innovative analytical techniques and their application
  to real problems". Offers free-format submission.
- **Why second:** scope is as good as the primary, but the JCR quartile instability is a risk
  against a hard "Q2" requirement.

## Unverified candidates worth checking

Listed because they plausibly satisfy all three constraints, not because they have been checked.

- *Behaviormetrika* (Springer) — psychometrics/behavioural measurement; the Rasch-sufficiency
  framing would be native here, and the audience already knows Cronbach's α and Fleiss.
- *Advances in Data Analysis and Classification* (Springer) — sources conflict Q1 vs Q2.
- *British Journal of Mathematical and Statistical Psychology* — natural home for the
  conditional-inference argument; quartile and APC unchecked.
- *Journal of Computational Science* (Elsevier), *Scientometrics* (Springer),
  *Quantitative Science Studies* (MIT Press, APC with possible waivers).

Deliberately excluded: *Transactions on Machine Learning Research* — an excellent scope fit and
free, but not Scimago-ranked, so it cannot satisfy a Q2 requirement.

## Fit assessment against the current manuscript

The paper's strongest features for a statistics venue are the exactness argument (conditioning on
sufficient statistics rather than fitting a nuisance model), the reconciliation of two
opposite-signed statistics via an exact variance decomposition, and the discipline of the
pre-registration — including a hypothesis refuted by its own kill condition, a gate that failed
and dropped a contribution, and a headline claim withdrawn after adversarial review. Reviewers at
a methods journal tend to reward that; a venue chasing novelty will not.

The weakest feature is that the underlying identities are classical. The paper must therefore be
sold as a **bridge and a measurement**, not a discovery — which is how it is now written.

## Before submitting

- Confirm both quartiles by hand on scimagojr.com.
- ~~Confirm in writing that the subscription route is genuinely free of charge for an unaffiliated
  author with no institutional agreement.~~ **Done 2026-09-02** — fetched
  `link.springer.com/journal/180/submission-guidelines` directly. Confirmed: no page/word limit on
  the article itself; abstract hard-capped at 150–250 words (the pre-existing 681-word abstract was
  rewritten to 249, verified by script); 4–6 keywords required (added); a "Statements and
  Declarations" section with that exact heading is required for completeness (added, with the full
  Funding/Competing Interests/Ethics/Consent/Data/Materials/Code/Author-Contribution set, not just
  the two the guidelines call out by name); a Data Availability Statement is mandatory (added,
  citing the Zenodo DOI, GitHub repo, and OSF deposit); citation format is author-year in
  parentheses, which `natbib[authoryear]` (loaded automatically by the `sn-mathphys-ay` class
  option) already produces without changing a single in-text citation.
- Check the journal's AI-disclosure policy against the statement in `paper/main.tex`; COPE
  guidance (AI cannot be an author, use must be disclosed) is already followed — confirmed against
  the actual guidelines text on 2026-09-02, which matches Section 9's wording closely.
- ~~Run the tier-2 response analysis or cut its forward reference from the limitations section.~~
  **Done 2026-07-26** — K7 fired (the accuracy-agreement claim survives conditioning, reported as
  robust); see `paper/main.tex` Section 6.8 and `results/RESULTS_DIGEST.md`.
- The manuscript now also cites two 2026 papers found in a later novelty sweep (Kim 2026, Sha &
  Zhao 2026 "BenchScope") that a journal reviewer in this space would very plausibly know; the
  paper already positions against both (see `docs/PRIOR_ART_LEDGER.md`), so no action needed here
  beyond being aware a reviewer may raise them independently.
- ~~Fill in the author's city on the title page.~~ **Done 2026-09-02** — "Mumbai, India".
- Editorial Manager portal located (`https://www.editorialmanager.com/cost/`); cover letter drafted
  (`docs/COVER_LETTER.md`). Submission itself still requires the author to create the account and
  upload files directly.
