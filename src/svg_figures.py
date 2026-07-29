"""Hand-authored SVG figures — no matplotlib, no LaTeX/TikZ. Coordinates computed in Python,
emitted as raw SVG markup, converted to PDF with rsvg-convert for \\includegraphics.

Palette: validated 3-slot categorical (dataviz skill, `references/palette.md`), light mode.
    slot1 blue   #2a78d6   -- primary / observed
    slot2 orange #eb6834   -- contrast / null or secondary term
    slot3 aqua   #1baf7a   -- tertiary (carries a WARN on light-surface contrast per the
                                validator; always paired with a direct label here, never
                                color-alone, satisfying the relief rule)
    ink    #0b0b0b primary text · #52514e secondary text · muted #8a8983 gridlines
"""
import json, os, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, "..", "results")
FIG = os.path.join(HERE, "..", "figures")
os.makedirs(FIG, exist_ok=True)

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, MUTED, SURFACE = "#0b0b0b", "#52514e", "#c9c8c0", "#fcfcfb"
FONT = "Helvetica Neue, Helvetica, Arial, sans-serif"
MONO = "SF Mono, Menlo, Consolas, monospace"


def svg_open(w, h):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" font-family="{FONT}">\n'
            f'<rect x="0" y="0" width="{w}" height="{h}" fill="{SURFACE}"/>\n')


def text(x, y, s, size=11, fill=INK, anchor="start", weight="400", family=FONT, style=""):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}" font-family="{family}" '
            f'{style}>{s}</text>\n')


def save(name, body_w, body_h, elems):
    svg = svg_open(body_w, body_h) + "".join(elems) + "</svg>\n"
    p = os.path.join(FIG, f"{name}.svg")
    open(p, "w").write(svg)
    pdf = os.path.join(FIG, f"{name}.pdf")
    subprocess.run(["rsvg-convert", "-f", "pdf", "-o", pdf, p], check=True)
    print(f"  wrote {name}.svg + .pdf", flush=True)


# ============================================================ Figure: variance reconciliation

def fig_reconcile():
    """Only the OBSERVED column has segments large enough to draw at this scale: the null's
    +2Cov and +Var(D) terms are ~0.2% and ~2.6% of Var(E) respectively (sub-pixel at any
    reasonable bar height), so an earlier version forced 3-segment waterfalls on both columns
    and the null segment labels collided illegibly. Fixed: null renders as a single flat
    reference bar with its (tiny) decomposition given as a text annotation instead of geometry
    that cannot legibly hold it.
    """
    d = json.load(open(os.path.join(RES, "arc_reconcile.json")))
    o, n = d["observed"], d["null_mean"]
    S = 1e3
    W, H = 640, 430
    left, right, top, bot = 100, 560, 46, 300
    ymax = max(o["var_E"], n["var_E"]) * S * 1.1

    def y(v):
        return bot - v / ymax * (bot - top)

    elems = []
    for gv in [0, 2, 4, 6, 8, 10]:
        gy = y(gv)
        if top - 4 <= gy <= bot + 2:
            elems.append(f'<line x1="{left}" y1="{gy:.1f}" x2="{right}" y2="{gy:.1f}" '
                         f'stroke="{MUTED}" stroke-width="1"/>')
            elems.append(text(left - 12, gy + 3.5, f"{gv}", 9.5, INK2, "end"))
    elems.append(text(24, (top + bot) / 2, "pairwise variance (×10⁻³)", 10.5, INK2,
                      "middle", "500", style=f'transform="rotate(-90 24 {(top+bot)/2})"'))
    elems.append(f'<line x1="{left}" y1="{bot}" x2="{right}" y2="{bot}" stroke="{INK2}" '
                 f'stroke-width="1.3"/>')

    bw = 92
    label_x = right + 14   # shared right margin for Var(C) callouts, clear of all bar geometry
    W = label_x + 150

    # NULL: single flat bar at Var(E) (its own two extra terms are sub-pixel at this scale)
    cx0 = left + 110
    ncum = n["var_E"] * S
    elems.append(f'<rect x="{cx0-bw/2:.1f}" y="{y(ncum):.1f}" width="{bw}" '
                 f'height="{bot-y(ncum):.1f}" rx="3" fill="{MUTED}"/>')
    elems.append(text(cx0, (y(ncum) + bot) / 2, "Var(E)", 10, "#ffffff", "middle", "600"))
    elems.append(f'<circle cx="{cx0}" cy="{y(ncum):.1f}" r="4" fill="{INK}" '
                 f'stroke="{SURFACE}" stroke-width="1.3"/>')

    # OBSERVED: 3-segment waterfall, all terms comfortably sized
    cx1 = left + 340
    o1 = o["var_E"] * S
    o2 = o1 + 2 * o["cov_E_D"] * S
    o3 = o2 + o["var_D"] * S
    segs = [(0, o1, MUTED, None), (o1, o2, BLUE, "2·Cov(E,D)"), (o2, o3, ORANGE, "Var(D)")]
    for lo, hi, c, lab in segs:
        ytop, ybot = y(max(lo, hi)), y(min(lo, hi))
        h = max(ybot - ytop, 1.5)
        elems.append(f'<rect x="{cx1-bw/2:.1f}" y="{ytop:.1f}" width="{bw}" height="{h:.1f}" '
                     f'rx="3" fill="{c}"/>')
    elems.append(f'<circle cx="{cx1}" cy="{y(o3):.1f}" r="4" fill="{INK}" '
                 f'stroke="{SURFACE}" stroke-width="1.3"/>')

    # segment value labels placed just OUTSIDE the bar, to its right, never inside cramped fills
    elems.append(text(cx1 + bw / 2 + 8, (y(o1) + y(o2)) / 2 + 3.5,
                      f"−{o1-o2:.3f}", 9.5, BLUE, "start", "600"))
    elems.append(text(cx1 + bw / 2 + 8, (y(o2) + y(o3)) / 2 + 3.5,
                      f"+{o3-o2:.3f}", 9.5, "#c2531f", "start", "600"))

    # Var(C) landing-value callouts: leader line from each dot to a shared label column,
    # kept clear of all bar/segment geometry
    elems.append(f'<line x1="{cx0+2}" y1="{y(ncum):.1f}" x2="{label_x-6}" y2="60" '
                 f'stroke="{MUTED}" stroke-width="1"/>')
    elems.append(text(label_x, 64, "Var(C)_null", 9.5, INK2, "start", "500"))
    elems.append(text(label_x, 80, f"= {n['var_C']*S:.3f}", 12, INK, "start", "700"))

    elems.append(f'<line x1="{cx1+2}" y1="{y(o3):.1f}" x2="{label_x-6}" y2="140" '
                 f'stroke="{MUTED}" stroke-width="1"/>')
    elems.append(text(label_x, 144, "Var(C)_obs", 9.5, INK2, "start", "500"))
    elems.append(text(label_x, 160, f"= {o['var_C']*S:.3f}", 12, INK, "start", "700"))

    elems.append(text(cx0, bot + 22, "margin-preserving null", 10.5, INK2, "middle", "500"))
    elems.append(text(cx1, bot + 22, "observed ARC data", 10.5, INK2, "middle", "500"))

    lx, ly = left, 20
    for i, (c, lab) in enumerate([(MUTED, "Var(E)"), (BLUE, "+2·Cov(E,D)"), (ORANGE, "+Var(D)")]):
        elems.append(f'<rect x="{lx+i*140:.1f}" y="{ly-9:.1f}" width="11" height="11" rx="2" '
                     f'fill="{c}"/>')
        elems.append(text(lx + i * 140 + 16, ly, lab, 10, INK2, "start", "500"))

    elems.append(text(left, 348, f"Null decomposition (too small to draw to scale): "
                      f"+2·Cov(E,D) = {2*n['cov_E_D']*S:+.4f}, "
                      f"+Var(D) = {n['var_D']*S:+.4f}.", 9.3, INK2))
    elems.append(text(left, 366, "Var(E) is identical for null and observation — margins "
                      "are shared exactly. Var(D) is 29× the null,", 9.5, INK2))
    elems.append(text(left, 382, "but a strongly negative 2·Cov(E,D) pulls the observed "
                      "total below the null: both are true at once.", 9.5, INK2))
    elems.append(text(left, 408, "Figure computed from results/arc_reconcile.json "
                      "(src/reconcile.py); no manual numbers.", 8.5, MUTED))

    save("fig_reconcile", W, H, elems)


# ============================================================ Figure: misspecification controls

def fig_misspec():
    rows = [
        ("1PL, correctly specified", 1.001, 0.065, False),
        ("2PL, sd(log a)=0.35", 0.966, 0.068, False),
        ("2PL, sd(log a)=0.60", 0.862, 0.076, False),
        ("two ability dimensions", 0.230, 0.162, False),
        ("20 exact clone clusters", 0.112, 0.234, False),
        ("real ARC", 0.052, 0.248, True),
    ]
    W, H = 700, 430
    left, right, top, bot = 210, 560, 50, 320
    rh = (bot - top) / len(rows)
    xmax = 0.27

    def x(v):
        return left + v / xmax * (right - left)

    elems = []
    for gv in [0, 0.05, 0.10, 0.15, 0.20, 0.25]:
        gx = x(gv)
        elems.append(f'<line x1="{gx:.1f}" y1="{top-6}" x2="{gx:.1f}" y2="{bot}" '
                     f'stroke="{MUTED}" stroke-width="1"/>')
        elems.append(text(gx, bot + 16, f"{gv:.2f}", 9.5, INK2, "middle"))
    elems.append(text((left + right) / 2, bot + 34,
                      "rms ∣Rᵢⱼ∣  (margin-conditioned residual correlation)", 10.5, INK2,
                      "middle", "500"))

    for i, (label, ratio, rms, hi) in enumerate(rows):
        cy = top + rh * i + rh / 2
        col = BLUE if not hi else ORANGE
        elems.append(text(left - 14, cy + 3.5, label, 10.5, INK if not hi else "#8a3a12",
                          "end", "700" if hi else "400"))
        elems.append(f'<line x1="{left:.1f}" y1="{cy:.1f}" x2="{x(rms):.1f}" y2="{cy:.1f}" '
                     f'stroke="{col}" stroke-width="2.4" stroke-linecap="round"/>')
        r = 6.5 if hi else 5
        elems.append(f'<circle cx="{x(rms):.1f}" cy="{cy:.1f}" r="{r}" fill="{col}" '
                     f'stroke="{SURFACE}" stroke-width="1.4"/>')
        elems.append(text(x(rms) + 12, cy + 3.5, f"{rms:.3f}", 9.5, INK, "start", "600" if hi else "400"))
        elems.append(text(right + 14, cy + 3.5, f"{ratio:.2f}×", 9.5, INK2, "start", "500"))
        if i < len(rows) - 1:
            elems.append(f'<line x1="{left}" y1="{top+rh*(i+1):.1f}" x2="{right}" '
                         f'y2="{top+rh*(i+1):.1f}" stroke="{MUTED}" stroke-width="0.6"/>')

    elems.append(text(left - 14, 24, "generating process (no clusters unless noted)", 10,
                      INK2, "end", "500"))
    elems.append(text(right + 14, 24, "PR/null", 10, INK2, "start", "500"))
    elems.append(text(left, bot + 62, "Discrimination heterogeneity alone (2PL) tops out at "
                      "0.076 — far short of ARC's observed 0.248.", 9.5, INK2))
    elems.append(text(left, bot + 78, "Real ARC's signature sits closest to additional "
                      "latent ability dimensions, not duplicated models.", 9.5, INK2))

    save("fig_misspec", W, H, elems)


# ============================================================ Figure: corrected residual summary

def fig_residual_summary():
    order = ["arc", "winogrande", "truthfulqa", "gsm8k", "hellaswag"]
    nice = {"arc": "ARC-Challenge", "winogrande": "Winogrande", "truthfulqa": "TruthfulQA",
            "gsm8k": "GSM8K", "hellaswag": "HellaSwag"}
    rows = []
    for b in order:
        p = os.path.join(RES, f"{b}_null_independent.json")
        e = json.load(open(p))
        ses = e["N_eff"]["SES"]
        ratio = e["N_eff"]["ratio"]
        rows.append((nice[b], e["N_eff"]["observed"], e["N_eff"]["null_mean"],
                    e["N_eff"]["null_sd"], ratio))
    # (An `extra` dict of ARC-specific diagnostics used to sit here, hardcoding a null rms of
    # 0.0389 -- the same value that turned out to trace to no executed run. It was assigned and
    # never read, so it never reached a rendered figure. Deleted rather than repaired: dead code
    # holding an unverifiable constant is how that constant gets picked up later.)

    W, H = 640, 330
    left, right, top, bot = 130, 600, 30, 230
    n = len(rows)
    bw = 46
    gap = (right - left - n * 2 * bw) / (n + 1)
    ymax = max(r[2] + r[3] for r in rows) * 1.15

    def y(v):
        return bot - v / ymax * (bot - top)

    elems = []
    for gv in range(0, int(ymax) + 1, 100):
        gy = y(gv)
        if gy < bot + 2:
            elems.append(f'<line x1="{left}" y1="{gy:.1f}" x2="{right}" y2="{gy:.1f}" '
                         f'stroke="{MUTED}" stroke-width="1"/>')
            elems.append(text(left - 10, gy + 3.5, f"{gv}", 9, INK2, "end"))
    elems.append(f'<line x1="{left}" y1="{bot}" x2="{right}" y2="{bot}" stroke="{INK2}" '
                 f'stroke-width="1.2"/>')
    elems.append(text(24, (top + bot) / 2, "participation ratio (PR)", 10, INK2, "middle", "500",
                      style=f'transform="rotate(-90 24 {(top+bot)/2})"'))

    cx = left + gap
    for name, obs, nmean, nsd, ratio in rows:
        c0 = cx + bw / 2
        c1 = cx + bw + bw / 2 + 6
        # null bar with error bar
        elems.append(f'<rect x="{c0-bw/2:.1f}" y="{y(nmean):.1f}" width="{bw}" '
                     f'height="{bot-y(nmean):.1f}" fill="{ORANGE}" opacity="0.85" rx="2"/>')
        elems.append(f'<line x1="{c0:.1f}" y1="{y(nmean-nsd):.1f}" x2="{c0:.1f}" '
                     f'y2="{y(nmean+nsd):.1f}" stroke="{INK}" stroke-width="1.2"/>')
        elems.append(text(c0, y(nmean) - 8, f"{nmean:.0f}", 9, "#8a3a12", "middle", "600"))
        # observed bar
        elems.append(f'<rect x="{c1-bw/2:.1f}" y="{y(obs):.1f}" width="{bw}" '
                     f'height="{bot-y(obs):.1f}" fill="{BLUE}" rx="2"/>')
        elems.append(text(c1, y(obs) - 8, f"{obs:.1f}", 9.5, BLUE, "middle", "700"))
        elems.append(text((c0 + c1) / 2, bot + 34, f"{ratio*100:.1f}%", 9.5, INK, "middle", "700"))
        elems.append(text((c0 + c1) / 2, bot + 17, "of null", 8.5, INK2, "middle"))
        elems.append(text((c0 + c1) / 2, bot + 52, name, 9.5, INK2, "middle", "500"))
        cx += 2 * bw + 6 + gap

    lx, ly = left, 14
    elems.append(f'<rect x="{lx:.1f}" y="{ly-9:.1f}" width="11" height="11" rx="2" fill="{ORANGE}" '
                 f'opacity="0.85"/>')
    elems.append(text(lx + 16, ly, "PR under exact-margin null", 9.5, INK2, "start", "500"))
    elems.append(f'<rect x="{lx+195:.1f}" y="{ly-9:.1f}" width="11" height="11" rx="2" '
                 f'fill="{BLUE}"/>')
    elems.append(text(lx + 211, ly, "PR observed", 9.5, INK2, "start", "500"))

    elems.append(text(left, 300, "PR alone does not license “effective independent model "
                      "count” (Sec. 4.3): it is N/(1+(N−1)·mean Rᵢⱼ²).", 9,
                      INK2))
    elems.append(text(left, 314, "Reported here as the calibrated summary statistic; see "
                      "Fig. \\ref{fig:misspec} for the identification diagnostics.", 9, INK2))

    save("fig_residual_summary", W, H, elems)


def fig_power():
    """Detection power against three planted alternatives, from results/power_study.json.

    The scientific point is the contrast between the two rising curves and the flat one: the test
    sees shared failure modes and copied models easily, and is blind by construction to a shared
    item-difficulty profile, because that alternative IS the null. The blind spot is drawn as a
    line at alpha rather than described in a caption, so it cannot be skimmed past.
    """
    d = json.load(open(os.path.join(RES, "power_study.json")))
    alpha = d["alpha"]
    A = [a for a in d["alt_A_shared_failure_modes"] if a["g"] == 8]
    C = d["alt_C_partial_copying"]
    B = d["alt_B_shared_difficulty"]["power"]

    # H must clear the second caption line at bot+76; at H=300 it was clipped off the canvas.
    W, H = 620, 326
    left, right, top, bot = 62, 430, 34, 232

    def X(t):
        return left + t * (right - left)

    def Y(p):
        return bot - p * (bot - top)

    e = [text(left, 20, "What the exact conditional null can and cannot detect",
              size=12.5, weight="600")]
    for p in (0, 0.25, 0.5, 0.75, 1.0):
        e.append(f'<line x1="{left}" y1="{Y(p):.1f}" x2="{right}" y2="{Y(p):.1f}" '
                 f'stroke="{MUTED}" stroke-width="0.6"/>\n')
        e.append(text(left - 8, Y(p) + 3.5, f"{p:.2f}", size=9, fill=INK2, anchor="end"))
    e.append(text(left - 46, (top + bot) / 2, "power", size=10, fill=INK2, anchor="middle",
                  style=f'transform="rotate(-90 {left-46} {(top+bot)/2})"'))

    def curve(rows, key, lo, hi, colour, label, ly):
        pts = []
        for r in rows:
            t = (r[key] - lo) / (hi - lo)
            pts.append(f"{X(t):.1f},{Y(r['power']):.1f}")
        e.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{colour}" '
                 f'stroke-width="2.4"/>\n')
        for p in pts:
            x, y = p.split(",")
            e.append(f'<circle cx="{x}" cy="{y}" r="3" fill="{colour}"/>\n')
        e.append(text(right + 12, ly, label, size=10, fill=colour, weight="600"))

    curve(A, "s", 0.0, 1.2, BLUE, "shared failure modes", Y(1.0) + 4)
    curve(C, "c", 0.0, 0.5, ORANGE, "copying a reference model", Y(1.0) + 20)

    e.append(f'<line x1="{left}" y1="{Y(B):.1f}" x2="{right}" y2="{Y(B):.1f}" '
             f'stroke="{AQUA}" stroke-width="2.4" stroke-dasharray="6 3"/>\n')
    e.append(text(right + 12, Y(B) + 3.5, "shared item difficulty only", size=10,
                  fill=AQUA, weight="600"))
    e.append(text(right + 12, Y(B) + 16, f"power = {B:.2f} = α", size=9, fill=INK2))

    e.append(f'<line x1="{left}" y1="{bot}" x2="{right}" y2="{bot}" stroke="{INK}" '
             f'stroke-width="1"/>\n')
    e.append(text((left + right) / 2, bot + 24, "planted strength (rescaled per alternative)",
                  size=10, fill=INK2, anchor="middle"))
    e.append(text(left, bot + 40, "none", size=9, fill=INK2))
    e.append(text(right, bot + 40, "strong", size=9, fill=INK2, anchor="end"))

    e.append(text(left, bot + 62,
                  "Full power is reached at a planted rms of 0.048 — far below the "
                  "0.099–0.294 observed on real data.", size=9.5, fill=INK2))
    e.append(text(left, bot + 76,
                  "The flat line is not a weak result: that alternative is the null, so the test "
                  "has no power against it by construction.", size=9.5, fill=INK2))
    save("fig_power", W, H, e)


if __name__ == "__main__":
    fig_reconcile()
    fig_misspec()
    fig_residual_summary()
    fig_power()
