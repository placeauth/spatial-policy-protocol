# SPP 0.1.0 Experimental Preview

## Purpose

This experimental preview presents the Spatial Policy Protocol (SPP) as an open interoperability layer between autonomous systems and physical environments. A place publishes machine-readable requirements, a machine demonstrates conformance, and the resulting evidence supports a spatially scoped operating profile.

SPP is developed under the PlaceAuth project. The robot application remains unchanged while the place requirements determine which actions are permitted, conditional, or denied.

## Current architecture

- **SPP Core** — place requirements, hierarchical spaces, inherited policy, action families, and `permit` / `deny` / `conditional` decisions.
- **SPP Conformance** *(experimental)* — deterministic conformance plans, requirement-to-proof mapping, evidence, and assurance levels.
- **SPP Admission** *(experimental)* — evidence verification, `ADMITTED` / `DEGRADED` / `DENIED` profiles, `RequirementDelta`, and selective requalification.

## Implemented capabilities

- JSON Schemas and YAML examples for common physical environments.
- Local Python and OPA/Rego policy evaluation.
- Hierarchical policy inheritance with deny-by-default behavior.
- Deterministic evidence generation and binding.
- Evidence digest, freshness, policy/environment binding, and reference replay checks.
- Explicit degraded restrictions and essential-safety denial.
- ROS 2 enforcement-point stub and Docker Compose reference stack.

## Four admission scenarios

```sh
python demo/admission/run_demo.py a  # full conformance -> ADMITTED
python demo/admission/run_demo.py b  # video-retention failure -> DEGRADED
python demo/admission/run_demo.py c  # essential safety failure -> DENIED
python demo/admission/run_demo.py d  # transition, reuse, and selective requalification
```

Scenario D reuses the lobby movement guarantee and runs only the three unresolved patient-wing checks before issuing `ADMITTED`.

## Test status

The reference environment reports **35 passed, 1 skipped, 0 failed** with the full pytest suite.

## Limitations and security disclaimer

This is an experimental preview, not an adopted standard or production security system. SPP does not itself force a malicious autonomous system to obey an operating profile. Trust depends on evidence assurance, enforcement-point integrity, robot/runtime integrity, site infrastructure, hardware guarantees, and any attestation or independent observation mechanisms used by a deployment.

Not production-ready: hardware attestation, distributed replay protection, production ROS 2/Nav2 or Open-RMF integration, certification infrastructure, discovery, production identity/PKI, physical enforcement guarantees, and broad vendor interoperability testing.

## Contributing

See [CONTRIBUTING.md](https://github.com/placeauth/spatial-policy-protocol/blob/main/CONTRIBUTING.md), [SECURITY.md](https://github.com/placeauth/spatial-policy-protocol/blob/main/SECURITY.md), and [ROADMAP.md](https://github.com/placeauth/spatial-policy-protocol/blob/main/ROADMAP.md). Reproduce the demos, review the schemas, report implementation bugs, and propose interoperability improvements with focused tests where possible.

Licensed under Apache-2.0. Certain technologies described in this project are patent pending.
