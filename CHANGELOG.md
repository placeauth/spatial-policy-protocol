# Changelog

## Unreleased

- Hardened Place Package 0.1 requirement semantics: new package output carries
  explicit vocabulary versions and canonical units, validation rejects
  incompatible versions, invalid extensions, and conflicting requirements, and
  deterministic creation orders requirements without changing the package format.

- Added a local versioned requirement vocabulary with built-in definitions,
  exact provider-version compatibility, additive PlaceRequirementSet fields,
  and version-aware RequirementDelta handling.

- Added trace format 0.1: a stable JSON schema, canonical fixture output, and
  deterministic machine-readable projection of existing explain decisions. It
  does not change SPP 0.1 or admission behavior.

- Validated Open-RMF Humble delivery consideration with one registered test
  robot: ADMITTED produces a bid proposal; DENIED returns admission_denied.
  This validates task eligibility, not dispatch execution or physical motion.

- Defined the SPP 0.3 Operational Interoperability milestone and its bounded
  documentation, validation, and independent-implementation priorities. This
  is planning only and does not revise SPP 0.1 or the 0.2.0 release.
- Added local Ed25519 signed place requirements and a separate trusted
  policy-authority registry with place/scope authorization and fail-closed
  verified policy-plus-evidence admission. This remains experimental reference
  infrastructure; it adds no SPP 0.1 wire format or PKI.
- Added a deterministic local AdmissionProfile lifecycle assessment with
  explicit revocation, evidence/trust/binding checks, and selective
  requalification triggers. It adds no distributed state or SPP 0.1 schema.
- Added Place Package 0.1: a portable, single-file JSON PlaceRequirementSet
  exchange with local policy-authority verification and Ed25519 tamper
  detection. It adds no discovery, registry, or SPP 0.1 wire change.
- Added an explicit local external conformance-provider interface with
  deterministic requirement, embodiment, and assurance-level selection. It
  feeds the existing evidence and admission path and adds no provider discovery,
  remote trust service, or SPP 0.1 wire change.

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
