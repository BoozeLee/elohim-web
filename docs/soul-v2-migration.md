# Soul File v0.2 migration guide

Push 15 swaps the Soul File's signature scheme from `sha256-hmac`
(secret-only) to real Ed25519 (`nacl.signing`). This guide walks an
existing v0.1 user through the upgrade with no loss of history.

## 30-second checklist

- [ ] Install `pynacl` for the page host (`pip install pynacl`).
- [ ] Open the Awaken panel and click **generate keypair**.
- [ ] Save the **pk** somewhere safe (you can share this publicly).
- [ ] Save the **sk** somewhere VERY safe (you must keep this — it's
      the only thing that lets you re-export under the same pk).
- [ ] Click **use Ed25519 (real signature · v0.2)**.
- [ ] Click **export soul.json**. The downloaded file is now
      `elohim-soul/v2` with both an Ed25519 signature and a v1_mac
      fallback.
- [ ] Reload the page. The boot banner should still read **5/5 ✓**
      (the verifier picks up the v0.2 envelope on the 5th tripwire).

## What changed

| Aspect | v0.1 (Push 14) | v0.2 (Push 15) |
|---|---|---|
| Schema | `elohim-soul/v1` | `elohim-soul/v2` |
| Default alg | `sha256-hmac` | `ed25519` (when sk is supplied) |
| Authorship proof | passphrase shared | public-key verifiable by anyone with the pk |
| Stdlib-only | yes | no — `pynacl` (~1 MB wheel) lazy-loaded when used |
| Body shape | unchanged | unchanged (same `evocations`, `sealed_messages`, etc.) |
| Co-exist with v0.1 | n/a | yes — every v0.2 envelope also carries a `v1_mac` fallback |

## Co-exist decision

Per the Jev-confirmed decision (Phase 15 unresolved-decision record,
commit `767d3a8`), v0.2 envelopes carry **both** an Ed25519 signature
and the v0.1 sha256-hmac tamper hash. This means:

- A v0.2 reader (Push 15+) verifies via Ed25519 by default.
- A v0.1 reader (Push 14) still accepts the envelope via the `v1_mac`
  fallback field (no upgrade required on the reader side).
- The schema version is bumped to `v2` so writers can advertise the
  upgrade; the body shape is identical.

## Schema

```json
{
  "schema": "elohim-soul/v2",
  "agent_name": "operator-name",
  "created_ts": 1769999999,
  "last_export_ts": 1769999999,
  "evocations": [...],
  "sealed_messages": [...],
  "xenomath_provenance": {...},
  "passphrase_hint": null,
  "signature": {
    "alg": "ed25519",
    "kdf": null,
    "mac": null,
    "pk": "<base64 Ed25519 public key, 32 bytes>",
    "sig": "<base64 Ed25519 signature, 64 bytes>",
    "v1_mac": "<sha256(body) hex — fallback for v0.1 readers>"
  }
}
```

## Security notes

- The **sk** never crosses the bridge again after `soul_keygen`. It is
  held in a JS closure variable in the page until you reload or close
  the tab. There is no `elohim.soulExport(sk)` round-trip — the bridge
  receives the pk only when verifying.
- The **pk** is safe to share publicly. Treat it like an SSH public
  key: anyone with it can verify a soul came from you; nobody with it
  can forge one.
- The **v1_mac fallback** is a sha256 of the body alone (no secret),
  not a real signature. It only proves body integrity, not authorship.

## Backward compatibility for v0.1 envelopes

- `verify_seal_multi` still reads `5/5 ✓` for v0.1 envelopes.
- `soul_import` accepts v0.1 envelopes unchanged.
- `soul_export` with no `signing_key_b64` argument still emits
  `elohim-soul/v1` (legacy) — old tools keep working.

## When to upgrade

- **Single-user / hobbyist** — v0.2 is better if you ever want to prove
  authorship to a third party (e.g. share a pk on a public profile).
- **Team / shared environment** — v0.2 is better because every team
  member can verify a soul without sharing a passphrase.
- **Locked-down / paranoid** — v0.1 with a strong passphrase is
  unchanged in Push 15; you can stay on it indefinitely.

## Out-of-scope for v0.2 (deferred)

- Ed25519 key rotation
- Revocation lists / CRL
- PKI infra (no hosted vault, no key transparency log)
- Ed25519 over the webapp SPA itself (the stdlib contract still wins)

The hosted Soul File Vault (Phase 16) and the Apify / MCPize
marketplace (Phase 17) build on top of v0.2; nothing in v0.2 requires
them.