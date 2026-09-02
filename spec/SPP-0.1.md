# Spatial Policy Protocol 0.1

Status: working draft
Date: 2026-09-02

This specification is developed as a PlaceAuth open-protocol project. PlaceAuth
stewards the reference implementation; the SPP protocol and its data model are
intended to remain vendor-neutral.

## 1. Purpose

Spatial Policy Protocol (SPP) lets the authority for a physical place express
whether an autonomous actor may perform an action there under supplied context.
The protocol's core question is:

> May Actor X perform Action Y in Space Z under Context C?

The key words MUST, MUST NOT, REQUIRED, SHOULD, SHOULD NOT, and MAY are to be
interpreted as normative requirement levels.

## 2. Scope

SPP 0.1 defines:

1. a policy bundle owned by a spatial authority;
2. hierarchical spaces and inherited rules;
3. an actor, action, space, and context decision request;
4. permit, deny, and conditional decisions;
5. named authorizations and obligations; and
6. six initial action families.

SPP 0.1 does not define identity proofing, policy discovery, geometry, robot
control, transport authentication, credential formats, policy signatures,
revocation distribution, or audit storage. Deployments MUST supply appropriate
mechanisms for those concerns.

## 3. Data model

### 3.1 Actor

An actor has a stable \`id\`, a \`type\`, and optional attributes. The authority
decides which identity system makes those assertions trustworthy. Rules MAY
select exact actor IDs, actor types, and flat attribute values.

### 3.2 Space

A space has a unique ID, an optional parent, and an ordered list of rules.
Exactly one declared space is the root. Every non-root space MUST name a
declared parent, and the parent graph MUST be acyclic.

SPP 0.1 space IDs are opaque strings. Slash-separated IDs are recommended for
human readability but have no implicit inheritance semantics; the explicit
\`parent\` property is authoritative.

### 3.3 Action

An action is a \`family\` and a deployment-defined \`name\`. Version 0.1 defines
these families:

| Family | Illustrative names |
|---|---|
| movement | enter, traverse, dwell, dock |
| sensing | lidar, video_capture, audio_record, thermal |
| data | video_store, map_retain, transmit |
| manipulation | package_pick, package_place, door_handle |
| infrastructure | elevator_use, door_open, charge |
| human_interaction | approach, identify, touch, request_attention |

The names are illustrative, not a registry. A rule name of \`*\` matches every
name in the same family. Requests MUST use a concrete action name.

### 3.4 Context

Context MAY carry a purpose, RFC 3339 timestamp, emergency flag, named
authorizations, and deployment attributes. Version 0.1 selectors support
purpose, emergency state, and flat attribute equality. Time is carried for
policy-engine extensions but the core evaluator does not interpret schedules.

An authorization string is evidence only after the deployment verifies the
credential or grant it represents. A caller MUST NOT be trusted merely because
it places a string in \`context.authorizations\`.

### 3.5 Rule

A rule contains an action, decision, and optional actor selector, context
selector, required authorizations, obligations, reason, and decision lifetime.
A conditional rule MUST declare at least one required authorization.

Rules are policy statements, not executable programs.

### 3.6 Decision

A decision is one of:

- \`permit\`: the action may proceed while its obligations are enforced;
- \`deny\`: the action must not proceed; or
- \`conditional\`: the action must not proceed until the listed requirements
  have been satisfied and the request has been evaluated again.

A conditional result is not a weak permit. Enforcement points MUST block it.

Obligations constrain an otherwise permitted activity. An enforcement point
that cannot understand or enforce an obligation MUST deny the action.

## 4. Evaluation algorithm

An SPP 0.1 evaluator MUST behave as follows:

1. Validate the request and active policy bundle.
2. Resolve the requested space. Unknown spaces MUST fail closed.
3. Build the space chain from requested space to root.
4. At each space, consider rules whose family, name or wildcard, actor selector,
   and context selector match.
5. Prefer an exact action name over a wildcard at the same space.
6. If multiple equally specific rules match at one space, use document order.
7. Stop at the first matching rule. This is the nearest-space rule.
8. For a conditional rule, compare its required authorizations with verified
   authorizations in context. If any are missing, return \`conditional\`; if
   none are missing, return \`permit\`.
9. If no rule matches anywhere in the chain, return \`deny\`.

Child spaces therefore override inherited behavior only for matching actions.
Other actions continue walking toward the parent.

## 5. Protocol exchange

The reference binding uses JSON over authenticated HTTPS:

\`\`\`http
POST /v1/decision
Content-Type: application/json
\`\`\`

The request and response MUST conform to \`schema/request.schema.json\` and
\`schema/decision.schema.json\`. YAML is a human-friendly serialization for
policy authoring; the normative data model is JSON-compatible.

Decision IDs are unique. \`expires_in\` is seconds from \`evaluated_at\`.
Enforcement points MUST re-evaluate after expiration and SHOULD re-evaluate
when the actor, action, space, context, policy version, or authorization state
changes.

## 6. Enforcement

SPP separates decision from enforcement. A policy decision point evaluates;
the robot, fleet adapter, building controller, or other policy enforcement
point blocks or permits the action.

Enforcement MUST fail closed on malformed policy, invalid response, unknown
decision, network failure, timeout, expired decision, unsupported obligation,
or inability to establish the requested space.

For continuous actions such as recording or dwelling, a deployment SHOULD
define checkpoints and stop the activity when its decision expires or the space
changes.

## 7. Versioning

Every document carries \`spp_version\`. Implementations MUST reject unsupported
major or minor versions rather than silently reinterpret them. Policy changes
increment \`policy_version\`. Version 0.1 does not define merge semantics.

## 8. Extension rules

Action names, actor types, attributes, authorization names, and obligation types
are extension points. Public extensions SHOULD use collision-resistant names.
Unknown action names are allowed in requests but remain deny-by-default unless a
rule explicitly covers them.

## 9. Examples

The repository examples are informative and schema-valid. The hospital example
is used by the reference server and clinic demo.
