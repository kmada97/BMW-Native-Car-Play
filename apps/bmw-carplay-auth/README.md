# Owned-device BAA authentication adapter

This is a deployable **protocol adapter candidate**, not an identity issuer. It translates a working Showcase-compatible local signing broker into xcertplay's remote authentication API. It cannot obtain private Apple entitlements, create an Apple-trusted certificate, export a broker key, or establish that an iPhone accepts an identity. No working owned-device broker or actual iPhone authentication was established by this implementation.

The implementation uses Python3.10+ standard library only. The tests use clearly synthetic certificate bytes and DER-shaped signatures; they are not accepted identities or cryptographic signatures.

```text
xcertplay receiver → HTTP API → local BAA3 Unix socket → owned-device signing broker
                    adapter                           key stays in that broker
```

## Interface

| Request | Response / behavior |
| --- | --- |
| `GET /mfi/certificate` | `type: "baa"`, `protocolMajor: 3`, base64 certificate package and SHA256 of its exact binary bytes. |
| `POST /mfi/sign` | JSON `challenge` (standard base64,1–128decoded bytes) and canonical UUID `requestId`; returns base64 DER/X9.62 signature. |
| `POST /mfi/reset` | Body `{}`; returns `reset: true`, `identityPreserved: true`. Does not rotate identity, restart the broker or discard retry entries. |

The broker uses the12-byte `BAA3` header: magic4, opcode1, status1, reserved2, payload length u32LE. Opcode1 retrieves certificates, opcode2 signs the **exact supplied challenge bytes** with the broker's ECDSA-SHA256 implementation. The adapter does not pre-hash them. Certificate payload length headers are converted from two u32LE values to two u32BE values; leaf/intermediate DER remain unchanged. The signature is validated for canonical DER shape and passed unchanged; the adapter does not independently verify its cryptographic validity or certificate trust.

## Identity and retries

The first certificate pins one identity for the adapter process. Certificate retrieval and signing run under one lock. Before and after a new signing request, the adapter checks that the broker's chain still matches the pinned bytes. If it changes, the adapter latches HTTP409 and refuses further identity access, even after `/mfi/reset`. The operator must explicitly restart the adapter **between phone sessions** to adopt a new identity.

The upstream broker protocol has separate certificate and signing operations, so it cannot offer an atomic identity-and-sign transaction. Before/after checks detect ordinary broker replacement; they do not create a cryptographic attestation of broker behavior. Use a trusted broker owned by this user.

Successful signatures are cached in memory for the last256UUIDs. A retry with the same UUID/challenge returns the same signature. Reusing a UUID with different bytes returns409. The cache and identity survive HTTP reset; process restart clears them. No challenges, credentials, certificates, signatures or request URLs are logged by the adapter.

## Running, once a real broker is available

The broker must already be running at a private Unix socket owned by the adapter user or root, with mode0600. The adapter must have OS permission to connect. It never starts the broker or contacts Apple enrollment services itself.

Loopback-only default:

```sh
python3 apps/bmw-carplay-auth/adapter.py --socket /tmp/showcase_baa.sock
```

This binds `127.0.0.1:8765`. It is not directly reachable from the Pi. No server was left running as part of development.

For a Pi on another machine, this adapter requires **TLS and a bearer token** before accepting a non-loopback bind. Supply a TLS certificate trusted by the Android receiver and its private key. A random token is read from an owner-only file, never a command-line token argument:

```sh
python3 -c 'import os,secrets; p="/private/tmp/bmw-auth-token"; fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600); os.write(fd,secrets.token_urlsafe(32).encode()); os.close(fd)'
python3 apps/bmw-carplay-auth/adapter.py \
  --socket /tmp/showcase_baa.sock \
  --bind 192.0.2.10 --port 8765 \
  --tls-cert /path/to/server-cert.pem --tls-key /path/to/server-key.pem \
  --token-file /private/tmp/bmw-auth-token
```

`192.0.2.10` is a documentation placeholder; use the actual interface address. xcertplay's Remote MFi URL is the corresponding `https://…:8765` address, with the same token in its separate token setting. The signer must remain reachable during both iAP2 and AirPlay authentication. This does not solve in-car connectivity to an off-car Mac.

Limits: broker roundtrip1.5seconds by default (maximum2), broker payload64KiB, certificate package65,525bytes, sign response1,024bytes, HTTP body2,048bytes. HTTP handling is serialized, has a bounded accept backlog, a2second socket timeout, and an8second absolute connection deadline. TLS1.2minimum; no insecure external-bind switch. Browser-origin requests are rejected. Temporary failures return502/503/504; identity changes and UUID conflicts return409.

## Verification

```sh
python3 -m unittest discover -s apps/bmw-carplay-auth/tests -v
```

Twelve tests pass against temporary fake Unix brokers and loopback HTTP servers. They cover fragmented broker responses, LE/BE conversion, certificate digest, exact challenge forwarding, DER pass-through, retry deduplication/concurrent access, reset semantics, identity replacement before/during signing, malformed headers/lengths/signatures, timeout/error mapping, socket permissions, request validation, bearer gating and external TLS enforcement. Test servers are closed and their threads joined on completion.

Not tested: real DeviceIdentity issuance, a real BAA broker, trusted certificate validation, iPhone acceptance, Android-to-Mac TLS reachability or a complete CarPlay handshake.

## Pinned source contract

- [Showcase broker header](https://github.com/amineross/showcase/blob/68b0fe54483031353184258577f3d42de4dd313c/source/baa_broker.h)
- [Showcase certificate/signing implementation](https://github.com/amineross/showcase/blob/68b0fe54483031353184258577f3d42de4dd313c/source/carplay_services.m)
- [xcertplay remote client](https://github.com/shilapi/xcertplay/blob/8b01399a17ef8b3193931a2ff4ed93b410a73570/shared/src/main/java/com/shilapi/xcertplay/mfi/RemoteMfiAuthenticationClient.kt)

Pinned hashes and implementation status are recorded in `provenance.json`. The adapter is an original standard-library protocol implementation based on these interfaces; no third-party identity or private key is bundled.
