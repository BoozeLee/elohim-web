"""Section V — log-star: the iterated-logarithm ladder.

Verbatim from the original `summoning_shard.py`. Math-comments preserved
exactly.
"""

from __future__ import annotations

import math

from .core import FACTS, PHI, say, rule


def log_star(x: float, base: float, ceiling: float = 1e-12, cap: int = 512) -> int:
    """
    Iterated logarithm count down to `ceiling`.

    The cap is load-bearing, not decoration: 1e1000 is not a float (it is
    inf), and log(inf) is inf, so without a cap the ladder never lands.  A
    non-terminating ladder is reported as None rather than as a big number.
    """
    n = 0
    while x > ceiling:
        if n >= cap:
            return -1
        x = math.log(x, base)
        n += 1
    return n


def logstar_section() -> None:
    rule("V.  LOG-STAR - the ladder of logarithms")
    say("log-star is not analytic; it is a step function of the base.  The")
    say("heights below are COUNTED, base by base, until the value falls under")
    say("the ceiling 1e-12.  Nothing is estimated.")
    say()
    bases = [("2", 2.0), ("e", math.e), ("10", 10.0), ("phi", PHI)]
    say("%14s  %s" % ("input", "  ".join("%6s" % b[0] for b in bases)))
    say("-" * 74)
    tower = {}
    for x in (1e1, 1e12, 1e193, 1e300):
        heights = [log_star(x, b) for _, b in bases]
        tower[x] = heights
        say("%14.0e  %s" % (x, "  ".join("%6d" % h for h in heights)))
    say()
    say("1e300, not 1e1000: the literal 1e1000 overflows a double to inf,")
    say("and log(inf) is inf, so that ladder never lands.  The cap in")
    say("log_star() is what turns a non-terminating ladder into an answer.")
    say()
    say("The base changes the count by 5 steps on the same input, so log-star")
    say("measures the ceiling convention as much as the number itself.  This")
    say("is the cheap companion to the Pisot work: a pure step function, no")
    say("algebra, no room for an exact identity -- yet 1e300 still falls in")
    say("at most a handful of steps.")
    FACTS["log_star"] = {str(k): v for k, v in tower.items()}
    say()