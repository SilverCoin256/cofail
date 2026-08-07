# Deposit instructions — reduced to the minimum that requires your credentials

Both remaining items (Zenodo DOI, OSF pre-registration timestamp) are blocked on account creation,
which is not something this assistant can or should do on your behalf. Everything that could be
prepared without an account has been. What's below should take under ten minutes total.

## Zenodo — GitHub auto-archival, no manual upload

`.zenodo.json` is committed at the repo root with the title, description, license note, and
keywords already written. Zenodo reads this automatically when it archives a GitHub release, so
there is no metadata form to fill in and no zip file to build or upload by hand.

1. Go to **zenodo.org**, sign in with **"Log in with GitHub"** (uses your existing GitHub account
   — no new password to create).
2. Under your account → **GitHub**, find `SilverCoin256/cofail` in the repository list and flip
   its toggle **on**.
3. Back in GitHub, cut a release: `gh release create v1.0.0 --title "v1.0.0" --notes "First
   archived release: paper, substrate, code, pre-registration."` (or use the GitHub web UI —
   Releases → Draft a new release). **This is a public, visible action — confirm you want to do
   it before running the command; I have not run it.**
4. Zenodo detects the release, archives the repo automatically, mints a DOI, and reads
   `.zenodo.json` for the deposit metadata. Takes a minute or two.
5. Add the resulting DOI badge to `README.md` (a one-line edit I can make once you have the DOI).

**Known limitation, already documented in `docs/DATASHEET.md`:** this archives the whole repo,
including `substrate/`. The datasheet already states that ARC-Challenge is CC-BY-SA-4.0
(share-alike) and that `substrate/raw/arc_resp.npz` (the reconstructed answer key) should not be
publicly redistributed. **Before cutting the release, either confirm you're comfortable archiving
`substrate/` as-is under the documented license caveats, or tell me and I'll add a
`.gitattributes`/export-ignore rule to exclude `arc_resp.npz` from the archived snapshot** — the
recovery code stays, only the reconstructed key is dropped.

## OSF — pre-registration timestamp

The pre-registration content already exists in full at `PREREGISTRATION.md` (hypotheses, kill
conditions, two dated amendments). OSF's job here is just to put an independently-verifiable
timestamp on it — the content itself needs no further preparation.

1. Go to **osf.io**, create an account (email or your existing GitHub/ORCID/Google login).
2. New project → **Registrations** → choose a basic template (OSF's generic "Open-Ended
   Registration" template is the right fit; no need for a domain-specific one).
3. **Title:** `Excess co-failure and effective model count in the open-model ecosystem`
4. **Description** (paste as-is):
   > Pre-registered hypotheses, kill conditions, and analysis plan for a study of correlated
   > failure between open language models at the exact conditional null implied by Rasch
   > sufficiency. Registered before confirmatory analysis; two dated amendments were made before
   > any confirmatory statistic was computed. Full content, code, and results at
   > https://github.com/SilverCoin256/cofail.
5. Upload `PREREGISTRATION.md` as the registration's file (or paste its sections into the
   template's matching fields, if you prefer the structured form over a file upload).
6. Submit for registration. OSF timestamps it immediately; no review wait for a basic
   registration.
7. Add the resulting OSF link to `README.md` and `paper/main.tex`'s reproducibility section (a
   one-line edit I can make once you have it) — this is what upgrades "self-hosted git
   timestamps, author-controlled" (a reviewer objection recorded in `docs/NEURIPS_BLUEPRINT.md`)
   to an independently verifiable date.

## What's already done, so neither step involves original work

- Zenodo metadata: written (`.zenodo.json`).
- OSF title/description: written above.
- Pre-registration content: already complete and dated (`PREREGISTRATION.md`).
- Datasheet, Croissant metadata, verified license chain: already complete
  (`docs/DATASHEET.md`, `docs/croissant.json`).

Neither step requires deciding anything or writing anything new — just logging in and clicking
through what's already prepared.
