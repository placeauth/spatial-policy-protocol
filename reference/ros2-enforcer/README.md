# Experimental SPP ROS 2 / Nav2 adapter

`AdmissionProfile` → `map_profile()` → `Nav2EnforcementPlan` → `Nav2Enforcer.apply()`.

This replaces the old HTTP intent-forwarding node and its `enforcer` executable.
It is a library boundary for the trusted admission service, not a new network
endpoint. Admission/core logic and wire formats are unchanged.

## Mapping without ROS

From the repository root, with the normal Python dependencies installed:

```sh
python demo/ros2_enforcement/run_demo.py
```

The demo uses illustrative real `AdmissionProfile` objects, not newly measured
robot evidence. It prints 1.0 m/s for ADMITTED, 0.5 m/s for DEGRADED and no action
for DENIED. The mapper reads `operating_profile.guarantees` entries with
`id: movement.max_speed`, `operator: <=` and a finite numeric `value` in m/s.
It does not infer speed from capabilities or unrelated guarantees.

Both profile restriction lists are checked. The sole supported textual
restriction is `movement.max_speed<=NUMBER`, optionally with whitespace around
`<=`, in m/s. Multiple bounds choose the minimum. Unsupported restrictions deny
the enforcement plan instead of silently discarding obligations. This is an
adapter convention for the existing text field, not a new protocol schema.

Malformed, negative, non-finite or boolean bounds fail closed. Zero also refuses
navigation: **Nav2 uses zero to remove a speed limit, not to stop a robot**.
No speed restriction maps to `max_speed_mps=None` and publishes nothing; it does
not clear any previously applied limit. Explicit clearance and arbitration with
other limit publishers belong to the deployment. Other guarantees are not
enforced by this speed-only adapter and require their own enforcement points.

## Optional ROS runtime

Target interface: ROS 2 Humble / Nav2's
[`nav2_msgs/msg/SpeedLimit`](https://github.com/ros-navigation/navigation2/blob/humble/nav2_msgs/msg/SpeedLimit.msg).
Publish with `percentage=False`, `speed_limit=<m/s>` and the node clock timestamp.
The [controller server](https://github.com/ros-navigation/navigation2/blob/humble/nav2_controller/src/controller_server.cpp)
subscribes to its `speed_limit_topic` parameter (default `speed_limit`, QoS depth
10) and forwards the limit to controller plugins. Configure the adapter topic
and namespace to match that server and verify the selected plugin honors it.

Use an existing sourced ROS/Nav2 environment with `rclpy` and `nav2_msgs`.
No ROS distribution is installed by this project. Copy/link this directory into
a ROS workspace's `src/`, then run `colcon build --packages-select spp_enforcer`
and source its install setup. Also make the repository admission package
available to that Python environment, using the normal repository dependencies:

```sh
# Run from the SPP repository root in the sourced ROS shell.
export PYTHONPATH="$PWD/reference/admission/src:$PYTHONPATH"
```

In the trusted service, using its already initialized and spinning rclpy node:

```python
from spp_enforcer.node import Nav2Enforcer

enforcer = Nav2Enforcer(node, speed_limit_topic="speed_limit")
# profile must come from trusted admit_evidence_backed(), for this robot/state.
plan = enforcer.apply(profile)
if not plan.navigation_allowed:
    # Refuse new navigation; invoke the deployment's stop/cancel path if active.
    return
# Continue only after deployment-specific controller readiness/enforcement checks.
```

Keep the enforcer/publisher alive. Apply after subscriber discovery; lack of a
subscriber or a publication exception returns a denied plan. Subscriber count
does not prove that Nav2 applied the limit. Publishing has no application-level
acknowledgment. Controller restarts/reconfiguration require reapplication and
readiness checks; this adapter does not manage lifecycle, retries or persistence.

DENIED issues no enabling message. It **does not stop an already moving robot**
or cancel a Nav2 action. The caller must gate navigation, handle active stopping,
and serialize admission with runtime changes. No safety certification is implied.

Profiles are trusted inputs, not authenticated by their Python type. The adapter
does not revalidate evidence or actor bindings; use the enforced admission
boundary and bind it to the correct robot. ROS imports are deferred until runtime
construction; missing dependencies produce a clear `RuntimeError`. Pure tests
include transport test doubles, which are not a claim of live ROS validation.

## Runtime validation status — Tier 1

ROS 2 runtime publication using the real `nav2_msgs/SpeedLimit` interface is
validated in a Linux Docker container running ROS 2 Humble on Ubuntu 22.04
(`ros:humble-ros-base-jammy`, `ros-humble-nav2-msgs` 1.1.20).
`tests/ros2/test_nav2_runtime.py` uses actual rclpy nodes, DDS discovery and a
real subscriber: ADMITTED delivers 1.0 m/s, DEGRADED delivers 0.5 m/s, both with
`percentage=False`. DENIED returns navigation disallowed and emits no message
over a 0.75-second observation window, with a positive-control publication
verifying the observer works. All three runtime cases passed.

The separate `ROS 2 Nav2 runtime` workflow installs binary packages and runs:

```sh
source /opt/ros/humble/setup.bash
ROS_LOCALHOST_ONLY=1 SPP_REQUIRE_ROS=1 python3 -m pytest -v -s tests/ros2/test_nav2_runtime.py
```

The environment needs rclpy, nav2_msgs, pytest, PyYAML and jsonschema >=4.23.
Normal pytest skips this module only when ROS packages are absent; the dedicated
job requires ROS and treats missing dependencies as errors. Normal CI is unchanged.

Tier 1 proves ROS message transport; its subscriber is an actual ROS test node,
not a Nav2 controller. See the separately bounded Tier 2a result below.

## Controller-plugin boundary validation — Tier 2a

SPP-derived speed limits have been validated through ROS 2 and Nav2
ControllerServer to the Nav2 controller-plugin enforcement boundary.

`tests/ros2/test_nav2_controller_boundary.py` launches the unmodified binary
`nav2_controller::ControllerServer` from `ros-humble-nav2-controller`
1.1.20-1jammy.20260804.211701 on Humble. Normal pluginlib loading installs the
test-only `spp_test::BoundaryObserver` from `tests/ros2/plugins/`. Its official
`setSpeedLimit()` method publishes the received arguments on
`spp_boundary_observed`; it does not subscribe to the SPP input topic itself.
The real ControllerServer is therefore the link between the adapter's
publication and the asserted plugin observation: **0.5 m/s, percentage=False**
from a DEGRADED AdmissionProfile.

Only the configure transition is needed. ControllerServer configures its
required empty rolling costmap with an inflation layer; no static map, sensors,
localization, navigation goal, activation or simulator is used. The observation
publisher is diagnostic, not a navigation/lifecycle authorization. The plugin
refuses path-following and velocity-generation calls and must never be deployed
as a production controller.

The existing ROS workflow builds only this small test plugin against apt-installed
Nav2 binaries; it does not compile or patch Nav2. In the sourced Humble environment:

```sh
cmake -S tests/ros2/plugins -B /tmp/spp-boundary-build -DCMAKE_INSTALL_PREFIX=/tmp/spp-boundary-install
cmake --build /tmp/spp-boundary-build -j2
cmake --install /tmp/spp-boundary-build
source /tmp/spp-boundary-install/share/spp_boundary_observer/local_setup.bash
ROS_LOCALHOST_ONLY=1 SPP_REQUIRE_ROS=1 python3 -m pytest -v -s tests/ros2/test_nav2_runtime.py tests/ros2/test_nav2_controller_boundary.py
```

Additional binary/build dependencies are `ros-humble-nav2-controller`,
`build-essential` and `cmake`. When ROS exists, missing ControllerServer or the
test plugin is a test failure, not a skip. On non-ROS machines the new module
skips cleanly. No production adapter, admission or mapping semantics changed.

Tier 2a observes only the test plugin's official interface. The separate Tier 3
test below measures stock-controller command output. Physical speed enforcement,
safety, stopping and controller restart behavior remain unproven.

## Running controller command-speed validation — Tier 3

SPP has been validated changing the speed behavior of a running Nav2 runtime
from a higher operating limit to an SPP-imposed 0.5 m/s limit.

`tests/ros2/test_nav2_motion_limit.py` runs the apt-installed Humble
`nav2_controller::ControllerServer` with the stock
`nav2_regulated_pure_pursuit_controller::RegulatedPurePursuitController`.
Validated binaries: `ros-humble-nav2-controller` 1.1.20-1jammy.20260804.211701 and
`ros-humble-nav2-regulated-pure-pursuit-controller` 1.1.20-1jammy.20260804.211511,
in the existing Ubuntu 22.04/Humble container.

The test configures and activates ControllerServer, submits one straight
FollowPath goal, and measures the linear magnitude of its real `cmd_vel` Twist
messages. The existing mapper and Nav2Enforcer apply trusted AdmissionProfile
fixtures for the lobby (1.0 m/s) and patient wing (0.5 m/s). The same goal stays
active throughout; no path replacement or controller parameter update occurs.
The fixture supplies a fixed pose, static TF and zero odometry in an empty
rolling costmap. It does not simulate robot dynamics or physical travel.

Observed: **10 commands at 1.000000 m/s**, then **20 commands at 0.500000 m/s**.
After allowing 0.3 seconds for message/callback scheduling, all sampled commands
must be between 0.45 and 0.5 m/s (upper tolerance 0.000001 m/s). Requiring positive
commands and an unfinished goal prevents a stopped or failed controller from
passing. This tests command behavior, not an instantaneous response deadline.

In the sourced Humble environment, install the additional binary package
`ros-humble-nav2-regulated-pure-pursuit-controller` and run:

```sh
ROS_LOCALHOST_ONLY=1 SPP_REQUIRE_ROS=1 python3 -m pytest -v -s tests/ros2/test_nav2_motion_limit.py
```

The existing ROS workflow includes this test. On machines without ROS it skips;
when ROS exists, missing controller packages and runtime failures are errors.
The motion fixture uses no test controller plugin and builds no Nav2 source.
It disables collision/cost/curvature speed regulation to isolate the received
limit; `tests/ros2/motion_controller.yaml` is not deployment configuration.
The profiles are trusted test inputs; evidence generation/authentication is not
retested here. Physical robot safety, stopping, production enforcement, other
controller configurations and general Nav2 certification are not established.
