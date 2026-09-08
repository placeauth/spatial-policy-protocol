# Changelog

## 0.3.0 — Experimental Preview (release-ready)

- Added a deterministic, schema-defined machine-readable decision trace format
  0.1 for independent tooling; it explains decisions but is not authorization.

- Added a versioned requirement vocabulary with dotted identifiers, explicit
  requirement versions, canonical units, exact comparison semantics, extension
  namespace conventions, and fail-closed incompatible-version handling.

- Hardened Place Package 0.1 with canonical versioned requirements, exact
  unit/version validation, fail-closed unknown extensions, deterministic signed
  package semantics, and independently verifiable single-file JSON.

- Hardened the external conformance-provider contract with provider identity
  and version, exact requirement-version, embodiment, assurance, evidence-type
  compatibility, deterministic selection, and provider-result validation.

- Added an implementation-oriented guide for independent experimental SPP
  consumers covering Place Packages, vocabulary, providers, evidence, admission,
  lifecycle, trace output, and fail-closed interoperability behavior.

- Added an explicit AdmissionProfile lifecycle with `VALID`, `REVALIDATE`,
  `REQUALIFY`, and `INVALID` states, local revocation, trust-anchor
  invalidation, and policy/evidence/binding change handling.

- Added local Ed25519 verification for signed evidence issuers and separate
  signed place-policy authorities. These are distinct local trust roles and do
  not add PKI, remote discovery, or trust federation.

- Validated the evidence-backed ROS 2 Humble / Nav2 path through
  `nav2_msgs/msg/SpeedLimit`, ControllerServer, and stock Regulated Pure
  Pursuit: under one active `FollowPath` goal, commanded speed changed from
  1.0 m/s to 0.5 m/s. This is not a physical stopping, functional-safety, or
  physical-world validation claim.

- Validated a live Open-RMF Humble task-eligibility fixture using fleet adapter
  Python 2.1.8, a real `Adapter`, `FleetUpdateHandle`, one stationary registered
  test robot, real delivery bids, and four delivery-consideration callback
  invocations. `ADMITTED` produced a bid proposal; `DENIED` produced no proposal
  with `admission_denied`. `DEGRADED` remains adapter-tested, not
  runtime-validated. No dispatch execution, traffic negotiation, fleet-wide,
  or physical-motion claim is made.

- Added a bounded facility-side access-control adapter. It maps current
  AdmissionProfiles to exact place-access decisions, preserves DEGRADED
  restrictions only when explicitly accepted, and fails closed on stale,
  revoked, invalid, denied, or wrong-place profiles. It adds no physical door,
  building protocol, or vendor integration.

- SPP 0.3 remains experimental and pre-standardization. It does not revise the
  normative SPP 0.1 protocol specification or claim production certification,
  physical safety, PKI, or trust federation.

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
