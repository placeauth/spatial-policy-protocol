# Changelog

## Unreleased

- Added local Ed25519 signed place requirements and a separate trusted
  policy-authority registry with place/scope authorization and fail-closed
  verified policy-plus-evidence admission. This remains experimental reference
  infrastructure; it adds no SPP 0.1 wire format or PKI.
- Added a deterministic local AdmissionProfile lifecycle assessment with
  explicit revocation, evidence/trust/binding checks, and selective
  requalification triggers. It adds no distributed state or SPP 0.1 schema.

## 0.2.0 — Experimental Preview

- Added evidence sufficiency, selective requalification, and admission-boundary revalidation with explicit TOCTOU rejection.
- Added local Ed25519 signed evidence and trusted-issuer verification; the unsigned trusted legacy path remains explicit for compatibility.
- Added the experimental ROS 2/Nav2 adapter and validated actual Humble `SpeedLimit` transport, ControllerServer-to-plugin-boundary delivery, and stock Regulated Pure Pursuit command behavior from 1.0 m/s to 0.5 m/s under one active `FollowPath` goal.
- Added a bounded Open-RMF Humble Python delivery-acceptance adapter targeting `FleetUpdateHandle.consider_delivery_requests`; the adapter boundary is validated, not an Open-RMF runtime.
- Added deterministic embodiment-specific conformance mapping, a humanoid reference embodiment, and `spp-explain` decision tracing.
- The dependency-free suite reports 186 passed, 4 skipped. This release remains experimental and pre-standardization: it makes no physical-robot safety or guaranteed-stopping claim and is not a production deployment certification.

## 0.1.0 — Experimental Preview

- Initial public release candidate for the Spatial Policy Protocol.
- Added machine-readable policy, request, decision, and admission schemas.
- Added hierarchical place examples for home, hospital, warehouse, and hotel settings.
- Added local and OPA/Rego reference policy evaluation.
- Added a ROS 2 enforcement-point stub.
- Added clinic Core demos and evidence-based Admission scenarios A–D.
- Added deterministic conformance planning, evidence binding, degraded admission, safety denial, and selective requalification examples.
- Added public contribution, security, roadmap, and release documentation.

This release is experimental and is not an adopted standard or production security system.
