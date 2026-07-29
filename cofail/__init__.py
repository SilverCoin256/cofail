"""cofail -- identified estimation of correlated failure between models.

The mean pairwise co-failure rate over a set of models is a function of the item margins alone
(see the accompanying paper). Comparing it to an independence baseline therefore measures item
difficulty dispersion, not shared behaviour. This package provides the margin-conditioned
alternative.

Typical use::

    import numpy as np, cofail
    F = np.load("failures.npy")          # (n_models, n_items), 1 = model failed item

    cofail.naive_excess(F)               # what an independence baseline reports
    cofail.marginal_artifact(F)          # what the margins alone force (closed form)
    cofail.neff(F, calibrate=True)       # participation ratio of the conditioned spectrum

Or from the command line, `cofail audit --matrix F.npy`, which runs all of the above plus a
near-duplicate census and states what the test cannot detect.

WHAT `neff` IS NOT. Despite its name, it does **not** return an effective number of independent
models, and that interpretation is withdrawn. The participation ratio is algebraically
N/(1+(N-1)*mean(R_ij^2)) -- a monotone function of the mean squared residual correlation -- so it
cannot distinguish one weak global factor from many tight clusters. Read it as a summary of
residual correlation. The function keeps its name for backward compatibility; the CLI spelling is
`cofail pr`.

WHAT THE NULL CANNOT SEE. Conditioning on the item margins means the test has no power against the
alternative in which every model shares one item-difficulty profile and differs only in overall
ability -- that case is the null. A null result here is not evidence that models are independent.

Everything is plain NumPy; no GPU, no network, no model inference.
"""
from .core import (
    curveball,
    margins_preserved,
    mean_cofail,
    naive_excess,
    marginal_artifact,
    fit_margin_model,
    excess_matrix,
    neff,
    NeffResult,
)

__all__ = [
    "curveball", "margins_preserved", "mean_cofail", "naive_excess",
    "marginal_artifact", "fit_margin_model", "excess_matrix", "neff", "NeffResult",
]
__version__ = "0.1.0"
