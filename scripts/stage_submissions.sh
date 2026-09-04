#!/usr/bin/env bash
# Populate ~/Downloads/neurips/<venue>/ with the exact, gate-verified materials to upload.
#
# paper/workshops/<venue>/ (inside this repo) is the source of truth: edited, compiled, tested
# there, and pushed to GitHub. The staged copy is deliberately OUTSIDE the repo, in the user's
# own Downloads folder — nothing under the destination is version-controlled or pushed anywhere.
# This script is the only thing that should write to it.
# It refuses to stage anything until scripts/check_submissions.sh passes on every venue, so the
# staged folder can never hold a PDF that failed a formatting or blinding check.
#
# Destination is $NEURIPS_STAGE_DIR if set, else ~/Downloads/neurips.
#
# Run this after any edit to a paper, and always right before uploading:
#   ./scripts/stage_submissions.sh
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2
ROOT=$(pwd)
STAGE_DIR="${NEURIPS_STAGE_DIR:-$HOME/Downloads/neurips}"

echo "Running the submission gate first — staging is refused if it fails."
echo
if ! "$ROOT/scripts/check_submissions.sh"; then
  echo
  echo "GATE FAILED — nothing staged. Fix the failures above and re-run."
  exit 1
fi
echo
echo "Gate passed. Staging to $STAGE_DIR ..."
echo

# venue : dir : display name : portal : deadline (IST) : track : blinding
VENUES=(
"e-values|paper/workshops/e-values|E-Values: From Statistics to ML|https://openreview.net/group?id=NeurIPS.cc/2026/Workshop/E-values|Sat Sep 6, 17:29 IST (Sep 5 23:59 AoE)|Short paper|Single-blind — name shown (sglblindworkshop)"
"attrib|paper/workshops/attrib|3rd Workshop on Attributing Model Behavior at Scale (ATTRIB 2026)|https://openreview.net/group?id=NeurIPS.cc/2026/Workshop/ATTRIB|Sat Sep 6, 17:29 IST (Sep 5 23:59 AoE)|Main track (NOT idea track)|Double-blind — anonymised (dblblindworkshop)"
"evorobust|paper/workshops/evorobust|Self-Evolving Diversity-Driven Search for Robust AI Systems (EvoRobust 2026)|https://openreview.net/group?id=NeurIPS.cc/2026/Workshop/EvoRobust|Sun Sep 13, 17:59 IST (Sep 12 23:59 AoE)|Standard|Double-blind — anonymised (dblblindworkshop)"
"neuralartifacts|paper/workshops/neuralartifacts|Neural Network Artifacts as a New Data Modality|https://openreview.net/group?id=NeurIPS.cc/2026/Workshop/NeuralArtifacts|Mon Sep 7, 17:29 IST (Sep 7 11:59 UTC — their site also shows Sep 9 AoE; target the earlier)|Full paper (NOT extended abstract)|Double-blind — anonymised (blinding not yet confirmed by the venue; re-check before upload)"
)

for spec in "${VENUES[@]}"; do
  IFS='|' read -r SLUG SRC NAME PORTAL DEADLINE TRACK BLIND <<< "$spec"
  DST="$STAGE_DIR/$SLUG"
  mkdir -p "$DST"
  cp "$ROOT/$SRC/main.pdf" "$DST/main.pdf"
  cp "$ROOT/$SRC/main.tex" "$DST/main.tex"
  cp "$ROOT/$SRC/neurips_2026.sty" "$DST/neurips_2026.sty"

  PAGES=$(python3 - "$DST/main.pdf" <<'PY'
import subprocess, sys
t = subprocess.run(['pdftotext','-layout',sys.argv[1],'-'],capture_output=True,text=True).stdout
for i,p in enumerate(t.split('\f')):
    if 'References' in p:
        L = p.split('\n'); n = next(k for k,l in enumerate(L) if 'References' in l)
        print(f"{i + n/max(len(L),1):.2f}"); break
PY
)

  cat > "$DST/SUBMISSION.md" <<EOF
# $NAME

Staged $(date "+%Y-%m-%d %H:%M %Z") by \`scripts/stage_submissions.sh\` from the
\`model-monoculture\` repo (\`$SRC/\`). This folder lives in Downloads and is not part of that repo
or git-tracked — edit the paper at its source, never here, then re-run the staging script to
refresh this copy.

| | |
|---|---|
| **Upload** | \`main.pdf\` (only the PDF is required by this venue) |
| **Portal** | $PORTAL |
| **Track** | $TRACK |
| **Blinding** | $BLIND |
| **Deadline** | $DEADLINE — **re-verify on the portal**; every one of these four has been extended at least once already |
| **Content pages at last stage** | $PAGES |

## Before you upload

1. **OpenReview profile.** Non-institutional (gmail) profiles are moderated for up to two weeks.
   If you don't already have an active profile, this is the actual bottleneck, not the paper.
2. Open \`main.pdf\` in this folder and confirm it shows what the Blinding row above says it
   should (author name for single-blind, "Anonymous Author(s)" for double-blind).
3. Full details, per-venue reminders, and the ATTRIB reciprocal-reviewing obligation:
   see \`docs/WORKSHOP_SUBMISSION_CHECKLIST.md\` in the \`model-monoculture\` repo
   (\`$ROOT/docs/WORKSHOP_SUBMISSION_CHECKLIST.md\` on this machine).

## After you upload

Note the submission ID/URL somewhere durable — this repo does not track it automatically.
EOF

  echo "  staged $STAGE_DIR/$SLUG/  ($PAGES content pages)"
done

cat > "$STAGE_DIR/README.md" <<EOF
# NeurIPS 2026 workshop submissions

Four ready-to-upload deliverables, one per subfolder. Regenerated $(date "+%Y-%m-%d %H:%M %Z") by
\`scripts/stage_submissions.sh\` in the \`model-monoculture\` repo — this whole folder is a mirror,
not the source; edit the papers in the repo, then re-run that script to refresh this copy. Nothing
here is version-controlled or pushed anywhere.

| Venue | Folder | Deadline (IST) | Track | Blinding |
|---|---|---|---|---|
EOF
for spec in "${VENUES[@]}"; do
  IFS='|' read -r SLUG SRC NAME PORTAL DEADLINE TRACK BLIND <<< "$spec"
  echo "| $NAME | [\`$SLUG/\`]($SLUG/) | $DEADLINE | $TRACK | $BLIND |" >> "$STAGE_DIR/README.md"
done
cat >> "$STAGE_DIR/README.md" <<EOF

Every deadline above has already been extended at least once — re-verify on the portal, don't trust
this table alone. Each subfolder's \`SUBMISSION.md\` carries the same row plus the portal link and
upload steps specific to that venue.

## Before uploading anything

1. **OpenReview profile.** All four venues submit through OpenReview. A profile created without an
   institutional email is moderated for up to two weeks — check at <https://openreview.net/>.
2. **ATTRIB only:** submitting the PDF is not enough — it uses reciprocal reviewing (register on
   the Reviewer Registration Form linked from its OpenReview portal; reviews due Sep 22 AoE).
3. **NeuralArtifacts only:** its CFP had not published anonymity requirements as of staging; we
   built it anonymised (the safe default) but re-check the portal before uploading.

Full detail, verified against each venue's live CFP:
\`$ROOT/docs/WORKSHOP_SUBMISSION_CHECKLIST.md\` in the repo.
EOF

echo
echo "Done. $STAGE_DIR/<venue>/main.pdf is what to upload; SUBMISSION.md alongside it has the"
echo "portal link, track, blinding and deadline for that venue."
echo "Nothing under $STAGE_DIR is part of this repo or git-tracked."
