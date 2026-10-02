"""Dependency guard for `elohim_enhanced`.

The Enhanced Elohim Shard depends on numpy, which is **not** a runtime
dependency of `elohim_summoning` (the sibling package in this repo keeps a
strict stdlib-only contract). Anyone reaching for the enhanced surface gets a
clear import-time error pointing at the optional extra:

    pip install "elohim-summoning[enhanced]"
"""

from __future__ import annotations

try:
    import numpy as np  # noqa: F401
except ImportError as _exc:  # pragma: no cover - guarded by pyproject extras
    raise ImportError(
        "elohim_enhanced requires numpy. Install with:\n"
        "    pip install \"elohim-summoning[enhanced]\"\n"
        "(or `pip install numpy` in your environment).\n"
        "The original error was: %s" % _exc
    )


def get_numpy():
    """Re-import numpy with a clean error if it has been removed mid-process."""
    try:
        import numpy as np
        return np
    except ImportError as _exc:  # pragma: no cover
        raise ImportError(
            "numpy disappeared from this process — install it with "
            "`pip install numpy` to use elohim_enhanced."
        ) from _exc