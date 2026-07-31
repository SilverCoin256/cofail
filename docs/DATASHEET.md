# Datasheet for the `cofail` evaluation substrate

Following Gebru et al., *Datasheets for Datasets* (Commun. ACM 64(12):86–92, 2021).

**Version:** 0.2 (2026-07-28). **Contact:** Shaurya Gupta, shauryaguptaa8@gmail.com.
**Code license:** MIT (see `LICENSE`). **Data license:** see §6 — *this is the section to read
before redistributing anything.* **Machine-readable metadata:** `docs/croissant.json`
(MLCommons Croissant 1.0), carrying the same per-benchmark license findings and limitations.

> **Status of this document.** Written to close a Critical artifact objection raised in the
> NeurIPS forensic audit (`docs/NEURIPS_BLUEPRINT.md`, F10). Items marked **[TO VERIFY]** are
> stated as intent and have **not** been confirmed against the upstream sources; they must be
> checked before any public data release. Nothing here should be read as a legal opinion.

---

## 1. Motivation

**Why was this created?** To make it possible to study correlated failure between language models
at a scale where the model axis, not the item axis, is the large one. Published work on model
monoculture used 349 models; this substrate has 1,228–1,373 per benchmark. It exists because the
statistical question — is co-failure between models more than item difficulty predicts? — cannot
be answered from aggregate leaderboard scores. It needs per-item outcomes.

**Who created it?** One unaffiliated author. No funding.

## 2. Composition

Five model × item **binary correctness matrices**, one per benchmark, plus one model × item
**chosen-option** tensor for a 600-model ARC subsample.

| file | shape | cell meaning |
|---|---|---|
| `substrate/raw/arc.npz` | 1362 × 1165 | 1 = model answered item correctly |
| `substrate/raw/winogrande.npz` | 1361 × 1267 | " |
| `substrate/raw/truthfulqa.npz` | 1334 × 786 | " (mc1) |
| `substrate/raw/gsm8k.npz` | 1228 × 1319 | " (strict-match extraction) |
| `substrate/raw/hellaswag.npz` | 1362 × 9404 | " |
| `substrate/raw/arc_resp.npz` | 600 × 1172 | index of the option the model selected |

Each `.npz` also carries `models` (HuggingFace repo ids) and `dates` (leaderboard snapshot date).

**Is correctness one quantity across the five?** **No, and this matters.** On the v1 leaderboard,
ARC / HellaSwag / Winogrande / TruthfulQA-mc1 correctness is length-normalised log-likelihood
ranking over answer continuations under a fixed prompt template; GSM8K correctness is strict-match
extraction from generated text. Pooling them assumes a comparability that does not strictly hold.
This was raised as a Major objection in the audit and is disclosed rather than resolved.

**Population.** Self-selected submissions to the HuggingFace Open LLM Leaderboard v1, snapshots
July 2023 – June 2024. **This is not a sample of independent models.** Measured directly
(`results/dedup_sensitivity.json`): removing models that agree with a retained model at ≥0.95
removes **36–64%** of the population. A coarse name-based family census attributes only ~35% of
model ids to a named base family and finds ~125 models per benchmark with merge-related names —
both are **lower bounds** on relatedness, not lineage ground truth. Any analysis treating these
rows as exchangeable independent models is partly measuring duplication.

**Missing data.** Item attrition versus canonical split sizes (TruthfulQA-mc1 786 of 817 items;
HellaSwag 9,404 of 10,042; ARC 1,165 of 1,172 in tier 1) comes from dropping degenerate columns —
items every model got right or every model got wrong, which are frozen under any margin-preserving
randomisation and carry no information. Per-stage counts are in `results/RESULTS_DIGEST.md`.

**Does it contain personal or sensitive data?** No. It contains no human subjects, no text — only
per-item correctness bits and option indices.

## 3. Collection

Derived, not collected. Read from the `open-llm-leaderboard-old` parquet archive on HuggingFace by
**column-selective reads**: only the metric column of each file is fetched (≈1.4 KB out of a 63 MB
file for HellaSwag). No model was run and no inference was purchased; total compute cost was zero.

**Item identity is the row index.** The archive's per-item identifiers are not stable across
harness schema generations, so item `m` means "row `m` of the benchmark's evaluation file."
This is licensed by a row-order verification (`src/audit_roworder.py`, artifact
`results/audit_roworder_arc.json`): **149 of 149 readable models** in a 150-model sample drawn
evenly across 2023-07-18 – 2024-05-30 had byte-identical item ordering, covering both
identity-column schema generations (28 models where the identity field is `query`, 121 where it
is `example`). One model was unreadable due to a transient network error. A row-count guard runs
on every read. The audit covers **all five benchmarks**, 334 models in total, with **zero
mismatches**: ARC 149/149, TruthfulQA 60/60, GSM8K 60/60, Winogrande 40/40, HellaSwag 25/25.
Artifacts: `results/audit_roworder_<bench>.json`.

**Only ARC and HellaSwag sample both identity-column schema generations.** The other three
samples drew entirely from the later generation, so they do not independently exercise the
cross-generation drift that produced an empty intersection in Phase 0 — that specific hazard
is tested by ARC and HellaSwag only.

**This is a sample of ~1,400 models, not a proof.** A single undetected misalignment would bias
every correlation estimate toward zero — i.e. toward the null, so this failure mode would
understate the paper's result rather than manufacture it. The original release cited a 14-model
spot check; that has been widened by an order of magnitude, and the remaining gap is stated here
rather than closed.

## 4. Preprocessing

Degenerate rows (models that got everything right or everything wrong) and degenerate columns are
dropped before analysis; the raw `.npz` files retain them. Reject counts per benchmark: ARC 0,
GSM8K 0, Winogrande few, TruthfulQA 22, HellaSwag 0.

For `arc_resp.npz`, the option each model selected is reconstructed from per-choice
log-likelihoods, and the answer key is recovered from models that answered correctly. Validation:
agreement among correct models on shared items = 1.0000 (1,144 of 1,172 items recovered); the
recovered key reproduces each model's own reported accuracy on **99.01%** of cells. **The residual
~1% is an undocumented label-error rate** whose effect on downstream estimates has not been
quantified.

## 5. Uses

**Used for:** the analyses in `paper/main.tex` and every result in `results/`.

**Suitable for:** methodological work on agreement, diversity and correlated-failure statistics;
IRT and psychometric modelling of model populations; null-model methodology.

**NOT suitable for:** claims about currently deployed systems. The population predates
Llama-3.1, Qwen-2.5 and reasoning models; the v1 benchmark suite was retired for saturation and
contamination; and **contamination is not measured here**, though it produces exactly the
signature these matrices are used to study.

**Do not** treat rows as independent models without deduplicating first — see §2.

## 6. Distribution

**The code in this repository is MIT-licensed. The data is not the author's to relicense.**

`substrate/` is a derivative of the Open LLM Leaderboard archive, which is itself derived from
five benchmark datasets, each with its own upstream terms. Redistribution of the derived matrices
is governed by that chain.

Queried against the HuggingFace Hub API on **2026-07-28**. "Verified" means the license appears in
the dataset's own card metadata or tags, read programmatically — not inferred from a paper or a
secondary source.

| benchmark | upstream dataset | declared license | share-alike? | verified |
|---|---|---|---|---|
| ARC-Challenge | `allenai/ai2_arc` | **CC-BY-SA-4.0** | **YES** | ☑ card + tag |
| TruthfulQA | `truthfulqa/truthful_qa` | Apache-2.0 | no | ☑ card + tag |
| GSM8K | `openai/gsm8k` | MIT | no | ☑ card + tag |
| HellaSwag | `Rowan/hellaswag` | **none declared** | unknown | ☐ no tag, no LICENSE file on the Hub |
| Winogrande | `allenai/winogrande` | **none declared** | unknown | ☐ no tag, no LICENSE file on the Hub |
| leaderboard archive | `open-llm-leaderboard-old/details_*` | **none declared** | unknown | ☐ no tag |

**Two consequences, one of them binding.**

1. **ARC is share-alike, and this is now a verified fact rather than a suspicion.** The derived ARC
   correctness matrix, and emphatically the reconstructed ARC answer key in `arc_resp.npz`, are
   derivatives of a CC-BY-SA-4.0 work. Releasing them under this repository's MIT terms is very
   likely non-compliant. Any release of the ARC-derived data must carry CC-BY-SA-4.0 with
   attribution to AI2, separately from the MIT code. **The recommendation below to withhold the
   reconstructed answer key is therefore not merely prudential — it also removes the most
   clearly encumbered artifact.**
2. **Three of six upstream sources declare no license at all**, including the leaderboard archive
   that everything here derives from. Absence of a declared license is not permission. Until this
   is resolved with the upstream maintainers, the honest position is that redistribution rights for
   the HellaSwag- and Winogrande-derived matrices are **unestablished**, and they should not be
   mirrored outside this repository. Harvesting them from the archive oneself, which the released
   code supports, raises no such question.

**Known hazard, acted on.** `arc_resp.npz` embeds a reconstructed ARC answer key at 99.01%
fidelity. Redistributing a benchmark's answer key is both a possible share-alike violation and a
contamination vector — a future model could train on it. **Recommendation, and the current plan:
publish the recovery *code* and withhold the reconstructed key from the public release.**

**Persistence.** The repository is on GitHub with no DOI, no checksums, and no archival copy, and
`results/timeseries.csv` is *mutated on a schedule* by the Layer C workflow. **[TO VERIFY]** before
release: deposit a frozen, versioned snapshot on Zenodo with a DOI and checksums, and separate the
frozen paper substrate from the mutating monitor output. Upstream durability is also not
guaranteed — the source archive has already been renamed once (`open-llm-leaderboard` →
`open-llm-leaderboard-old`).

## 7. Maintenance

Maintained by the author. Layer C (`.github/workflows/layer_c_monitor.yml`) re-runs monthly,
appending to `results/timeseries.csv` and `CHANGELOG.md`. There is currently **no** deprecation
policy, erasure policy for model records, or second point of contact. Model owners wanting a
record removed should open an issue; requests will be honoured, and this is a stated intention
rather than an established process.

## 8. Known defects

Collected in one place deliberately.

1. Item alignment is verified on ~330 models across all five benchmarks with zero mismatches,
   but that is a sample of ~1,400, and only two of the five samples span both schema
   generations (§3).
2. ~1% label-error rate in the reconstructed ARC key, effect unquantified (§4).
3. "Binary correctness" is not one quantity across the five benchmarks (§2).
4. The population is 36–64% redundant and only ~35% lineage-attributable (§2).
5. Contamination is unmeasured (§5).
6. Evaluation-harness version drift across the July 2023 – June 2024 window is uncontrolled.
7. No DOI, no checksums, no versioning; part of the artifact mutates on a schedule (§6).
8. Upstream license chain is **partly resolved** (§6, verified 2026-07-28): ARC is CC-BY-SA-4.0
   and therefore share-alike, so the ARC-derived matrices and the reconstructed key cannot ship
   under this repository's MIT terms; TruthfulQA (Apache-2.0) and GSM8K (MIT) are clear;
   HellaSwag, Winogrande and the leaderboard archive itself declare **no license at all**, so
   redistribution rights for those derivatives are unestablished.
