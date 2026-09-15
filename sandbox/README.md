# SPP Reference Sandbox

This small Docker sandbox demonstrates existing PlaceAuth reference admission
logic through a local HTTP API. It is experimental and non-normative: it does
not change SPP 0.1, define a production deployment, or make a physical-safety
claim.

It deliberately reuses the current reference `PlaceRequirementSet`,
`ConformancePlan`, `EvidenceBundle`, binding, locally trusted Ed25519 issuer
and policy-authority verification, admission, and lifecycle paths. The compact
restriction acknowledgement check is sandbox-local adapter configuration: it
shows that every exact `DEGRADED` restriction has a named handler mapping. It
does **not** prove execution of a handler or physical enforcement.

## Quick start

From this directory:

```sh
docker compose up --build
```

The API is then available at `http://localhost:8080`.

```sh
curl http://localhost:8080/health
curl http://localhost:8080/about
curl http://localhost:8080/examples
curl -X POST http://localhost:8080/evaluate \
  -H 'content-type: application/json' \
  -d '{"scenario":"degraded"}'
curl -X POST http://localhost:8080/verify \
  -H 'content-type: application/json' \
  -d '{"scenario":"tampered"}'
```

Run every deterministic scenario with `./scripts/run-demo.sh`, or on Windows,
`./scripts/run-demo.ps1`. Set `SPP_SANDBOX_URL` (shell) or `-BaseUrl` (PowerShell)
to point either script at another local sandbox address.

## Endpoints

- `GET /health` — liveness and the explicit SPP 0.1/non-normative boundary.
- `GET /about` — the reference layers demonstrated and their limits.
- `GET /examples` and `GET /examples/{name}` — ready-to-run JSON requests.
- `POST /evaluate` — produces the existing `ADMITTED`, `DEGRADED`, or `DENIED`
  `AdmissionProfile` for a selected scenario.
- `POST /verify` — runs the same path and reports policy/evidence signature,
  subject/place/scope/time binding, lifecycle, and local restriction-mapping
  checks. Its sandbox-only conclusion is `RELIABLE_ADMITTED`,
  `RELIABLE_DEGRADED`, or `BLOCKED`.

Supported scenario names are `admitted`, `degraded`, `denied`, `expired`,
`tampered`, `missing-restriction-ack`, and `changed-subject`.

The canonical `degraded` fixture is lifecycle-current: it begins with complete
current evidence and represents an already-issued profile with the explicit
`sensing.video.capture=disabled` operating restriction. Its exact local
acknowledgement and handler mapping therefore demonstrate
`RELIABLE_DEGRADED`. This sandbox fixture does not change the existing
admission engine, which separately derives a restriction from a nonessential
failed test and correctly requests requalification for that case.

## What this does not supply

There are no external credentials, cloud calls, database, ROS/Open-RMF
dependency, PKI, certificate lifecycle, distributed replay registry, or
physical-enforcement attestation. The in-process keys and identities are newly
generated fixtures for each request, never deployment credentials.

The source reference currently uses its established deterministic JSON
serialization and SHA-256 digest helper. This sandbox does not claim the
separate experimental RFC 8785 JCS interoperability profile or import that
experiment.

## Independent implementation challenge

Implement the documented inputs in another language and demonstrate the same
outcomes for every endpoint example. In particular, show that changing a
signed result, presenting evidence for a different subject, passing expiry, or
omitting the exact restricted-operation mapping produces `BLOCKED`. Report
differences as interoperability questions rather than treating this sandbox as
a standards test suite.
