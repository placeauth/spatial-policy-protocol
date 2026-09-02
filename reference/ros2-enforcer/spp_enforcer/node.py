from __future__ import annotations

import json
from urllib.error import URLError
from urllib.request import Request, urlopen

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class SppEnforcer(Node):
    """A fail-closed enforcement point between intent and execution topics."""

    def __init__(self) -> None:
        super().__init__("spp_enforcer")
        self.declare_parameter("policy_endpoint", "http://127.0.0.1:8000/v1/decision")
        self.declare_parameter("actor_id", "robot:demo:delivery-01")
        self.declare_parameter("actor_type", "delivery_robot")
        self.intent_subscription = self.create_subscription(
            String, "spp/action_intent", self.on_intent, 10
        )
        self.allowed_publisher = self.create_publisher(String, "spp/action_allowed", 10)
        self.pending_publisher = self.create_publisher(String, "spp/action_pending", 10)
        self.decision_publisher = self.create_publisher(String, "spp/decision", 10)

    def on_intent(self, message: String) -> None:
        try:
            intent = json.loads(message.data)
            request = {
                "spp_version": "0.1",
                "request_id": intent["request_id"],
                "actor": {
                    "id": self.get_parameter("actor_id").value,
                    "type": self.get_parameter("actor_type").value,
                },
                "space": intent["space"],
                "action": intent["action"],
                "context": intent.get("context", {}),
            }
            decision = self._decide(request)
        except (KeyError, ValueError, URLError, TimeoutError) as error:
            decision = {
                "spp_version": "0.1",
                "request_id": "invalid",
                "decision": "deny",
                "reason": f"Enforcement failure (fail closed): {error}",
            }

        decision_message = String()
        decision_message.data = json.dumps(decision)
        self.decision_publisher.publish(decision_message)

        if decision.get("decision") == "permit":
            self.allowed_publisher.publish(message)
            self.get_logger().info(f"PERMIT {request['request_id']}")
        elif decision.get("decision") == "conditional":
            self.pending_publisher.publish(message)
            self.get_logger().warning(
                f"CONDITIONAL {decision.get('request_id', 'invalid')}: paused pending "
                f"{decision.get('requires', [])}"
            )
        else:
            self.get_logger().warning(
                f"{decision.get('decision', 'deny').upper()} "
                f"{decision.get('request_id', 'invalid')}: {decision.get('reason')}"
            )

    def _decide(self, request_body: dict) -> dict:
        endpoint = self.get_parameter("policy_endpoint").value
        body = json.dumps(request_body).encode("utf-8")
        request = Request(
            endpoint,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=2.0) as response:
            return json.load(response)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = SppEnforcer()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
