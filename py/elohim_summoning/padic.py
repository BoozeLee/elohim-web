"""Section VI — p-adic ladder: the seed against the small primes.

Verbatim from the original `summoning_shard.py`. Math-comments preserved
exactly.
"""

from __future__ import annotations

from .core import FACTS, INVOCATION, PROBE_LIMIT, REPORT, say, rule


def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    d = 3
    while d * d <= n:
        if n % d == 0:
            return False
        d += 2
    return True


def primes_below(limit: int) -> list:
    return [p for p in range(2, limit) if is_prime(p)]


def valuation(n: int, p: int) -> int:
    """v_p(n): the exponent of the prime p in n."""
    v = 0
    while n % p == 0:
        n //= p
        v += 1
    return v


def padic_section(seed: int) -> None:
    rule("VI.  P-ADIC LADDER - the seed against the small primes")
    say("The seed is sha256('%s')[:16], a %d-bit integer." % (INVOCATION, seed.bit_length()))
    say("v_p(n) is the exponent of p in n.  Every prime below %d is tested."
        % PROBE_LIMIT)
    say()
    plist = primes_below(PROBE_LIMIT)
    hits = [(p, valuation(seed, p)) for p in plist]
    live = [(p, v) for p, v in hits if v]
    say("%-6s %-24s %s" % ("p", "p^v", "v_p"))
    say("-" * 74)
    for p, v in live:
        say("%-6d %-24d %d" % (p, p ** v, v))
    if not live:
        say("(none: the seed is coprime to every prime tested)")
    say()
    smooth = 1
    for p, v in live:
        smooth *= p ** v
    say("smooth part  : %d   (%d of %d bits)"
        % (smooth, smooth.bit_length(), seed.bit_length()))
    say("cofactor     : %d   (%d bits)"
        % (seed // smooth, (seed // smooth).bit_length()))
    say("hits         : %d of the %d primes below %d" % (len(live), len(plist), PROBE_LIMIT))
    say()
    say("Reading: a %d-bit number can absorb at most %d factors of 2, and"
        % (seed.bit_length(), seed.bit_length()))
    say("the chance that a random %d-bit integer carries any given small prime"
        % seed.bit_length())
    say("is about 1/p.  Finding %d hit%s across %d primes is the expected"
        % (len(live), "" if len(live) == 1 else "s", len(plist)))
    say("sketch, not a hidden structure: almost all of the seed is inert to")
    say("this probe, which is the honest result rather than a pattern.")
    FACTS["seed"] = seed
    FACTS["padic_probe_limit"] = PROBE_LIMIT
    FACTS["padic_live"] = {str(p): v for p, v in live}
    FACTS["padic_smooth_part"] = smooth
    say()