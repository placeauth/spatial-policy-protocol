# PlaceAuth SPP ROS 2 enforcer stub

This small \`ament_python\` package demonstrates an enforcement point, not a
complete Nav2 or Open-RMF adapter.

- Subscribe to \`spp/action_intent\` for JSON action intents.
- Ask the configured SPP policy endpoint for a decision.
- Publish every decision on \`spp/decision\`.
- Forward only permitted intents to \`spp/action_allowed\`.
- Forward conditional intents to \`spp/action_pending\` so a planner can pause
  and request authorization.
- Deny on malformed input, timeout, or policy-server failure.

An intent uses this shape:

\`\`\`json
{
  "request_id": "nav-42",
  "space": "clinic/pharmacy",
  "action": {"family": "movement", "name": "enter"},
  "context": {"purpose": "package_delivery"}
}
\`\`\`

Build in a ROS 2 workspace by copying or linking this directory into \`src/\`,
then run \`colcon build --packages-select spp_enforcer\`.
