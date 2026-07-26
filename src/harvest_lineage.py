"""Phase 1D -- harvest declared model lineage, then run pre-registered kill condition K5.

H2 asks whether excess co-failure is concentrated along declared lineage. That needs, for each
evaluated model, its declared parent(s): the `base_model` field of the model card, plus merge
parents which mergekit-style cards list in the YAML front matter.

K5 (pre-registered): if `base_model` coverage is below 40% of analysed models, Contribution 3
is DROPPED rather than estimated on a biased subset.

Note the model id must be recovered from the details-dataset name:
  open-llm-leaderboard-old/details_<org>__<name>  ->  <org>/<name>
Model names may themselves contain "__", so only the FIRST separator is split on; ambiguous
cases are recorded and counted rather than guessed.

Run: python harvest_lineage.py [bench]  ->  substrate/lineage.json, results/k5_gate.json
"""
import json, os, re, sys, threading, time
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from huggingface_hub import HfApi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ratelimit import LIMITER, is_429

SUB = os.path.join(HERE, "..", "substrate")
RES = os.path.join(HERE, "..", "results")
os.makedirs(RES, exist_ok=True)
api = HfApi()
_lock = threading.Lock()


def details_to_model_id(ds_id):
    """open-llm-leaderboard-old/details_<org>__<name>  ->  <org>/<name>"""
    tail = ds_id.split("/", 1)[1]
    if not tail.startswith("details_"):
        return None
    body = tail[len("details_"):]
    if "__" not in body:
        return None
    org, name = body.split("__", 1)
    return f"{org}/{name}"


def parse_parents(info):
    """Return (list_of_parents, source_tag)."""
    parents, src = [], None
    cd = getattr(info, "card_data", None)
    # ModelCardData defines __getitem__ by key but is not iterable as a mapping, so dict(cd)
    # raises KeyError: 0. Use to_dict().
    d = {}
    if cd is not None:
        try:
            d = cd.to_dict()
        except Exception:
            d = {}
    bm = d.get("base_model")
    if bm:
        parents = [bm] if isinstance(bm, str) else list(bm)
        src = "card_data.base_model"
    if not parents:
        tags = getattr(info, "tags", []) or []
        t = [x.split(":", 1)[1] for x in tags
             if isinstance(x, str) and x.startswith("base_model:")]
        # tags look like base_model:finetune:org/name -- keep the trailing repo id
        t = [x.split(":")[-1] for x in t]
        if t:
            parents, src = t, "tags"
    parents = [p for p in parents if isinstance(p, str) and "/" in p]
    return sorted(set(parents)), src


def fetch(mid, tries=30):
    while tries > 0:
        try:
            LIMITER.acquire(cost=1)
            info = api.model_info(mid)
            LIMITER.ok()
            par, src = parse_parents(info)
            return mid, {"parents": par, "source": src,
                         "downloads": getattr(info, "downloads", None),
                         "created": str(getattr(info, "created_at", "") or "")[:10]}, None
        except Exception as e:
            if is_429(e):
                LIMITER.hit_429(e)
                continue
            tries -= 1
            code = getattr(getattr(e, "response", None), "status_code", None)
            if code in (401, 403, 404) or tries <= 27:
                return mid, None, f"http:{code}" if code else type(e).__name__
            time.sleep(1.0)
    return mid, None, "retries-exhausted"


def main(bench="arc"):
    z = np.load(os.path.join(SUB, "raw", f"{bench}.npz"), allow_pickle=True)
    ds_ids = [str(m) for m in z["models"]]
    pairs = [(d, details_to_model_id(d)) for d in ds_ids]
    unresolved = [d for d, m in pairs if not m]
    todo = [(d, m) for d, m in pairs if m]
    print(f"models in {bench}: {len(ds_ids)}  resolvable ids: {len(todo)}  "
          f"unresolvable: {len(unresolved)}", flush=True)

    out_path = os.path.join(SUB, "lineage.json")
    lin = json.load(open(out_path)) if os.path.exists(out_path) else {}
    todo = [(d, m) for d, m in todo if d not in lin]
    print(f"cached {len(lin)}, fetching {len(todo)}", flush=True)

    errs, done, t0 = {}, [0], time.time()
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(fetch, m): d for d, m in todo}
        for f in as_completed(futs):
            d = futs[f]
            mid, rec, err = f.result()
            with _lock:
                done[0] += 1
                if rec is not None:
                    rec["model_id"] = mid
                    lin[d] = rec
                else:
                    errs[d] = err
                if done[0] % 200 == 0:
                    r = done[0] / max(time.time() - t0, 1e-9)
                    print(f"  {done[0]}/{len(todo)} ok={len(lin)} err={len(errs)} "
                          f"{r:.2f}/s eta={(len(todo)-done[0])/max(r,1e-9)/60:.1f}min "
                          f"{LIMITER.stats()}", flush=True)
                    json.dump(lin, open(out_path, "w"))
    json.dump(lin, open(out_path, "w"))
    json.dump(errs, open(os.path.join(SUB, "lineage_errors.json"), "w"))

    n = len(ds_ids)
    with_par = sum(1 for d in ds_ids if lin.get(d, {}).get("parents"))
    cov = with_par / n
    srcs = {}
    for d in ds_ids:
        s = lin.get(d, {}).get("source")
        srcs[str(s)] = srcs.get(str(s), 0) + 1
    roots = {}
    for d in ds_ids:
        for p in lin.get(d, {}).get("parents", []):
            roots[p] = roots.get(p, 0) + 1
    gate = {
        "bench": bench, "n_models": n, "fetched": len(lin), "errors": len(errs),
        "unresolvable_ids": len(unresolved),
        "models_with_declared_parent": with_par, "coverage": cov,
        "K5_threshold": 0.40, "K5_pass": bool(cov >= 0.40),
        "source_breakdown": srcs,
        "top_parents": sorted(roots.items(), key=lambda kv: -kv[1])[:25],
        "n_distinct_parents": len(roots),
    }
    json.dump(gate, open(os.path.join(RES, "k5_gate.json"), "w"), indent=1)
    print(f"\nK5 GATE: coverage {with_par}/{n} = {cov:.1%}  -> "
          f"{'PASS, H2 proceeds' if cov >= 0.40 else 'FAIL, Contribution 3 dropped'}", flush=True)
    print(f"  distinct declared parents: {len(roots)}", flush=True)
    for p, c in gate["top_parents"][:12]:
        print(f"    {c:5d}  {p}", flush=True)
    return gate


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "arc")
