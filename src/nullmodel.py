"""Margin-preserving (fixed-fixed) randomization null and the statistics computed on it.

Why a fixed-fixed null at all: see PREREGISTRATION.md AMENDMENT 1. Proposition 1 shows
the MEAN pairwise co-failure is a function of the item margins alone, so it is invariant
under any column-margin-preserving randomization. Correlated-failure structure is therefore
only identifiable at second order, which is what `var_cofail` and the eigenspectrum measure.

Curveball (Strona et al. 2014) is used rather than sequential 2x2 swaps because it mixes in
far fewer proposals per unit of structure destroyed.
"""
import numpy as np


# ---------------------------------------------------------------- randomization

def curveball(F, n_trades, rng, callback=None, cb_every=0):
    """Curveball / trade randomization. Returns a NEW matrix; both margins exactly preserved.

    F : (N, M) uint8/bool matrix.  n_trades : number of row-pair trades to attempt.
    callback(k, X) is invoked every `cb_every` trades for convergence tracing.
    """
    X = np.array(F, dtype=bool, copy=True)
    N = X.shape[0]
    ii = rng.integers(0, N, size=n_trades)
    jj = rng.integers(0, N, size=n_trades)
    for k in range(n_trades):
        i, j = ii[k], jj[k]
        if i == j:
            continue
        xi, xj = X[i], X[j]
        diff = np.flatnonzero(xi ^ xj)          # positions held by exactly one of the two
        d = diff.size
        if d < 2:
            continue
        na = int(xi[diff].sum())                # row i keeps its own count -> row sums fixed
        if na == 0 or na == d:
            continue
        rng.shuffle(diff)                       # column sums fixed: each unit merely changes owner
        xi[diff] = False
        xj[diff] = False
        xi[diff[:na]] = True
        xj[diff[na:]] = True
        if cb_every and callback is not None and (k + 1) % cb_every == 0:
            callback(k + 1, X)
    return X.astype(np.uint8)


def margins_ok(A, B):
    return bool((A.sum(1) == B.sum(1)).all() and (A.sum(0) == B.sum(0)).all())


# ---------------------------------------------------------------- statistics

def mean_cofail(F):
    """Exact mean pairwise co-failure over ordered pairs (Proposition 1: margins only)."""
    N, M = F.shape
    c = F.sum(0, dtype=np.float64)
    return float((c * c - c).sum() / (M * N * (N - 1)))


def naive_excess_closed_form(F):
    """Proposition 2 closed form: [N*Var_m(f) + Var_i(p) - fbar(1-fbar)] / (N-1)."""
    N, M = F.shape
    f = F.sum(0, dtype=np.float64) / N
    p = F.sum(1, dtype=np.float64) / M
    fb = f.mean()
    return float((N * f.var() + p.var() - fb * (1 - fb)) / (N - 1))


def naive_excess_empirical(F):
    """Directly computed observed-minus-independence excess (used to verify kill condition K6)."""
    N, M = F.shape
    c = F.sum(0, dtype=np.float64)
    p = F.sum(1, dtype=np.float64) / M
    O = (c * c - c).sum() / (M * N * (N - 1))
    I = (p.sum() ** 2 - (p * p).sum()) / (N * (N - 1))
    return float(O - I)


def gram(F, block=1024):
    """Model x model co-failure count matrix F @ F.T, blocked to bound peak memory."""
    X = np.ascontiguousarray(F, dtype=np.float32)
    N = X.shape[0]
    G = np.empty((N, N), dtype=np.float32)
    for s in range(0, N, block):
        e = min(s + block, N)
        G[s:e] = X[s:e] @ X.T
    return G


def var_cofail(F, G=None):
    """Var over unordered model pairs of C_ij = (1/M) * |failures shared by i and j|.

    This is the pre-registered primary statistic T for H1b. Unlike the mean, it is NOT
    pinned by the margins (it depends on the item x item co-failure structure).
    """
    N, M = F.shape
    G = gram(F) if G is None else G
    tot = G.sum(dtype=np.float64) - np.trace(G).astype(np.float64)   # off-diagonal sum
    sq = (G.astype(np.float64) ** 2).sum() - (np.diag(G).astype(np.float64) ** 2).sum()
    npairs = N * (N - 1)
    m1 = tot / npairs / M
    m2 = sq / npairs / (M * M)
    return float(m2 - m1 * m1)


def var_cofail_sampled(F, pairs):
    """Unbiased estimate of Var over a FIXED sample of model pairs.

    Used when N makes the full N x N Gram too costly per replicate. The same pair set is
    reused for the observation and every null replicate, so the comparison is paired.
    """
    M = F.shape[1]
    X = np.ascontiguousarray(F, dtype=np.float32)
    c = np.einsum("ij,ij->i", X[pairs[:, 0]], X[pairs[:, 1]], dtype=np.float64) / M
    return float(c.var())


def eig_spectrum(F, G=None, k=None):
    """Eigenvalues of the model x model co-failure correlation matrix, descending."""
    N, M = F.shape
    G = gram(F) if G is None else G
    C = G.astype(np.float64) / M
    d = np.sqrt(np.clip(np.diag(C), 1e-12, None))
    R = C / d[:, None] / d[None, :]
    w = np.linalg.eigvalsh(R)[::-1]
    return w


def n_eff_participation(w):
    """N_eff definition 1: participation ratio of the eigenspectrum, (sum w)^2 / sum w^2."""
    w = np.clip(np.asarray(w, dtype=np.float64), 0, None)
    return float(w.sum() ** 2 / (w * w).sum())


def n_eff_variance_inflation(F, G=None):
    """N_eff definition 2: variance-inflation form.

    For an N-model committee voting on failure, the variance of the mean failure indicator
    is inflated over the independent case by the mean pairwise correlation rbar:
        N_eff = N / (1 + (N-1) * rbar)
    A claim is reported only if both definitions agree in direction (pre-registered).
    """
    N, M = F.shape
    G = gram(F) if G is None else G
    C = G.astype(np.float64) / M
    d = np.sqrt(np.clip(np.diag(C), 1e-12, None))
    mu = F.mean(1, dtype=np.float64)
    Cov = C - np.outer(mu, mu)
    sd = np.sqrt(np.clip(np.diag(Cov), 1e-12, None))
    R = Cov / sd[:, None] / sd[None, :]
    iu = np.triu_indices(N, 1)
    rbar = float(R[iu].mean())
    return float(N / (1.0 + (N - 1) * rbar)), rbar


# ------------------------------------------------- margin-conditioned excess (Rasch mean-field)

def fit_rasch(F, iters=300, tol=1e-11, verbose=False):
    """Maximum-entropy / Rasch margin model:  P(F_im = 1) = sigmoid(alpha_i + beta_m).

    This is the mean field of the fixed-fixed null: the unique product-Bernoulli law whose
    expected row and column margins equal the observed ones. Fitted by alternating Newton
    steps on the two margin conditions. Returns (alpha, beta, max_margin_error).

    Needed because N_eff computed on the RAW correlation matrix is dominated by a single
    huge eigenvalue that is pure shared item difficulty -- the very artifact Proposition 1
    identifies. Conditioning on the margins removes it analytically.
    """
    F = np.asarray(F, dtype=np.float64)
    N, M = F.shape
    r = F.sum(1)
    c = F.sum(0)
    eps = 1e-9
    a = np.log(np.clip(r, eps, M - eps) / np.clip(M - r, eps, None))
    b = np.zeros(M)
    for t in range(iters):
        P = 1.0 / (1.0 + np.exp(-(a[:, None] + b[None, :])))
        gr = P.sum(1) - r
        hr = np.clip((P * (1 - P)).sum(1), 1e-12, None)
        a -= gr / hr
        P = 1.0 / (1.0 + np.exp(-(a[:, None] + b[None, :])))
        gc = P.sum(0) - c
        hc = np.clip((P * (1 - P)).sum(0), 1e-12, None)
        b -= gc / hc
        err = max(np.abs(gr).max(), np.abs(gc).max())
        if verbose and t % 50 == 0:
            print(f"    rasch it{t} max|margin err|={err:.3e}")
        if err < tol:
            break
    P = 1.0 / (1.0 + np.exp(-(a[:, None] + b[None, :])))
    err = max(np.abs(P.sum(1) - r).max(), np.abs(P.sum(0) - c).max())
    return a, b, float(err)


def rasch_P(a, b):
    return 1.0 / (1.0 + np.exp(-(a[:, None] + b[None, :])))


def excess_gram(F, P, block=1024):
    """Margin-conditioned excess co-failure matrix: (F F^T - P P^T) / M."""
    N, M = F.shape
    X = np.ascontiguousarray(F, dtype=np.float32)
    Q = np.ascontiguousarray(P, dtype=np.float32)
    D = np.empty((N, N), dtype=np.float32)
    for s in range(0, N, block):
        e = min(s + block, N)
        D[s:e] = (X[s:e] @ X.T - Q[s:e] @ Q.T) / M
    return D


def n_eff_from_excess(D, ridge=1e-9):
    """N_eff (participation ratio) on the margin-conditioned excess correlation matrix."""
    d = np.sqrt(np.clip(np.diag(D).astype(np.float64), ridge, None))
    R = D.astype(np.float64) / d[:, None] / d[None, :]
    w = np.linalg.eigvalsh(R)[::-1]
    wp = np.clip(w, 0, None)
    return float(wp.sum() ** 2 / (wp * wp).sum()), w
