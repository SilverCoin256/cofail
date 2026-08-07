"""Harvest ARC-Challenge from the Open LLM Leaderboard v2 archive.

Why this exists and why it is scoped the way it is: v2 stores per-sample outcomes as JSON, not
parquet, so there is no column-selective read the way v1 allowed -- the whole per-item file must
come down. Measured directly (docs/NEURIPS_BLUEPRINT.md, X7 feasibility check): ARC-Challenge in
v2 is ~9.4 MB per model per snapshot, so a full six-task replication is infeasible (~369 GB for
1,000 models) but a single-task, ~300-model replication is a bounded, explicitly authorized
~2.8 GB download -- authorized by the user 2026-08-07, not started unprompted.

For each model, only the LATEST snapshot's ARC-Challenge sample file is fetched, and only the
fields needed for a binary correctness matrix (predicted answer index, gold index) are kept in
memory -- the raw JSON is not retained after parsing, only the parsed correctness bit per item.

Run: ./.venv/bin/python src/harvest_v2_arc.py [n_models]
Status as of 2026-08-07: blocked on HF auth (v2 details datasets are gated; see
docs/NEURIPS_BLUEPRINT.md, "X7 correction"). Output paths are defined in main() below and do
not exist yet -- do not add them as literal paths here until a run has actually produced them,
per this project's own dangling-reference discipline (tests/test_no_dangling_refs.py).
"""
import json, os, re, sys, time
import numpy as np
from huggingface_hub import HfApi, hf_hub_download
from huggingface_hub.utils import EntryNotFoundError, HfHubHTTPError

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ratelimit import LIMITER, is_429

SUB = os.path.join(HERE, "..", "substrate")
RAW = os.path.join(SUB, "raw")
os.makedirs(RAW, exist_ok=True)

SAMPLE_RE = re.compile(r"^(?P<model>.+)/samples_leaderboard_arc_challenge_(?P<ts>[\d\-T.]+)\.json$")


def list_models(n_models, cache_hours=24):
    """Discover model ids with an ARC-Challenge v2 details dataset. Cached, since listing all
    4,500 dataset names is itself a non-trivial number of API calls."""
    cache_path = os.path.join(SUB, "v2_model_list_cache.json")
    if os.path.exists(cache_path) and (time.time() - os.path.getmtime(cache_path)) < cache_hours * 3600:
        ids = json.load(open(cache_path))
    else:
        api = HfApi()
        ids = sorted(d.id for d in api.list_datasets(author="open-llm-leaderboard", limit=None)
                     if d.id.endswith("-details"))
        json.dump(ids, open(cache_path, "w"))
    return ids[:n_models] if n_models else ids


def latest_arc_sample_file(model_id):
    """Return the repo-relative path of the most recent ARC-Challenge samples file, or None."""
    api = HfApi()
    files = api.list_repo_files(model_id, repo_type="dataset")
    hits = []
    for f in files:
        m = SAMPLE_RE.match(f)
        if m and m.group("model") == model_id.split("/")[-1].replace("-details", ""):
            hits.append((m.group("ts"), f))
    if not hits:
        # fall back: any file matching the benchmark name, timestamp parse best-effort
        hits = [(f.rsplit("_", 1)[-1].replace(".json", ""), f) for f in files
                if "samples_leaderboard_arc_challenge" in f]
    if not hits:
        return None
    hits.sort(key=lambda t: t[0])
    return hits[-1][1]


def extract_correctness(path):
    """Parse a v2 samples_* file into a per-item (predicted_correct: bool) list, in file order."""
    data = json.load(open(path))
    rows = data if isinstance(data, list) else data.get("samples") or list(data.values())
    out = []
    for r in rows:
        # v2 sample records carry the model's argmax prediction and the gold index/label under
        # varying key names across harness point releases; try the common ones in order.
        pred = r.get("predictions") or r.get("pred") or r.get("filtered_resps")
        gold = r.get("target") or r.get("gold") or r.get("doc", {}).get("answerKey")
        acc = r.get("acc") or r.get("acc_norm")
        if acc is not None:
            out.append(bool(round(float(acc))))
        elif pred is not None and gold is not None:
            p = pred[0] if isinstance(pred, list) else pred
            out.append(str(p) == str(gold))
        else:
            out.append(None)
    return out


def main(n_models=300):
    models = list_models(n_models)
    print(f"[v2-arc] targeting {len(models)} models (scoped, user-authorized 2026-08-07)",
          flush=True)

    rows, kept_models, rejects = [], [], []
    n_items_ref = None
    t0 = time.time()
    total_bytes = 0

    for i, mid in enumerate(models):
        try:
            LIMITER.acquire()
            rel = latest_arc_sample_file(mid)
            if rel is None:
                rejects.append({"model": mid, "reason": "no ARC-Challenge samples file"})
                continue
            local = hf_hub_download(mid, rel, repo_type="dataset")
            total_bytes += os.path.getsize(local)
            correctness = extract_correctness(local)
            if n_items_ref is None:
                n_items_ref = len(correctness)
            if len(correctness) != n_items_ref or any(c is None for c in correctness):
                rejects.append({"model": mid, "reason": "length/parse mismatch",
                                "n": len(correctness), "expected": n_items_ref})
                continue
            rows.append(correctness)
            kept_models.append(mid)
        except (EntryNotFoundError, HfHubHTTPError) as e:
            if is_429(e):
                LIMITER.penalise()
            rejects.append({"model": mid, "reason": f"{type(e).__name__}: {str(e)[:100]}"})
        except Exception as e:
            rejects.append({"model": mid, "reason": f"{type(e).__name__}: {str(e)[:100]}"})

        if (i + 1) % 10 == 0:
            gb = total_bytes / 1e9
            print(f"  {i+1}/{len(models)}  kept={len(kept_models)} rejected={len(rejects)}  "
                  f"{gb:.2f} GB downloaded  {time.time()-t0:.0f}s elapsed", flush=True)
            # checkpoint every 10 models so a long-running, rate-limited harvest over ~300
            # models can't lose everything to a single failure late in the run
            if rows:
                arr = np.array(rows, dtype=np.uint8)
                np.savez_compressed(os.path.join(RAW, "arc_v2.npz"), prim=arr,
                                    models=np.array(kept_models, dtype=object))
                json.dump(rejects, open(os.path.join(SUB, "v2_arc_rejects.json"), "w"))

    arr = np.array(rows, dtype=np.uint8) if rows else np.zeros((0, 0), dtype=np.uint8)
    np.savez_compressed(os.path.join(RAW, "arc_v2.npz"), prim=arr,
                        models=np.array(kept_models, dtype=object))
    json.dump(rejects, open(os.path.join(SUB, "v2_arc_rejects.json"), "w"), indent=1)
    json.dump({"n_requested": len(models), "n_kept": len(kept_models), "n_rejected": len(rejects),
              "n_items": n_items_ref, "total_bytes_downloaded": total_bytes,
              "seconds_elapsed": time.time() - t0},
             open(os.path.join(SUB, "v2_arc_manifest.json"), "w"), indent=1)

    print(f"\n[v2-arc] done: {len(kept_models)}/{len(models)} kept, {len(rejects)} rejected, "
          f"{n_items_ref} items, {total_bytes/1e9:.2f} GB, {time.time()-t0:.0f}s")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    main(n)
