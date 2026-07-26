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
    cofail.neff(F, calibrate=True)       # effective number of independent models, vs null

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
