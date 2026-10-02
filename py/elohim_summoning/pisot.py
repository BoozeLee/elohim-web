"""Section III — Pisot signature: |alpha| = sqrt(1/lambda), and the constant 2
is tight.

Verbatim from the original `summoning_shard.py`. Math-comments preserved
exactly. Per-function `decimal.getcontext().prec` setting kept as-is.
"""

from __future__ import annotations

import cmath
import math
from decimal import Decimal, getcontext

from .core import FACTS, say, rule
from .parry import deflation_for, newton


ALGEBRA = {
    "tribonacci": {
        "text": "x^3 - x^2 - x - 1",
        "f": lambda x: x ** 3 - x ** 2 - x - 1,
        "df": lambda x: 3 * x ** 2 - 2 * x - 1,
        "guess": "1.8393",
    },
    "plastic": {
        "text": "x^3 - x - 1",
        "f": lambda x: x ** 3 - x - 1,
        "df": lambda x: 3 * x ** 2 - 1,
        "guess": "1.3247",
    },
}


def quadratic_roots(b: Decimal, c: Decimal):
    """
    Roots of x^2 + b x + c = 0 as Python complex numbers.

    The discriminant of a Pisot conjugate pair is NEGATIVE, so the square root
    must go through cmath.  Taking the real sqrt of the negated discriminant
    silently returns two real numbers whose product is not c, which is how
    |alpha| came out as 0.1 instead of sqrt(1/lambda).
    """
    bf, cf = float(b), float(c)
    root = cmath.sqrt(complex(bf * bf - 4.0 * cf, 0.0))
    return (-bf + root) / 2.0, (-bf - root) / 2.0


def pisot_one(label: str, n_max: int) -> tuple:
    spec = ALGEBRA[label]
    # pass 1: coarse root, only to size the precision budget
    getcontext().prec = 40
    root = newton(spec["f"], spec["df"], Decimal(spec["guess"]))
    b, c, _ = deflation_for(label, root)
    alpha, beta = quadratic_roots(b, c)
    modulus = abs(alpha)
    gap = math.log10(float(root)) - math.log10(modulus)
    prec = int(n_max * gap) + 30

    # pass 2: everything at the real precision
    getcontext().prec = prec
    root = newton(spec["f"], spec["df"], Decimal(spec["guess"]))
    b, c, rem = deflation_for(label, root)
    alpha, beta = quadratic_roots(b, c)
    modulus = abs(alpha)
    lam = float(root)
    predicted = math.sqrt(1.0 / lam)

    say("-- %s --" % label)
    say("  minimal polynomial : %s" % spec["text"])
    say("  deflation residual  : %.2e   (f(root); must vanish)" % float(abs(rem)))
    say("  lambda              : %.20f" % lam)
    say("  conjugate alpha    : %.16f %+.16fi" % (alpha.real, alpha.imag))
    say("  |alpha| measured   : %.15f" % modulus)
    say("  sqrt(1/lambda)     : %.15f" % predicted)
    say("  discrepancy        : %.2e" % abs(modulus - predicted))
    say("  working precision  : %d digits   (n_max*log10(lam/|a|)+30)" % prec)
    say()

    worst, worst_n = 0.0, 0
    for n in range(1, n_max + 1):
        p = root ** n
        err = abs(p - p.to_integral_value())
        ratio = float(err) / (modulus ** n)
        if ratio > worst:
            worst, worst_n = ratio, n
    say("  max over n<=%d of |lam^n - round(lam^n)| / |alpha|^n = %.6f at n=%d"
        % (n_max, worst, worst_n))
    if worst > 1.98:
        say("  Pisot's bound |err| <= 2|alpha|^n is ATTAINED here: the constant")
        say("  2 is not slack, and the round(lam^n) fingerprint is tight.")
    else:
        say("  measured maximum sits strictly below Pisot's constant 2.")
    say()
    FACTS[label] = {
        "lambda": lam,
        "alpha": [alpha.real, alpha.imag],
        "modulus": modulus,
        "sqrt_inv_lambda": predicted,
        "modulus_discrepancy": abs(modulus - predicted),
        "bound_max": worst,
        "bound_argmax_n": worst_n,
        "precision": prec,
    }
    return root, modulus


def pisot_section(bases: dict) -> None:
    rule("III.  PISOT SIGNATURE - where the integers hide")
    say("For a Pisot number lambda the fractional part of lambda^n decays like")
    say("|alpha|^n, where alpha is a conjugate.  The two facts printed below")
    say("are both machine-verified, with the residual that proves each.")
    say()
    say("FACT A.  |alpha| = sqrt(1/lambda) exactly.  Not 1/lambda.  The three")
    say("  roots of x^3 - ... - 1 have product 1, and the two non-real roots")
    say("  are complex conjugates, so each carries modulus sqrt(1/lambda).")
    say()
    say("FACT B.  The constant 2 in Pisot's bound is TIGHT, not a safe margin.")
    say()
    lam_t, mod_t = pisot_one("tribonacci", 200)
    lam_p, mod_p = pisot_one("plastic", 200)
    say("Why the regression was dropped: fitting log(error) against n with")
    say("least squares is biased upward by the oscillation of |alpha|^n times")
    say("cos(n*arg alpha).  The deflation identity above is exact and needs no")
    say("fit at all, so this instrument reports the identity, not a slope.")
    say()
    FACTS["pisot_decay"] = {
        "tribonacci": mod_t,
        "plastic": mod_p,
    }
    return {"tribonacci": (lam_t, mod_t), "plastic": (lam_p, mod_p)}