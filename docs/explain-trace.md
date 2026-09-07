# Explain an SPP decision

`spp-explain` emits a stable, machine-readable projection of an existing
reference admission decision. It explains how a decision was reached; it does
not evaluate policy, add admission semantics, or authorize an operation.

## Trace format 0.1

`spp-explain --json` emits trace format version `0.1`. This is a trace-format
version, not an SPP protocol version. Incompatible changes to documented fields
require a trace-version change.

```sh
spp-explain --scenario patient-wing --json
```

The schema is [explain-trace.schema.json](../schema/explain-trace.schema.json).
A canonical result generated from the actual patient-wing fixture is
[patient-wing.json](../examples/traces/patient-wing.json).

## Envelope

The top-level envelope has these stable fields:

- `trace_version` and deterministic `decision_id`
- `place` and `subject` summaries
- `requirements`, `provider_selection`, and `evidence_assessment`
- `requirement_delta`, `selected_tests`, and `reused_guarantees`
- `admission`, `lifecycle`, `restrictions`, and `reasons`

Requirements retain their existing IDs, actions, operators, bounds, units, and
any available scope. Provider selections expose the selected provider ID,
embodiment, assurance level, and unresolved reason. Evidence assessment uses
only references and canonical reason codes; it does not embed evidence payloads.

The delta is the existing RequirementDelta projection, with classified items
and grouped reusable, new, stricter, unresolved, and invalidated references.
`selected_tests` identifies the chosen test and provider. Reused guarantees
reference source evidence. `admission.outcome` is one of `ADMITTED`,
`DEGRADED`, or `DENIED`; its reasons and restrictions are duplicated at the
envelope level for simple consumers.

When lifecycle assessment applies, `lifecycle` contains the existing `VALID`,
`REVALIDATE`, `REQUALIFY`, or `INVALID` status, reasons, reusable and
invalidated guarantees, and required action. It is `null` when no assessment is
available.

## Compatibility and consumption

Consumers should validate input against the schema, require
`trace_version: "0.1"`, and interpret only documented fields and existing
reason codes. Arrays preserve the deterministic order of the underlying
requirement, assessment, and test outputs. Optional values are represented as
`null`; absent fields are not substituted with inferred values.

The trace is intentionally compact. It does not guarantee the stability of
undocumented fields, human-readable console formatting, private payloads,
runtime object identities, or a complete audit history. Human output remains
available for developer inspection:

```sh
spp-explain --scenario patient-wing
```

## Security and privacy

The trace contains no private keys, signatures, raw evidence payloads, secrets,
or internal Python object dumps. It is still a decision explanation, not a
substitute for verifying the policy, evidence, trust state, AdmissionProfile,
or enforcement point that a deployment relies on.
