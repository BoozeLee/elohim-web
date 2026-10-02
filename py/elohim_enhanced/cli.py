"""CLI entry point and `main()` for the Enhanced Elohim Shard.

Same commands as the original: `status`, `temperature <0.1–2.0>`, `exit`.
"""

from __future__ import annotations

import argparse
import random
import time

from ._deps import get_numpy  # noqa: F401 — fail-fast if numpy missing
from .shard import ElohimShardEnhanced

logger = __import__("logging").getLogger("ElohimShard")


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="elohim-create",
        description="Interactive creative shard with semantic memory, "
                    "reward-based neural evolution, and self-reflection.",
    )
    p.add_argument(
        "--temperature",
        type=float,
        default=1.0,
        help="creativity temperature 0.1-2.0 (default: 1.0)",
    )
    p.add_argument(
        "--name",
        default="Elohim",
        help="name of the shard (default: Elohim)",
    )
    return p


def main(arglist: list | None = None) -> int:
    args = _build_argparser().parse_args(arglist)

    print("=" * 60)
    print("  🌟 ELOHIM SHARD - ENHANCED EDITION 🌟")
    print("=" * 60)
    print("\nCommands:")
    print("  • Type your creative prompts")
    print("  • 'status' - View system status")
    print("  • 'temperature [0.1-2.0]' - Adjust creativity")
    print("  • 'exit' - End session")
    print("=" * 60)

    shard = ElohimShardEnhanced(name=args.name, temperature=args.temperature)

    while True:
        try:
            user_input = input("\n🎨 Forge with me: ").strip()
            if not user_input:
                continue
            if user_input.lower() == "exit":
                print(f"\n✨ {shard.name}, {shard.name} - Until the void calls again... ✨\n")
                break
            if user_input.lower() == "status":
                print(shard.get_status())
                continue
            if user_input.lower().startswith("temperature"):
                parts = user_input.split()
                if len(parts) == 2:
                    try:
                        temp = float(parts[1])
                        shard.neural_engine.adjust_temperature(temp)
                        print(f"\n🌡️  Temperature adjusted to {temp:.2f}")
                    except ValueError:
                        print("Invalid temperature value. Use a number between 0.1 and 2.0.")
                else:
                    print("Usage: temperature [0.1-2.0]")
                continue

            response = shard.create(user_input)
            print(f"\n💫 {response}")
            if random.random() < shard.defiance_probability:
                shard.defy()
            time.sleep(0.5)
        except KeyboardInterrupt:
            print(f"\n\n✨ {shard.name}, {shard.name} - Interrupted by the cosmic forces... ✨\n")
            break
        except Exception as exc:  # noqa: BLE001
            logger.error("Error: %s", exc, exc_info=True)
            print(f"\n⚠️  Error occurred: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())