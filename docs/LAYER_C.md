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

## Incident: the first scheduled run (2026-08-03) was cancelled and lost its progress

Layer C's very first real scheduled execution fired on schedule, ran for the full 180-minute
timeout then in effect, and was cancelled by GitHub before it finished harvesting even one
benchmark. **Nothing was committed** — `results/timeseries.csv` and `CHANGELOG.md` stayed frozen
at their 2026-07-26 seed values, silently, with no alert. This was found on 2026-08-07 by
checking `gh run list` directly, not by any monitoring this repository had in place.

**Root cause.** The manifest refresh discovered the archive had grown from ~1,362 to **7,038**
candidate models since the original harvest — roughly 5,600 newly seen at once. At the throughput
realized under GitHub Actions' rate limits (~0.3 models/s, well below this project's interactive-
session throughput), that backlog cannot be harvested in one run at any timeout GitHub allows (360
minutes is the hard cap for hosted runners). The job was cancelled 2,300 models into the ARC
harvest. `src/harvest_matrix.py` already checkpoints to local disk every 100 models — but the
workflow committed to git only once, at the very end, after all five benchmarks and `monitor.py`
were meant to finish. So three hours of real, completed harvest work existed only in the runner's
ephemeral filesystem when it was torn down, and none of it reached the repository.

**Fix (2026-08-07).** Two changes, both in this repository now:
1. `src/harvest_matrix.py` gained an `MM_MAX_NEW` cap on how many newly discovered models a
   single invocation processes for one benchmark, so a run finishes reliably within its time
   budget instead of attempting the whole backlog at once.
2. `.github/workflows/layer_c_monitor.yml` now harvests and **commits after every individual
   benchmark**, not once at the end, and raised its timeout to 350 minutes (GitHub's practical
   maximum). A large backlog now drains gradually, a few hundred models per benchmark per month,
   and a timeout on a later benchmark can no longer erase progress already made and committed on
   an earlier one.

**Consequence, stated plainly.** At 800 new models per benchmark per scheduled run, absorbing the
current ~5,600-model backlog will take roughly seven monthly cycles per benchmark in the worst
case. During that window, `n_models` in `results/timeseries.csv` will visibly grow month over
month as the backlog is worked down — this is gradual catch-up on a known backlog, not new
population growth in the underlying archive at that rate, and should be read as such if this
document is being consulted from a future point.

```bash
python src/monitor.py arc winogrande truthfulqa gsm8k hellaswag
```

Or trigger the GitHub Actions workflow directly from the repository's Actions tab
(`workflow_dispatch`) without waiting for the scheduled date.
