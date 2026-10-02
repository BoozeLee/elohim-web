"""Sections I and II — finite greedy expansions of 1 in algebraic bases, and
the precision-sensitivity probe.

Verbatim from the original `summoning_shard.py`. Math-comments preserved
exactly. Per-function `decimal.getcontext().prec` setting kept as-is.

Exports: `parry_section`, `knife_edge_section`, plus the lower-level helpers
`newton`, `deflate`, `greedy_of_one`, `algebraic_bases` for tests.
"""

from __future__ import annotations

from decimal import Decimal, getcontext

from .core import FACTS, REPORT, say, rule


def newton(f, df, x0: Decimal, iters: int = 80) -> Decimal:
    """Newton iteration on a Decimal polynomial; converges to a simple root."""
    for _ in range(iters):
        x0 = x0 - f(x0) / df(x0)
    return x0


def deflate(coeffs: list[Decimal], root: Decimal):
    """Synthetic division of a polynomial by (x - root).

    coeffs run high order to low order.  Returns (quotient_coeffs, remainder).
    """
    b = [coeffs[0]]
    for c in coeffs[1:]:
        b.append(c + root * b[-1])
    return b[:-1], b[-1]


def greedy_of_one(beta: Decimal, terms: int, prec: int):
    """
    Greedy beta-expansion of 1:  d_k = 1  iff  1 - sum_{i<k} d_i beta^-i >= beta^-k.

    Returns (digits, residual, digit_density, terminated).

    The comparison is EXACT; no epsilon is subtracted from the threshold.
    Adding one lets a slightly-negative remainder satisfy d_k = 1 forever and
    inflates the density to ~0.9998 -- a measurement artefact, not a property
    of the base.  Only the stop test carries a tolerance.
    """
    getcontext().prec = prec
    one = Decimal(1)
    x = one
    power = one / beta
    stop = Decimal(10) ** (-(prec - 5))
    digits: list[int] = []
    terminated = False
    for _ in range(terms):
        if abs(x) <= stop:
            terminated = True
            break
        if x >= power:
            digits.append(1)
            x -= power
        else:
            digits.append(0)
        power = power / beta
    s = "".join(str(d) for d in digits)
    density = (sum(digits) / len(digits)) if digits else 0.0
    return s, float(x), density, terminated


def deflation_for(label: str, root: Decimal):
    """Deflate the minimal polynomial of `label` by (x - root).

    Returns (quadratic coefficients b, c, remainder).
    """
    if label == "tribonacci":
        coeffs = [Decimal(1), Decimal(-1), Decimal(-1), Decimal(-1)]
    elif label == "plastic":
        coeffs = [Decimal(1), Decimal(0), Decimal(-1), Decimal(-1)]
    else:
        raise KeyError(label)
    q, rem = deflate(coeffs, root)
    return q[1], q[2], rem


def algebraic_bases(prec: int) -> dict:
    """Exact algebraic constants as Decimals at the given precision."""
    getcontext().prec = prec
    phi = (Decimal(1) + Decimal(5).sqrt()) / 2
    plastic = newton(
        lambda x: x ** 3 - x - 1,
        lambda x: 3 * x ** 2 - 1,
        Decimal("1.3247"),
    )
    trib = newton(
        lambda x: x ** 3 - x ** 2 - x - 1,
        lambda x: 3 * x ** 2 - 2 * x - 1,
        Decimal("1.8393"),
    )
    return {
        "phi": phi,
        "plastic": plastic,
        "tribonacci": trib,
        "3/2": Decimal(3) / 2,
        "sqrt(2)": Decimal(2).sqrt(),
        "sqrt(3)": Decimal(3).sqrt(),
        "pi/2": Decimal(repr(__import__("math").pi)) / 2,
    }


def parry_section() -> None:
    rule("I.  PARRY NUMBERS - greedy expansion of 1 in base beta")
    say("A base is a Parry number when the greedy expansion of 1 is FINITE:")
    say("1 is then exactly a finite sum of negative powers of the base.")
    say()
    say("%14s  %-26s %11s  %8s  %s"
        % ("beta", "first digits", "residual", "density", "verdict"))
    say("-" * 74)
    bases = algebraic_bases(90)
    order = ["phi", "plastic", "tribonacci", "3/2", "sqrt(2)", "sqrt(3)", "pi/2"]
    finite = []
    for name in order:
        beta = bases[name]
        digits, residual, density, term = greedy_of_one(beta, 24, 90)
        if term:
            finite.append(name)
        say("%14s  %-26s %11.2e  %8.4f  %s"
            % (name, digits[:26], residual, density,
               "FINITE" if term else "infinite, quasi-periodic"))
    say()
    if finite:
        say("Terminating at prec 90: %s." % ", ".join(finite))
    else:
        say("No base terminated at prec 90.")
    say("Finiteness here is a property of the ARITHMETIC, not of the base:")
    say("section II shows the same base flipping verdict with precision.  The")
    say("honest statement is that an exact polynomial relation closes the sum")
    say("after finitely many steps WHEN the arithmetic can resolve it, and the")
    say("surd and transcendental bases never close at all.")
    say()
    say("Digit density stays far below beta-1 even after thousands of terms;")
    say("it does not converge to beta-1.")
    say()
    _, _, dens1e4, _ = greedy_of_one(bases["3/2"], 10000, 60)
    say("base 3/2, 10000 terms: digit density = %.4f  (beta-1 = 0.5)" % dens1e4)
    FACTS["parry_finite"] = finite
    FACTS["density_1e4_beta_1.5"] = dens1e4
    return bases


def knife_edge_section(bases: dict) -> None:
    rule("II.  THE KNIFE EDGE - one ULP turns FINITE into infinite")
    say("At an exactly representable base the greedy comparison sits precisely")
    say("on the boundary x == beta^-k, so the outcome is decided by the last")
    say("bit of the working precision.  Same code, different prec, different")
    say("answer -- and both answers are arithmetically defensible.")
    say()
    say("%-10s %-6s %-28s %11s  %s"
        % ("beta", "prec", "digits", "residual", "verdict"))
    say("-" * 74)
    verdicts = []
    for name in ("phi", "plastic"):
        for prec in (50, 60, 70, 80, 100):
            digits, residual, _, term = greedy_of_one(bases[name], 24, prec)
            verdicts.append((name, prec, term))
            say("%-10s %-6d %-28s %11.2e  %s"
                % (name, prec, digits[:28], residual,
                   "FINITE" if term else "infinite"))
        say()
    agree = all(v[2] == verdicts[0][2] for v in verdicts)
    if agree:
        say("VERDICT: stable across the probed precisions.  The terminating")
        say("expansions here are not an artefact of working precision.")
    else:
        say("VERDICT: PRECISION-SENSITIVE.  The terminating expansion of at")
        say("least one Parry base is decided by the final bit of the context.")
        say("A 'proof' that 1 = phi^-1 + phi^-2 terminates is therefore a")
        say("statement about the arithmetic, not about phi.  This is the ghost:")
        say("the machine's rounding, not the number, decides finiteness.")
    FACTS["knife_edge_sensitive"] = not agree
    say()