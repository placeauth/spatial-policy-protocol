package spp_core

import rego.v1

default result := {"decision": "DENY", "obligations": [], "reason_codes": ["scope_mismatch"]}

result := {"decision": "DENY", "obligations": [], "reason_codes": ["required_obligation_unsupported"]} if {
  scope_applicable
  candidate := selected_candidate
  rule := input.scope_chain[candidate[0]].rules[candidate[2]]
  some obligation in object.get(rule, "obligations", [])
  not obligation.type in object.get(input.deployment, "supported_obligations", [])
}

result := normalized(rule) if {
  scope_applicable
  candidate := selected_candidate
  rule := input.scope_chain[candidate[0]].rules[candidate[2]]
  every obligation in object.get(rule, "obligations", []) {
    obligation.type in object.get(input.deployment, "supported_obligations", [])
  }
}

result := {"decision": "DENY", "obligations": [], "reason_codes": ["no_applicable_rule"]} if {
  scope_applicable
  count(candidates) == 0
}

scope_applicable if {
  count(input.scope_chain) > 0
  input.scope_chain[0].id == input.request.governed_scope
  input.scope_chain[count(input.scope_chain) - 1].id == input.profile.governed_scope
}

candidates := [entry |
  some scope_index, rule_index
  scope := input.scope_chain[scope_index]
  rule := scope.rules[rule_index]
  action_matches(rule, input.request.action)
  subject_matches(rule, input.request.subject)
  context_matches(rule, object.get(input.request, "context", {}))
  priority := action_priority(rule, input.request.action)
  entry := [scope_index, priority, rule_index]
]

selected_candidate := sort(candidates)[0] if count(candidates) > 0

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
  every key, value in expected { actual[key] == value }
}

subject_matches(rule, subject) if {
  selector := object.get(rule, "actor", {})
  selection_allows(subject.id, object.get(selector, "ids", []))
  selection_allows(subject.type, object.get(selector, "types", []))
  attributes_match(object.get(selector, "attributes", {}), object.get(subject, "attributes", {}))
}

purpose_matches(null, _)
purpose_matches(expected, actual) if { type_name(expected) == "string"; expected == actual }
purpose_matches(expected, actual) if { type_name(expected) == "array"; actual in expected }

emergency_matches(when, context) if not object.keys(when)["emergency"]
emergency_matches(when, context) if { object.keys(when)["emergency"]; when.emergency == object.get(context, "emergency", false) }

context_matches(rule, context) if {
  when := object.get(rule, "when", {})
  purpose_matches(object.get(when, "purpose", null), object.get(context, "purpose", null))
  emergency_matches(when, context)
  attributes_match(object.get(when, "attributes", {}), object.get(context, "attributes", {}))
}

missing(rule) := [value | value := object.get(rule, "requires", [])[_]; not value in object.get(input.request.context, "authorizations", [])]

normalized(rule) := {"decision": "CONDITIONAL", "obligations": object.get(rule, "obligations", []), "reason_codes": ["required_authorization_missing"]} if {
  rule.decision == "conditional"
  count(missing(rule)) > 0
}

normalized(rule) := {"decision": "PERMIT", "obligations": object.get(rule, "obligations", []), "reason_codes": ["matched_rule"]} if {
  rule.decision == "conditional"
  count(missing(rule)) == 0
}

normalized(rule) := {"decision": upper(rule.decision), "obligations": object.get(rule, "obligations", []), "reason_codes": ["matched_rule"]} if rule.decision != "conditional"
