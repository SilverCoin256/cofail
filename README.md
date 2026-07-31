# cofail — measuring correlated failure between models, at the exact conditional null

[![Layer C monitor](https://github.com/SilverCoin256/cofail/actions/workflows/layer_c_monitor.yml/badge.svg)](https://github.com/SilverCoin256/cofail/actions/workflows/layer_c_monitor.yml)

**[Project page](https://silvercoin256.github.io/cofail/)** · **[Paper (PDF)](docs/paper.pdf)** ·
**[Short version, 4pp](docs/workshop.pdf)** · **[One-page brief](docs/brief/brief.pdf)** ·
**[Layer C — live changelog](CHANGELOG.md)**

Do independently developed language models fail on the same inputs more than chance? The usual
evidence is a co-failure or agreement rate compared against an independence baseline. That
comparison cannot answer the question, for a reason that is arithmetic rather than statistical:

```
$ cofail excess --matrix arc_failures.npy
reported excess over independence : +0.114174444
forced by the item margins alone  : +0.114174444
residual carrying any information : -1.388e-17
```

The mean pairwise co-failure rate over a population of models is a function of the **item
margins alone**. Any randomisation that preserves item difficulty leaves it exactly unchanged,
so the excess over such a null is identically zero — not small, zero. This package supplies the
conditioning that does carry information, and the calibration without which the conditioned
number is equally uninterpretable.

## Install

```bash
pip install -e .
```

Only NumPy is required for the estimator. `pip install -e ".[harvest,figures,dev]"` adds the
data harvester, plotting, and tests.

## Use

```python
import numpy as np, cofail

F = np.load("failures.npy")        # (n_models, n_items), 1 = model failed item

cofail.naive_excess(F)             # what an independence baseline reports
cofail.marginal_artifact(F)        # what the margins alone force — equal to the above
print(cofail.neff(F, calibrate=True))
```

`calibrate=True` is not optional in spirit: the null value of the statistic is emphatically not
the model count, and an uncalibrated figure is not interpretable. See the caveat below on what
the participation ratio does and does not measure.

```bash
cofail audit --matrix F.npy --json report.json   # start here
cofail selftest                                  # verify the identities on synthetic data
cofail pr    --matrix F.npy --n-null 40          # the participation ratio on its own
```

`cofail audit` is the command to reach for before reporting any model-agreement number. It runs
four checks in one pass: whether your reported excess is a margin artifact, how much of your model
population is near-duplicate (with a warning if removing pairs above 0.95 agreement discards more
than a fifth of it), what survives conditioning, and — stated explicitly because it is easy to
misread a null result — what the test structurally cannot detect.

`cofail neff` still works but is **deprecated and prints a warning**: the name asserted an
"effective number of independent models" reading that this project withdrew. Use `cofail pr`.

## What is in here

| path | what |
|---|---|
| `cofail/` | the installable estimator (pure NumPy) |
| `src/harvest_*.py` | zero-cost harvest of the Open LLM Leaderboard archive |
| `src/nullmodel.py` | curveball randomisation, Rasch margin model, spectral statistics |
| `src/experiments.py` | the confirmatory run (E0–E7) |
| `src/controls.py`, `src/dedup.py`, `src/reconcile.py`, `src/null_independent.py` | the checks that decide whether the headline is real |
| `src/noise_floor.py`, `src/sampler_validation.py` | is the exact null better than a trivial one, and is the sampler actually uniform |
| `src/dedup_sensitivity.py`, `src/rank_redundancy*.py` | the duplication audit — how much of each result is near-duplicate models |
| `src/power_study.py` | what the test can and cannot detect, including the blind spot |
| `src/selection_killtest.py`, `src/incremental_validity.py` | whether conditioned diversity buys anything downstream (it does not) |
| `src/null_ladder.py`, `src/dimensionality.py` | the null ladder, and a retracted dimensionality estimate kept as a record |
| `PREREGISTRATION.md` | hypotheses and kill conditions, fixed in advance, with two dated amendments |
| `results/RESULTS_DIGEST.md` | every reported number, with the corrections that followed adversarial review |
| `docs/PRIOR_ART_LEDGER.md` | what in this work is mine and what is not |
| `docs/DATASHEET.md`, `docs/croissant.json` | datasheet and machine-readable metadata, incl. the verified upstream licenses |
| `docs/NEURIPS_BLUEPRINT.md` | adversarial audit of this paper and the redesign it produced |
| `paper/main.tex`, `paper/workshop.tex` | the manuscript, and a 4-page cut |

## Reproducing

```bash
python src/harvest_manifest.py                       # resolve file paths (rate-limited, resumable)
python src/harvest_matrix.py arc winogrande truthfulqa gsm8k
python src/experiments.py arc winogrande truthfulqa gsm8k
python src/controls.py && python src/dedup.py arc && python src/reconcile.py arc
python src/figures.py
python -m pytest tests -q
```

The harvest reads only the metric column of each parquet — 1.4 KB out of a 63 MB file for
HellaSwag — so ~1,350 models per benchmark cost no GPU, no inference, and a few hundred MB of
traffic. Hugging Face rate-limits anonymous access to 500 requests per 300 s; `src/ratelimit.py`
paces to that budget and the harvesters are resumable.

Two archive pitfalls are handled and worth knowing about if you build on this data. Item
identifiers are **not stable** — the harness stored a dataset id in mid-2023 and raw question
text afterwards, so a naive id join returns an *empty* intersection. And the accuracy field moved
into a nested `metrics` struct in 2024. Item identity here is the row index, verified stable for
149 of 149 readable models in a 150-model sample spanning July 2023 – May 2024 and both
identity-column schema generations, with a row-count guard on every read
(`src/audit_roworder.py`). Still a sample of ~1,400, not a proof.

## Honest caveats

**The participation ratio does not count independent models.** For any unit-diagonal `R`,
`PR = N / (1 + (N−1)·mean(R_ij²))` exactly — the eigendecomposition contributes nothing, and PR
cannot distinguish one weak global factor from many tight clusters. An earlier version of this
work reported "≈1,300 models behave like ≈24 independent ones"; that claim is **withdrawn**. Use
`rms|R_ij|`, `λ₁²/Σλ²`, the deflated PR, and the count of eigenvalues above the null spectral
edge, all of which discriminate.

**Conditioning on a one-parameter model is a real limitation.** Simulated populations with no
clusters and no shared lineage, but two latent ability dimensions, reproduce much of the observed
effect. Discrimination heterogeneity alone does not. See `results/RESULTS_DIGEST.md` § C3.

**There is one thing this test structurally cannot see.** If every model finds the same items
hard and differs only in overall ability, that case *is* the null, and the measured power against
it is exactly α (0.05). A null result is therefore not evidence that models are independent. The
test does have power 1.00 against shared failure modes at a planted strength well below what real
data shows, and detects copying of a reference model from a copy rate of 0.1 — see
`src/power_study.py`.

**The core identities are not new.** They are Schluter's V-ratio in ecology, Kuder–Richardson /
Cronbach's α in psychometrics, and Fleiss's observed agreement for the multi-category case. This
package restates and attributes them; it does not claim them. See `docs/PRIOR_ART_LEDGER.md`.

## AI assistance

The code in this repository was written with a large language model (Claude, Anthropic) acting as
a coding and analysis assistant, including the adversarial prior-art review that caused the
central claim to be corrected. The author directed the work, set the pre-registered hypotheses and
kill conditions, verified the derivations, and is responsible for the content.

## Licence

**MIT for the code.** The derived data is a different matter, and the chain was verified against
the HuggingFace Hub on 2026-07-28 rather than assumed:

| upstream | licence | note |
|---|---|---|
| ARC-Challenge | **CC-BY-SA-4.0** | **share-alike** — ARC-derived matrices are *not* redistributable under MIT |
| TruthfulQA | Apache-2.0 | clear |
| GSM8K | MIT | clear |
| HellaSwag, Winogrande, the leaderboard archive | **none declared** | absence of a licence is not permission; rights are **unestablished** |

The reconstructed ARC answer key is **withheld** from release — it derives from a share-alike work
and republishing a benchmark answer key is a training-contamination vector. The recovery code ships
instead, so you can rebuild it yourself. Full detail in [`docs/DATASHEET.md`](docs/DATASHEET.md)
§6 and [`docs/croissant.json`](docs/croissant.json).
