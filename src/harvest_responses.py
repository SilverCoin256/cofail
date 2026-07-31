"""Phase 1, tier 2: reconstruct each model's CHOSEN answer, not just correctness.

Needed to test Proposition 3 / H4 (PREREGISTRATION.md AMENDMENT 2), which concern the
multi-category statistic used by prior work: P(same wrong answer | both models wrong).

The archive stores `predictions` = per-choice log-likelihoods, so the chosen option is
argmax(predictions). The correct option is NOT reliably stored -- in the 2024 schema the
`gold` and `gold_index` columns are empty. It is instead RECOVERED: for any model that
answered item m correctly (acc == 1), argmax(predictions) IS the gold index. With hundreds
of models, essentially every item is answered correctly by someone.

That recovery is checked, not assumed: models correct on the same item must agree on the
argmax, and the recovered gold must reproduce each model's `acc` out of sample. Both
diagnostics are written alongside the tensor: substrate/raw/<bench>_resp_rejects.json and
substrate/raw/<bench>_resp_sample.json. The gold-recovery validation itself (agreement among
correct models, and the fraction of cells reproducing each model's reported accuracy) is
emitted by src/responses_analysis.py into results/<bench>_responses.json under `gold_recovery`.

Cost note: `predictions` is ~60x the bytes of `acc`, so this runs on a subsample.
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
fs = HfFileSystem()
_lock = threading.Lock()

MAX_CHOICES = 8          # ARC/HellaSwag items have <= 5; guard against ragged rows
SENTINEL = -1            # unparseable / ragged row


def read_choice(mid, rfile):
    """Return (chosen_index array int8, acc array uint8, n_choices array int8, date)."""
    pf = pq.ParquetFile(fs.open(f"datasets/{mid}/{rfile}", "rb"))
    names = set(pf.schema_arrow.names)
    if "predictions" not in names:
        raise KeyError("no predictions column")
    cols = ["predictions"] + (["metrics"] if "metrics" in names else ["acc"])
    tb = pf.read(columns=cols)
    preds = tb.column("predictions").to_pylist()
    if "metrics" in names:
        recs = tb.column("metrics").to_pylist()
        acc = [float((r or {}).get("acc", np.nan)) for r in recs]
    else:
        acc = [float(x) for x in tb.column("acc").to_pylist()]
    n = len(preds)
    ch = np.full(n, SENTINEL, dtype=np.int8)
    nc = np.zeros(n, dtype=np.int8)
    for k, p in enumerate(preds):
        if not p or len(p) < 2 or len(p) > MAX_CHOICES:
            continue
        arr = np.asarray(p, dtype=np.float64)
        if not np.all(np.isfinite(arr)):
            continue
        ch[k] = int(np.argmax(arr))
        nc[k] = len(arr)
    return ch, np.asarray(acc, dtype=np.float32), nc, rfile.split("/")[0][:10]


def harvest(bench, models, manifest):
    out = os.path.join(RAW, f"{bench}_resp.npz")
    CH, AC, NC, D = {}, {}, {}, {}
    if os.path.exists(out):
        z = np.load(out, allow_pickle=True)
        for k, m in enumerate(z["models"]):
            CH[str(m)] = z["choice"][k]; AC[str(m)] = z["acc"][k]
            NC[str(m)] = z["nchoice"][k]; D[str(m)] = str(z["dates"][k])
        print(f"[{bench}-resp] resuming, {len(CH)} cached", flush=True)
    todo = [(m, manifest[m][bench]) for m in models
            if m in manifest and bench in manifest[m] and m not in CH]
    print(f"[{bench}-resp] todo {len(todo)}", flush=True)
    rej, done, t0 = [], [0], time.time()

    def work(it):
        mid, rf = it
        tries = 0
        while tries < 40:
            try:
                LIMITER.acquire(cost=3)
                r = read_choice(mid, rf)
                LIMITER.ok()
                return mid, r, None
            except Exception as e:
                if is_429(e):
                    LIMITER.hit_429(e); continue
                tries += 1
                if tries >= 3:
                    return mid, None, f"{type(e).__name__}:{str(e)[:60]}"
                time.sleep(tries)
        return mid, None, "retries-exhausted"

    ncan = None
    with ThreadPoolExecutor(max_workers=int(os.environ.get("MM_WORKERS", "6"))) as ex:
        for f in as_completed([ex.submit(work, it) for it in todo]):
            mid, r, err = f.result()
            with _lock:
                done[0] += 1
                if err:
                    rej.append((mid, err))
                else:
                    ch, ac, nc, d = r
                    if ncan is None and CH:
                        ncan = len(next(iter(CH.values())))
                    if ncan is None:
                        ncan = len(ch)
                    if len(ch) != ncan:
                        rej.append((mid, f"rowcount:{len(ch)}!={ncan}"))
                    else:
                        CH[mid], AC[mid], NC[mid], D[mid] = ch, ac, nc, d
                if done[0] % 100 == 0:
                    r_ = done[0] / max(time.time() - t0, 1e-9)
                    print(f"[{bench}-resp] {done[0]}/{len(todo)} ok={len(CH)} rej={len(rej)} "
                          f"{r_:.2f}/s eta={(len(todo)-done[0])/max(r_,1e-9)/60:.1f}min "
                          f"{LIMITER.stats()}", flush=True)
                    save(out, CH, AC, NC, D)
    save(out, CH, AC, NC, D)
    json.dump(rej, open(os.path.join(RAW, f"{bench}_resp_rejects.json"), "w"))
    print(f"[{bench}-resp] DONE models={len(CH)} rejected={len(rej)}", flush=True)


def save(path, CH, AC, NC, D):
    ms = sorted(CH)
    if not ms:
        return
    np.savez_compressed(path, models=np.array(ms, object),
                        choice=np.stack([CH[m] for m in ms]),
                        acc=np.stack([AC[m] for m in ms]),
                        nchoice=np.stack([NC[m] for m in ms]),
                        dates=np.array([D[m] for m in ms], object))


def recover_gold(choice, acc):
    """Recover the correct option per item from models that answered it correctly.

    Returns (gold int8 array, agreement_rate, n_recovered). Items where correct models
    disagree on the argmax are a red flag and are reported, not silently resolved.
    """
    N, M = choice.shape
    gold = np.full(M, SENTINEL, dtype=np.int8)
    agree, cnt = [], 0
    for m in range(M):
        ok = (acc[:, m] == 1) & (choice[:, m] >= 0)
        if not ok.any():
            continue
        v = choice[ok, m]
        vals, c = np.unique(v, return_counts=True)
        gold[m] = int(vals[np.argmax(c)])
        agree.append(c.max() / c.sum())
        cnt += 1
    return gold, (float(np.mean(agree)) if agree else float("nan")), cnt


if __name__ == "__main__":
    bench = sys.argv[1] if len(sys.argv) > 1 else "arc"
    n_sub = int(sys.argv[2]) if len(sys.argv) > 2 else 600
    man = json.load(open(os.path.join(SUB, "manifest_files.json")))
    z = np.load(os.path.join(RAW, f"{bench}.npz"), allow_pickle=True)
    pool = [str(m) for m in z["models"]]
    rng = np.random.default_rng(20260726)
    sel = sorted(rng.choice(pool, size=min(n_sub, len(pool)), replace=False).tolist())
    json.dump(sel, open(os.path.join(RAW, f"{bench}_resp_sample.json"), "w"))
    harvest(bench, sel, man)
