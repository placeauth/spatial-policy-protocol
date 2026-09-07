# PlaceAuth / Spatial Policy Protocol (SPP)

An experimental, open interoperability protocol for establishing how autonomous systems may operate in physical environments.

[![Status: Experimental](https://img.shields.io/badge/status-experimental-orange.svg)](CHANGELOG.md)
[![SPP v0.2.0 Experimental Preview](https://img.shields.io/badge/SPP-v0.2.0%20Experimental%20Preview-blue.svg)](docs/releases/SPP-0.2.0-experimental-preview.md)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)

[Quickstart](docs/quickstart.md) · [Technical review](docs/technical-review.md) · [Whitepaper](docs/whitepaper.md) · [PDF Whitepaper](docs/whitepaper/PlaceAuth-SPP-White-Paper.pdf) · [Specification](spec/SPP-0.1.md) · [SPP v0.2 release notes](docs/releases/SPP-0.2.0-experimental-preview.md) · [Latest release: v0.2](docs/releases/SPP-0.2.0-experimental-preview.md)

## The core question

> May Actor X perform Action Y in Space Z under Context C?

SPP gives a place a machine-readable way to publish requirements and gives an autonomous system a vendor-neutral way to demonstrate conformance. The result is a spatially scoped operating profile that can be evaluated again when the system enters a different space.

PlaceAuth is the umbrella project; SPP is the protocol and specification family. PlaceAuth is not a formal standards body.

## Example: the place changes

The same robot application moves from a lobby into a patient wing. The destination publishes stricter requirements; sufficient movement evidence is reused, while new or unresolved guarantees are tested before the profile is updated.

```text
Same robot + new space
        │
        ├─ reuse sufficient movement evidence
        ├─ test new human-separation guarantee
        ├─ test new sensing and data restrictions
        └─ issue an updated ADMITTED / DEGRADED / DENIED profile
```

```yaml
Lobby:
  movement.max_speed: <= 0.8

Patient Wing:
  movement.max_speed: <= 0.8
  human_separation: >= 1.2
  sensing.facial_recognition: prohibited
  data.video_retention: = 0
```

The protocol lifecycle is:

```text
Place requirements → Conformance plan → Evidence → Admission profile → Spatial transition
```

For the technical overview, read the [whitepaper](docs/whitepaper.md), [SPP 0.1 specification](spec/SPP-0.1.md), [SPP v0.2 release notes](docs/releases/SPP-0.2.0-experimental-preview.md), and the [current-main changelog](CHANGELOG.md).

## Where SPP fits

SPP is a place-centered decision and evidence contract. It complements, rather than replaces:

- authorization and identity systems, which establish who an actor is and what it may request;
- geofencing and navigation, which constrain where a system can travel;
- policy engines such as OPA/Rego, which can evaluate a policy decision;
- evidence and attestation systems, which provide assurance about a capability or test result;
- ROS 2, Nav2, and Open-RMF, which integrate robot behavior and facility resources;
- fleet managers and building-automation systems, which operate deployed robots and infrastructure.

SPP connects these surfaces around a physical place and a specific action under context. It is not itself an access-control product, attestation service, navigation stack, fleet manager, or building-automation system.

## What SPP is

- A place-centered policy and decision contract.
- A way to express requirements for movement, sensing, data, manipulation, infrastructure, and human interaction.
- A hierarchy-aware model in which child spaces inherit applicable parent requirements.
- A conformance and evidence model for a reference implementation.
- A protocol surface intended for independent implementations and technical review.

## What SPP is not

- Not merely a robot-permissions product or a geofencing service.
- Not an adopted industry standard.
- Not a substitute for safety controls, hardware guarantees, enforcement, or trusted identity.
- Not production-ready security infrastructure.

## Public architecture

```text
PlaceAuth
└── Spatial Policy Protocol (SPP)
    ├── SPP Core
    ├── SPP Conformance       (experimental)
    └── SPP Admission         (experimental)
```

### SPP Core

SPP Core defines place requirements, spatial policy semantics, hierarchical inheritance, and the `permit`, `deny`, and `conditional` decision outcomes. The initial action families are `movement`, `sensing`, `data`, `manipulation`, `infrastructure`, and `human_interaction`.

### SPP Conformance

The experimental Conformance layer turns requirements into a `ConformancePlan`, selects requirement-to-proof mappings appropriate to an embodiment, and records evidence with assurance levels. It supports deterministic reference checks without requiring a particular robot vendor, middleware, or transport.

### SPP Admission

The experimental Admission layer verifies evidence and derives `ADMITTED`, `DEGRADED`, or `DENIED` operating profiles. It models `RequirementDelta` across spatial transitions so that sufficient guarantees can be reused and unresolved guarantees selectively requalified.

## Quick start

Python 3.11 or newer is required.

```sh
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux:       source .venv/bin/activate
python -m pip install -r requirements-dev.txt
pytest
```

Run the zero-service clinic demo:

```sh
python demo/clinic/run_demo.py
```

Start the reference API:

```sh
python -m uvicorn --app-dir reference/policy-server/src spp.server:app
```

The API exposes `GET /health` and `POST /v1/decision`. A browser demo can be served in a second terminal:

```sh
python -m http.server 8080 -d demo/clinic
```

Open <http://127.0.0.1:8080>.

The Docker Compose reference stack starts the API and OPA together:

```sh
docker compose up --build
```

## Evidence-based admission demo

Run the four deterministic scenarios:

```sh
python demo/admission/run_demo.py a  # full conformance -> ADMITTED
python demo/admission/run_demo.py b  # video-retention failure -> DEGRADED
python demo/admission/run_demo.py c  # essential safety failure -> DENIED
python demo/admission/run_demo.py d  # spatial transition and requalification
```

Scenario D demonstrates the central interoperability point: the robot application remains unchanged while the destination place supplies different requirements. Existing sufficient evidence is reused and only unresolved guarantees are tested again. See [the admission demo guide](demo/admission/README.md).

## Embodiment-specific conformance mapping

The same place requirement can select different registered conformance
mechanisms for a mobile base and a humanoid while retaining the same SPP
vocabulary. Run the deterministic reference demonstration:

```sh
python demo/embodiment_mapping/run_demo.py
```

See [embodiment-specific requirement mapping](docs/requirement-mapping.md) for
the provider model, deterministic selection rule, and limitations.

### External conformance providers

External conformance providers can explicitly register a descriptor, be
selected deterministically for a requirement and embodiment, and feed their
result into the existing evidence and admission path. See [external conformance
providers](docs/conformance-providers.md) and run:

```sh
python demo/conformance_provider/run_demo.py
```

## Explain a decision

After `python -m pip install -e .`, trace the existing patient-wing
requalification path from requirements through provider selection, evidence
assessment, tests, and admission:

```sh
spp-explain --scenario patient-wing
```

Use `--json` for deterministic machine-readable output. See [the explain trace
guide](docs/explain-trace.md) for the other fixture-backed scenarios.

## Security and status

Inspect evidence sufficiency across a four-space route, including a stricter
bound and a denied destination:

```sh
python demo/requalification/run_demo.py
```

The [evidence sufficiency guide](docs/evidence-sufficiency.md) covers integrity,
freshness, scope and configuration checks, plus tamper and expiry demo variants.

> **Current release:** SPP v0.2.0 Experimental Preview. The normative protocol specification remains SPP 0.1.

The current reference implementation demonstrates:

- machine-readable place requirements and hierarchical inheritance;
- deterministic conformance planning and requirement-to-proof mapping;
- evidence generation, binding, integrity, freshness, and replay checks;
- admission-time evidence sufficiency and provenance revalidation, including TOCTOU rejection;
- `ADMITTED`, `DEGRADED`, and `DENIED` admission profiles;
- degraded operation with explicit restrictions;
- essential-safety denial;
- spatial transition deltas and selective requalification; and
- local and OPA/Rego policy evaluation.

Not yet production-ready:

- hardware attestation and certification infrastructure;
- distributed replay protection;
- production-grade ROS 2/Nav2 or Open-RMF deployment integration;
- discovery and production identity/PKI;
- physical enforcement guarantees; and
- broad vendor interoperability testing.

SPP does not itself force a malicious autonomous system to obey an operating profile. Trust depends on evidence assurance, the enforcement point, robot/runtime integrity, site infrastructure, hardware guarantees, and any attestation or independent observation mechanisms used by a deployment. Conditional decisions must remain blocked until their requirements are satisfied, and safety systems remain independently authoritative. Read [security considerations](spec/security.md) and the [threat model](spec/threat-model.md) before connecting SPP to physical systems.

The SPP 0.1 protocol is implemented by an experimental reference implementation for pre-standardization experimentation. Certain technologies described in this project are patent pending.

## ROS 2 / Nav2 integration

Open-RMF: SPP can gate Open-RMF task eligibility using evidence-backed AdmissionProfiles.
The [bounded adapter](docs/open-rmf.md) targets Humble's delivery-acceptance callback;
only the adapter boundary is tested, with no RMF runtime validation. Run
`python demo/open_rmf/run_demo.py` for ADMITTED, DEGRADED and DENIED examples.

The experimental adapter maps a trusted `AdmissionProfile` to a deterministic
Nav2 enforcement plan, then publishes `movement.max_speed` through an optional
ROS runtime adapter. Denied navigation is represented fail-closed; actual stop
enforcement and navigation gating depend on the surrounding robot deployment.
No ROS installation is needed for the mapping demo:

```sh
python demo/ros2_enforcement/run_demo.py
```

See [Nav2 integration and limitations](reference/ros2-enforcer/README.md).

SPP has been validated changing the speed behavior of a running Nav2 runtime from a higher operating limit to an SPP-imposed 0.5 m/s limit, measured in stock-controller command output with a fixed-pose test fixture; physical robot speed and stopping remain unproven.

## Repository map

```text
schema/                    JSON Schemas
spec/                      protocol, security, and threat model
examples/                  home, hospital, warehouse, and hotel policies
reference/policy-server/   Python API and OPA/Rego adapter
reference/ros2-enforcer/   experimental admission-to-Nav2 speed adapter
reference/admission/       experimental conformance/admission implementation
demo/clinic/               CLI, browser, and policy A/B demonstrations
demo/admission/            evidence-based admission scenarios A-D
demo/embodiment_mapping/   mobile-base and humanoid mapping demonstration
docs/                      specifications, guides, whitepaper, and release notes
.github/                   issue templates and test workflow
tests/                     schema, API, policy, admission, and ROS runtime tests
```

## Documentation

Use the [documentation index](docs/README.md) for the core specification, evidence and admission model, schemas, security and threat model, demos, roadmap, release notes, and whitepaper. The [SPP 0.3 Operational Interoperability roadmap](ROADMAP.md) defines the next planned development milestone.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), and [SECURITY.md](SECURITY.md). Protocol feedback, reproducible implementation bugs, and interoperability proposals are welcome. All contributions should include focused tests or examples where practical.

## License

SPP is licensed under the [Apache License 2.0](LICENSE).
