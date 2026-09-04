#!/usr/bin/env bash
# Populate neurips/<venue>/ with the exact, gate-verified materials to upload.
#
# paper/workshops/<venue>/ is the source of truth (edited, compiled, tested there).
# neurips/<venue>/ is a staging mirror: this script is the ONLY thing that should write to it.
# It refuses to stage anything until scripts/check_submissions.sh passes on every venue, so
# neurips/ can never hold a PDF that failed a formatting or blinding check.
#
# Run this after any edit to a paper, and always right before uploading:
#   ./scripts/stage_submissions.sh
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2
ROOT=$(pwd)

echo "Running the submission gate first — staging is refused if it fails."
echo
if ! "$ROOT/scripts/check_submissions.sh"; then
  echo
  echo "GATE FAILED — nothing staged. Fix the failures above and re-run."
  exit 1
fi
echo
echo "Gate passed. Staging neurips/<venue>/ ..."
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
  DST="$ROOT/neurips/$SLUG"
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

Staged $(date "+%Y-%m-%d %H:%M %Z") by \`scripts/stage_submissions.sh\` from \`$SRC/\`.
This file and the two beside it (\`main.pdf\`, \`main.tex\`, \`neurips_2026.sty\`) are a mirror —
edit the paper in \`$SRC/\`, never here, then re-run the staging script.

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
   see \`../../docs/WORKSHOP_SUBMISSION_CHECKLIST.md\`.

## After you upload

Note the submission ID/URL somewhere durable — this repo does not track it automatically.
EOF

  echo "  staged neurips/$SLUG/  ($PAGES content pages)"
done

echo
echo "Done. neurips/<venue>/main.pdf is what to upload; neurips/<venue>/SUBMISSION.md has the portal"
echo "link, track, blinding and deadline for that venue."
