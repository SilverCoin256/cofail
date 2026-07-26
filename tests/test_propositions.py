"""Tests. The first three assert the paper's propositions numerically, so a regression in the
estimator shows up as a failing test rather than as a wrong number in a table.

Run: python -m pytest tests -q     (or: python tests/test_propositions.py)
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import cofail


def _matrix(n=250, m=400, seed=0, families=0):
    r = np.random.default_rng(seed)
    a = r.normal(0, 1.2, n)
    b = r.normal(0, 1.5, m)
    lin = a[:, None] + b[None, :]
    if families:
        fam = r.integers(0, families, n)
        lin = lin + r.normal(0, 1.6, (families, m))[fam]
    return (r.random((n, m)) < 1 / (1 + np.exp(-lin))).astype(np.uint8)


def test_prop1_mean_cofail_is_margin_only():
    """Two matrices with identical column sums must have identical mean co-failure."""
    F = _matrix(seed=1)
    rng = np.random.default_rng(0)
    X = cofail.curveball(F, rng=rng)
    assert cofail.margins_preserved(F, X)
    assert abs(cofail.mean_cofail(F) - cofail.mean_cofail(X)) < 1e-15


def test_prop1_invariance_over_many_draws():
    F = _matrix(n=150, m=300, seed=2)
    rng = np.random.default_rng(1)
    base = cofail.mean_cofail(F)
    for _ in range(10):
        X = cofail.curveball(F, rng=rng)
        assert cofail.margins_preserved(F, X)
        assert abs(cofail.mean_cofail(X) - base) < 1e-15


def test_prop2_closed_form_matches_measurement():
    """The closed form must reproduce the naive excess to machine precision."""
    for seed, n, m in [(3, 80, 250), (4, 300, 400), (5, 600, 200)]:
        F = _matrix(n=n, m=m, seed=seed)
        assert abs(cofail.naive_excess(F) - cofail.marginal_artifact(F)) < 1e-12


def test_margin_model_matches_margins():
    F = _matrix(n=120, m=200, seed=6)
    P, err = cofail.fit_margin_model(F)
    assert err < 1e-8
    assert np.allclose(P.sum(1), F.sum(1), atol=1e-7)
    assert np.allclose(P.sum(0), F.sum(0), atol=1e-7)


def test_neff_negative_control():
    """A matrix drawn FROM the margin model should not look concentrated."""
    F = _matrix(n=200, m=400, seed=7)
    r = cofail.neff(F, calibrate=True, n_null=12, rng=np.random.default_rng(0))
    assert 0.55 < r.ratio < 1.8, f"negative control ratio out of range: {r.ratio}"


def test_neff_positive_control():
    """Latent families must reduce the effective count well below the null."""
    F = _matrix(n=200, m=400, seed=8, families=6)
    r = cofail.neff(F, calibrate=True, n_null=12, rng=np.random.default_rng(0))
    assert r.ratio < 0.5, f"positive control failed to detect structure: ratio {r.ratio}"


def test_rejects_non_binary():
    try:
        cofail.mean_cofail(np.array([[0, 2], [1, 0]]))
    except ValueError:
        return
    raise AssertionError("non-binary input should raise")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    bad = 0
    for f in fns:
        try:
            f()
            print(f"  PASS {f.__name__}")
        except Exception as e:
            bad += 1
            print(f"  FAIL {f.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(fns)-bad}/{len(fns)} passed")
    sys.exit(1 if bad else 0)
