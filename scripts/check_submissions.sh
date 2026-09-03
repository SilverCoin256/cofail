#!/usr/bin/env bash
# Pre-upload gate for the three NeurIPS workshop submissions.
# Recompiles each paper from source and fails on anything that risks a desk reject:
# compile errors, undefined references, overfull boxes, page-limit breaches, and
# blinding mistakes (an anonymous paper leaking the author, or a single-blind one missing them).
#
# Note: text extraction is captured into a variable and matched with grep on that variable.
# Piping pdftotext into `grep -q` looks equivalent but is not: grep -q exits at the first match
# and SIGPIPEs pdftotext, which under `set -o pipefail` reports the pipeline as failed. That made
# an earlier version of this script emit a timing-dependent false failure.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2
ROOT=$(pwd)
FAIL=0

# venue : dir : max_content_pages : blinding
VENUES=(
  "E-Values:paper/workshops/e-values:4:single"
  "ATTRIB:paper/workshops/attrib:6:double"
  "EvoRobust:paper/workshops/evorobust:4:double"
)

for spec in "${VENUES[@]}"; do
  IFS=: read -r NAME DIR MAXP BLIND <<< "$spec"
  echo "=== $NAME ($DIR) ==="
  cd "$ROOT/$DIR" || { echo "  FAIL: directory missing"; FAIL=1; continue; }

  pdflatex -interaction=nonstopmode main.tex >/tmp/chk1.log 2>&1
  pdflatex -interaction=nonstopmode main.tex >/tmp/chk.log  2>&1
  LOG=$(cat /tmp/chk.log)

  if grep -q '^!' <<< "$LOG"; then
    echo "  FAIL: LaTeX error"; grep '^!' <<< "$LOG" | head -3; FAIL=1
  else echo "  ok: compiles clean"; fi

  if grep -qi 'undefined' <<< "$LOG"; then
    echo "  FAIL: undefined reference or citation"; FAIL=1
  else echo "  ok: no undefined references"; fi

  if grep -q 'Overfull' <<< "$LOG"; then
    echo "  FAIL: overfull box (text outside the margin)"; FAIL=1
  else echo "  ok: no overfull boxes"; fi

  CONTENT=$(python3 - "$MAXP" <<'PY'
import subprocess, sys
maxp = float(sys.argv[1])
t = subprocess.run(['pdftotext','-layout','main.pdf','-'],capture_output=True,text=True).stdout
pages = t.split('\f')
for i,p in enumerate(pages):
    if 'References' in p:
        L = p.split('\n'); n = [k for k,l in enumerate(L) if 'References' in l][0]
        c = i + n/max(len(L),1)
        print(f"{c:.2f}"); sys.exit(0 if c <= maxp else 7)
print(f"{len(pages):.2f}"); sys.exit(7)
PY
)
  PAGE_RC=$?
  if [ "$PAGE_RC" -eq 0 ]; then echo "  ok: $CONTENT content pages (limit $MAXP)"
  else echo "  FAIL: $CONTENT content pages exceeds limit $MAXP"; FAIL=1; fi

  TXT=$(pdftotext main.pdf - 2>/dev/null)
  if [ "$BLIND" = "double" ]; then
    if grep -qiE 'Shaurya|Gupta|shauryaguptaa8|SilverCoin256' <<< "$TXT"; then
      echo "  FAIL: double-blind paper leaks author identity"; FAIL=1
    elif grep -q 'Anonymous Author' <<< "$TXT"; then
      echo "  ok: anonymised"
    else
      echo "  FAIL: no 'Anonymous Author(s)' block found"; FAIL=1
    fi
  else
    if grep -q 'Shaurya Gupta' <<< "$TXT"; then
      echo "  ok: single-blind, author shown"
    else
      echo "  FAIL: single-blind paper is missing the author block"; FAIL=1
    fi
  fi
  cd "$ROOT" || exit 2
done

echo
if [ "$FAIL" -eq 0 ]; then
  echo "ALL CHECKS PASSED — PDFs are safe to upload."
  echo "REMINDER: ATTRIB additionally requires the Reviewer Registration Form"
  echo "          (up to 2 papers, reviews due Sep 22 AoE). A submission without a"
  echo "          registered reciprocal reviewer may be desk rejected."
else
  echo "CHECKS FAILED — do not upload until the failures above are fixed."
fi
exit $FAIL
