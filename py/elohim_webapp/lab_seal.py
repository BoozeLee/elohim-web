"""elohim_lab · lab_seal — vendored copy of the monorepo's elohim_lab.seal.

The deploy repo on gh-pages cannot import from /home/kilisan/elohim/ —
Pyodide only sees the files vendored under py/elohim_webapp/. We vendor
lab_seal() here so the in-browser Lab tab can stamp every artifact with
the same 64-hex sha256 the monorepo FastAPI does.

The original lives in elohim/src/elohim_lab/seal.py. If you update the
monorepo copy, mirror the change here.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


VERSION = "0.1.0"

# The schema tag is also vendored so the in-browser UI can validate that
# the seal format matches what the server expects.
FACTS: dict[str, str] = {
    "name": "elohim_lab",
    "version": VERSION,
    "schema": "elohim-lab/v1",
    "seal_algorithm": "sha256",
}


def lab_seal(record: Any, status: str, version: str = VERSION) -> str:
    """Compute the 64-hex sha256 seal for ``record`` at ``status``.

    ``status`` is the string form of a VerificationStatus enum value
    (the browser never instantiates the enum; it just sends the string).
    """
    payload = {
        "v": version,
        "s": str(status),
        "r": record,
    }
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(body).hexdigest()