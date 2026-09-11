# PlaceAuth / SPP technical peer-review entry point

PlaceAuth is seeking technical criticism of selected experimental work around
the Spatial Policy Protocol (SPP). This page is an entry point, not a claim
that the work is standardized, production-ready, or complete. Reviewers do not
need to understand the full repository before responding.

## 1. What we are asking reviewers to evaluate

Two review tracks are useful and may be considered independently.

### A. Robotics and architecture

SPP explores a narrow question: how can a physical place express
machine-operational constraints that apply to any autonomous system attempting
to operate within that place? Examples include sensing restrictions, speed
constraints, or conditions for entering a bounded space.

We are asking whether the proposed boundary is coherent:

- Place-originated requirements are distinct from robot membership, fleet, or
  organizational taxonomy.
- A place may express declarative constraints without dictating a specific
  planner or robot stack.
- A route or action can require candidate-plan-dependent evaluation when the
  relevant spatial context is known.
- Planner, fleet, and deployment integrations should determine feasibility and
  enforcement without treating SPP as a replacement for those systems.
- There is a real interoperability boundary here, rather than only an
  application-specific policy problem.

### B. Security and interoperability

The admission-trust work explores a portable experimental representation for
signed `AdmissionProfile` artifacts. It uses the
`rfc8785-jcs-v1-experimental` canonicalization profile, a signed envelope,
subject/place/space/time binding, exact `DEGRADED` restriction binding, and
structured verification outcomes.

We are asking whether another implementation could faithfully reproduce the
contract or find an ambiguity that breaks it. Reviewers should focus on the
canonicalization boundary, numeric and timestamp rules, signature preimage,
local issuer expectations, parser behavior, binding semantics, failure
taxonomy, and the limits of reliance on a verified result.

## 2. What is explicitly out of scope

This request is not asking reviewers to decide whether SPP should become a
formal standard, evaluate production PKI or issuer federation, define a
universal capability or restriction ontology, implement a complete robot
planner, assess commercialization or patentability, or draft normative SPP 0.2
language. It also does not ask for a full physical-robot safety claim.

The work should be criticized within its stated experimental boundary. A useful
review can conclude that the boundary is wrong, insufficient, unnecessary, or
not yet ready; it need not propose a full replacement architecture.

## 3. Recommended reading

Read only the track relevant to your review. The links below point to the
specific files, not to a request for broad branch review.

### Architecture track

- [SPP and Open-RMF Next Generation: Place-Originated Requirements and Hierarchical Groups](https://github.com/placeauth/spatial-policy-protocol/blob/main/docs/design/spp-open-rmf-next-generation.md)
- [Planner-aware spatial constraints experiment](https://github.com/placeauth/spatial-policy-protocol/blob/experiment/planner-aware-constraints/demo/planner_constraints/README.md)

### Security and interoperability track

- [Experimental admission-trust interoperability profile](https://github.com/placeauth/spatial-policy-protocol/blob/experiment/admission-trust-profile-draft/docs/experimental/admission-trust-interoperability-profile.md)
- [RFC 8785 JCS canonicalization profile](https://github.com/placeauth/spatial-policy-protocol/blob/experiment/jcs-rust-verifier/docs/jcs-canonicalization-profile.md)
- [Golden vectors and Node verifier](https://github.com/placeauth/spatial-policy-protocol/tree/experiment/jcs-rust-verifier/interop/experimental/admission-trust-jcs)
- [Independent Rust-verifier experiment](https://github.com/placeauth/spatial-policy-protocol/blob/experiment/jcs-rust-verifier/docs/jcs-rust-verifier-experiment.md)
- [Experimental P0 trust-pipeline composition](https://github.com/placeauth/spatial-policy-protocol/blob/experiment/p0-trust-pipeline/docs/p0-trust-pipeline.md)

## 4. Evidence already established

The current evidence is bounded reference validation, not formal verification
or independent external validation. The Python reference implementation,
dependency-free Node verifier, and independent Rust verifier reproduce the
experimental JCS profile across ten deterministic golden vectors. They agree
on canonical bytes, SHA-256 digests, Ed25519 signature inputs and verification,
profile bindings, restriction digests, and expected outcomes.

A deterministic 35-case adversarial corpus exercises duplicate decoded keys,
numeric boundaries, Unicode representations, empty/container forms, and
timestamp spellings. The three implementations have zero cross-language
disagreements on that corpus after the documented numeric-rule correction. The
experimental P0 trust pipeline has also been exercised as a composition of
signed-envelope verification, lifecycle validity, and exact `DEGRADED`
restriction acknowledgement.

Normative SPP 0.1 is unchanged. None of this evidence establishes standards
adoption, production readiness, complete raw-wire-schema interoperability,
physical enforcement, or security against every deployment threat.

## 5. Questions for reviewers

For architecture:

- Is the separation between place policy and machine/fleet/group taxonomy
  coherent and useful?
- Should place-originated requirements remain declarative while planners
  evaluate candidate routes, actions, and sequences?
- Do existing standards or architectures already solve this boundary better?
- Where does this model become unnecessarily complex, duplicate another system,
  or create an unclear operational owner?

For security and interoperability:

- Can the profile be independently implemented from the document and vectors?
- Are any signed fields, parser rules, or binding semantics ambiguous?
- Are there replay, canonicalization, trust, lifecycle, or TOCTOU gaps?
- Is exact `DEGRADED` restriction acknowledgement a useful safety boundary or
  unnecessary machinery?
- What would block serious technical adoption of the experimental profile?

## 6. How to report feedback

Use a GitHub Issue for a concrete bug, vector discrepancy, or documentation
ambiguity. Use a GitHub Discussion, or a linked public discussion, for
architecture questions and alternatives. Send security-sensitive reports to
[security@placeauth.org](mailto:security@placeauth.org). No bug bounty,
response-time commitment, or disclosure SLA is implied by this invitation.

## 7. Current maturity

This work is experimental and is actively seeking technical criticism. It
makes no claim of standards adoption, production readiness, or a normative SPP
protocol change. Experimental artifacts and branches may change incompatibly.

## 8. Review etiquette

Please identify the type of feedback: a correctness bug, interoperability
ambiguity, security issue, architecture disagreement, or scope/preference
concern. Cite the file, section, vector, or observable behavior when possible.
Separating those categories helps maintainers distinguish a defect from a
reasonable alternative design or an intentionally deferred scope decision.
