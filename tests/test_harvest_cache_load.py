"""Guard the npz cache-load path against quadratic re-decompression.

This is the bug that killed Layer C for three days and produced four failed workflow runs, plus
three local failures I initially misdiagnosed as a sandbox resource policy.

`numpy.load` on a .npz returns a lazy `NpzFile`. Every `z["key"]` access decompresses that entire
array from scratch and caches nothing. The original resume loop was:

    for k, m in enumerate(ms):
        P[m] = z["prim"][k]
        if "sec" in z.files and z["sec"].size:   # decompresses sec ...
            S[m] = z["sec"][k]                   # ... and again
        D[m] = str(z["dates"][k])

so reading an n-row cache cost ~4n full decompressions of n-row arrays: quadratic in the model
count. Measured on the real ARC cache at 2,162 models, that was ~49 GB of transient allocation to
read a 965 KB file, taking 68 s; the OOM killer took the process (exit 137) before it printed its
first progress line. HellaSwag, 8x wider, would have churned ~168 GB.

The sting is that it was survivable at the original 1,362 models and only began failing after
Layer C's own harvesting grew the file past ~2,000 -- the system broke itself by working.

This test counts decompressions rather than timing anything, so it is precise and not flaky.
"""
import os
import sys

import pytest

np = pytest.importorskip("numpy")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))


def _write_cache(path, n_models=200, n_items=50):
    rng = np.random.default_rng(0)
    np.savez_compressed(
        path,
        models=np.array([f"org/model-{i}" for i in range(n_models)], object),
        prim=rng.integers(0, 2, size=(n_models, n_items), dtype=np.uint8),
        sec=rng.random((n_models, n_items), dtype=np.float32),
        dates=np.array([f"2024-01-{(i % 28) + 1:02d}" for i in range(n_models)], object),
    )


def test_resume_load_decompresses_each_array_once(tmp_path, monkeypatch):
    """The whole point: reading the cache must not scale with the number of models."""
    cache = tmp_path / "bench.npz"
    _write_cache(str(cache), n_models=200)

    counts = {}
    original = np.lib.npyio.NpzFile.__getitem__

    def counting_getitem(self, key):
        counts[key] = counts.get(key, 0) + 1
        return original(self, key)

    monkeypatch.setattr(np.lib.npyio.NpzFile, "__getitem__", counting_getitem)

    # the load path, mirroring src/harvest_matrix.py::harvest
    z = np.load(str(cache), allow_pickle=True)
    ms = list(z["models"])
    prim_all = z["prim"]
    dates_all = z["dates"]
    sec_all = z["sec"] if ("sec" in z.files and z["sec"].size) else None
    P, S, D = {}, {}, {}
    for k, m in enumerate(ms):
        P[m] = prim_all[k]
        if sec_all is not None:
            S[m] = sec_all[k]
        D[m] = str(dates_all[k])

    assert len(P) == 200
    for key in ("models", "prim", "dates"):
        assert counts.get(key, 0) <= 1, (
            f"{key!r} was decompressed {counts.get(key)} times; it must be hoisted out of the "
            "per-model loop or the load cost becomes quadratic in the model count"
        )
    # `sec` is read once for the emptiness check and once for the value, sharing one decompression
    assert counts.get("sec", 0) <= 2, (
        f"'sec' was decompressed {counts.get('sec')} times; hoist it out of the loop"
    )


def test_real_harvest_module_load_path_is_hoisted():
    """Assert the shipped source does not index the NpzFile inside its resume loop."""
    src = open(os.path.join(HERE, "..", "src", "harvest_matrix.py")).read()
    start = src.index("def harvest(")
    body = src[start:src.index("\ndef ", start + 1)]
    loop = body[body.index("for k, m in enumerate(ms):"):]
    loop = loop[:loop.index("have = set(ms)")]
    for bad in ('z["prim"]', 'z["sec"]', 'z["dates"]', "z.files"):
        assert bad not in loop, (
            f"{bad} appears inside the resume loop in harvest(); each access re-decompresses the "
            "whole array. Hoist it above the loop."
        )
