# SPP 0.1 threat model

## Assets

- integrity and freshness of spatial policy;
- correctness of actor, space, action, and context assertions;
- confidentiality of facility structure and activity;
- enforcement of deny, conditional, and obligation results;
- availability of safe autonomous operations; and
- audit evidence linking a decision to the evaluated input.

## Trust boundaries

1. spatial authority to policy administration;
2. policy store to decision point;
3. actor or fleet to decision point;
4. decision point to enforcement point;
5. enforcement point to robot or building actuator; and
6. localization and credential systems to request context.

SPP 0.1 specifies the decision contract across these boundaries but does not
make them trustworthy by itself.

## Adversaries and failure cases

| Threat | Example | Required mitigation |
|---|---|---|
| Policy tampering | Pharmacy deny changed to permit | authenticated administration, integrity protection, audit |
| Rollback | Old permissive policy is replayed | monotonic policy versions, freshness checks |
| Actor spoofing | Delivery robot claims to be a safety robot | authenticated actor identity and attestation |
| Context forgery | Caller inserts a staff-escort string | external credential verification |
| Space spoofing | Robot claims it is in the lobby | trusted localization or building corroboration |
| Action confusion | Video storage is described as capture | narrow action vocabulary, enforcement close to actuator |
| Decision replay | Lobby permit reused in pharmacy | bind decision to request, space, version, and lifetime |
| Obligation stripping | Permit forwarded without no-retention | integrity-protected complete response, fail closed |
| Parser differential | YAML aliases or duplicate keys change meaning | canonical ingestion, schema validation, conservative parser |
| Denial of service | Decision endpoint is flooded or isolated | local PDP, rate limits, redundancy, bounded cache |
| Policy probing | Attacker maps restricted spaces from reasons | authorization, rate limits, minimal error disclosure |
| Enforcement bypass | ROS node publishes directly to actuator topic | isolate actuator interface and make enforcer mandatory |

## Evidence and admission threats

Evidence-based admission adds these failure modes:

- forged or modified test results;
- stale or replayed bundles and challenges;
- evidence from the wrong build, controller configuration, policy version, or
  environment/site-model digest;
- compromised embodiment adapters or dishonest self-declaration;
- unavailable attestation hardware;
- proprietary internals leaked through over-detailed evidence;
- unsafe degraded profiles treated as full admission; and
- a malicious robot ignoring the resulting operating profile.

The reference implementation binds evidence to fingerprints, digests, a
challenge, and a validity window, and fails closed on binding mismatch or stale
evidence. E2 evidence is behavioral test evidence, not independent observation.
Higher assurance levels require stronger external signing, attestation, or
observation systems supplied by a deployment.

SPP decisions and AdmissionProfiles are not enforcement. Actual compliance
depends on the enforcement point, robot runtime, actuator isolation, external
infrastructure, and hardware guarantees. A malicious robot can ignore a
profile; the protocol cannot magically force it to comply.

## Out of scope for 0.1

- compromise of the robot operating system or building controller;
- malicious physical modification of sensors or actuators;
- collision avoidance and functional safety certification;
- a standard identity, credential, signing, or revocation system;
- semantic proof that an action name matches physical behavior; and
- conflicts between multiple independent spatial authorities.

## Security invariants

An implementation is conformant only if these invariants hold:

1. no match, error, or unknown state produces a permit;
2. a conditional result never directly releases an action;
3. a permit with an unsupported obligation never releases an action;
4. a child rule cannot silently erase unrelated parent rules;
5. decisions expire and are not reused for a changed request; and
6. safety controls can always override an SPP permit.
