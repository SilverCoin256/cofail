"""Audit the ONE assumption the whole substrate rests on: that item identity is the row index.

WHY THIS FILE EXISTS. `src/harvest_matrix.py` states that row order was verified identical for
14 sampled models and cites this script as the evidence. **The script was not in the repository.**
A reviewer following that pointer found nothing, which makes the load-bearing assumption of the
entire dataset unverifiable from the release. This is that script, and it audits a much larger
sample than 14 because the datasheet flagged the original as a spot check rather than a proof.

WHAT COULD GO WRONG. Every matrix here is built by stacking per-model outcome vectors and treating
column m as "the same item" across models. If any model's parquet stores its rows in a different
order, that model's outcomes are silently permuted relative to everyone else's. The effect is not
noise: a permuted row looks independent of every other row, so undetected misalignment biases all
correlation estimates TOWARD ZERO, i.e. toward the null. The paper's headline is an excess over the
null, so this failure mode would understate the result rather than manufacture it — but it would
also mean the substrate is not what it claims to be.

THE COMPARISON IS NOT TRIVIAL, because the archive spans three schema generations:
  gen A (early Jul 2023) : `example` = dataset ID          , `query` = question text
  gen B (late Jul 2023+) : `example` = question text
  gen C (2024+)          : `example` = question text, no `query`, metrics nested
So a raw `example` comparison across generations is meaningless — that is the exact bug that
produced an empty intersection during Phase 0. We therefore normalise to a question-text hash:
gen A reads `query`, gen B/C read `example`; both are whitespace-collapsed, lowercased and MD5'd.
A model is ALIGNED if its full sequence of hashes equals the reference model's, position by
position.

Run: ./.venv/bin/python src/audit_roworder.py [bench] [n_models]
  -> results/audit_roworder_<bench>.json
"""
import hashlib, json, os, re, sys
from collections import Counter

import pyarrow.parquet as pq
from huggingface_hub import HfFileSystem

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ratelimit import LIMITER, is_429

SUB = os.path.join(HERE, "..", "substrate")
RES = os.path.join(HERE, "..", "results")
fs = HfFileSystem()
WS = re.compile(r"\s+")


def norm_hash(s):
    return hashlib.md5(WS.sub(" ", str(s).strip().lower()).encode("utf-8")).hexdigest()[:16]


def item_keys(mid, rfile):
    """Ordered list of normalised question-text hashes, plus which schema generation was used."""
    pf = pq.ParquetFile(fs.open(f"datasets/{mid}/{rfile}", "rb"))
    names = set(pf.schema_arrow.names)
    if "query" in names:
        col, gen = "query", "A(query)"
    elif "example" in names:
        col, gen = "example", "B/C(example)"
    else:
        raise KeyError(f"no identity column; have {sorted(names)[:8]}")
    vals = pf.read(columns=[col]).column(col).to_pylist()
    # gen A `example` holds a dataset id, so `query` is the only cross-generation-comparable
    # field. Where both exist we deliberately prefer `query`.
    return [norm_hash(v) for v in vals], gen


def main(bench="arc", n_models=120):
    man = json.load(open(os.path.join(SUB, "manifest_files.json")))
    # manifest layout: {model_id: [{bench: path, ...}]}
    cand = []
    for mid, fl in man.items():
        rec = fl[0] if isinstance(fl, list) and fl and isinstance(fl[0], dict) else fl
        if not isinstance(rec, dict):
            continue
        path = rec.get(bench)
        if isinstance(path, str):
            cand.append((mid, path, path.split("/")[0][:10]))     # (model, file, snapshot date)

    # Sample EVENLY ACROSS THE DATE RANGE rather than taking the first N alphabetically. The
    # failure mode being audited is schema drift over time, so a sample concentrated in one month
    # would be nearly uninformative -- it is the July-2023 rows that use the other schema.
    cand.sort(key=lambda t: t[2])
    if len(cand) > n_models:
        step = len(cand) / n_models
        cand = [cand[int(i * step)] for i in range(n_models)]
    entries = [(m, f) for m, f, _ in cand]
    dates = [d for _, _, d in cand]
    print(f"[{bench}] auditing row order across {len(entries)} models, "
          f"snapshots {dates[0]} .. {dates[-1]}", flush=True)

    ref_keys, ref_mid, ref_gen = None, None, None
    aligned, mismatched, errors, gens = [], [], [], Counter()

    for i, (mid, rfile) in enumerate(entries):
        try:
            LIMITER.acquire()
            keys, gen = item_keys(mid, rfile)
        except Exception as e:
            if is_429(e):
                LIMITER.penalise()
            errors.append({"model": mid, "error": f"{type(e).__name__}: {str(e)[:90]}"})
            continue
        gens[gen] += 1
        if ref_keys is None:
            ref_keys, ref_mid, ref_gen = keys, mid, gen
            aligned.append(mid)
            print(f"  reference: {mid} ({gen}, {len(keys)} items)", flush=True)
            continue
        if len(keys) != len(ref_keys):
            mismatched.append({"model": mid, "reason": "length",
                               "n": len(keys), "ref_n": len(ref_keys), "gen": gen})
        elif keys != ref_keys:
            bad = [j for j, (a, b) in enumerate(zip(keys, ref_keys)) if a != b]
            mismatched.append({"model": mid, "reason": "order", "n_positions_differing": len(bad),
                               "first_differing_positions": bad[:10], "gen": gen})
        else:
            aligned.append(mid)
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(entries)}  aligned={len(aligned)} "
                  f"mismatch={len(mismatched)} err={len(errors)}", flush=True)

    checked = len(aligned) + len(mismatched)
    out = {
        "benchmark": bench, "n_requested": len(entries), "n_checked": checked,
        "reference_model": ref_mid, "reference_gen": ref_gen,
        "n_items": len(ref_keys) if ref_keys else 0,
        "schema_generations_seen": dict(gens),
        "n_aligned": len(aligned), "n_mismatched": len(mismatched),
        "alignment_rate": (len(aligned) / checked) if checked else None,
        "mismatches": mismatched[:40], "n_errors": len(errors), "errors": errors[:20],
    }
    os.makedirs(RES, exist_ok=True)
    json.dump(out, open(os.path.join(RES, f"audit_roworder_{bench}.json"), "w"), indent=1)

    print(f"\n[{bench}] {len(aligned)}/{checked} models row-order identical to {ref_mid} "
          f"({len(ref_keys) if ref_keys else 0} items); {len(errors)} unreadable")
    print(f"  schema generations covered: {dict(gens)}")
    if mismatched:
        print(f"  !! {len(mismatched)} MISMATCHED -- the row-index assumption does NOT hold "
              f"universally; see results/audit_roworder_{bench}.json")
    else:
        print("  no mismatches: the row-index assumption holds on every model checked")


if __name__ == "__main__":
    b = sys.argv[1] if len(sys.argv) > 1 else "arc"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 120
    main(b, n)
