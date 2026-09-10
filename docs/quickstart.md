# Try SPP in 5 Minutes

This is the canonical PlaceAuth / SPP demonstration. It runs actual inherited policy evaluation plus the experimental evidence-backed admission path locally: no API server, simulator, Docker installation, or robot hardware is required.

## Prerequisites

- Git
- Python 3.11 or newer

## Run the canonical demo

```sh
git clone https://github.com/placeauth/spatial-policy-protocol.git
cd spatial-policy-protocol
python -m pip install -r requirements-dev.txt
python demo/admission/run_demo.py --canonical
```

The output has two layers.

1. **Core policy:** the same machine requests `movement.enter` in three clinic spaces. The lobby returns `PERMIT`, the staff corridor returns `CONDITIONAL` and requires `clinic.staff_escort`, and the pharmacy returns `DENY`. The policy of the destination place changes what the machine may do.
2. **Evidence-based admission:** `PlaceRequirementSet -> ConformancePlan -> EvidenceBundle / EvidenceBinding -> AdmissionProfile`. The same machine moves from the lobby to the patient wing, reuses sufficient movement evidence, and evaluates the new requirements. You then see `ADMITTED`, `DEGRADED` with `sensing.video.capture=disabled`, and `DENIED` for a failed essential human-separation requirement.

Representative output:

```text
PLACE: clinic/staff-corridor
DECISION: CONDITIONAL
REQUIRES: clinic.staff_escort

MOVE: same machine -> clinic/patient-wing
REUSED EVIDENCE: movement.max_speed
ADMISSION: ADMITTED

UNSATISFIED: data.video_retention (nonessential)
ADMISSION: DEGRADED
RESTRICTIONS: sensing.video.capture=disabled

UNSATISFIED: human_separation (essential)
ADMISSION: DENIED
WHY: failed:human_separation
```

## What happened

SPP is not static robot configuration or a geofence. The place declares requirements; the machine evaluates its capabilities and evidence against them; SPP returns a policy decision or scoped admission profile that constrains behavior in that place. A `DEGRADED` profile preserves its explicit restriction, while an essential failure yields `DENIED`.

The command uses deterministic reference logic. It does not demonstrate physical robot behavior, hardware attestation, or production enforcement.

## Verify the checkout

```sh
python -m pytest -q
```

## Continue exploring

- [Repository overview](../README.md)
- [Admission demo details](../demo/admission/README.md)
- [SPP 0.1 core specification](../spec/SPP-0.1.md)
- [Evidence-based spatial admission specification](../spec/evidence-based-admission.md)
- [Security considerations](../spec/security.md)
- [Technical review](technical-review.md)
