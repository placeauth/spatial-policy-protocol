# Roadmap

SPP is an experimental protocol project. This roadmap describes validation and
interoperability work, not adoption commitments. The latest published
implementation release is SPP 0.2.0 Experimental Preview. SPP v0.3.0
Experimental Preview is prepared for release; the normative protocol
specification remains SPP 0.1.

## SPP 0.3 — Operational Interoperability

The 0.3 milestone makes SPP easier to implement, integrate, validate, and
extend across independent systems. It does not add protocol features merely for
feature breadth.

### 1. Machine-readable explain / trace

- **Objective:** make existing decision reasoning consumable by tooling.
- **Deliverable:** a stable JSON trace shape for the existing explain path.
- **Complete when:** documented fixtures produce deterministic, versioned trace
  output without changing admission semantics.
- **Non-goals:** a second audit, event, or telemetry framework.

Trace format 0.1 and its schema are now implemented. Future work may only
change this format through explicit trace-versioning.

### 2. Requirement vocabulary / namespacing

- **Objective:** make independent extensions safer and more predictable.
- **Deliverable:** naming, versioning, unit, bound, and compatibility
  conventions for requirements.
- **Complete when:** guidance and examples show how an independent
  implementation adds a compatible extension.
- **Non-goals:** standardizing every robot capability or a universal robotics
  vocabulary.

Vocabulary version 1.0 is now defined for the current built-ins, including
provider compatibility and Place Package behavior.

### 3. Place Package hardening

- **Objective:** stabilize the portable package as an exchange boundary.
- **Deliverable:** clarified field semantics, versioning, canonicalization, and
  independent-consumer guidance.
- **Complete when:** a reader can implement package production or consumption
  without relying on the Python source.
- **Non-goals:** network discovery, PKI expansion, or remote package services.

Place Package 0.1 now emits explicit requirement versions and canonical units,
with deterministic ordering and vocabulary-aware verification. Independent
consumer guidance is published; no format-version change was required.

### 4. Conformance-provider contract hardening

- **Objective:** make the external provider interface precise for third parties.
- **Deliverable:** formal descriptor and result semantics, assurance behavior,
  and implementation guidance.
- **Complete when:** an independent provider can register, select, execute, and
  contribute evidence through the documented contract.
- **Non-goals:** dynamic plugins, a provider marketplace, or provider
  certification.

The reference contract now requires exact requirement-version declarations and
validates execution results before evidence conversion. Provider identity is
still local configuration, not a trust authority.

### 5. Third-party implementation guidance

- **Objective:** document a minimal implementation path independent of this
  reference codebase.
- **Deliverable:** an implement-from-scratch guide covering Place Packages,
  providers, evidence issuance, admission, and profile lifecycle.
- **Complete when:** the guide connects those boundaries using only published
  semantics and fixtures.
- **Non-goals:** a mandatory SDK, cloud service, or governance program.

The independent implementation guide is published at
[Implementing SPP Independently](docs/implementing-spp.md). It connects the
published exchange boundaries without prescribing the reference code structure.

### 6. Live Open-RMF runtime validation

- **Objective:** exercise the bounded Open-RMF task-admission hook in a real
  runtime.
- **Deliverable:** a documented runtime fixture using the intended
  `FleetUpdateHandle` task-admission boundary.
- **Complete when:** an actual runtime hook is exercised and its limits are
  reported. The bounded fixture now exercises real delivery callbacks and bid
  responses using one stationary registered test robot; see
  [validation details](docs/open-rmf.md).
- **Non-goals:** a full Open-RMF fleet deployment or broad RMF integration.

### 7. Second enforcement or facility-side integration

- **Objective:** test SPP at a distinct external execution boundary.
- **Deliverable:** one targeted facility/building-side or otherwise non-Nav2
  integration with bounded validation.
- **Complete when:** the selected boundary accepts an SPP-derived decision or
  profile in a documented fixture.
- **Non-goals:** a near-duplicate Nav2 path or a mandatory building platform.

The bounded [facility access-control boundary](docs/facility-access.md) now
maps a current AdmissionProfile to an exact place-access decision, preserving
DEGRADED restrictions and lifecycle fail-closed behavior. It is a pure
reference decision boundary, not building-hardware validation.

### 8. Release-readiness pass

- **Objective:** ensure the 0.3 surfaces tell one consistent, bounded story.
- **Deliverable:** final documentation, fixture, compatibility, and claim
  review.
- **Complete when:** the Definition of Done below is met and release materials
  distinguish implementation version 0.3 from normative SPP 0.1.
- **Non-goals:** changing the normative SPP version without a separate protocol
  process.

## 0.3 release status

- **0.3 implementation:** COMPLETE
- **Release preparation:** IN PROGRESS
- **Publication:** PENDING

The reference implementation/package version is prepared as `0.3.0`. The
normative protocol specification remains SPP 0.1; Place Package and explain
trace formats remain 0.1.

## Recommended order

1. Machine-readable explain / trace
2. Requirement vocabulary / namespacing
3. Place Package hardening
4. Conformance-provider contract hardening
5. Third-party implementation guidance
6. Live Open-RMF runtime validation
7. Second enforcement or facility-side integration
8. Release-readiness pass

## Definition of Done

SPP 0.3 is ready only when new 0.3 surfaces have no unresolved versioning
ambiguity; the independent implementation path is documented; the
machine-readable trace is stable enough for tooling; requirement naming and
versioning conventions are published; Place Packages and provider interfaces
are documented as implementable exchange and extension boundaries; at least one
new external integration validation beyond the current state or live Open-RMF
runtime validation is complete; tests are green; documentation, README,
roadmap, and release notes agree; no unsupported production or safety claims
are made; and the implementation release remains explicitly distinct from the
normative SPP 0.1 specification.

## 0.3 non-goals

- Full PKI or global trust federation
- Remote provider marketplace or dynamic plugin ecosystem
- Production safety certification or a mandatory cloud service
- Universal robotics vocabulary
- Full Open-RMF fleet deployment
- Distributed revocation service
- Broad governance restructuring

These items are research directions. They do not promise adoption,
certification, production security, or participation by any particular
organization.
