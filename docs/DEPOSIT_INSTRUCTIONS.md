# Deposits — DONE (2026-08-09)

Both deposits are live. This file previously held step-by-step instructions for completing them;
that is now history, kept below only as a record of what was decided and why.

| deposit | identifier | status |
|---|---|---|
| Zenodo (concept, all versions) | [10.5281/zenodo.21860005](https://doi.org/10.5281/zenodo.21860005) | live |
| Zenodo (this paper's snapshot) | 10.5281/zenodo.21860006 (`v1.0.0`) | live, 18.1 MB |
| OSF pre-registration | [osf.io/cmh7q](https://osf.io/cmh7q) | live, public |
| OSF project (wiki holds the full pre-registration) | [osf.io/sknu9](https://osf.io/sknu9) | live |

Both are cited in `README.md` (badges) and in the reproducibility sections of `paper/main.tex`
and `paper/workshop.tex`.

## Decisions made at deposit time, recorded because they are not reversible

**OSF: Open-Ended Registration, not the OSF Preregistration template.** The deposit is dated
2026-08-09, after the confirmatory analyses. Filing it under the prospective-preregistration
template would have implied a pre-commitment date the deposit cannot establish. The registration's
description and narrative summary both state explicitly that the ordering of the original plan and
Amendments 1–2 (2026-07-26) is evidenced by the dated commit history of `PREREGISTRATION.md`, not
by the deposit date, and that Amendment 3 (2026-07-28) is post-hoc and earns no pre-registration
credit. This is weaker than a genuine prospective registration would have been, and saying so is
the point: a reviewer who checks the dates finds the paper already conceded them.

**OSF: public, not embargoed.** OSF offers embargo for authors submitting to venues requiring
blind review. It would have bought nothing here — the repository and the Zenodo record are already
public under the author's name, and the paper itself cites both — while defeating the independent
verifiability the deposit exists to provide.

**Zenodo: `.gitattributes` `export-ignore` verified to hold.** `substrate/raw/arc_resp.npz`, the
reconstructed ARC answer key, is confirmed absent from the published archive. The
`substrate/raw/arc_resp_sample.json` that *is* included was checked and contains only the 600
model identifiers of the response subsample — no gold labels.

## Errors caught in the deposit process, kept as a warning

Three things were wrong at the moment of deposit and would have been permanent had they not been
checked first. A DOI record and an OSF registration cannot be edited afterwards.

1. **The Zenodo description and the draft release notes both still carried the retired
   "1,228–1,373" model count.** That figure traces to no artifact (see
   `results/RESULTS_DIGEST.md`); the true post-filter range is 1,228–1,362. Corrected in
   `.zenodo.json` and in the release body before publishing.
2. **The release tag had to be checked against `main`.** The draft was staged a day earlier. Had
   its target resolved to that older commit, Zenodo would have permanently archived the version of
   the papers still containing all eight defects fixed on 2026-08-08–09. `target_commitish` was
   confirmed to be `main` before publishing.
3. **The OSF wiki editor silently corrupted the pasted content twice** — auto-close-brackets
   appended a stray `)))))])`, and 4-space-indented formula lines opened a markdown code block
   that swallowed the second half of the document into raw monospace. Both were caught by reading
   the rendered page rather than trusting the editor, and fixed by moving formulas to inline code.

The general lesson, which is the same one `tests/test_rendered_pdfs.py` encodes for the papers:
check the artifact a reader will actually see, not the source you submitted.

## Still outstanding (not a deposit)

The Hugging Face v2 leaderboard replication remains blocked on an account token. It is a bonus
robustness check, explicitly out of scope for the paper's argument — see
`docs/NEURIPS_BLUEPRINT.md`, "X7 correction" and the 2026-08-08 parser audit. The harvester is
ready and its parser has been corrected and unit-tested against the harness's real record schema,
so the harvest can start the moment a token is available.
