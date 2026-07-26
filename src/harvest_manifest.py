"""Phase 1, step A: enumerate every model-detail dataset and resolve, per benchmark,
the file path of its LATEST snapshot (the snapshot rule fixed in PREREGISTRATION.md).

Writes a resumable cache so the job can be interrupted and restarted.
Output: substrate/manifest_files.json  {model_id: {bench: rfilename}}
        substrate/manifest_errors.json {model_id: reason}
"""
import json, os, sys, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from huggingface_hub import HfApi
from huggingface_hub.utils import HfHubHTTPError
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ratelimit import LIMITER, is_429

ORG = "open-llm-leaderboard-old"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "substrate")
os.makedirs(OUT, exist_ok=True)

# benchmark key -> substring identifying its detail file
BENCH = {
    "arc":        "arc:challenge",
    "hellaswag":  "|hellaswag|",
    "winogrande": "|winogrande|",
    "truthfulqa": "truthfulqa:mc",
    "gsm8k":      "|gsm8k|",
}
MMLU_TAG = "hendrycksTest-"

api = HfApi()
_lock = threading.Lock()
_done = 0


def list_models():
    cache = os.path.join(OUT, "manifest_models.json")
    if os.path.exists(cache):
        return json.load(open(cache))
    ids = [d.id for d in api.list_datasets(author=ORG, limit=None) if "/details_" in d.id]
    ids.sort()
    json.dump(ids, open(cache, "w"))
    return ids


def resolve(mid, tries=8):
    """Return {bench: rfilename} for the latest snapshot of each benchmark.

    HF rate-limits anonymous traffic; 429 is retried with exponential backoff and
    is never cached as a permanent failure (see RETRYABLE in main()).
    """
    for a in range(tries):
        try:
            LIMITER.acquire()
            info = api.repo_info(mid, repo_type="dataset")
            names = [s.rfilename for s in info.siblings]
            LIMITER.ok()
            break
        except Exception as e:
            if is_429(e):
                LIMITER.hit_429(e)
                continue
            code = getattr(getattr(e, "response", None), "status_code", None)
            if a == tries - 1:
                return None, (f"http:{code}" if code else type(e).__name__)
            time.sleep(1.5 * (a + 1))
    out = {}
    for b, tag in BENCH.items():
        c = sorted(n for n in names if tag in n and n.endswith(".parquet"))
        if c:
            out[b] = c[-1]  # lexicographic sort on the ISO-dated dir == latest snapshot
    mm = sorted(n for n in names if MMLU_TAG in n and n.endswith(".parquet"))
    if mm:
        # keep only files from the newest snapshot directory
        newest = max(n.split("/")[0] for n in mm)
        out["mmlu"] = [n for n in mm if n.startswith(newest + "/")]
    return (out, None) if out else (None, "no-benchmark-files")


def main():
    models = list_models()
    print(f"models: {len(models)}", flush=True)
    fp = os.path.join(OUT, "manifest_files.json")
    ep = os.path.join(OUT, "manifest_errors.json")
    files = json.load(open(fp)) if os.path.exists(fp) else {}
    errs = json.load(open(ep)) if os.path.exists(ep) else {}
    # transient failures must not be cached as permanent
    RETRYABLE = ("http:429", "http:5", "ConnectionError", "ReadTimeout", "Timeout")
    errs = {k: v for k, v in errs.items() if not any(v.startswith(r) for r in RETRYABLE)}
    todo = [m for m in models if m not in files and m not in errs]
    print(f"cached: {len(files)}  todo: {len(todo)}", flush=True)
    t0 = time.time()
    global _done
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(resolve, m): m for m in todo}
        for f in as_completed(futs):
            m = futs[f]
            try:
                got, err = f.result()
            except Exception as e:
                got, err = None, type(e).__name__
            with _lock:
                if got:
                    files[m] = got
                else:
                    errs[m] = err
                _done += 1
                if _done % 250 == 0:
                    el = time.time() - t0
                    rate = _done / max(el, 1e-9)
                    print(f"  {_done}/{len(todo)}  ok={len(files)} err={len(errs)}  "
                          f"{rate:.1f}/s  eta={(len(todo)-_done)/max(rate,1e-9)/60:.1f}min  "
                          f"{LIMITER.stats()}", flush=True)
                    json.dump(files, open(fp, "w"))
                    json.dump(errs, open(ep, "w"))
    json.dump(files, open(fp, "w"))
    json.dump(errs, open(ep, "w"))
    print(f"DONE  resolved={len(files)}  errors={len(errs)}  {(time.time()-t0)/60:.1f}min", flush=True)
    cov = {}
    for v in files.values():
        for b in v:
            cov[b] = cov.get(b, 0) + 1
    print("coverage:", json.dumps(cov, indent=2), flush=True)


if __name__ == "__main__":
    main()
