"""TEST ONLY: one stationary robot, one charger, real delivery bids; no dispatch."""
import json
import time
from datetime import timedelta
import rmf_adapter as a
import rclpy
from rmf_task_msgs.msg import BidNotice, BidResponse
from spp_admission.open_rmf import make_delivery_callback, TaskContext
from spp_admission.models import AdmissionProfile, EvidenceBinding

a.init_rclcpp()
rclpy.init()
traits = a.vehicletraits.VehicleTraits(a.vehicletraits.Limits(1., .5), a.vehicletraits.Limits(1., .5), a.vehicletraits.Profile(a.geometry.make_final_convex_circle(.2)))
graph = a.graph.Graph()
graph.add_waypoint('fixture', [0., 0.]).set_charger(True)
graph.add_key('lobby', 0)
adapter = a.Adapter.make('spp_runtime_probe', wait_time=timedelta(seconds=10))
assert adapter is not None
fleet = adapter.add_fleet('spp_fixture', traits, graph)
battery = a.battery.BatterySystem.make(24., 40., 8.)
motion = a.battery.SimpleMotionPowerSink(battery, a.battery.MechanicalSystem.make(20., 10., .2))
device = a.battery.SimpleDevicePowerSink(battery, a.battery.PowerSystem.make(1.))
assert fleet.set_task_planner_params(battery, motion, device, device, .2, 1., False)
print('REAL ADAPTER AND FLEET:', type(adapter), type(fleet), flush=True)
observed = []
context = TaskContext('robot:1', 'clinic', 'clinic/wing')
profile = AdmissionProfile('ADMITTED', context.actor_id, context.place, context.space, 1, 'sha256:evidence', EvidenceBinding('robot:1', 'b', 'c', 'p', 'e', 'plan'))
def resolve(description):
    assert description == {'handler': 'test', 'payload': [], 'place': 'lobby'}
    observed.append(description)
    print('REAL CALLBACK:', description, flush=True)
    return context
callback = make_delivery_callback(resolve, lambda _: profile)
fleet.consider_delivery_requests(callback, callback)
print('REAL HOOK REGISTERED', flush=True)
adapter.start()
class Robot(a.RobotCommandHandle):
    def stop(self):
        pass
    def dock(self, name, finished):
        finished()
    def follow_new_path(self, waypoints, arrival, finished):
        finished()
robot = Robot()
handles = []
fleet.add_robot(robot, 'spp_test_robot', traits.profile, [a.plan.Start(adapter.now(), 0, 0.)], handles.append)
deadline = time.monotonic() + 10
while not handles and time.monotonic() < deadline:
    time.sleep(.1)
print('ROBOT HANDLES', handles, flush=True)
assert handles
node = rclpy.create_node('spp_bid_probe')
responses = []
sub = node.create_subscription(BidResponse, 'rmf_task/bid_response', lambda msg: responses.append(msg), 10)
pub = node.create_publisher(BidNotice, 'rmf_task/bid_notice', 10)
deadline = time.monotonic() + 5
while pub.get_subscription_count() == 0 and time.monotonic() < deadline:
    rclpy.spin_once(node, timeout_sec=.1)
print('BID SUBSCRIBERS', pub.get_subscription_count(), flush=True)
for status in ('ADMITTED', 'DENIED'):
    profile.status = status
    before = len(observed)
    msg = BidNotice()
    msg.task_id = 'spp-runtime-' + status
    msg.time_window.sec = 5
    msg.request = json.dumps({'category': 'delivery', 'description': {'pickup': {'place': 'lobby', 'handler': 'test', 'payload': []}, 'dropoff': {'place': 'lobby', 'handler': 'test', 'payload': []}}, 'unix_millis_earliest_start_time': int(time.time()*1000)})
    pub.publish(msg)
    deadline = time.monotonic() + 8
    while not any(r.task_id == msg.task_id for r in responses) and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=.1)
    print('OBSERVED CALLBACKS', len(observed), flush=True)
    print('RESPONSES', responses, flush=True)
    assert len(observed) > before, status + ': runtime callback did not fire'
    response = next(r for r in responses if r.task_id == msg.task_id)
    assert response.has_proposal == (status == 'ADMITTED'), str(response)
    if status == 'DENIED':
        assert 'admission_denied' in str(response.errors), str(response)
    print(status, 'CALLBACKS', len(observed) - before, 'PROPOSAL', response.has_proposal, 'ERRORS', response.errors, flush=True)
adapter.stop()
node.destroy_node()
rclpy.shutdown()
