# NeurIPS 2026 workshop submissions — operational checklist

Three papers, three venues, all non-archival (so none of this blocks the Computational Statistics
journal submission, and all three CFPs explicitly permit work under review elsewhere).

Every item marked **YOU** requires the author personally: it needs an account, a credential, or a
commitment only the author can make. Nothing on this list can be done on the author's behalf.

---

## ⚠️ READ FIRST — the OpenReview profile is the real bottleneck

All three venues submit through OpenReview, and OpenReview's own moderation policy (quoted in the
NeurIPS 2026 Main Track Handbook) is:

> New profiles created **without an institutional email** will go through a moderation process that
> **can take up to two weeks**. New profiles created with an institutional email will be activated
> automatically.

The E-values site independently says: *"Please create your OpenReview profile at least two weeks
before the submission deadline."*

**You are an independent researcher submitting from a gmail address, so you fall in the
non-institutional bucket.** Today is Sep 3; the E-values and ATTRIB deadlines are Sep 5 AoE.

- **If you already have an active OpenReview profile:** nothing to do, proceed below.
- **If you do not:** create it *today*, and treat the two Sep 5 submissions as at risk. EvoRobust
  (Sep 12) has enough runway to survive the moderation window. Nothing in the papers can fix this;
  it is a platform queue.

Check by logging in at https://openreview.net/ — an active profile resolves to
`https://openreview.net/profile?id=~Firstname_Lastname1`.

## Deadlines (verified against each workshop's own site, 2026-09-03)

| Venue | Deadline | Local (IST, UTC+5:30) | Page limit | Blinding |
|---|---|---|---|---|
| E-Values: From Statistics to ML | **Sep 5, 23:59 AoE** | **Sep 6, 17:29** | 4 pages + refs | single-blind (name shown) |
| ATTRIB 2026 | **Sep 5 AoE** | **Sep 6, 17:29** | main track 3–6 pages | double-blind |
| EvoRobust | **Sep 12, 23:59 AoE** | **Sep 13, 17:29** | 4 content pages | anonymised |

AoE is UTC−12. A deadline of "Sep 5 AoE" expires at 17:29 IST on **Sep 6**.

---

## ⚠️ ATTRIB: the reciprocal reviewing commitment — **YOU**, and it is a desk-reject risk

ATTRIB uses reciprocal reviewing. From their CFP, verbatim in substance:

> For each submission, at least one author is expected to serve as a reviewer. Reviewers are
> assigned up to 2 papers, with reviews due **September 22 (AoE)**. Please designate your
> submission's reciprocal reviewer on the **Reviewer Registration Form** linked in the OpenReview
> portal. **Submissions without a participating reviewer may be desk rejected.**

**This is not optional and it is not automatic.** Submitting the PDF is not enough. You must:

1. Open the Reviewer Registration Form linked from the ATTRIB OpenReview portal.
2. Register yourself as the reciprocal reviewer for this submission.
3. Hold **Sep 22 AoE** open to review up to 2 papers.

If you are not willing to review 2 papers by Sep 22, **do not submit to ATTRIB** — a desk reject
for an unmet reviewing commitment costs more than not submitting. The other two venues carry no
such obligation.

---

## Verified against the live CFPs, 2026-09-03

Re-read all three sites plus the NeurIPS 2026 Main Track Handbook on the date above. Nothing had
changed since the papers were written. Specifically confirmed:

| Requirement | Source | Our status |
|---|---|---|
| E-values: ≤4 pages excl. refs and appendices | e-values-workshop.github.io | 3.70 ✓ |
| E-values: `sglblindworkshop` option | same | ✓ |
| ATTRIB main track: 3–6 pages, refs/appendices excluded | attrib-workshop.cc | 3.31 ✓ |
| ATTRIB: `dblblindworkshop`, anonymised | same | ✓ renders "Anonymous Author(s)" |
| ATTRIB: appendix in the same PDF, no appendix limit | same | n/a — no appendix |
| EvoRobust: ≤4 content pages, refs/supp unlimited | liuj-2023.github.io | 3.55 ✓ |
| EvoRobust: anonymised, NeurIPS 2026 style, ≤50 MB | same | ✓ (0.2 MB) |
| All three: non-archival | all three CFPs | ✓ |
| Dual submission to non-archival workshops permitted | NeurIPS Main Track Handbook | ✓ journal track unaffected |
| LLM usage policy (ATTRIB defers to NeurIPS 2026) | NeurIPS Main Track Handbook | ✓ see below |
| No submission checklist required | none of the three CFPs mention one | n/a |

**LLM policy.** NeurIPS 2026 requires documenting LLM use only when it is "an important, original,
or non-standard component of the approach"; it states explicitly that "basic code assistance" and
"aid for editing purposes" **do not need to be documented**. Ours is code and drafting assistance,
so no disclosure is strictly required — all three papers disclose it anyway, which is compliant and
more transparent than the rule demands. The policy also states that agents and LLMs cannot be
authors (ours are not) and that hallucinated citations violate the Code of Conduct — every
reference in all three bibliographies has been checked against a primary source (publisher page,
PMLR, arXiv, or Project Euclid).

## Per-venue submission steps

### 1. E-Values (strongest fit — submit this one first)

- **YOU**: create/log in to an OpenReview profile. *Their site asks for profiles to exist at least
  two weeks before the deadline; a brand-new profile may be restricted. If yours is new, check this
  before the deadline, not at it.*
- Portal: <https://openreview.net/group?id=NeurIPS.cc/2026/Workshop/E-values>
- Upload `paper/workshops/e-values/main.pdf`.
- Author name **is** shown (single-blind, `sglblindworkshop`) — the PDF already carries it.
- Content is 3.7 pages against a 4-page limit; references do not count.

### 2. ATTRIB (main track — read the reviewing box above first)

- **YOU**: OpenReview profile; **YOU**: Reviewer Registration Form.
- Portal: <https://openreview.net/group?id=NeurIPS.cc/2026/Workshop/ATTRIB>
- Upload `paper/workshops/attrib/main.pdf`.
- Submit to the **main track** (3–6 pages), not the idea track. The paper now carries a full
  experiment with pre-registered controls, so the idea track undersells it.
- Anonymity: the PDF renders "Anonymous Author(s)" automatically via `dblblindworkshop`. **Check
  the uploaded PDF shows that and not your name.**
- Content is ~3 pages against a 3–6 page limit.

### 3. EvoRobust (Sep 12 — most runway, submit last)

- **YOU**: OpenReview profile.
- Portal: `openreview.net/group?id=NeurIPS.cc/2026/Workshop/EvoRobust`.
- Upload `paper/workshops/evorobust/main.pdf`.
- Anonymised; the PDF renders "Anonymous Author(s)". **Verify before upload.**
- Content is ~3.6 pages against a 4-page limit.
- Max file size 50 MB; ours is well under.

---

## Pre-upload verification (run this, do not assume)

```bash
cd ~/CascadeProjects/model-monoculture && ./scripts/check_submissions.sh
```

It re-compiles all three from source and fails loudly on: a compile error, an undefined reference,
an overfull box, a page-limit breach, or a double-blind paper that leaks the author's name. A green
run is the only evidence that the PDF on disk matches the source.

## After submitting

- ATTRIB: complete the Reviewer Registration Form the same day. Put **Sep 22** in your calendar.
- All three notify on **Sep 29**. Camera-ready: EvoRobust Oct 29; the others announce later.
- None of this affects the Computational Statistics submission; all three are non-archival and all
  three CFPs permit concurrent submission elsewhere.
