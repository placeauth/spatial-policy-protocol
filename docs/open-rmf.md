# Open-RMF admission adapter

SPP can gate Open-RMF task eligibility using evidence-backed AdmissionProfiles.

**Validation level: live delivery consideration and bid response.** SPP task
eligibility has been validated through a live Open-RMF Humble
FleetUpdateHandle.consider_delivery_requests runtime path using a minimal test
fleet and registered test robot.

The fixture creates a real Adapter, uses add_fleet and add_robot, and obtains a
RobotUpdateHandle. A real ROS BidNotice reaches the registered pickup/dropoff
callbacks. ADMITTED produces a BidResponse with a proposal; DENIED produces no
proposal and returns admission_denied. Both requests invoke two callbacks.
The profiles reuse the existing adapter-test structure; this test validates the
runtime bridge, not evidence issuance or signature verification end to end.

## Reproduce the runtime validation

Use Ubuntu 22.04 with ROS 2 Humble and binary package
ros-humble-rmf-fleet-adapter-python (locally validated version:
2.1.8-1jammy.20260726.143012). Install pytest and the existing SPP Python
dependencies. In a sourced Humble shell, start the packaged schedule service:

```sh
ros2 run rmf_traffic_ros2 rmf_traffic_schedule
```

In another sourced shell at the repository root:

```sh
SPP_RMF_RUNTIME=1 python3 -m pytest -v -s tests/open_rmf/test_rmf_runtime.py
```

The isolated Open-RMF Runtime workflow runs only this test. Missing runtime
dependencies fail when explicitly enabled; ordinary runs skip it.

All configuration is TEST ONLY: one lobby waypoint marked as a charger,
linear/angular velocity and acceleration limits (1.0, 0.5), a 0.2 m circular
footprint, and one stationary robot. Mandatory planner defaults use a 24 V,
40 Ah, 8 A battery, 20 kg mass, 10 inertia, 0.2 friction, and 1 W device loads;
battery drain accounting is disabled. Command callbacks immediately acknowledge
startup paths; no task is dispatched and pickup/dropoff share the lobby.

This is not physical robot, building integration, fleet-wide scheduler,
traffic negotiation, dispatch execution, or production deployment validation.
DEGRADED restriction semantics remain covered by the existing adapter tests,
not this runtime fixture.

## Use

Install the repository's existing development dependencies, then run:

```sh
python demo/open_rmf/run_demo.py
python -m pytest tests/test_open_rmf.py -q
```

The demo generates fresh local evidence and calls `admit_evidence_backed` for
each destination. Its task decisions come from `spp_admission.open_rmf.map_profile`.
It prints explicitly that RMF is not connected. The staff-assistance example
accepts a restriction only to demonstrate mapping; it does not enforce assistance.

`TaskContext(actor_id, place, space)` identifies the intended admission scope.
The mapper rejects absent, malformed, mismatched and DENIED profiles. ADMITTED
is eligible; DEGRADED requires nonempty restrictions and explicit acceptance of
every restriction. Restrictions from both profile locations are preserved in
`RMFAdmissionDecision.restrictions`, including on rejection. Exact accepted
restriction strings must be supplied by trusted deployment configuration backed
by real enforcement. Request data must never control that configuration.

## Verified upstream hook

The [Open-RMF Humble Python binding](https://github.com/open-rmf/rmf_ros2/blob/humble/rmf_fleet_adapter_python/src/adapter.cpp)
exposes `FleetUpdateHandle.consider_delivery_requests(consider_pickup,
consider_dropoff)`. Each Python callback receives a description and returns
`rmf_adapter.fleet_update_handle.Confirmation`. The bridge uses `accept()` for
eligibility or `set_errors(...)` for rejection; Python returns the confirmation
rather than receiving it as the C++ callback's second argument.

```python
from spp_admission.open_rmf import make_delivery_callback

# Existing RMF FleetUpdateHandle and deployment callbacks, supplied by the host:
pickup = make_delivery_callback(resolve_pickup_context, evaluate_admission)
dropoff = make_delivery_callback(resolve_dropoff_context, evaluate_admission)
fleet_handle.consider_delivery_requests(pickup, dropoff)
```

The resolver maps the host's delivery description into an explicit `TaskContext`;
this adapter invents no destination field or discovery protocol. The admission
callback must return a freshly evaluated profile from the trusted admission
service, preferably `admit_verified_evidence_backed` for signed evidence.
Resolver or admission errors reject the request. Restrictions are accepted only
when configured for this callback; RMF Confirmation itself does not enforce them.

## Scope and trust limits

This is a fleet acceptance hook, with no selected robot ID in its callback.
Use a single-robot fleet or an externally enforced actor-assignment constraint.
A profile for one robot must not authorize arbitrary members of a multi-robot
fleet. Acceptance is eligibility, not dispatch completion or execution approval:
the host must revalidate the selected robot at execution and after state changes.
This implementation adds no execution intercept or reassignment mechanism.

AdmissionProfile is a constructible object with no standalone expiry field. The
mapper's structural checks cannot prove signature authenticity or freshness;
the trusted callback must perform admission with current evidence/state/time on
each request. No replay policy, schema, signature logic, ROS/Nav2 code, or SPP 0.1
protocol semantics are changed. There is no stopping or physical safety claim.
