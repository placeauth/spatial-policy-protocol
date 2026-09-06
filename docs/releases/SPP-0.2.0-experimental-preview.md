# SPP v0.2.0 Experimental Preview

## Summary

SPP v0.2.0 Experimental Preview advances the reference implementation for technical review of evidence-based spatial admission and a narrowly scoped ROS 2/Nav2 enforcement path. The normative protocol specification remains [SPP 0.1](../../spec/SPP-0.1.md).

## What changed

- Added evidence sufficiency, selective requalification across spatial transitions, and admission-boundary revalidation with explicit TOCTOU rejection.
- Added local Ed25519 signed evidence and trusted-issuer scope/type verification before sufficiency and admission checks.
- Added deterministic embodiment-specific requirement mapping for mobile-base and humanoid reference conformance paths.
- Added `spp-explain`, a deterministic developer trace of requirements, provider selection, evidence reuse, requalification, and admission results.
- Added an experimental SPP-to-Nav2 `SpeedLimit` adapter and validated real ROS 2 Humble transport, the Nav2 ControllerServer/controller-plugin boundary, and stock Regulated Pure Pursuit command behavior.
- SPP can gate Open-RMF task eligibility using evidence-backed AdmissionProfiles. The [bounded adapter](../open-rmf.md) targets Humble Python `FleetUpdateHandle.consider_delivery_requests`; the adapter boundary is validated, but no Open-RMF runtime was tested. DEGRADED eligibility requires explicit restriction acceptance; multi-robot assignment and execution revalidation remain host duties.

## Evidence/admission hardening

- Added conservative evidence-sufficiency assessment with explicit reuse and retest reasons.
- Validated provenance, freshness, and policy, environment, actor, controller, plan, and configuration state bindings at the admission boundary.
- Added a local trusted-issuer registry. The verified path rejects unknown, disabled, unauthorized, unsigned, and tampered evidence before sufficiency and admission evaluation.

## ROS 2/Nav2 runtime validation

- Added an optional adapter that maps an `AdmissionProfile` movement limit to Nav2 `SpeedLimit` messages.
- Validated real ROS 2 Humble `SpeedLimit` transport.
- Validated real Nav2 `ControllerServer` delivery to a pluginlib-loaded controller test boundary.
- Validated stock Nav2 Regulated Pure Pursuit command behavior in a fixed-pose runtime fixture.

## Demonstrated behavior

With one active `FollowPath` goal, the stock Regulated Pure Pursuit fixture emitted command speeds of 1.0 m/s and then 0.5 m/s after the SPP-derived limit changed. The normal dependency-free suite reports **186 passed, 4 skipped**. This demonstrates bounded command-output behavior in the stated fixture; it is not a physical-motion or stopping claim.

## Current limitations

- Experimental and pre-standardization; not an adopted standard or production security system.
- No physical-robot safety claim and no guaranteed stopping behavior.
- No PKI, remote trust discovery, production key management, HSM protection, certificate lifecycle, or distributed revocation infrastructure.
- No distributed replay service, broad vendor interoperability validation, or production deployment certification.
- The embodiment registry is a local reference configuration, not a plugin
  system, vendor certification program, or physical-safety guarantee.
- Runtime validation is scoped to the documented Humble fixtures and does not certify arbitrary Nav2 configurations.

## Quickstart

Follow [Try SPP in 5 Minutes](../quickstart.md) for the reference setup, then run `pytest` for the normal suite. The ROS 2/Nav2 runtime validation is optional and documented in the [ROS 2 enforcer guide](../../reference/ros2-enforcer/README.md).

## Whitepaper

Read the canonical [PlaceAuth whitepaper](../whitepaper.md) or its [PDF edition](../whitepaper/PlaceAuth-SPP-White-Paper.pdf) for the project rationale and interoperability model.

## Technical Review

Review [Technical Review](../technical-review.md) for bounded claims, validation evidence, and feedback paths.

## Compatibility

SPP 0.2.0 remains compatible with the normative SPP 0.1 Core specification. The new admission and ROS integration work is experimental reference-implementation material and does not revise SPP 0.1 policy, request, or decision semantics.

## License/status

Licensed under Apache-2.0. Certain technologies described by PlaceAuth are patent pending. This release remains experimental and pre-standardization.
