# Target venue shortlist

**Superseded as the sole strategy — 2026-08-07.** This document was written when the only target
under consideration was a Q2 statistics journal. Since then the project ran a full adversarial
NeurIPS-readiness audit (`docs/NEURIPS_BLUEPRINT.md`) and built a submittable 4-page workshop cut
(`paper/workshop.tex`). **The two tracks do not conflict** — a NeurIPS workshop is non-archival, so
submitting there does not block or compete with a journal submission — and the current plan runs
both in parallel:

1. **NeurIPS 2026 workshop, time-sensitive.** Suggested contribution deadline ~Aug 29, 2026 (AoE);
   `paper/workshop.tex` is ready. This is the higher-priority, deadline-bound item right now.
2. **The journal track below, not time-sensitive.** Everything in this document remains the
   correct analysis for that track and has not been re-verified or invalidated by the pivot — it
   just stopped being the *only* plan.

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
- Confirm in writing that the subscription route is genuinely free of charge for an unaffiliated
  author with no institutional agreement.
- Check the journal's AI-disclosure policy against the statement in `paper/main.tex`; COPE
  guidance (AI cannot be an author, use must be disclosed) is already followed.
- ~~Run the tier-2 response analysis or cut its forward reference from the limitations section.~~
  **Done 2026-07-26** — K7 fired (the accuracy-agreement claim survives conditioning, reported as
  robust); see `paper/main.tex` Section 6.8 and `results/RESULTS_DIGEST.md`.
- The manuscript now also cites two 2026 papers found in a later novelty sweep (Kim 2026, Sha &
  Zhao 2026 "BenchScope") that a journal reviewer in this space would very plausibly know; the
  paper already positions against both (see `docs/PRIOR_ART_LEDGER.md`), so no action needed here
  beyond being aware a reviewer may raise them independently.
