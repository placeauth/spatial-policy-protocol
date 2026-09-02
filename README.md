# Spatial Policy Protocol (SPP)

SPP is an experimental, vendor-neutral authorization contract for physical
places and autonomous actors. It is an open-protocol project from **PlaceAuth**,
the parent company behind the work.

> May Actor X perform Action Y in Space Z under Context C?

Version 0.1 defines policy, request, and decision documents; inherited policy
for hierarchical spaces; six initial action families; and permit, deny, and
conditional outcomes. It deliberately does not define robot identity,
navigation, mapping, transport security, policy discovery, or a new policy
programming language.

## What works

- JSON Schemas for policy bundles, decision requests, and decisions
- Human-readable YAML policies for a home, hospital, warehouse, and hotel
- Deterministic inheritance: nearest matching space rule wins
- Deny-by-default evaluation
- Conditional decisions with named authorizations and obligations
- A Python policy server with local and OPA/Rego modes
- A fail-closed ROS 2 enforcement-point stub
- A runnable clinic demo and automated tests

The action families in 0.1 are \`movement\`, \`sensing\`, \`data\`,
\`manipulation\`, \`infrastructure\`, and \`human_interaction\`.

## Quick start

Python 3.11 or newer is required.

\`\`\`sh
python -m venv .venv
.venv/Scripts/activate
python -m pip install -r requirements-dev.txt
pytest
python demo/clinic/run_demo.py
\`\`\`

On macOS or Linux, activate the environment with
\`source .venv/bin/activate\`.

To run the HTTP server and browser demo:

\`\`\`sh
python -m uvicorn --app-dir reference/policy-server/src spp.server:app
# In a second terminal:
python -m http.server 8080 -d demo/clinic
\`\`\`

Open <http://127.0.0.1:8080>.

## One request

\`\`\`json
{
  "spp_version": "0.1",
  "request_id": "delivery-42",
  "actor": {
    "id": "robot:demo:delivery-01",
    "type": "delivery_robot"
  },
  "space": "clinic/staff-corridor",
  "action": {
    "family": "movement",
    "name": "enter"
  },
  "context": {
    "purpose": "package_delivery"
  }
}
\`\`\`

The hospital policy returns \`conditional\` and requires
\`clinic.staff_escort\`. Add that value to \`context.authorizations\` and the
same request becomes \`permit\`. A request to enter \`clinic/pharmacy\` is
denied by the nearer pharmacy rule.

## Run with OPA

The Python service is the protocol adapter and the Rego module is the policy
decision point:

\`\`\`sh
docker compose up --build
\`\`\`

This starts OPA on port 8181 and the SPP API on port 8000. The server resolves
the requested space into a leaf-to-root policy chain, then asks Rego to select
and evaluate the first applicable rule. The default local evaluator uses the
same semantics and keeps development and tests lightweight.

## Repository map

\`\`\`text
schema/                      JSON Schemas
spec/                        Protocol, security, and threat model
examples/                    Four policy bundles
reference/policy-server/     Python API and Rego policy
reference/ros2-enforcer/     ROS 2 enforcement stub
demo/clinic/                 CLI and browser demonstrations
tests/                       Schema and behavior tests
\`\`\`

## Project identity

PlaceAuth is the project steward; SPP itself is designed to remain vendor
neutral so that a place can publish policy for robots and other autonomous
actors from any manufacturer. The name PlaceAuth describes the broader company
direction, while SPP names this protocol and its reference implementation.

## Status

SPP 0.1 is a working discussion draft, not a security standard. Signatures,
discovery, identity federation, audit exchange, geometry, conflict sets, and
standard action registries are intentionally deferred. See
[the specification](spec/SPP-0.1.md), [security considerations](spec/security.md),
and [threat model](spec/threat-model.md).

Licensed under Apache-2.0. Contributions and independent implementations are
welcome.
