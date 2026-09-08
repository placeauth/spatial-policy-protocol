# Place Package 0.1

A Place Package is one portable JSON file that carries a place's complete
PlaceRequirementSet and a policy-authority signature. It is additive reference
infrastructure: it does not change normative SPP 0.1 policy, request, or
decision semantics.

## Format

The package has these required fields:

- `place_package_version`: supported format version, currently `"0.1"`.
- `place_id`: applicable primary space; it must equal `requirements.space`.
- `policy_id` and `policy_version`: identifiers mirrored from the requirement
  set (`requirement_set_id` and `policy_version`).
- `scope`: one or more applicable space identifiers, including `place_id`.
- `authority_id`: local trusted-policy-authority lookup key.
- `requirements`: complete SPP PlaceRequirementSet payload.
- `metadata`: optional inspectable object for non-normative information such as
  a human-readable name or description.
- `algorithm`: currently `Ed25519`.
- `package_digest`: SHA-256 digest of all package content except
  `package_digest` and `signature`.
- `signature`: base64 Ed25519 signature over canonical authority ID, algorithm,
  and package digest.

The canonical example is
[`examples/place-packages/clinic-patient-wing.json`](../examples/place-packages/clinic-patient-wing.json).

Newly emitted packages use the canonical embedded requirement shape:

```json
{"id":"movement.max_speed","requirement_version":"1.0","value":0.8,"unit":"m/s"}
```

The requirement ID and version resolve the comparison semantics from the
[requirement vocabulary](requirement-vocabulary.md); `movement.max_speed`
version `1.0` therefore means `MAX`, without duplicating that definition in the
package. Creation orders requirements by ID and version and supplies the
canonical unit when an existing built-in omitted it.

Legacy packages may omit `requirement_version` only for a known built-in with
exactly one registered definition, currently built-in `1.0`. An unknown
extension never receives a version default. Extension IDs must use
`x-<organization>.<requirement>` syntax and must also be explicitly registered
by the consumer; valid syntax alone does not establish semantics. Conflicting
duplicate ID/version entries are rejected.

## Canonicalization and verification

JSON is canonicalized as UTF-8 JSON with lexicographically sorted object keys,
stable requirement ordering, and no insignificant whitespace. For the same
semantic package, reference creation produces the same package digest; changing
a requirement ID, version, value, or unit produces a different digest.

An independent consumer must: (1) parse the package and confirm format `0.1`;
(2) confirm the package fields mirror the embedded requirement set; (3) resolve
each requirement ID/version and validate its value, unit, comparison, extension
syntax, and duplicate behavior; (4) look up an enabled local authority and
authorize its place/scope; (5) recompute the package digest; and (6) verify the
Ed25519 signature. Requirements are accepted only after every step passes.

`verify_place_package(...)` returns `PlacePackageVerification` with `valid`,
ordered reason codes, package digest, and authority ID. Typical failures are
`unsupported_place_package_version`, `invalid_place_package`,
`unknown_policy_authority`, `policy_authority_disabled`,
`policy_authority_unauthorized`, `unknown_requirement`,
`incompatible_requirement_version`, `requirement_unit_mismatch`,
`requirement_value_type_mismatch`, `invalid_extension_namespace`,
`conflicting_requirement`, and `place_package_signature_invalid`.

After verification, a consumer hands `movement.max_speed` version `1.0` to a
conformance provider that declares support for that same ID/version, then uses
the resulting evidence for admission. RequirementDelta compares the same ID and
compatible version normally; an incompatible version is `UNRESOLVED` and needs
requalification.

The package supplies an authority identifier, not a trust anchor. Consumers
must provision trusted public keys locally in `TrustedPolicyAuthorityRegistry`.
For an installed reference package, verify with:

```sh
spp-place-package verify examples/place-packages/clinic-patient-wing.json \
  --authority-key <base64-raw-ed25519-public-key> --json
```

`--authority-key` is an explicit local trust input for the reference CLI. A
production consumer should obtain its local trusted authority registry through
its own protected configuration.

## Limits

Place Package 0.1 supports single-file offline exchange and deterministic
tamper detection. It does not provide network discovery, a global registry,
PKI or certificate chains, DNS trust, remote revocation, automatic trust-anchor
distribution, or proof that an authority legally or physically controls a
place.
