# Project continuity

## Project identity

**PlaceAuth** is the project. The **Spatial Policy Protocol (SPP)** is its
open, place-centered protocol. This repository contains the SPP specification,
schemas, examples, and experimental reference implementation. The repository
states that PlaceAuth and SPP are stewarded by
[PlaceAuth Foundation, Inc.](https://github.com/placeauth/governance). This
file describes technical continuity in this repository; it does not replace
Foundation governance.

## What is normative

[SPP 0.1](spec/SPP-0.1.md) is the current normative protocol specification.
It defines the place policy bundle; hierarchical spaces; actor, action, space,
and context inputs; `permit`, `deny`, and `conditional` decisions; and the
associated authorization and obligation rules. The JSON schemas in `schema/`
are the corresponding exchange artifacts.

Do not confuse that protocol version with a repository release. The Python
package in `pyproject.toml` is version `0.3.0`, and the repository contains the
annotated `v0.3.0-experimental-preview` tag. Those establish a versioned
experimental reference implementation state; they do not revise SPP 0.1. Place
Package and decision trace formats remain 0.1. GitHub verification establishes
that tag's published prerelease: **SPP v0.3.0 Experimental Preview**, with
`prerelease: true`, `draft: false`, and `published_at:
2026-09-08T17:14:29Z`. The historical 0.3 checklist's unchecked prerelease
item is stale documentation, not evidence against that publication. See
[RELEASING.md](RELEASING.md) for the release-state record.

`spec/evidence-based-admission.md` is explicitly experimental and
pre-standardization. It is not a second normative SPP specification.

## What is experimental

- The admission/evidence reference path: requirements, conformance plans,
  evidence and bindings, selective requalification, profiles, lifecycle, and
  local trust verification.
- Trust-pipeline work, including local Ed25519 roles and the independent JCS
  Rust-verifier experiment. It is not production PKI, issuer federation, or
  an adopted wire-format standard.
- The engine-neutral [Core Profile](docs/experimental/spp-core-profile.md), its
  native/OPA comparison, and the independent-implementation challenge. None
  changes SPP 0.1 or requires a particular policy engine.
- Bounded ROS 2/Nav2, Open-RMF, and facility-side adapters and their fixtures.
  They demonstrate their stated integration boundaries only.
- Research and design materials in `docs/research/` and `docs/design/`,
  including IEEE 1872/P1872.3 vocabulary research, Open-RMF site-region
  binding, and planner-aware discussions. They are not standards adoption,
  partnership, endorsement, or API commitments.

## Architectural boundary

### SPP owns

- Place-originated policy and policy applicability to a declared space/scope.
- Evaluation of supplied subject/actor, action, space, and context inputs.
- Normalized policy outcomes (`permit`, `deny`, or `conditional`) and named
  authorizations or obligations where the applicable rule requires them.

The experimental reference layer additionally evaluates place requirements and
evidence to produce scoped `ADMITTED`, `DEGRADED`, or `DENIED` profiles. These
are not SPP 0.1 policy decisions and must not be described as such.

### SPP intentionally does not own

- Geometry, maps, localization, or region containment.
- Fleet taxonomy, route/task planning, scheduling, or task allocation.
- A universal robotics ontology or capability taxonomy.
- Identity infrastructure, production PKI, remote trust discovery, or key
  lifecycle services.
- Safety certification, stopping guarantees, or physical enforcement.

External systems retain ownership of those domains. In particular, a planner
evaluates a candidate route or task; an enforcement point must enforce a policy
result or restriction; a deployment supplies trusted identity and site facts.

## Repository map

| Location | Purpose |
| --- | --- |
| `spec/` | Normative SPP 0.1 plus security/threat material and explicitly experimental admission design. |
| `schema/` | JSON schemas for protocol and reference exchange artifacts. |
| `reference/` | Reference policy server, admission implementation, and experimental adapters. |
| `examples/` | Informative policy and Place Package examples. |
| `demo/` | Runnable reference demonstrations; `demo/admission/` is canonical. |
| `tests/` | Dependency-free reference suite and optional ROS/Open-RMF runtime fixtures. |
| `sandbox/` | Docker-based, non-normative local reference sandbox. |
| `experiments/` | Isolated experimental implementations, including Core Profile native/OPA comparison. |
| `challenges/` | Independent-implementation fixtures and reporting aid. |
| `docs/` | Implementation guides, release history, technical review, whitepaper, and non-normative research/design notes. |
| `.github/` | General test, ROS 2/Nav2 runtime, and Open-RMF runtime workflows; issue templates. |

## Canonical verification path

From the repository root, using Python 3.11 or newer:

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
python demo/admission/run_demo.py --canonical
```

The admission command is the canonical five-minute demonstration. It requires
no service, simulator, Docker installation, or robot hardware.

### Verification environment note

The canonical admission demo passed in the recorded local verification. A
repository test run under Python 3.14.7 recorded **255 passed, 5 skipped, and
1 failure**. The remaining failure was `tests/test_explain_trace.py`, where
Windows reported `WinError 6` while creating a subprocess. That has not been
established as an SPP implementation failure. Do not claim Python 3.14
compatibility from that run; use the repository's declared supported Python
version (`>=3.11`) for canonical verification.

The focused Core policy demonstration is also supported:

```sh
python demo/clinic/run_demo.py
```

For the browser/API clinic demonstration, use the documented reference server
and static server commands in two terminals:

```sh
python -m uvicorn --app-dir reference/policy-server/src spp.server:app
python -m http.server 8080 -d demo/clinic
```

The documented reference sandbox is optional and requires Docker. From
`sandbox/`:

```sh
docker compose up --build
./scripts/run-demo.ps1
```

The sandbox is a local, non-normative demonstration; it does not supply
deployment credentials, cloud services, or physical enforcement.

Optional integration checks have their own environment requirements. Use the
existing guides and workflows rather than implying they are part of a normal
developer checkout: [Open-RMF](docs/open-rmf.md) and
[ROS 2/Nav2](reference/ros2-enforcer/README.md).

## Current research and interoperability tracks

- **Open-RMF:** the live delivery-consideration adapter and bounded runtime
  fixture are documented in `docs/open-rmf.md`; the site-region-binding note
  and Next Generation design note explore a deliberately thin boundary.
- **IEEE 1872 / P1872.3:** `docs/research/` contains terminology mapping,
  meeting brief, presentation, and question materials for non-normative
  ontology/interoperability discussion.
- **Core Profile / policy-engine interoperability:** the experimental profile,
  native/OPA comparison, and independent challenge test whether a narrow,
  engine-neutral policy contract is reproducible.
- **Trust and portable-result research:** `docs/jcs-rust-verifier-experiment.md`
  records an independent verifier for an experimental JCS admission profile;
  the peer-review entry point links related experimental branch material.

These are research tracks, not evidence of endorsement, adoption,
partnership, standards acceptance, or production readiness.

## Decision principles

- Prefer reuse of established vocabulary and systems over a parallel
  vocabulary.
- Keep SPP narrower than the robotics, fleet, mapping, planning, identity, and
  enforcement systems around it.
- Experimental work must remain visibly experimental and must not silently
  become normative.
- Make interoperability claims only when reproducible fixtures or validation
  evidence supports the exact claim.
- Let external systems retain ownership of their respective domains.

## What a new maintainer should do first

1. Confirm the branch, remote, and clean worktree; read this file and
   [MAINTAINERS.md](MAINTAINERS.md).
2. Read [SPP 0.1](spec/SPP-0.1.md), then `SECURITY.md` and the threat model.
3. Install `requirements-dev.txt`, run the full suite, and run the canonical
   admission demo.
4. Read `docs/README.md`, the relevant release note, and
   `docs/implementing-spp.md` before changing a public exchange surface.
5. Treat work in `docs/experimental/`, `docs/research/`, `docs/design/`,
   `experiments/`, and adapters as non-normative unless a deliberate review
   changes that status.

## Known unresolved questions

The following are recorded questions or ambiguities, not commitments:

- The Open-RMF site-region research leaves external-region identity, revision,
  resolution, overlap, and runtime-location association unresolved.
- Open-RMF design material leaves candidate-plan timing, reassignment,
  revalidation, restriction enforcement, and audit correlation unresolved.
- IEEE ontology research asks for correction of the place/environment/space,
  requirement/capability/evidence, permission/admission, and governed-scope
  distinctions before any future alignment work.
- The next-release hardening plan keeps an experimental, signed, time-bound
  admission envelope and subject-bound revalidation as proposed hardening, not
  normative SPP work.
- GitHub verification establishes the published `v0.3.0-experimental-preview`
  prerelease. `ROADMAP.md` still says publication is pending, and the historical
  checklist leaves prerelease creation unchecked; treat both as stale status
  documentation when describing the current 0.3 release state.
