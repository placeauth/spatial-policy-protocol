# SPP v0.3.0 Experimental Preview

## Operational Interoperability

## Overview

SPP v0.3.0 Experimental Preview prepares the reference implementation for
independent implementation and bounded operational integration. It strengthens
the interoperability boundaries around Place Packages, requirement semantics,
conformance providers, decision traces, profile lifecycle, trust, and
place-side/runtime integration. The normative protocol specification remains
[SPP 0.1](../../spec/SPP-0.1.md).

## Interoperability contracts

- **Decision trace 0.1:** schema-defined, deterministic trace output that
  independent tooling can consume. A trace explains a decision; it is not
  authorization.
- **Versioned requirement vocabulary:** dotted IDs, explicit versions,
  canonical units, comparison semantics, and `x-<organization>.<requirement>`
  extension conventions. Unknown or incompatible versions fail closed or remain
  unresolved.
- **Place Package 0.1:** canonical versioned requirement entries, exact
  version/unit validation, deterministic signed single-file JSON, and
  fail-closed unknown extensions.
- **Conformance-provider contract:** provider ID/version, requirement
  ID/version, embodiment, assurance, evidence-type compatibility,
  deterministic selection, and provider-result validation.

## Runtime / integration validation

- **ROS 2 Humble / Nav2:** evidence-backed operating profiles changed the
  commanded speed of a running Nav2 robot from 1.0 m/s to 0.5 m/s under the
  same active `FollowPath` goal. The validated path used
  `nav2_msgs/msg/SpeedLimit`, ControllerServer, and stock Regulated Pure
  Pursuit.
- **Open-RMF Humble:** using RMF fleet adapter Python 2.1.8, a real `Adapter`,
  `FleetUpdateHandle`, one stationary registered test robot, and real ROS
  delivery bids, four delivery-consideration callback invocations were
  exercised. `ADMITTED` produced a bid proposal; `DENIED` produced no proposal
  with `admission_denied`. `DEGRADED` was not runtime-validated.
- **Facility access:** a bounded generic facility-side adapter grants a
  matching-place `ADMITTED` profile; a `DEGRADED` profile grants only when every
  restriction is explicitly accepted; denied, wrong-place, stale, or revoked
  profiles fail closed.

## Trust and lifecycle

- Separate local Ed25519 trust roles verify signed evidence issuers and signed
  place-policy authorities. There is no PKI or federation claim.
- AdmissionProfiles have explicit `VALID`, `REVALIDATE`, `REQUALIFY`, and
  `INVALID` lifecycle states, including local revocation and invalidation on
  policy, evidence, binding, or trust changes.

## Developer / implementation tooling

The [independent implementation guide](../implementing-spp.md) documents the
path from Place Package through vocabulary, provider, evidence, admission,
lifecycle, and trace without relying on the Python reference implementation.

## Validation status

The dependency-free reference suite reports **255 passed, 5 skipped, 1
unrelated Windows pytest-cache warning**. Runtime fixtures are separately
covered by the ROS 2 Nav2 and Open-RMF Runtime GitHub Actions workflows; their
release-candidate status must be confirmed before publication.

## Known limitations

- Experimental and pre-standardization; not an adopted standard, production
  security system, or certification program.
- No physical-robot safety claim, functional-safety certification, or guaranteed
  stopping behavior.
- Open-RMF validation does not establish physical dispatch execution, traffic
  negotiation, fleet-wide production integration, or physical motion.
- Facility validation does not establish a physical door, vendor system,
  BACnet, MQTT, or building-system integration.
- No PKI, remote trust discovery, production key management, HSM protection,
  certificate lifecycle, distributed revocation, or physical trust in evidence
  generation.

## Upgrade / compatibility notes

- The normative protocol specification remains **SPP 0.1**.
- Place Package remains **0.1** and explain trace remains **0.1**.
- Existing v0.2 tags and history are unchanged.
- Newly emitted Place Packages carry explicit requirement versions and canonical
  units. Legacy built-ins have only documented deterministic compatibility
  handling; unknown extensions require explicit local registration.
- Provider compatibility now requires exact requirement-version compatibility.

## License / status

Licensed under Apache-2.0. Certain technologies described by PlaceAuth are
patent pending. This prepared release remains experimental and
pre-standardization.
