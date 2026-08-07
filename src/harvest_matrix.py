"""Phase 1, step B: build model x item binary outcome matrices.

Only the metric column is read from each parquet. On HellaSwag that is ~1.4 KB out of a
63 MB file, which is what makes an ecosystem-scale harvest possible without a GPU,
an API budget, or bulk downloads.

Robust to three harness schema generations observed in the archive:
  gen A (early Jul 2023) : example = dataset ID, query = question text, flat `acc`
  gen B (late Jul 2023+) : example = question text,                    flat `acc`
  gen C (2024+)          : example = question text, no query,          `metrics` struct

Item identity is the ROW INDEX. That is licensed by an explicit verification
(src/audit_roworder.py, artifact results/audit_roworder_arc.json): row order was identical
for 149 of 149 readable models out of a 150-model sample drawn evenly across
2023-07-18 - 2024-05-30, covering both identity-column schema generations (28 gen-A,
121 gen-B/C); one model was unreadable due to a transient network error. Every read is
additionally guarded on row count, and any model whose length deviates is rejected and
logged. This is a sample of ~1,400, so it raises confidence rather than proving alignment
for every model.

Usage:  python harvest_matrix.py [bench ...]     (default: all single-file benchmarks)
"""
import json, os, sys, time, threading
import numpy as np
import pyarrow.parquet as pq
from concurrent.futures import ThreadPoolExecutor, as_completed
from huggingface_hub import HfFileSystem

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ratelimit import LIMITER, is_429
SUB = os.path.join(HERE, "..", "substrate")
RAW = os.path.join(SUB, "raw")
os.makedirs(RAW, exist_ok=True)

# benchmark -> (primary metric, secondary metric or None)
METRIC = {
    "arc":        ("acc", "acc_norm"),
    "hellaswag":  ("acc", "acc_norm"),
    "winogrande": ("acc", None),
    "gsm8k":      ("acc", None),
    "truthfulqa": ("mc1", "mc2"),
}
WORKERS = int(os.environ.get("MM_WORKERS", "8"))
fs = HfFileSystem()
_lock = threading.Lock()


def read_one(mid, rfile, prim, sec):
    """Return (n_rows, primary uint8 array, secondary float32 array or None, snapshot date)."""
    pf = pq.ParquetFile(fs.open(f"datasets/{mid}/{rfile}", "rb"))
    names = set(pf.schema_arrow.names)
    nested = "metrics" in names
    cols = ["metrics"] if nested else [c for c in (prim, sec) if c and c in names]
    if not cols:
        raise KeyError(f"no metric column; have {sorted(names)[:8]}")
    tb = pf.read(columns=cols)
    if nested:
        recs = tb.column("metrics").to_pylist()
        if not recs or prim not in (recs[0] or {}):
            raise KeyError(f"metrics lacks {prim}; has {sorted((recs[0] or {}).keys())}")
        pv = [r[prim] for r in recs]
        sv = [r.get(sec) for r in recs] if sec and sec in (recs[0] or {}) else None
    else:
        if prim not in names:
            raise KeyError(f"flat schema lacks {prim}")
        pv = tb.column(prim).to_pylist()
        sv = tb.column(sec).to_pylist() if (sec and sec in cols) else None
    p = np.asarray([float(x) for x in pv], dtype=np.float32)
    s = np.asarray([np.nan if x is None else float(x) for x in sv], dtype=np.float32) if sv else None
    return len(p), p, s, rfile.split("/")[0][:10]


def harvest(bench, manifest):
    prim, sec = METRIC[bench]
    out = os.path.join(RAW, f"{bench}.npz")
    have, P, S, D = {}, {}, {}, {}
    if os.path.exists(out):
        z = np.load(out, allow_pickle=True)
        ms = list(z["models"])
        for k, m in enumerate(ms):
            P[m] = z["prim"][k]
            if "sec" in z.files and z["sec"].size:
                S[m] = z["sec"][k]
            D[m] = str(z["dates"][k])
        have = set(ms)
        print(f"[{bench}] resuming, {len(have)} cached", flush=True)
    todo = [(m, v[bench]) for m, v in manifest.items() if bench in v and m not in have]

    # Bound a single invocation's work. Added after Layer C's first real scheduled run
    # (2026-08-03): the archive had grown from ~1,362 to 7,038 candidate models since the
    # original harvest, discovering ~5,600 new-to-us models in one go. At the realized
    # throughput under GitHub Actions' rate limits (~0.3 models/s, far below this project's
    # interactive-session throughput), that backlog does not fit in a single run at any
    # timeout GitHub allows (360 min hard cap for hosted runners) -- the run was cancelled
    # 2,300 models into ARC alone, and because the workflow only committed once at the very
    # end, all of that progress was lost, not just delayed. Capping the per-run delta and
    # committing after every benchmark (see .github/workflows/layer_c_monitor.yml) means a
    # large backlog drains gradually across several scheduled runs instead of requiring one
    # run to finish everything atomically or lose everything.
    max_new = int(os.environ.get("MM_MAX_NEW", "0") or "0")
    if max_new and len(todo) > max_new:
        print(f"[{bench}] {len(todo)} new models discovered, capping this run to {max_new} "
              f"(MM_MAX_NEW); remainder will be picked up on the next scheduled run", flush=True)
        todo = todo[:max_new]

    # canonical row count = mode over a 40-model probe (never hardcoded)
    ncan = None
    rej = []
    done = [0]
    t0 = time.time()

    def work(item):
        mid, rf = item
        tries = 0
        while tries < 40:                     # 429s are paced, not counted as failures
            try:
                LIMITER.acquire(cost=3)       # each parquet read is ~3 HTTP requests
                r = read_one(mid, rf, prim, sec)
                LIMITER.ok()
                return mid, r, None
            except Exception as e:
                if is_429(e):
                    LIMITER.hit_429(e)
                    continue
                tries += 1
                if tries >= 3:
                    return mid, None, f"{type(e).__name__}:{str(e)[:60]}"
                time.sleep(1.0 * tries)
        return mid, None, "retries-exhausted"

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = [ex.submit(work, it) for it in todo]
        for f in as_completed(futs):
            mid, res, err = f.result()
            with _lock:
                done[0] += 1
                if err:
                    rej.append((mid, err))
                else:
                    n, p, s, d = res
                    if ncan is None and len(P) >= 40:
                        from collections import Counter
                        ncan = Counter(len(v) for v in P.values()).most_common(1)[0][0]
                        for m2 in [m2 for m2, v in P.items() if len(v) != ncan]:
                            rej.append((m2, f"rowcount:{len(P[m2])}!={ncan}"))
                            P.pop(m2); S.pop(m2, None); D.pop(m2, None)
                        print(f"[{bench}] canonical rows = {ncan}", flush=True)
                    if ncan is not None and n != ncan:
                        rej.append((mid, f"rowcount:{n}!={ncan}"))
                    elif not np.all(np.isin(p, (0.0, 1.0))):
                        rej.append((mid, "non-binary-primary"))
                    else:
                        P[mid] = p.astype(np.uint8)
                        if s is not None:
                            S[mid] = s
                        D[mid] = d
                if done[0] % 100 == 0:
                    el = time.time() - t0
                    r = done[0] / max(el, 1e-9)
                    print(f"[{bench}] {done[0]}/{len(todo)} ok={len(P)} rej={len(rej)} "
                          f"{r:.1f}/s eta={(len(todo)-done[0])/max(r,1e-9)/60:.1f}min "
                          f"{LIMITER.stats()}", flush=True)
                    save(out, P, S, D)
    save(out, P, S, D)
    json.dump(rej, open(os.path.join(RAW, f"{bench}_rejects.json"), "w"))
    print(f"[{bench}] DONE models={len(P)} rejected={len(rej)} rows={ncan} "
          f"{(time.time()-t0)/60:.1f}min", flush=True)


def save(path, P, S, D):
    ms = sorted(P)
    if not ms:
        return
    np.savez_compressed(
        path,
        models=np.array(ms, object),
        prim=np.stack([P[m] for m in ms]),
        sec=(np.stack([S[m] for m in ms]) if len(S) == len(ms) else np.array([])),
        dates=np.array([D.get(m, "") for m in ms], object),
    )


if __name__ == "__main__":
    # single-writer lock: two concurrent harvesters would race on the .npz and double
    # the request rate against an already tight API budget
    lock = os.path.join(RAW, ".harvest.lock")
    if os.path.exists(lock):
        pid = open(lock).read().strip()
        alive = os.path.exists(f"/proc/{pid}") or (
            os.system(f"kill -0 {pid} 2>/dev/null") == 0)
        if alive:
            sys.exit(f"another harvester is running (pid {pid}); refusing to start")
    open(lock, "w").write(str(os.getpid()))
    import atexit
    atexit.register(lambda: os.path.exists(lock) and os.remove(lock))

    man = json.load(open(os.path.join(SUB, "manifest_files.json")))
    print(f"manifest models: {len(man)}", flush=True)
    for b in (sys.argv[1:] or ["arc", "winogrande", "truthfulqa", "gsm8k", "hellaswag"]):
        harvest(b, man)
