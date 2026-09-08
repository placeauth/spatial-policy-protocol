# Requirement vocabulary

SPP requirement vocabulary identifies a place-defined guarantee without naming a
robot, provider, or runtime. It lets independent implementations compare the
same requirement without guessing its meaning.

## Identifiers and versions

New identifiers use lowercase dotted namespaces, such as movement.max_speed.
They do not contain units, embodiments, or provider names. The existing
human_separation identifier is retained as a compatibility built-in. New
third-party identifiers use x-<organization>.<requirement>, such as
x-acme.visibility.

Each definition has a version such as 1.0. Wording-only clarification keeps its
version. A change to meaning, value type, unit, or comparison requires a new
version. New definitions begin at 1.0. Version matching is exact.

## Built-ins

| Identifier | Version | Value type | Unit | Comparison |
| --- | --- | --- | --- | --- |
| movement.max_speed | 1.0 | number | m/s | MAX: measured <= value |
| human_separation | 1.0 | number | m | MIN: measured >= value |
| sensing.facial_recognition | 1.0 | boolean | none | PROHIBITED: behavior is false |
| data.video_retention | 1.0 | integer | seconds | EXACT: measured = value |

Numeric quantities use canonical SI strings. The reference layer has no unit
conversion. A supplied unit must match the definition. Legacy built-ins may omit
requirement_version and a numeric unit; they resolve only to built-in 1.0 and
its canonical unit. Unknown extensions never receive that default.

## Registry and compatibility

RequirementVocabularyRegistry explicitly registers and looks up
RequirementDefinition values. It rejects incompatible duplicate definitions and
validates value type, unit, and comparison for known requirements.

Same ID and version are compatible. A known ID with an unknown version is
incompatible. An unknown ID is unresolved unless explicitly registered.
RequirementDelta marks incompatible versions UNRESOLVED and requires
requalification instead of comparing bounds.

## Providers and Place Packages

External providers may declare supported_requirement_versions as an ID-to-version
set. Legacy descriptors remain compatible with built-in 1.0 only. Provider
selection rejects an ID whose requested version is not supported.

Place Packages carry the embedded PlaceRequirementSet unchanged. They may add
requirement_version to each requirement. Package verification accepts known
built-ins with the documented 1.0 default and fails closed for an unknown
extension without a locally registered definition.

## Limits

This is a small local convention. It does not provide a universal robotics
ontology, central registry, semantic-web model, unit-conversion engine,
expression language, remote discovery service, or certification process.
