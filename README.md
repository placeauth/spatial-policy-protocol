# PlaceAuth / Spatial Policy Protocol (SPP)

An experimental, open interoperability protocol for establishing how autonomous systems may operate in physical environments.

[![Status: Experimental](https://img.shields.io/badge/status-experimental-orange.svg)](docs/releases/SPP-0.1.0-experimental-preview.md)
[![SPP 0.1.0 Experimental Preview](https://img.shields.io/badge/SPP-0.1.0%20Experimental%20Preview-blue.svg)](docs/releases/SPP-0.1.0-experimental-preview.md)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)

[Quickstart](docs/quickstart.md) · [White Paper](docs/whitepaper.md) · [PDF White Paper](docs/whitepaper/PlaceAuth-SPP-White-Paper.pdf) · [Specification](spec/SPP-0.1.md) · [Release notes](docs/releases/SPP-0.1.0-experimental-preview.md)

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

For the technical overview, read the [white paper](docs/whitepaper.md), [SPP 0.1 specification](spec/SPP-0.1.md), and [SPP 0.1.0 release notes](docs/releases/SPP-0.1.0-experimental-preview.md).

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

## Security and status

> **Status: SPP 0.1.0 Experimental Preview**

The current reference implementation demonstrates:

- machine-readable place requirements and hierarchical inheritance;
- deterministic conformance planning and requirement-to-proof mapping;
- evidence generation, binding, integrity, freshness, and replay checks;
- `ADMITTED`, `DEGRADED`, and `DENIED` admission profiles;
- degraded operation with explicit restrictions;
- essential-safety denial;
- spatial transition deltas and selective requalification; and
- local and OPA/Rego policy evaluation.

Not yet production-ready:

- hardware attestation and certification infrastructure;
- distributed replay protection;
- production ROS 2/Nav2 or Open-RMF integration;
- discovery and production identity/PKI;
- physical enforcement guarantees; and
- broad vendor interoperability testing.

SPP does not itself force a malicious autonomous system to obey an operating profile. Trust depends on evidence assurance, the enforcement point, robot/runtime integrity, site infrastructure, hardware guarantees, and any attestation or independent observation mechanisms used by a deployment. Conditional decisions must remain blocked until their requirements are satisfied, and safety systems remain independently authoritative. Read [security considerations](spec/security.md) and the [threat model](spec/threat-model.md) before connecting SPP to physical systems.

SPP 0.1.0 is a draft reference implementation for pre-standardization experimentation. Certain technologies described in this project are patent pending.

## Repository map

```text
schema/                    JSON Schemas
spec/                      protocol, security, and threat model
examples/                  home, hospital, warehouse, and hotel policies
reference/policy-server/   Python API and OPA/Rego adapter
reference/ros2-enforcer/   ROS 2 enforcement-point stub
reference/admission/       experimental conformance/admission implementation
demo/clinic/               CLI, browser, and policy A/B demonstrations
demo/admission/            evidence-based admission scenarios A-D
docs/                      specifications, guides, white paper, and release notes
.github/                   issue templates and test workflow
tests/                     schema, API, policy, and admission tests
```

## Documentation

Use the [documentation index](docs/README.md) for the core specification, evidence and admission model, schemas, security and threat model, demos, roadmap, release notes, and white paper.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), and [SECURITY.md](SECURITY.md). Protocol feedback, reproducible implementation bugs, and interoperability proposals are welcome. All contributions should include focused tests or examples where practical.

## License

SPP is licensed under the [Apache License 2.0](LICENSE).
