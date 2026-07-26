"""Core estimators. Pure NumPy.

Conventions: `F` is a binary (n_models, n_items) matrix with 1 = model failed item.
"""
from dataclasses import dataclass, asdict
from typing import Optional

import numpy as np

__all__ = ["curveball", "margins_preserved", "mean_cofail", "naive_excess",
           "marginal_artifact", "fit_margin_model", "excess_matrix", "neff", "NeffResult"]


def _as_binary(F):
    F = np.asarray(F)
    if F.ndim != 2:
        raise ValueError(f"F must be 2-D, got shape {F.shape}")
    u = np.unique(F)
    if not np.all(np.isin(u, (0, 1))):
        raise ValueError(f"F must contain only 0/1; found {u[:6]}")
    return F.astype(np.uint8)


# --------------------------------------------------------------------- randomization

def curveball(F, n_trades=None, rng=None):
    """Sample the fixed-fixed null: uniform over matrices with the same row AND column sums.

    Implements the curveball trade of Strona et al. (2014). Both margins are preserved exactly
    by construction, not approximately.
    """
    F = _as_binary(F)
    rng = np.random.default_rng() if rng is None else rng
    n, _ = F.shape
    n_trades = 50 * n if n_trades is None else int(n_trades)
    X = F.astype(bool, copy=True)
    ii = rng.integers(0, n, size=n_trades)
    jj = rng.integers(0, n, size=n_trades)
    for k in range(n_trades):
        i, j = ii[k], jj[k]
        if i == j:
            continue
        xi, xj = X[i], X[j]
        diff = np.flatnonzero(xi ^ xj)
        d = diff.size
        if d < 2:
            continue
        na = int(xi[diff].sum())
        if na == 0 or na == d:
            continue
        rng.shuffle(diff)
        xi[diff] = False
        xj[diff] = False
        xi[diff[:na]] = True
        xj[diff[na:]] = True
    return X.astype(np.uint8)


def margins_preserved(A, B):
    A, B = _as_binary(A), _as_binary(B)
    return bool((A.sum(1) == B.sum(1)).all() and (A.sum(0) == B.sum(0)).all())


# --------------------------------------------------------------------- degeneracy results

def mean_cofail(F):
    """Mean pairwise co-failure over ordered pairs. Depends ONLY on the item margins."""
    F = _as_binary(F)
    n, m = F.shape
    c = F.sum(0, dtype=np.float64)
    return float((c * c - c).sum() / (m * n * (n - 1)))


def naive_excess(F):
    """Observed mean co-failure minus an independence baseline -- the quantity commonly
    reported as evidence of correlated failure."""
    F = _as_binary(F)
    n, m = F.shape
    c = F.sum(0, dtype=np.float64)
    p = F.sum(1, dtype=np.float64) / m
    O = (c * c - c).sum() / (m * n * (n - 1))
    I = (p.sum() ** 2 - (p * p).sum()) / (n * (n - 1))
    return float(O - I)


def marginal_artifact(F):
    """Closed form for `naive_excess`, computed from the margins alone:

        [ n * Var_m(f_m) + Var_i(p_i) - fbar (1 - fbar) ] / (n - 1)

    Equals `naive_excess(F)` to machine precision. The gap between them is zero, which is the
    point: the reported excess carries no information beyond the margins.
    """
    F = _as_binary(F)
    n, m = F.shape
    f = F.sum(0, dtype=np.float64) / n
    p = F.sum(1, dtype=np.float64) / m
    fb = f.mean()
    return float((n * f.var() + p.var() - fb * (1 - fb)) / (n - 1))


# --------------------------------------------------------------------- conditioning

def fit_margin_model(F, iters=300, tol=1e-11):
    """Maximum-entropy (Rasch) margin model P[i,m] = sigmoid(alpha_i + beta_m).

    The unique product-Bernoulli law whose expected margins equal the observed ones; the mean
    field of the fixed-fixed null. Returns (P, max_abs_margin_error).
    """
    F = _as_binary(F).astype(np.float64)
    n, m = F.shape
    r, c = F.sum(1), F.sum(0)
    eps = 1e-9
    a = np.log(np.clip(r, eps, m - eps) / np.clip(m - r, eps, None))
    b = np.zeros(m)
    for _ in range(iters):
        P = 1.0 / (1.0 + np.exp(-(a[:, None] + b[None, :])))
        gr = P.sum(1) - r
        a -= gr / np.clip((P * (1 - P)).sum(1), 1e-12, None)
        P = 1.0 / (1.0 + np.exp(-(a[:, None] + b[None, :])))
        gc = P.sum(0) - c
        b -= gc / np.clip((P * (1 - P)).sum(0), 1e-12, None)
        if max(np.abs(gr).max(), np.abs(gc).max()) < tol:
            break
    P = 1.0 / (1.0 + np.exp(-(a[:, None] + b[None, :])))
    err = max(np.abs(P.sum(1) - r).max(), np.abs(P.sum(0) - c).max())
    return P, float(err)


def excess_matrix(F, P=None, block=1024):
    """Margin-conditioned excess co-failure, (F F^T - P P^T) / n_items."""
    F = _as_binary(F)
    if P is None:
        P, _ = fit_margin_model(F)
    n, m = F.shape
    X = np.ascontiguousarray(F, dtype=np.float32)
    Q = np.ascontiguousarray(P, dtype=np.float32)
    D = np.empty((n, n), dtype=np.float32)
    for s in range(0, n, block):
        e = min(s + block, n)
        D[s:e] = (X[s:e] @ X.T - Q[s:e] @ Q.T) / m
    return D


def _participation(D, mode="clip"):
    d = np.sqrt(np.clip(np.diag(D).astype(np.float64), 1e-12, None))
    R = D.astype(np.float64) / d[:, None] / d[None, :]
    w = np.linalg.eigvalsh(R)[::-1]
    if mode == "clip":
        v = np.clip(w, 0, None)
    elif mode == "abs":
        v = np.abs(w)
    else:
        v = w
    return float(v.sum() ** 2 / (v * v).sum()), w


@dataclass
class NeffResult:
    n_models: int
    neff: float
    neff_abs: float
    neff_raw: float
    null_mean: Optional[float] = None
    null_sd: Optional[float] = None
    ses: Optional[float] = None
    ratio: Optional[float] = None
    n_null: int = 0
    margin_error: float = 0.0

    def as_dict(self):
        return asdict(self)

    def __str__(self):
        s = (f"N={self.n_models}  N_eff={self.neff:.1f} "
             f"(abs {self.neff_abs:.1f}, raw {self.neff_raw:.1f})")
        if self.null_mean is not None:
            s += (f"\nnull={self.null_mean:.1f}+-{self.null_sd:.1f} over {self.n_null} draws"
                  f"  SES={self.ses:+.1f}  ratio={self.ratio:.3f}")
        return s


def neff(F, calibrate=True, n_null=40, burn_per_model=50, rng=None, progress=False):
    """Effective number of independent models.

    Participation ratio of the eigenspectrum of the margin-conditioned excess matrix. With
    `calibrate=True` it is compared against curveball replicates that share F's margins exactly
    -- which is essential: the null value is NOT the nominal model count, and an uncalibrated
    figure is not interpretable.
    """
    F = _as_binary(F)
    rng = np.random.default_rng() if rng is None else rng
    P, err = fit_margin_model(F)
    obs, _ = _participation(excess_matrix(F, P))
    obs_abs, _ = _participation(excess_matrix(F, P), "abs")
    obs_raw, _ = _participation(excess_matrix(F, P), "raw")
    res = NeffResult(n_models=int(F.shape[0]), neff=obs, neff_abs=obs_abs,
                     neff_raw=obs_raw, margin_error=err)
    if not calibrate:
        return res
    n = F.shape[0]
    draws = []
    for k in range(n_null):
        X = curveball(F, burn_per_model * n, rng)
        draws.append(_participation(excess_matrix(X, P))[0])
        if progress:
            print(f"  null draw {k+1}/{n_null}", flush=True)
    draws = np.asarray(draws)
    sd = draws.std(ddof=1)
    res.null_mean = float(draws.mean())
    res.null_sd = float(sd)
    res.ses = float((obs - draws.mean()) / sd) if sd > 0 else float("nan")
    res.ratio = float(obs / draws.mean())
    res.n_null = int(n_null)
    return res
