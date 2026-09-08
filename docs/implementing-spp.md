# Implementing SPP Independently

*A practical guide to consuming place requirements, producing conformance evidence, requesting admission, and maintaining operating profiles without depending on the PlaceAuth Python reference implementation.*

This guide describes the experimental SPP Conformance and Admission reference semantics. It is not a replacement for [SPP 0.1](../spec/SPP-0.1.md), a complete normative specification, or a certification program. An independent team does not need to copy the Python package structure. Interoperability comes from matching the documented serialized formats and decision semantics.

`Place Package → requirement vocabulary → conformance provider → conformance result → EvidenceBundle → signed evidence → admission → AdmissionProfile → profile lifecycle → decision trace`

## 1. Implementation boundary

An implementation needs a Place Package parser/verifier, requirement-vocabulary resolver, local conformance-provider registry, evidence and binding representations, evidence-signature verification, policy-authority verification, admission evaluation, AdmissionProfile lifecycle assessment, and trace-format `0.1` output. It may implement those pieces in any language or process model.

Use the published [Place Package](place-package.md), [requirement vocabulary](requirement-vocabulary.md), [provider contract](conformance-providers.md), [requirement mapping](requirement-mapping.md), [evidence and requalification guidance](evidence-sufficiency.md), [trace guide](explain-trace.md), and [security considerations](../spec/security.md) as the exchange-boundary references. The [technical review](technical-review.md) describes the current validation scope and limits.

## 2. Consume a Place Package

Place Package format `0.1` is a signed, single-file transport for a complete PlaceRequirementSet. Process it in this order:

1. Parse the JSON object and confirm `place_package_version` is `"0.1"`.
2. Confirm mirrored package fields match the embedded requirement set.
3. Resolve every requirement ID and version.
4. Validate its value type, canonical unit, comparison semantics, extension syntax, and duplicate behavior.
5. Find an enabled, locally provisioned policy authority authorized for the stated place and scope.
6. Recompute the package digest and verify the Ed25519 signature.

Accept requirements only after every check succeeds. A compact canonical entry from the clinic example is:

```json
{"id":"movement.max_speed","requirement_version":"1.0","value":0.8,"unit":"m/s"}
```

New packages carry an explicit version. A legacy package may omit a version only for a known built-in with one unambiguous definition, currently `1.0`. An unknown extension never receives that default. Extensions use `x-<organization>.<requirement>` syntax, such as `x-example.visibility`, but valid syntax alone does not establish semantics: register the definition locally or reject it.

## 3. Resolve the requirement vocabulary

Requirement identifiers are lowercase dotted names. Current built-ins include `movement.max_speed` version `1.0`, the compatibility identifier `human_separation`, `sensing.facial_recognition`, and `data.video_retention`. Definitions establish value type, canonical unit, and comparison meaning:

- `MAX`: measured value is at most the requirement value.
- `MIN`: measured value is at least the requirement value.
- `EXACT`: measured value equals the requirement value and type.
- `PROHIBITED`: the prohibited behavior is false.

Versions match exactly. A change to meaning, type, unit, or comparison is a new version; do not silently downgrade or compare different versions. Numeric units are canonical (`m/s`, `m`, and `seconds` for current built-ins); this reference model does not convert units. Unknown or incompatible requirements are `UNRESOLVED`, not an invitation to guess a meaning.

## 4. Select a conformance provider

Register providers explicitly in local configuration. Compatibility is the intersection of requirement ID/version, subject embodiment, and requested minimum assurance. Select deterministically:

1. Exact requirement ID/version.
2. Exact embodiment.
3. Assurance at or above the requested E0–E4 level.
4. Priority descending, then provider ID as a stable tie-break.

```python
ConformanceProviderDescriptor(
    provider_id="gait-speed-provider", provider_version="1.0",
    supported_requirement_types={"movement.max_speed"},
    supported_requirement_versions={"movement.max_speed": {"1.0"}},
    supported_embodiments={"humanoid"},
    supported_assurance_levels={"E2", "E3"},
    evidence_type="behavioral_test", priority=100,
)
```

`movement.max_speed` version `2.0` is incompatible with that descriptor. Likewise, a humanoid-only provider is not compatible with a mobile robot. When no candidate remains, return `UNRESOLVED` with its deterministic reason; do not fall back to lower assurance or infer support from a provider name. Provider registration is not provider trust and is not evidence-issuer trust.

## 5. Execute conformance and validate its result

Give the selected provider the requirement, authenticated subject and embodiment context, requested assurance target, and relevant test context. Its machine-readable result needs provider ID/version, requirement ID/version, pass/fail, measured value and canonical unit, assurance level, evidence type, reasons, and metadata.

Before converting that output to an evidence test result, verify that provider and requirement versions match the selected descriptor, the embodiment is supported, returned assurance is declared and sufficient, the evidence type matches, the unit matches the vocabulary definition, and structural fields are internally consistent. Invalid output fails closed and must not become evidence. This checks contract compatibility; it does not attest that a provider observed physical reality.

## 6. Produce evidence

A validated provider result becomes a plan test result. Build an `EvidenceBundle` with its `EvidenceBinding`. Bind evidence to the actor, robot build, controller configuration, embodiment, environment, place-policy and plan digests, challenge, assurance level, scope, issue time, expiry time, and complete test-result coverage.

Evidence reuse is conservative. A source record must have intact digests, matching authenticated bindings and scope, current freshness, sufficient assurance, unique result coverage, and a direct passing test that proves the destination bound. Existing evidence is neither blindly reused nor blindly discarded.

## 7. Sign and verify evidence

The reference signed-evidence path uses Ed25519 over canonical serialization and a SHA-256 digest of the complete bundle. A local `TrustedIssuerRegistry` maps issuer IDs to public keys, enabled state, allowed evidence types, and allowed scopes. Verify the signature and issuer authorization before running sufficiency or admission. Unknown, disabled, unauthorized, or invalid issuers fail closed.

A conformance provider is not necessarily an evidence issuer. The provider returns a test result; the evidence issuer attests the complete EvidenceBundle. This is a local reference trust model, not PKI, certificate lifecycle, remote key discovery, HSM custody, or proof of the evidence-generation process.

## 8. Verify place authority separately

Use a separate `TrustedPolicyAuthorityRegistry` for signed place requirements and Place Packages. An authority entry contains an ID, Ed25519 public key, allowed places, allowed scopes, and enabled state. Verify the complete requirements payload and signature before planning or admission relies on it.

An evidence issuer is not automatically authorized to define place requirements. Unknown, disabled, out-of-scope, or invalid policy authorities cause policy rejection. The registry is local configuration, not a global authority federation or proof of legal or physical place control.

## 9. Request admission

Admission combines trusted current place requirements, trusted machine evidence, and authenticated subject/place context into an `AdmissionProfile`. The outcomes are `ADMITTED`, `DEGRADED`, and `DENIED`. `DEGRADED` permits operation only with the profile's explicit restrictions; it is not equivalent to `ADMITTED`. Essential failures fail closed to `DENIED`. Admission independently checks fresh and reused evidence at the boundary, rather than trusting a prior planning result.

## 10. Selectively requalify on transitions

For a destination, derive a `RequirementDelta` from existing evidence and new requirements. Reuse guarantees that remain sufficient; requalify guarantees that are new, stricter, unresolved, invalidated, or expired. A relaxed bound may be reusable when the original direct proof entails it. Same ID with an incompatible requirement version is `UNRESOLVED`, never a normal numeric comparison.

## 11. Maintain the AdmissionProfile lifecycle

Lifecycle assessment is read-only: it does not silently mutate a profile. It returns `VALID`, `REVALIDATE`, `REQUALIFY`, or `INVALID` and tells the caller what action is required. Evidence expiry or controller changes require `REVALIDATE`; environment, policy, destination, new, or stricter requirements require `REQUALIFY`; actor/build changes, explicit profile revocation, failed current trust checks, disabled issuers, or disabled policy authorities produce `INVALID`. Supply authenticated current state and trusted time.

## 12. Emit a machine-readable trace

Trace format `0.1` explains a decision; it is not authorization. The reference command is:

```sh
spp-explain --scenario patient-wing --json
```

Its top-level information includes requirements, provider selection, evidence assessment, RequirementDelta, selected tests, reused guarantees, admission, lifecycle, restrictions, and reasons. Consumers must still verify the policy, evidence, trust state, profile, and enforcement point they rely on.

## 13. Fail-closed rules

| Condition | Required behavior |
| --- | --- |
| Unknown requirement | `UNRESOLVED` |
| Incompatible requirement version | `UNRESOLVED` |
| No compatible provider | `UNRESOLVED` |
| Invalid provider result | Reject evidence creation |
| Unknown or invalid evidence issuer | `DENIED` |
| Unknown or invalid policy authority | Reject policy |
| Expired evidence | `REVALIDATE` or `REQUALIFY` |
| Revoked profile | `INVALID` |

## 14. Minimal implementation checklist

- [ ] Parse and verify Place Package `0.1`.
- [ ] Resolve requirement ID/version and reject unknown semantics.
- [ ] Select compatible providers deterministically.
- [ ] Validate provider results before evidence conversion.
- [ ] Build bound, fresh evidence and verify signed evidence.
- [ ] Verify signed place policy with a separate authority registry.
- [ ] Produce `ADMITTED`, `DEGRADED`, or `DENIED` profiles.
- [ ] Assess `VALID`, `REVALIDATE`, `REQUALIFY`, or `INVALID` lifecycle state.
- [ ] Emit schema-valid trace format `0.1`.

## 15. Current interoperability examples and limits

The reference project has validated a ROS 2/Nav2 Humble path in which an operating-profile change changed stock-controller commanded speed from `1.0 m/s` to `0.5 m/s` under the same `FollowPath` goal. It also validates an Open-RMF Humble `FleetUpdateHandle` path with a registered stationary test robot and real delivery bids: `consider_delivery_requests` produced a proposal for `ADMITTED` and no proposal for `DENIED`.

These are bounded runtime validations, not physical-robot safety validation, physical RMF dispatch execution validation, or production certification. SPP does not provide PKI, global authority federation, remote vocabulary registries, remote provider discovery, plugin marketplaces, automatic unit conversion, distributed revocation, a mandatory cloud service, or universal robot support.
