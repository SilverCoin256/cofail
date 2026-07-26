"""Command line interface.

    cofail selftest                     verify the propositions on synthetic data
    cofail neff  --matrix F.npy         effective number of independent models
    cofail excess --matrix F.npy        what an independence baseline reports vs the margins

`--matrix` accepts .npy or .npz (first array, or the array named by --key), shaped
(n_models, n_items), binary, 1 = model failed item.
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
    print("first line is not evidence of shared behaviour. Use `cofail neff` instead.")
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

    q = sub.add_parser("neff", help="effective number of independent models")
    common(q)
    q.add_argument("--n-null", type=int, default=40)
    q.add_argument("--no-calibrate", action="store_true")
    q.add_argument("--seed", type=int, default=0)
    q.add_argument("--json", default=None, help="write the result to this path")
    q.add_argument("-v", "--verbose", action="store_true")
    q.set_defaults(fn=_cmd_neff)

    q = sub.add_parser("excess", help="reported excess vs what the margins force")
    common(q)
    q.set_defaults(fn=_cmd_excess)

    q = sub.add_parser("selftest", help="verify the propositions on synthetic data")
    q.set_defaults(fn=_cmd_selftest)

    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
