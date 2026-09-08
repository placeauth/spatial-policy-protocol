# Facility access-control boundary

The experimental facility access adapter is a small place-side boundary that
maps an `AdmissionProfile` to a deterministic `FacilityAccessDecision`. It
answers whether a facility endpoint would grant access to one exact target
place. It is not a hardware driver, a physical-door simulation, a building
automation platform, or a commercial access-control integration.

## Flow

`AdmissionProfile → FacilityAccessDecision → reference door-controller boundary`

Call `map_profile_to_access(profile, target_place, accepted_restrictions=...)`
or configure `ReferenceDoorController` with its accepted restrictions and call
`authorize(...)`. The decision contains `allowed`, target place, deterministic
profile identifier, profile outcome, accepted and rejected restrictions, and
reason codes.

## Admission and restriction behavior

- `ADMITTED` may grant access only when the profile applies to the exact target
  place and every profile restriction is accepted by the facility.
- `DEGRADED` may grant access only when every restriction is explicitly and
  exactly accepted. It is never treated as equivalent to `ADMITTED`.
- `DENIED`, a missing profile, an unknown profile status, or a profile for a
  different place denies access.

Restriction matching uses exact strings and deterministic sorted output. A
profile restricted by `video_disabled` is allowed only when the facility has
configured that exact restriction as acceptable. The adapter does not infer
that a controller can enforce a restriction.

## Lifecycle behavior

An optional `ProfileLifecycleAssessment` is read-only input. `VALID` continues
normal evaluation. `REVALIDATE`, `REQUALIFY`, and `INVALID` all deny with
`facility_profile_not_current`; the caller must obtain a current profile rather
than silently granting access. Explicit revocation is represented by the
existing `INVALID` lifecycle result.

## Fail-closed reasons

The adapter uses a small facility-specific set: `facility_profile_missing`,
`facility_profile_wrong_place`, `facility_profile_denied`,
`facility_profile_not_current`, and `facility_restriction_not_accepted`.
No access is granted when the adapter cannot establish a current profile for
the requested place.

## Demonstration

```sh
python demo/facility_access/run_demo.py
```

The demo exercises an admitted patient-wing profile, accepted and rejected
degraded `video_disabled` restrictions, a denied profile, and an invalid
lifecycle. It uses the real adapter logic only.

## Limits

The adapter does not validate a physical lock, relay, reader, BACnet, MQTT,
vendor API, network transport, facility identity, or physical security. A
deployment must authenticate profile provenance and current lifecycle state,
protect its controller configuration, and independently enforce every accepted
restriction.
