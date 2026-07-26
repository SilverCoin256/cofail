# Layer C — the longitudinal evidence engine

Most research code dies at publication: the paper is the last artifact, and the pipeline that
produced it is never run again. This is the piece designed not to die.

## What it is, concretely

`.github/workflows/layer_c_monitor.yml` runs `src/monitor.py` on GitHub's own infrastructure,
monthly, independent of any contributor's machine or any chat session:

1. `MM_REFRESH_MODELS=1 python src/harvest_manifest.py` re-queries the archive's model list
   (rather than trusting the cached one) to discover models added since the last run.
2. `python src/harvest_matrix.py` harvests only the delta — the existing per-model outcome
   caches (`substrate/raw/*.npz`) mean already-seen models cost nothing to re-fetch.
3. `python src/monitor.py` recomputes the calibrated statistics (participation ratio and
   rms residual correlation, both against their exact-margin null) and appends one dated row
   to `results/timeseries.csv` and one entry to `CHANGELOG.md`.
4. The workflow commits the result back to the repository.

Nothing here re-derives the paper's theorems. It re-applies the same estimator, unchanged, to
whatever the archive looks like at refresh time.

## Why this, and not a chat-session cron job

The obvious alternative — a scheduled agent task inside a Claude Code session — was considered
and rejected: those jobs are session-scoped and auto-expire after 7 days regardless of what's
scheduled. That is not a longitudinal instrument; it is a delayed one-shot. A workflow committed
to a public GitHub repository runs on GitHub's schedule, survives the repository's entire
lifetime, and needs nobody's laptop to be on. Public repositories get free scheduled Actions
minutes, so the monthly cadence costs nothing to sustain.

## What this can and cannot show

**Can show, mechanically, starting from the first scheduled run:** whether newly added models
join the ecosystem's existing residual structure or introduce new dimensions — i.e., whether
`PR_observed` / `PR_null` drifts as `N` grows, and whether `rms|R_ij|` rises, falls, or holds.

**Cannot yet show:** a confirmatory answer to H3 (does effective independence trend across
release cohorts?). That test needs enough accumulated history for a trend to be statistically
distinguishable from run-to-run noise — realistically a year or more of monthly points. The first
seeded row (2026-07-26, `results/timeseries.csv`) is a baseline, not a trend.

**Will not silently drift into a different claim.** The estimator, the null, and the calibration
are frozen by the pre-registration; this pipeline is not permitted to change what is measured,
only to measure it again on more data. Any change to the estimator itself must go through the
same pre-registration discipline as the original paper (a dated, appended amendment — see
`PREREGISTRATION.md`), not a silent edit to `monitor.py`.

## Reading the output

- `results/timeseries.csv` — one row per (benchmark, run), machine-readable.
- `CHANGELOG.md` — the same data, human-readable, in commit history.
- `figures/fig9_cohort.pdf` — regenerated each run from the accumulated cohort data.

## Running it manually

```bash
python src/monitor.py arc winogrande truthfulqa gsm8k
```

Or trigger the GitHub Actions workflow directly from the repository's Actions tab
(`workflow_dispatch`) without waiting for the scheduled date.
