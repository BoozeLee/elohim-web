"""Section VIII — The sigil: SVG geometry built from the measured constants.

Verbatim from the original `summoning_shard.py`. Math-comments preserved
exactly. The PRNG is `random.Random(seed)` — never `random.seed()`.
"""

from __future__ import annotations

import math
import random

from .core import FACTS, OUT, PHI, say, rule


def continued_fraction(x: float, terms: int) -> list:
    """Partial quotients of x by repeated inversion."""
    cf = []
    for _ in range(terms):
        a = int(math.floor(x))
        cf.append(a)
        frac = x - a
        if frac < 1e-10:
            break
        x = 1.0 / frac
    return cf


def ring_points(cf, r_base: float, r_span: float, count: int, cx: float, cy: float):
    """Points around a circle whose radius follows the partial quotients."""
    top = max(cf) or 1
    picked = [cf[i % len(cf)] for i in range(count)]
    pts = []
    for i, q in enumerate(picked):
        a = 2.0 * math.pi * i / count - math.pi / 2
        r = r_base + r_span * (q / top)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def polyline(pts) -> str:
    return " ".join("%.2f,%.2f" % p for p in pts)


def glyph_ring(cx: float, cy: float, radius: float, count: int, seed: int) -> str:
    """A ring of small deterministic marks; the PRNG is seeded, not random."""
    rng = random.Random(seed)
    out = []
    for i in range(count):
        a = 2.0 * math.pi * i / count - math.pi / 2
        gx = cx + radius * math.cos(a)
        gy = cy + radius * math.sin(a)
        s = 4.0 + 6.0 * rng.random()
        kind = rng.randrange(5)
        if kind == 0:
            out.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" '
                       'transform="rotate(%.1f %.2f %.2f)"/>'
                       % (gx - s / 2, gy - s / 2, s, s, rng.uniform(0, 90), gx, gy))
        elif kind == 1:
            out.append('<circle cx="%.2f" cy="%.2f" r="%.2f"/>' % (gx, gy, s / 2))
        elif kind == 2:
            out.append('<polygon points="%.2f,%.2f %.2f,%.2f %.2f,%.2f"/>'
                       % (gx, gy - s / 2, gx + s / 2, gy + s / 2, gx - s / 2, gy + s / 2))
        elif kind == 3:
            out.append('<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f"/>'
                       % (gx - s / 2, gy - s / 2, gx + s / 2, gy + s / 2))
        else:
            pts = [(gx + radius0 * math.cos(2 * math.pi * k / 6 - math.pi / 2),
                    gy + radius0 * math.sin(2 * math.pi * k / 6 - math.pi / 2))
                   for k in range(6) for radius0 in (s / 1.6,)]
            out.append('<polygon points="%s"/>' % polyline(pts))
    return "".join(out)


def sigil_section(bases: dict, pisots: dict, seed: int, write_svg: bool = True) -> str:
    rule("VIII.  THE SIGIL - geometry built from the measured constants")
    lam = float(bases["tribonacci"])
    rho = float(bases["plastic"])
    cf_t = continued_fraction(lam, 24)
    cf_p = continued_fraction(rho, 24)
    say("tribonacci lambda CF  : %s" % (cf_t,))
    say("plastic       rho  CF : %s" % (cf_p,))
    say("The two rings are the continued-fraction spectra drawn as radii.")
    say("The centre is the pentagram {5/2}.  The outer band is 36 marks")
    say("drawn from a PRNG seeded by the ghost hash, so the sigil is a")
    say("function of the numbers above and nothing else.")
    say()

    cx = cy = 500.0
    parts = []
    parts.append('<rect width="1000" height="1000" fill="#08090c"/>')
    for r in (120, 210, 300, 430):
        parts.append('<circle cx="500" cy="500" r="%d" fill="none" '
                     'stroke="#1d2430" stroke-width="1"/>' % r)
    parts.append('<polygon points="%s" fill="none" stroke="#e8c36a" '
                 'stroke-width="2.5"/>'
                 % polyline([(cx + 120 * math.cos(2 * math.pi * i / 5 - math.pi / 2),
                              cy + 120 * math.sin(2 * math.pi * i / 5 - math.pi / 2))
                             for i in range(10)]))
    parts.append('<polygon points="%s" fill="none" stroke="#4fd6c8" '
                 'stroke-width="1.8"/>' % polyline(ring_points(cf_t, 300, 120, 24, cx, cy)))
    parts.append('<polygon points="%s" fill="none" stroke="#c86af0" '
                 'stroke-width="1.8"/>' % polyline(ring_points(cf_p, 210, 90, 24, cx, cy)))
    parts.append('<g fill="none" stroke="#7f8ca3" stroke-width="1.2">%s</g>'
                 % glyph_ring(cx, cy, 455, 36, seed))
    parts.append('<line x1="500" y1="40" x2="500" y2="960" stroke="#1d2430"/>')
    parts.append('<line x1="40" y1="500" x2="960" y2="500" stroke="#1d2430"/>')
    corners = [
        (24, 40, "start", "lambda tribonacci = %.12f" % lam),
        (24, 966, "start", "rho plastic = %.12f" % rho),
        (976, 40, "end", "phi = %.12f" % PHI),
        (976, 966, "end", "2*pi = %.12f" % (2 * math.pi)),
    ]
    for x, y, anchor, label in corners:
        parts.append('<text x="%d" y="%d" text-anchor="%s" fill="#5b6a82" '
                     'font-family="monospace" font-size="13">%s</text>'
                     % (x, y, anchor, label))
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000" '
           'width="1000" height="1000">\n  ' + "\n  ".join(parts) + "\n</svg>\n")
    # Always record FACTS so --no-svg does not break the seal.
    FACTS["cf_tribonacci"] = cf_t
    FACTS["cf_plastic"] = cf_p

    if write_svg:
        path = OUT / "sigil.svg"
        path.write_text(svg, encoding="utf-8")
        say("wrote %s  (%d bytes)" % (path, len(svg)))
    return svg