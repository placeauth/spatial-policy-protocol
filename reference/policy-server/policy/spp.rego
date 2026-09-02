package spp

import rego.v1

default core := {
  "decision": "deny",
  "matched_space": null,
  "reason": "No applicable rule; SPP 0.1 is deny by default.",
  "requires": [],
  "obligations": [],
  "expires_in": 30,
}

core := result if {
  candidate := sort([item |
    some space_index, rule_index
    space := input.policy_chain[space_index]
    rule := space.rules[rule_index]
    action_matches(rule, input.request.action)
    actor_matches(rule, input.request.actor)
    context_matches(rule, input.request.context)
    priority := action_priority(rule, input.request.action)
    item := [space_index, priority, rule_index, space.id, rule]
  ])[0]
  result := resolve(candidate[3], candidate[4], input.request.context)
}

action_matches(rule, action) if {
  rule.action.family == action.family
  rule.action.name == action.name
}

action_matches(rule, action) if {
  rule.action.family == action.family
  rule.action.name == "*"
}

action_priority(rule, action) := 0 if rule.action.name == action.name
action_priority(rule, action) := 1 if rule.action.name == "*"

selection_allows(_, choices) if count(choices) == 0
selection_allows(value, choices) if value in choices

attributes_match(expected, actual) if {
  every key, value in expected {
    actual[key] == value
  }
}

actor_matches(rule, actor) if {
  selector := object.get(rule, "actor", {})
  selection_allows(actor.id, object.get(selector, "ids", []))
  selection_allows(actor.type, object.get(selector, "types", []))
  attributes_match(
    object.get(selector, "attributes", {}),
    object.get(actor, "attributes", {}),
  )
}

purpose_matches(null, _)
purpose_matches(expected, actual) if {
  type_name(expected) == "string"
  expected == actual
}
purpose_matches(expected, actual) if {
  type_name(expected) == "array"
  actual in expected
}

emergency_matches(when, context) if not object.keys(when)["emergency"]
emergency_matches(when, context) if {
  object.keys(when)["emergency"]
  when.emergency == object.get(context, "emergency", false)
}

context_matches(rule, context) if {
  when := object.get(rule, "when", {})
  purpose_matches(object.get(when, "purpose", null), object.get(context, "purpose", null))
  emergency_matches(when, context)
  attributes_match(
    object.get(when, "attributes", {}),
    object.get(context, "attributes", {}),
  )
}

missing_authorizations(rule, context) := [authorization |
  authorization := object.get(rule, "requires", [])[_]
  not authorization in object.get(context, "authorizations", [])
]

base(space_id, rule) := {
  "matched_space": space_id,
  "reason": object.get(rule, "reason", sprintf("Matched policy rule at %s.", [space_id])),
  "obligations": object.get(rule, "obligations", []),
  "expires_in": object.get(rule, "expires_in", 30),
}

resolve(space_id, rule, context) := object.union(base(space_id, rule), {
  "decision": "conditional",
  "requires": missing,
}) if {
  rule.decision == "conditional"
  missing := missing_authorizations(rule, context)
  count(missing) > 0
}

resolve(space_id, rule, context) := object.union(base(space_id, rule), {
  "decision": "permit",
  "requires": [],
}) if {
  rule.decision == "conditional"
  count(missing_authorizations(rule, context)) == 0
}

resolve(space_id, rule, _) := object.union(base(space_id, rule), {
  "decision": rule.decision,
  "requires": [],
}) if rule.decision != "conditional"

