# Try SPP in 5 Minutes

This path runs a representative evidence-based admission scenario. You will see a place's requirements become a conformance plan, receive passing test results as evidence, and produce an `ADMITTED` operating profile. The same demo also includes `DEGRADED` and `DENIED` outcomes; a second command below shows how SPP handles a move into a space with stricter requirements. Both paths run locally and do not require an API server.

## Prerequisites

- Git
- Python 3.11 or newer

The quickstart uses the repository's existing Python dependencies. Docker is not required.

## Run the primary admission scenario

Clone the repository and create an isolated environment:

```sh
git clone https://github.com/placeauth/spatial-policy-protocol.git
cd spatial-policy-protocol
python -m venv .venv
```

Activate it:

```sh
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate
```

Install the existing development dependencies and run Scenario A:

```sh
python -m pip install -r requirements-dev.txt
python demo/admission/run_demo.py a
```

Scenario A evaluates a robot against the patient-wing requirements. The output includes the requirements, the conformance tests and results, an evidence digest, and the resulting profile. A successful run includes output like this:

```text
requirements: movement.max_speed, human_separation, sensing.facial_recognition, data.video_retention
tests:        ['movement.max_speed', 'human_separation', 'sensing.facial_recognition', 'data.video_retention']
results:      [('movement.max_speed', 'PASS'), ('human_separation', 'PASS'), ('sensing.facial_recognition', 'PASS'), ('data.video_retention', 'PASS')]
admission:    ADMITTED
```

The full output also prints an `evidence: sha256:...` line; its digest value is specific to that run.

For the other admission outcomes, run `python demo/admission/run_demo.py b` for a `DEGRADED` profile or `python demo/admission/run_demo.py c` for a `DENIED` profile.

## Try the spatial-transition example

Run Scenario D:

```sh
python demo/admission/run_demo.py d
```

It first evaluates the robot in the lobby, then moves it to the patient wing. The output shows the requirement delta and that the still-sufficient movement guarantee is reused while only the three new requirements are tested:

```text
delta:        [{'requirement_id': 'movement.max_speed', 'classification': 'REUSED'}, {'requirement_id': 'human_separation', 'classification': 'NEW'}, {'requirement_id': 'sensing.facial_recognition', 'classification': 'NEW'}, {'requirement_id': 'data.video_retention', 'classification': 'NEW'}]
patient wing:
reused:       ['movement.max_speed']
tests:        ['human_separation', 'sensing.facial_recognition', 'data.video_retention']
admission:    ADMITTED
```

This is the central spatial admission flow: the same robot enters a new space with stricter requirements, reuses evidence that remains sufficient, requalifies only unresolved guarantees, and receives an updated profile.

## What just happened?

SPP starts with requirements published for a place and space. The reference implementation converts them into a conformance plan, runs the relevant checks, collects the results in an evidence bundle, and derives an `ADMITTED`, `DEGRADED`, or `DENIED` operating profile.

For a transition, SPP compares existing evidence with the destination requirements. That comparison produces a requirement delta: guarantees that remain sufficient can be reused, while new, stricter, or unresolved requirements are selectively requalified. The resulting evidence supports an updated profile scoped to the destination.

## Next steps

- [Repository overview](../README.md)
- [White paper — From Permission to Admission](whitepaper.md)
- [SPP 0.1 core specification](../spec/SPP-0.1.md)
- [Evidence-based spatial admission specification](../spec/evidence-based-admission.md)
- [Admission demo details](../demo/admission/README.md)
- [Security considerations](../spec/security.md)
- [Contributing guide](../CONTRIBUTING.md)
