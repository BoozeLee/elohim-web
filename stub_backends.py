"""Local stub backends for the vault and marketplace WebMCP tools.

The spec's verification tiers label six tools `stub`, not `in-browser`,
and this module is why that label is honest rather than a dodge: it is a
TEST DOUBLE for our own wiring — request shape, response parsing, error
paths — and explicitly NOT a conformance claim about Apify, x402, or the
real FastAPI vault. The real service contract is not verified by this.

Without a stub those six tools could only ever be tested against live
backends, which means either an unrunnable suite or no tests at all.
A stub that is honest about being a stub is the better of the two.

Both the vault routes and the marketplace MCP endpoint are served from one
stdlib ThreadingHTTPServer so the app only needs one port.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CANONICAL_SEAL = (
    "5f12cc7825b595a0df7bf5b97ae471b0bda4d3408474890d2d63548e93ebf596"
)


class _Handler(BaseHTTPRequestHandler):
    # Silence per-request logging; the smoke harness prints its own.
    def log_message(self, *_args):
        pass

    def _send(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        srv = self.server
        if path == "/api/vault/tiers":
            return self._send({
                "canonical_seal": CANONICAL_SEAL,
                "tiers": {
                    "free": {"count": len(srv.store), "price_usd": 0.0},
                    "indie": {"count": 500, "price_usd": 5.0},
                    "team": {"count": 5000, "price_usd": 25.0},
                },
                "prices_usd": {"free": 0.0, "indie": 5.0, "team": 25.0},
            })
        if path.startswith("/api/vault/lookup/"):
            pk = path.rsplit("/", 1)[-1]
            payload = srv.store.get(pk)
            if payload is None:
                return self._send({"ok": False, "error": "not found"}, 404)
            return self._send({"ok": True, "payload": payload})
        if path == "/api/vault/list_public":
            # Only genuinely-public souls belong on a public list. This was
            # not modelled before, which meant #87's `total >= 1` assertion
            # passed no matter what is_private said — the documented
            # "is_private:false publishes, and that cannot be undone" warning
            # in llms.txt had no test behind it at all.
            items = [{"pk": pk, "schema": p.get("schema")}
                     for pk, p in srv.store.items()
                     if p.get("is_private") is False]
            return self._send({"ok": True, "total": len(items), "items": items})
        return self._send({"ok": False, "error": f"no stub route for {path}"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return self._send({"ok": False, "error": "bad json"}, 400)
        srv = self.server
        path = self.path.split("?")[0]

        if path == "/api/vault/store":
            schema = (body.get("payload") or {}).get("schema")
            # Mirror the real service: unknown schemas are rejected with a
            # clear message, so the error path is exercised too.
            if schema not in ("elohim-soul/v1", "elohim-soul/v2"):
                return self._send(
                    {"ok": False,
                     "error": f"unsupported schema: {schema!r}",
                     "status": 400}, 400)
            pk = (body.get("payload") or {}).get("agent_name", "stub-agent")
            payload = dict(body.get("payload") or {})
            # The app always sends an explicit boolean (`is_private !== false`),
            # but default to private here so a caller that omits it gets the
            # safe answer rather than a silent publication.
            payload["is_private"] = body.get("is_private") is not False
            srv.store[pk] = payload
            return self._send({"ok": True, "pk": pk, "stored": True,
                               "is_private": payload["is_private"]})

        if path == "/mcp":
            name = ((body.get("params") or {}).get("name"))
            args = (body.get("params") or {}).get("arguments") or {}
            if name != "elohim_alien_codex":
                return self._send({"ok": False, "error": f"no tool {name}"}, 404)
            # A deterministic-looking but obviously fake seal. The real
            # determinism contract (actor seal == local bridge seal) is NOT
            # verified by this stub — that needs the real actor.
            inv = args.get("invocation", "ELOHIM:APIFY")
            fake = ("stub" + inv).encode().hex()[:64].ljust(64, "0")
            payload = {
                "invocation": inv,
                "codex_seal": fake,
                "encrypted_seal": fake[:32],
                "billing_event": {"charged": True, "amount_usd": 0.02},
            }
            # An invocation containing "AMBIGUOUS" gets a SUCCESSFUL charge
            # response with no `billing_event` at all — a server-side shape
            # change, a proxy, a partial response. This is the case the app's
            # idempotency guard used to get wrong: it recorded a charge only
            # when `billing_event.charged` was truthy, so an ambiguous success
            # left the invocation unrecorded and the agent's retry charged the
            # customer a second time. The guard now fails closed.
            if "AMBIGUOUS" in inv:
                payload.pop("billing_event", None)
            return self._send({
                "jsonrpc": "2.0", "id": body.get("id"),
                "result": {"resultType": "complete", "content": [{
                    "type": "text",
                    "text": json.dumps(payload),
                }]},
            })
        return self._send({"ok": False, "error": f"no stub route for {path}"}, 404)


class _Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, addr):
        super().__init__(addr, _Handler)
        self.store: dict[str, dict] = {}
        self.charged_invocations: set[str] = set()


class StubBackends:
    """One port serving both the vault REST routes and the /mcp endpoint."""

    def __init__(self, host="127.0.0.1", port=0):
        self._srv = _Server((host, port))
        self._thread = threading.Thread(target=self._srv.serve_forever,
                                        daemon=True)
        self._thread.start()

    @property
    def base(self) -> str:
        host, port = self._srv.server_address[:2]
        return f"http://{host}:{port}"

    @property
    def vault_base(self) -> str:
        return self.base

    @property
    def marketplace_url(self) -> str:
        return f"{self.base}/mcp"

    def __enter__(self) -> "StubBackends":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        self._srv.shutdown()
        self._srv.server_close()


def start_stub_backends(host="127.0.0.1", port=0) -> StubBackends:
    return StubBackends(host, port)


# ── Self-test. Run: python3 stub_backends.py ────────────────────────

def _get(url):
    import urllib.request
    with urllib.request.urlopen(url, timeout=5) as r:
        return json.loads(r.read())


def _post(url, payload):
    import urllib.request
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())


def test_stub_returns_shapes_the_app_parses():
    with start_stub_backends() as s:
        tiers = _get(s.vault_base + "/api/vault/tiers")
        assert "tiers" in tiers and "free" in tiers["tiers"]
        assert tiers["canonical_seal"] == CANONICAL_SEAL

        stored = _post(s.vault_base + "/api/vault/store",
                       {"payload": {"schema": "elohim-soul/v2",
                                    "agent_name": "self-test"},
                        "is_private": False})
        assert stored["ok"] is True and stored["pk"] == "self-test"

        found = _get(s.vault_base + "/api/vault/lookup/self-test")
        assert found["ok"] is True
        assert found["payload"]["schema"] == "elohim-soul/v2"

        listed = _get(s.vault_base + "/api/vault/list_public")
        assert listed["total"] == 1 and listed["items"][0]["pk"] == "self-test"

        r = _post(s.marketplace_url, {
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "elohim_alien_codex",
                       "arguments": {"invocation": "ELOHIM:APIFY"}}})
        body = json.loads(r["result"]["content"][0]["text"])
        assert body["codex_seal"] and body["billing_event"]["amount_usd"] == 0.02


def test_stub_rejects_unknown_schema():
    import urllib.error
    with start_stub_backends() as s:
        try:
            _post(s.vault_base + "/api/vault/store",
                  {"payload": {"schema": "elohim-soul/v999"}})
            raise AssertionError("stub accepted an unknown schema")
        except urllib.error.HTTPError as e:
            assert e.code == 400
            assert "unsupported schema" in json.loads(e.read())["error"]


if __name__ == "__main__":
    test_stub_returns_shapes_the_app_parses()
    test_stub_rejects_unknown_schema()
    print("stub_backends self-tests passed")
