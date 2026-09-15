# SPP Core Profile Experiment

## Question being tested

> Does SPP add value as an engine-neutral interoperability profile even if
> existing policy decision points perform the evaluation?

This experiment gives a native adapter and OPA/Rego the **same JSON fixture**.
Both produce one compact result: `PERMIT`, `DENY`, or `CONDITIONAL`, plus
obligations and deterministic reason codes.

## Run it

From the repository root, with Docker Desktop running:

```sh
python experiments/core-profile/run_conformance.py
```

The harness uses the official `openpolicyagent/opa:1.17.0-static` CLI image
and prints the native/OPA result for every fixture. Expected output ends with:

```text
summary:
8/8 fixtures matched
```

To run only the native adapter tests:

```sh
python -m pytest experiments/core-profile/tests -q
```

## What this demonstrates

- one place-policy profile, input, resolved scope chain, and deployment
  obligation capability set;
- two independently implemented evaluators;
- matching profile-significant outputs for permit, deny, conditional,
  scope-mismatch, context, inheritance, and unsupported-obligation cases; and
- fail-closed reliance when a required obligation is not recognized by the
  deployment.

`CONDITIONAL` means the required authorization is absent; it is not a permit.
The unsupported-obligation fixture returns `DENY`, even though the underlying
place rule is conditional, because the deployment cannot interpret the required
obligation. This proves configuration acknowledgement only—not handler
execution or physical enforcement.

## What this does not demonstrate

- that OPA is inadequate or that SPP needs its own policy engine;
- production security, robot safety, physical enforcement, or certification;
- identity, PKI, transport security, geometry, maps, routing, task allocation,
  capability ontology, evidence generation, admission, or lifecycle behavior;
- IEEE, Open-RMF, ROS, or standards-body endorsement; or
- a normative change to SPP 0.1.

SPP Core intentionally resembles ABAC/PDP models. That is not a defect. The
experiment tests whether a constrained place/robotics interoperability profile
is useful above general-purpose policy engines. If this contract cannot be
adopted independently of the evaluator, it is evidence against SPP as a
separate standard.
