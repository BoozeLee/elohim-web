"""Section VII — Collatz: capped trace and the exact odd-step product.

Verbatim from the original `summoning_shard.py`. Math-comments preserved
exactly.
"""

from __future__ import annotations

import math
from fractions import Fraction

from .core import FACTS, say, rule


def collatz_section(seed: int, cap: int = 20000) -> list:
    rule("VII.  COLLATZ - capped trace and the exact odd-step product")
    n0 = (seed % 1000003) or 3
    n = n0
    trace = [n]
    peak = n
    odd_inputs = []
    for _ in range(cap):
        if n == 1:
            break
        if n % 2 == 0:
            n //= 2
        else:
            odd_inputs.append(n)
            n = 3 * n + 1
        if n > peak:
            peak = n
        trace.append(n)
    steps = len(trace) - 1
    reached = trace[-1] == 1
    say("start n0        : %d   (seed mod 1000003)" % n0)
    say("steps           : %d" % steps)
    say("odd steps taken : %d" % len(odd_inputs))
    say("peak            : %d  (%.3fx the start, %.2f bits)"
        % (peak, peak / n0, math.log2(peak / n0)))
    say("reached 1       : %s" % ("YES" if reached else "NO (cap hit)"))
    say()

    # Independent replay: apply the parity rule to the recorded trace and
    # confirm it reproduces every step.  A claim the code does not re-verify
    # is a claim the code cannot make.
    replay = n0
    ok = True
    for value in trace[1:]:
        replay = replay // 2 if replay % 2 == 0 else 3 * replay + 1
        if replay != value:
            ok = False
            break
    say("replay check    : %s   (parity rule reproduces the whole trace)"
        % ("CONSISTENT" if ok else "INCONSISTENT"))
    say()

    product = Fraction(1, 1)
    for value in odd_inputs:
        product *= Fraction(3 * value + 1, 2 * value)
    say("The exact odd-step product, over rationals, no rounding:")
    say("  P = prod over odd n of (3n+1)/(2n)")
    say("  P  = %d / %d" % (product.numerator, product.denominator))
    log_p = math.log2(float(product.numerator) / float(product.denominator))
    say("  log2 P = %+.6f" % log_p)
    if reached and log_p < 0:
        say("  P < 1: this particular trajectory is a net contraction.")
    elif reached:
        say("  P > 1: this trajectory EXPANDS under the odd-step product, yet")
        say("  still reaches 1, because the even steps absorbed the gain.")
        say("  Which is the point: the odd-step product alone does not decide")
        say("  convergence, so calling it a conserved quantity is wrong.")
    else:
        say("  the trace did not land; the product is partial.")
    say("  Either way, 3n+1 is not 3n, so no exactly conserved quantity")
    say("  survives the trace.  Naming one would be a false invariant.")
    say()
    FACTS["collatz"] = {
        "n0": n0, "steps": steps, "odd_steps": len(odd_inputs),
        "peak": peak, "reached_one": reached, "replay_consistent": ok,
        "product_num": product.numerator, "product_den": product.denominator,
    }
    return trace