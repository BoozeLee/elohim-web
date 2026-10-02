"""CLI entry point and `main()` for the elohim summoning shard.

Reads `--invocation` and `--no-svg` from argv. Defaults reproduce the
canonical "ELOHIM:AWAKEN" run byte-for-byte (see `tests/fixtures/SEAL.txt`).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys

from . import collatz as _collatz_mod
from . import logstar as _logstar_mod
from . import padic as _padic_mod
from . import parry as _parry_mod
from . import pisot as _pisot_mod
from . import sigil as _sigil_mod
from . import unicorn as _unicorn_mod
from .core import FACTS, INVOCATION, OUT, REPORT, ghost_seed, rule, say


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="elohim-awaken",
        description="Summon the ghost in the machine. Stdlib only. "
                    "Emits a deterministic sigil and a sha256-sealed report.",
    )
    p.add_argument(
        "--invocation",
        default=INVOCATION,
        help="seed string for the ghost (default: %s)" % INVOCATION,
    )
    p.add_argument(
        "--no-svg",
        action="store_true",
        help="skip writing the sigil SVG (report + JSON only)",
    )
    return p


def main(arglist: list | None = None) -> int:
    args = _build_argparser().parse_args(arglist)

    # Always normalise module-level state at the top so this entry point is
    # hermetic across multiple calls (no leakage from earlier invocations).
    from . import core as _core_runtime
    _core_runtime.INVOCATION = args.invocation
    _core_runtime.FACTS.clear()
    _core_runtime.REPORT.clear()

    digest, seed = ghost_seed()
    rule("ELOHIM - summoning shard")
    say("invocation : %s" % args.invocation)
    say("sha256     : %s" % digest)
    say("seed       : %d" % seed)
    say("python     : %s" % sys.version.split()[0])

    bases = _parry_mod.parry_section()
    _parry_mod.knife_edge_section(bases)
    pisots = _pisot_mod.pisot_section(bases)
    _unicorn_mod.unicorn_section()
    _logstar_mod.logstar_section()
    _padic_mod.padic_section(seed)
    _collatz_mod.collatz_section(seed)

    if args.no_svg:
        _sigil_mod.sigil_section(bases, pisots, seed, write_svg=False)
    else:
        _sigil_mod.sigil_section(bases, pisots, seed, write_svg=True)

    rule("SHARD SEAL")
    seal = hashlib.sha256(
        json.dumps(FACTS, sort_keys=True, default=str).encode()
    ).hexdigest()
    say("facts recorded : %d" % len(FACTS))
    say("seal           : sha256 %s" % seal)
    FACTS["seal"] = seal
    say()
    say("The sigil, this log and the JSON digest all derive from the same")
    say("seed.  Any rounding change upstream moves the seal.")

    (OUT / "shard.md").write_text("\n".join(REPORT) + "\n", encoding="utf-8")
    (OUT / "shard.json").write_text(
        json.dumps(FACTS, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    print()
    print("wrote %s" % (OUT / "shard.md"))
    print("wrote %s" % (OUT / "shard.json"))
    return 0