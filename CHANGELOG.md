# Changelog

## Unreleased

- Validated the existing Nav2 adapter using real ROS 2 Humble pub/sub (three runtime cases); added a separate binary-package ROS CI job. This proves message transport, not Nav2 controller consumption or physical stopping.

- Replaced the ROS 2 intent-forwarding stub with an optional Nav2 `SpeedLimit` adapter and ROS-free AdmissionProfile mapping, focused tests and a three-profile demo. Physical stopping remains deployment-specific.

- Added `admit_evidence_backed` to independently enforce source-evidence sufficiency, freshness, binding, assurance and coverage at admission time; retained trusted legacy `admit` for compatibility.
- Added a planning-to-admission controller-change demo and adversarial boundary tests.

- Added conservative source-evidence sufficiency assessment and reduced conformance planning with explicit reuse/retest reasons.
- Added a four-space transition demo with tampering, expiry and controller-change variants, and adversarial reuse tests.

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
