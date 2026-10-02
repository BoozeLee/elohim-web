"""Section IV — Unicorn curve: superellipse perimeters climb from 2*pi toward 8.

Verbatim from the original `summoning_shard.py`. Math-comments preserved
exactly.
"""

from __future__ import annotations

import math

from .core import FACTS, say, rule


def adaptive_simpson(f, a: float, b: float, eps: float, depth: int) -> float:
    """Recursive adaptive Simpson; depth is the recursion budget."""
    fa, fb = f(a), f(b)
    mid = 0.5 * (a + b)
    fm = f(mid)
    whole = (b - a) / 6.0 * (fa + 4.0 * fm + fb)
    if depth <= 0:
        return whole
    left_mid = 0.5 * (a + mid)
    right_mid = 0.5 * (mid + b)
    left = (mid - a) / 6.0 * (fa + 4.0 * f(left_mid) + fm)
    right = (b - mid) / 6.0 * (fm + 4.0 * f(right_mid) + fb)
    if abs(left + right - whole) <= 15.0 * eps:
        return left + right + (left + right - whole) / 15.0
    return (adaptive_simpson(f, a, mid, eps / 2.0, depth - 1)
            + adaptive_simpson(f, mid, b, eps / 2.0, depth - 1))


def unicorn_perimeter(n: float, t0: float = 1e-6,
                      eps: float = 1e-13, depth: int = 30) -> float:
    """
    Perimeter of the superellipse |x|^n + |y|^n = 1, first-quadrant arc x4.

    Parameterisation x = cos(t)^(2/n), y = sin(t)^(2/n), so p = 2/n and
        ds = p * hypot( cos(t)^(p-1) sin(t),  sin(t)^(p-1) cos(t) )

    The exponent is p-1, not p.  Using p integrates x^2 + y^2 and returns
    2*sqrt(2) for the circle instead of 2*pi.

    For p < 1 the integrand has an integrable singularity at both ends,
    behaving like p*t^(p-1); the endpoint pieces integrate analytically to
    t0^p each, and the numeric part runs on [t0, pi/2 - t0].
    """
    p = 2.0 / n

    def integrand(t: float) -> float:
        c, s = math.cos(t), math.sin(t)
        return p * math.hypot(c ** (p - 1.0) * s, s ** (p - 1.0) * c)

    quarter = 2.0 * (t0 ** p)
    quarter += adaptive_simpson(integrand, t0, 0.5 * math.pi - t0, eps, depth)
    return 4.0 * quarter


def unicorn_section() -> None:
    rule("IV.  UNICORN CURVE - |x|^n + |y|^n = 1")
    say("One arc, many beasts.  n=2 is the circle, n->inf is the square;")
    say("everywhere between is the unicorn, and the perimeter is MONOTONIC")
    say("INCREASING, climbing from 2*pi toward the square's perimeter of 8.")
    say("It never dips below the circle.")
    say()
    say("%6s  %-20s  %s" % ("n", "perimeter", "note"))
    say("-" * 74)
    perims = {}
    for n in (2, 3, 4, 6, 8, 16, 64, 256):
        p = unicorn_perimeter(float(n))
        perims[n] = p
        note = ""
        if n == 2:
            note = "circle: expected 2*pi = %.10f, error %.2e" % (
                2 * math.pi, abs(p - 2 * math.pi))
        say("%6d  %-20.10f  %s" % (n, p, note))
    say()
    circle_err = abs(perims[2] - 2 * math.pi)
    say("circle check: |perimeter(n=2) - 2*pi| = %.2e" % circle_err)
    say("square limit: perimeter(256) = %.10f, distance to 8 = %.2e"
        % (perims[256], 8.0 - perims[256]))
    seq = [perims[n] for n in (2, 3, 4, 6, 8, 16, 64, 256)]
    increasing = all(b > a for a, b in zip(seq, seq[1:]))
    if increasing:
        say("monotonicity over the probed n: CONFIRMED, strictly increasing.")
    else:
        say("monotonicity over the probed n: VIOLATED -- a claim is wrong.")
    FACTS["unicorn_perimeters"] = {str(k): v for k, v in perims.items()}
    FACTS["unicorn_circle_error"] = circle_err
    FACTS["unicorn_monotonic"] = increasing
    say()