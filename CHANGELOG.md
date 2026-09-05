# Changelog

## Unreleased

## 0.2.0 — Experimental Preview (prepared; not yet released)

- Added evidence-sufficiency assessment, provenance, freshness, and state-binding validation; strengthened selective requalification and admission-boundary revalidation, including explicit TOCTOU rejection.
- Added the experimental ROS 2/Nav2 enforcement adapter and real runtime validation of `SpeedLimit` transport, ControllerServer-to-plugin-boundary delivery, and stock Nav2 Regulated Pure Pursuit motion behavior.
- Demonstrated a speed-command change from 1.0 m/s to 0.5 m/s under the same active `FollowPath` goal using a fixed-pose runtime fixture.
- Expanded the normal reference suite to 149 passing tests with 4 environment-dependent skips, plus 5 passing dedicated ROS runtime tests in the Humble validation environment.
- Remains experimental and pre-standardization: this work makes no physical-robot safety claim, does not guarantee stopping, does not yet provide issuer authentication, and is not a production deployment certification.

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
