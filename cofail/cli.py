"""Command line interface.

    cofail audit    --matrix F.npy      run every check below and print one report
    cofail excess   --matrix F.npy      what an independence baseline reports vs the margins
    cofail pr       --matrix F.npy      participation ratio of the conditioned excess spectrum
    cofail selftest                     verify the propositions on synthetic data

`--matrix` accepts .npy or .npz (first array, or the array named by --key), shaped
(n_models, n_items), binary, 1 = model failed item.

NOTE ON `pr`. This command was previously called `neff` and described as the "effective number
of independent models". That interpretation is withdrawn and the old name is kept only as a
deprecated alias. The participation ratio is algebraically N/(1+(N-1)*mean(R_ij^2)), i.e. a
monotone function of the mean squared residual correlation, so it cannot distinguish one weak
global factor from many tight clusters and does not count anything. Use it as a summary of
residual correlation, not as a count. `cofail audit` reports the diagnostics that can
discriminate those cases.
"""
import argparse
import json
import sys

import numpy as np

from . import core


def _load(path, key=None):
    if path.endswith(".npz"):
        z = np.load(path, allow_pickle=True)
        k = key or list(z.files)[0]
        return z[k]
    return np.load(path)


def _cmd_neff(a):
    if getattr(a, "deprecated", False):
        print("warning: `cofail neff` is deprecated -- the name asserts an 'effective number of\n"
              "         independent models' interpretation that this project withdrew. Use\n"
              "         `cofail pr`, and see `cofail audit` for diagnostics that discriminate.\n",
              file=sys.stderr)
    F = _load(a.matrix, a.key)
    rng = np.random.default_rng(a.seed)
    r = core.neff(F, calibrate=not a.no_calibrate, n_null=a.n_null, rng=rng,
                  progress=a.verbose)
    print(r)
    if a.json:
        json.dump(r.as_dict(), open(a.json, "w"), indent=1)
    return 0


def _cmd_excess(a):
    F = _load(a.matrix, a.key)
    naive = core.naive_excess(F)
    art = core.marginal_artifact(F)
    print(f"reported excess over independence : {naive:+.9f}")
    print(f"forced by the item margins alone  : {art:+.9f}")
    print(f"residual carrying any information : {naive - art:+.3e}")
    print("\nThe mean pairwise co-failure rate is a function of the item margins alone, so the")
    print("first line is not evidence of shared behaviour. Use `cofail audit` instead.")
    return 0


def _cmd_audit(a):
    """Everything a user should check before reporting a model-agreement number."""
    F = _load(a.matrix, a.key)
    F = np.ascontiguousarray(F).astype(np.uint8)
    rng = np.random.default_rng(a.seed)
    N, M = F.shape
    out = {"n_models": int(N), "n_items": int(M)}
    print(f"cofail audit -- {N} models x {M} items\n" + "=" * 58)

    naive, art = core.naive_excess(F), core.marginal_artifact(F)
    out["naive_excess"], out["forced_by_margins"] = float(naive), float(art)
    print("\n1. Is your reported excess a margin artifact?")
    print(f"     reported over independence : {naive:+.9f}")
    print(f"     forced by item margins     : {art:+.9f}")
    print(f"     residual                   : {naive - art:+.3e}")
    print("     -> mean co-failure carries no information about model similarity.")

    print("\n2. How redundant is your model population?")
    A = 1 - F.astype(np.float32)
    counts = {}
    for thr in (0.99, 0.95, 0.90):
        order = np.argsort(-A.mean(1))
        kept = []
        for i in order:
            if not kept:
                kept.append(int(i)); continue
            K = np.array(kept)
            ag = (A[i] @ A[K].T + (1 - A[i]) @ (1 - A[K]).T) / M
            if ag.max() < thr:
                kept.append(int(i))
        counts[thr] = len(kept)
        print(f"     dedup at agreement >= {thr}: {len(kept)}/{N} kept "
              f"({100*(N-len(kept))/N:.0f}% removed)")
    out["dedup_kept"] = {str(k): v for k, v in counts.items()}
    if (N - counts[0.95]) / N > 0.2:
        print("     -> WARNING: >20% removed at 0.95. Rerun your analysis deduplicated.")

    print("\n3. What survives conditioning, and how many dimensions?")
    r = core.neff(F, calibrate=True, n_null=a.n_null, rng=rng)
    out["pr_observed"] = float(r.neff)
    out["pr_null"] = float(r.null_mean) if r.null_mean is not None else None
    out["pr_ratio"] = float(r.ratio) if r.ratio is not None else None
    print("\n".join("     " + ln for ln in str(r).splitlines()))
    print("     -> participation ratio is NOT a count of independent models; see module docs.")

    print("\n4. What this test cannot see.")
    print("     If every model finds the same items hard and differs only in overall ability,")
    print("     that case IS the null and this test has no power against it. A null result")
    print("     here does not mean the models are independent.")

    if a.json:
        json.dump(out, open(a.json, "w"), indent=1)
    return 0


def _cmd_selftest(a):
    rng = np.random.default_rng(0)
    n, m = 300, 500
    al, be = rng.normal(0, 1.2, n), rng.normal(0, 1.5, m)
    F = (rng.random((n, m)) < 1 / (1 + np.exp(-(al[:, None] + be[None, :])))).astype(np.uint8)
    X = core.curveball(F, rng=rng)
    ok = []
    ok.append(("margins preserved by curveball", core.margins_preserved(F, X)))
    ok.append(("Prop 1: mean co-failure invariant",
               abs(core.mean_cofail(F) - core.mean_cofail(X)) < 1e-15))
    ok.append(("Prop 2: closed form matches measurement",
               abs(core.naive_excess(F) - core.marginal_artifact(F)) < 1e-12))
    P, err = core.fit_margin_model(F)
    ok.append(("margin model reproduces margins", err < 1e-8))
    for name, good in ok:
        print(f"  {'PASS' if good else 'FAIL'}  {name}")
    return 0 if all(g for _, g in ok) else 1


def main(argv=None):
    p = argparse.ArgumentParser(prog="cofail", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(q):
        q.add_argument("--matrix", required=True, help=".npy/.npz of a binary failure matrix")
        q.add_argument("--key", default=None, help="array name inside an .npz")

    q = sub.add_parser("audit", help="run every check and print one report")
    common(q)
    q.add_argument("--n-null", type=int, default=20)
    q.add_argument("--seed", type=int, default=0)
    q.add_argument("--json", default=None, help="write the report to this path")
    q.set_defaults(fn=_cmd_audit)

    # `neff` is the deprecated spelling; the name asserted an interpretation the paper withdrew.
    for name, helptext in (("pr", "participation ratio of the conditioned excess spectrum"),
                           ("neff", "deprecated alias for `pr`")):
        q = sub.add_parser(name, help=helptext)
        common(q)
        q.add_argument("--n-null", type=int, default=40)
        q.add_argument("--no-calibrate", action="store_true")
        q.add_argument("--seed", type=int, default=0)
        q.add_argument("--json", default=None, help="write the result to this path")
        q.add_argument("-v", "--verbose", action="store_true")
        q.set_defaults(fn=_cmd_neff, deprecated=(name == "neff"))

    q = sub.add_parser("excess", help="reported excess vs what the margins force")
    common(q)
    q.set_defaults(fn=_cmd_excess)

    q = sub.add_parser("selftest", help="verify the propositions on synthetic data")
    q.set_defaults(fn=_cmd_selftest)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
