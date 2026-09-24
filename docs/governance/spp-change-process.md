# SPP Technical Change Process

## Status and purpose

This document defines a conservative technical process for the Spatial Policy
Protocol (SPP). It does not change SPP 0.1 or delegate Foundation authority.
Its purpose is to let contributors and authorized maintainers classify a change,
collect appropriate evidence, and distinguish ordinary repository maintenance
from a normative protocol decision.

SPP remains experimental. A technical review is not, by itself, Foundation
governance approval. PlaceAuth Foundation, Inc. is a nonmembership corporation
whose Board of Directors holds governance authority. The Board may establish
advisory or technical bodies, but those bodies have no Board authority unless
authority is expressly delegated. No such delegated standards authority is
established by this repository.

## Change classes

| Class | Normative semantics | Expected review and evidence | Compatibility analysis | Foundation approval | May merge without changing SPP 0.1? |
| --- | --- | --- | --- | --- | --- |
| Editorial / documentation | No, if it does not alter the meaning of normative text or an exchange contract. | Focused peer review; links and examples checked when affected. | State whether a reader could reasonably infer a behavioral change. | No special approval established. | Yes. |
| Implementation-only | No, when behavior remains conformant with the existing specification and schemas. | Code review, affected tests, and regression evidence. | Identify public API, fixture, or observable-behavior impact. | No special approval established. | Yes. |
| Experimental / research | No; must retain an explicit experimental or non-normative label. | Focused review, appropriate fixtures or documented limitations, and clear scope. | Explain whether it touches or depends on a public experimental surface. | No special approval established. | Yes. |
| Interoperability profile or adapter | No, unless expressly promoted through the normative process. | Independent-implementation or integration evidence where practical; external claims must be bounded. | Identify dependency, mapping, failure boundary, and effect on existing consumers. | No special approval established for an experimental profile or adapter. | Yes. |
| Normative SPP protocol change | Yes: changes the meaning, required behavior, exchange contract, or normative version of SPP. | Full process below, including public and independent technical review where practical. | Required and explicit. | Yes. Explicit approval under Foundation governance is required until authority is formally delegated. | No. |
| Security-sensitive change | Depends on the underlying change class. | Follow `SECURITY.md`; use private handling for vulnerability details until coordinated disclosure is appropriate. | Required when security properties, defaults, trust boundaries, or consumers are affected. | Required only if it is also a normative change or if Foundation governance directs it. | Only if it does not change SPP 0.1. |

When in doubt, classify the change more conservatively. A package-version bump,
adapter, test, or documentation change must not be used to introduce a
normative semantic change indirectly.

## What counts as a normative SPP change

A change is normative when it changes what a conforming implementation is
required, permitted, or prohibited to do under SPP 0.1 or a successor
specification. Examples include changing policy evaluation semantics; the
meaning of actor, action, space, context, decisions, conditions, obligations,
or inheritance; a normative schema exchange contract; or the normative protocol
version.

Adding an experimental reference capability, research note, adapter, example,
or test is not normative merely because it is useful. It becomes normative only
through an explicit, approved specification decision.

## Normative SPP change process

Before a normative change is adopted, the proposal must include:

1. A written proposal or issue that identifies the affected protocol surface.
2. An explicit description of the semantic change and its rationale.
3. Compatibility impact, including migration, versioning, and failure behavior.
4. Synchronized specification, schema, example, and test updates where they
   apply.
5. A public review period appropriate to the scope and risk; no fixed duration
   is established here.
6. Independent technical review where practical, especially for exchange,
   security, or interoperability claims.
7. Resolution of substantive objections, or a documented record of unresolved
   objections and why the proposal proceeds.
8. Explicit approval under Foundation governance. Until the Foundation formally
   delegates that authority, this means approval under the Board's authority;
   this document does not specify a voting threshold or procedure.
9. Versioning and release documentation that distinguish protocol version from
   project/package release version.
10. A permanent decision record under the format below.

The absence of a formally delegated technical standards body is not a reason to
skip review or to infer an approval mechanism. It is a reason to obtain explicit
Foundation-governance approval before changing normative SPP.

## Experimental-to-normative promotion

Experimental work may be considered for normative inclusion only after it has:

- demonstrated a real problem need and clear interoperability value;
- kept a bounded scope rather than absorbing adjacent robotics, identity,
  planning, or enforcement domains;
- produced implementation evidence plus tests or reproducible fixtures;
- analyzed compatibility and, where relevant, security impact;
- received at least one independent technical review;
- considered existing standards and vocabulary before creating new terms; and
- been expressed as clear candidate normative text.

These criteria make work eligible for consideration. They do not make an
experimental profile, adapter, admission mechanism, research conclusion, or
implementation detail normative automatically.

## Permanent decision records

Normative decisions and other material cross-surface decisions should be stored
as concise Markdown records under `docs/decisions/`. This document defines the
location and format only; it does not create retroactive records.

Each record should contain:

```text
Title:
Date:
Status: proposed | accepted | superseded | rejected
Affected protocol/version:
Proposal:
Rationale:
Alternatives considered:
Compatibility impact:
Security impact:
External/interoperability considerations:
Decision authority:
Outcome:
```

For a normative decision, `Decision authority` must identify the applicable
Foundation-governance approval without inventing details that are not recorded.

## Maintainer workflow

1. Classify the change using the table above.
2. Read the affected specification, schemas, tests, examples, and current
   experimental status labels before proposing changes.
3. Make a focused proposal with tests, compatibility impact, and limitations.
4. Seek the review required by the change class; route security-sensitive work
   through `SECURITY.md`.
5. Do not merge a normative semantic change until the normative process,
   including explicit Foundation-governance approval, is complete.
6. Record the final decision when the change requires a decision record.

## Remaining limits

This process documents technical expectations, not a maintainer roster, Board
procedure, delegated authority, credentials, or an external release workflow.
An authorized maintainer can use it to prepare and review a proposal without
guessing. They still need the Foundation's authorized governance path for a
normative decision until a formal delegation is documented.
