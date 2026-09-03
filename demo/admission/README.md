# Evidence-based admission demo

This deterministic reference demo shows how a place-defined requirement set is converted into conformance tests, evidence, and an operating profile. It uses a declared mobile-base state and the same robot application in every scenario.

## Run

From the repository root, after installing `requirements-dev.txt`:

```sh
python demo/admission/run_demo.py a
python demo/admission/run_demo.py b
python demo/admission/run_demo.py c
python demo/admission/run_demo.py d
```

## Scenarios

| Scenario | Change | Expected profile |
| --- | --- | --- |
| A | All patient-wing requirements pass | `ADMITTED` |
| B | Video-retention requirement fails | `DEGRADED`, with `sensing.video.capture=disabled` |
| C | Essential human-separation requirement fails | `DENIED` |
| D | Move from the lobby to the patient wing | Reuse movement evidence, test the three new guarantees, then `ADMITTED` |

Representative output:

```text
SCENARIO A - FULL ADMISSION
admission:    ADMITTED

SCENARIO B - DEGRADED ADMISSION
admission:    DEGRADED
restrictions: ['sensing.video.capture=disabled']

SCENARIO C - SAFETY FAILURE
admission:    DENIED
reasons:      ['failed:human_separation']

SCENARIO D - SPATIAL TRANSITION / DELTA REQUALIFICATION
reused:       ['movement.max_speed']
tests:        ['human_separation', 'sensing.facial_recognition', 'data.video_retention']
admission:    ADMITTED
```

The evidence registry and replay protection in this demo are lightweight in-memory reference infrastructure. They are not a distributed production service. The demo does not claim hardware attestation, independent observation, or physical enforcement.

The robot application remains unchanged. The place publishes a different requirement set, and SPP determines which existing guarantees remain sufficient and which must be requalified.
