"""Check the RENDERED papers, not just their sources.

This file exists because a source-level fix and a source-level guard both passed while the
compiled paper was still wrong. The population range was corrected from "1,228-1,373" to
"1,228-1,362" everywhere it appeared as `$1{,}373$`, and a test was added asserting the string
`1{,}373` was gone -- but a section heading wrote the number in plain text, outside math mode.
The source test passed; workshop.pdf still said 1,373. It was caught by running pdftotext over
the built PDF.

The lesson generalises: a claim is wrong if it is wrong *in the artifact a reviewer reads*, and
LaTeX gives a number several spellings that a naive source grep will not unify. These tests scan
rendered text, which has exactly one spelling.

Skips cleanly when the PDFs have not been built or pdftotext is unavailable, so it never blocks a
source-only checkout.
"""
import os
import re
import shutil
import subprocess

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")

PDFS = {
    "main.pdf": os.path.join(ROOT, "paper", "main.pdf"),
    "workshop.pdf": os.path.join(ROOT, "paper", "workshop.pdf"),
    "brief.pdf": os.path.join(ROOT, "docs", "brief", "brief.pdf"),
}

# Values that were once in these papers and are now known wrong. Each entry is a list of
# regexes covering the spellings LaTeX can render the same claim as.
RETIRED = {
    "population range 1,228-1,373 (max N is 1,362)": [r"1,373", r"1 373"],
    "excess range 2.9-11.9x (artifact says 2.848 / 11.842)": [r"2\.9\s*[–-]\s*11\.9"],
    "dedup discard 36-64% (GSM8K drops 20.8%)": [r"36\s*[–-]\s*64\s*%"],
    "item-margin gap 'within 6%' (HellaSwag is 8.3%)": [r"within\s*6\s*%"],
    "ARC null spectral edge 28.7 (artifact says 27.9)": [r"\b28\.7\b"],
    "HellaSwag mean accuracy 0.613 (post-filter; table is pre-filter)": [r"\b0\.613\b"],
}


def rendered(path):
    if not os.path.exists(path):
        pytest.skip(f"{os.path.basename(path)} not built")
    if not shutil.which("pdftotext"):
        pytest.skip("pdftotext not available")
    out = subprocess.run(["pdftotext", path, "-"], capture_output=True, text=True)
    if out.returncode != 0:
        pytest.skip(f"pdftotext failed on {os.path.basename(path)}")
    return re.sub(r"\s+", " ", out.stdout)


@pytest.mark.parametrize("name", sorted(PDFS))
def test_no_retired_value_survives_in_the_rendered_pdf(name):
    text = rendered(PDFS[name])
    found = [
        f"{claim} [/{pat}/]"
        for claim, pats in RETIRED.items()
        for pat in pats
        if re.search(pat, text)
    ]
    assert not found, (
        f"{name} still renders a retired value: {found}. Fix the source and REBUILD the PDF -- "
        "a source-only fix does not change what a reviewer reads."
    )
