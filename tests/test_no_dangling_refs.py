"""No file in this repository may point at a repo path that does not exist.

This exists because `src/harvest_matrix.py` cited `src/audit_roworder.py` as the evidence
licensing the item-identity assumption -- the single most load-bearing assumption in the whole
substrate -- and that script was not in the repository. A reviewer following the pointer found
nothing. Two smaller instances of the same defect were found at the same time: a docstring
promising `results/tier2_validation.json`, and one promising `results/audit_roworder.json` when
the script writes a per-benchmark filename.

The failure mode is specific to this project's claims. The paper asserts that every number traces
to an executed run and that the artifacts are released; a citation to a file that was never
committed silently breaks both. Prose can be wrong in ways a compiler never catches, so this is
checked mechanically.

Paths inside URLs are ignored -- `github.com/owner/repo/blob/main/...` is not a local path -- as
are globs and angle-bracket placeholders, which are documentation patterns rather than references.
"""
import os
import re

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

TOP_LEVEL_DIRS = ("src", "cofail", "tests", "docs", "results", "figures", "paper", "substrate",
                  "configs")
SCAN_SUFFIXES = (".py", ".md", ".tex", ".yml", ".yaml")
SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules"}

URL = re.compile(r"https?://\S+")
PATH = re.compile(r"\b(?:" + "|".join(TOP_LEVEL_DIRS) + r")/[A-Za-z0-9_./-]+\.[A-Za-z]{1,5}\b")


SELF = os.path.abspath(__file__)


def iter_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith(SCAN_SUFFIXES):
                continue
            p = os.path.join(dirpath, fn)
            # This file names the very paths it exists to catch, so scanning it always fails.
            if os.path.abspath(p) == SELF:
                continue
            yield p


def referenced_paths(text):
    text = URL.sub(" ", text)          # a URL path is not a local path
    out = set()
    for m in PATH.findall(text):
        if "*" in m or "<" in m or ">" in m:
            continue
        out.add(m)
    return out


def test_no_dangling_repo_paths():
    dangling = []
    for path in iter_files():
        try:
            text = open(path, errors="ignore").read()
        except OSError:
            continue
        rel_src = os.path.relpath(path, ROOT)
        for ref in referenced_paths(text):
            if not os.path.exists(os.path.join(ROOT, ref)):
                dangling.append(f"{rel_src} -> {ref}")

    assert not dangling, (
        "these files cite repository paths that do not exist:\n  "
        + "\n  ".join(sorted(dangling))
        + "\n\nEither commit the file or fix the reference. A citation to a file that was never "
          "committed breaks the project's claim that every artifact is released."
    )


def test_scanner_actually_finds_paths():
    """Guard against the test silently passing because the regex matches nothing."""
    found = referenced_paths("see src/nullmodel.py and results/RESULTS_DIGEST.md for detail")
    assert found == {"src/nullmodel.py", "results/RESULTS_DIGEST.md"}
    assert referenced_paths("https://github.com/o/r/blob/main/src/nope.py") == set()
