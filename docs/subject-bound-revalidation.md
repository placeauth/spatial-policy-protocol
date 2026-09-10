# Experimental subject-bound revalidation

`assess_subject_bound_revalidation(...)` composes the existing experimental
AdmissionProfile lifecycle check with a current generic subject/context. It is
**experimental and does not modify normative SPP 0.1**.

Only `VALID` means the prior profile may be relied upon without additional
work. `REVALIDATE`, `REQUALIFY`, and `INVALID` all block use of the prior result
as current admission or authorization. The first two describe possible recovery
work; they do not grant a temporary permit. A place or space change likewise
requires successful requalification before the old profile may be replaced.

The caller supplies authenticated current `RobotState`, PlaceRequirementSet,
supporting evidence, and time. It returns the existing `VALID`, `REVALIDATE`,
`REQUALIFY`, or `INVALID` lifecycle outcomes with structured reasons. Subject
identity/build changes invalidate reuse; changed controller or expired/revoked
evidence require revalidation; changed environment, place/space, applicable
requirements, or a capability named by a current test mapping require selective
requalification. Unrelated capability keys do not invalidate a guarantee.
An equivalent requirement-set metadata/digest change still requires a new
profile binding, but may reuse the previously sufficient evidence without
rerunning its test.

The small local `EvidenceRevocationRegistry` is keyed by evidence digest. It is
not distributed revocation. Capability dependency comparison relies only on the
explicit capability field already named by the configured requirement-to-test
mapping; it does not create a generalized dependency graph.

This does not implement route planning, RMF reassignment, universal identity,
continuous attestation, PKI, policy federation, or physical enforcement.
`DEGRADED` restrictions remain descriptive and must be enforced by the host.
The separately experimental signed-envelope branch may later compose by
verifying envelope authenticity, issuer trust, time, and scope before calling
this assessor; only then may a caller consider the enclosed profile. Lifecycle
validity does not prove restriction enforcement, and a verified `DENIED` result
never becomes permission.
