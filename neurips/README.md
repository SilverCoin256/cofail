# NeurIPS 2026 workshop submissions

Four ready-to-upload deliverables, one per subfolder. This whole tree is a **generated staging
mirror** — every file in it is produced by `scripts/stage_submissions.sh` from the real source at
`paper/workshops/<venue>/`. Never hand-edit anything under `neurips/`; edit the paper at its source,
then re-run the staging script, which refuses to stage anything until the full submission gate
(`scripts/check_submissions.sh`) passes for all four venues.

```bash
./scripts/stage_submissions.sh
```

| Venue | Folder | Deadline (IST) | Track | Blinding |
|---|---|---|---|---|
| E-Values: From Statistics to ML | [`e-values/`](e-values/) | Sat Sep 6, 17:29 | Short paper | Single-blind |
| ATTRIB 2026 | [`attrib/`](attrib/) | Sat Sep 6, 17:29 | **Main track** | Double-blind |
| Neural Network Artifacts as a New Data Modality | [`neuralartifacts/`](neuralartifacts/) | Mon Sep 7, 17:29 | **Full paper** | Double-blind (unconfirmed by venue) |
| EvoRobust 2026 | [`evorobust/`](evorobust/) | Sun Sep 13, 17:59 | Standard | Double-blind |

Every deadline above has already been extended at least once — re-verify on the portal, don't trust
this table alone. Each subfolder's `SUBMISSION.md` carries the same row plus the portal link and
upload steps specific to that venue.

## What's in each subfolder

- **`main.pdf`** — the file to upload. Nothing else is required by any of the four venues.
- **`main.tex`** + **`neurips_2026.sty`** — source, kept alongside for reference; not requested by
  any venue but harmless to have on hand.
- **`SUBMISSION.md`** — portal URL, track, blinding, deadline, and a pre-upload checklist for that
  venue specifically.

## Before uploading anything

1. **OpenReview profile.** All four venues submit through OpenReview. A profile created without an
   institutional email is moderated for up to two weeks — for the Sep 6/7 deadlines that is the
   real constraint, not the papers. Check at <https://openreview.net/>.
2. **ATTRIB only:** submitting the PDF is not enough — it uses reciprocal reviewing (register as a
   reviewer on the Reviewer Registration Form linked from its OpenReview portal; reviews due Sep 22
   AoE). Skipping this risks a desk reject independent of the paper's quality.
3. **NeuralArtifacts only:** its CFP had not published anonymity requirements as of staging. We
   built it anonymised, which is the safe default (an anonymous paper at a single-blind venue is
   fine; the reverse is a desk reject) — but re-check the portal before uploading.

Full detail, verified against each venue's live CFP, is in
[`../docs/WORKSHOP_SUBMISSION_CHECKLIST.md`](../docs/WORKSHOP_SUBMISSION_CHECKLIST.md).
