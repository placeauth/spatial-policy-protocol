"""Optional Nav2 runtime surface; importing this module does not import ROS."""
from __future__ import annotations

from .mapping import Nav2EnforcementPlan, map_profile
from spp_admission.models import AdmissionProfile


class Nav2Enforcer:
    """Publish limits from trusted profiles using a caller-owned ROS 2 node.

    The caller must gate navigation on the returned plan. A publish is not an
    acknowledgment from Nav2, and denial does not cancel an existing mission.
    """

    def __init__(self, node, speed_limit_topic: str = "speed_limit") -> None:
        try:
            from rclpy.node import Node
            from nav2_msgs.msg import SpeedLimit
        except ImportError as error:
            raise RuntimeError(
                "Nav2Enforcer requires a sourced ROS 2 environment with rclpy "
                "and nav2_msgs; use map_profile for ROS-free evaluation."
            ) from error
        if not isinstance(node, Node):
            raise TypeError("node must be an initialized rclpy.node.Node")
        self._node = node
        self._message_type = SpeedLimit
        self._publisher = node.create_publisher(SpeedLimit, speed_limit_topic, 10)

    def apply(self, profile: AdmissionProfile) -> Nav2EnforcementPlan:
        plan = map_profile(profile)
        if not plan.navigation_allowed or plan.max_speed_mps is None:
            return plan
        try:
            if self._publisher.get_subscription_count() == 0:
                return Nav2EnforcementPlan(False, reasons=("nav2_subscriber_unavailable",))
            message = self._message_type()
            message.header.stamp = self._node.get_clock().now().to_msg()
            message.percentage = False
            message.speed_limit = plan.max_speed_mps
            self._publisher.publish(message)
        except Exception:
            return Nav2EnforcementPlan(False, reasons=("nav2_publish_failed",))
        return plan
