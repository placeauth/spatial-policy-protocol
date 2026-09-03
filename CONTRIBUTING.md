# Contributing to SPP

SPP is an experimental PlaceAuth project. Small, reviewable changes are
welcome, especially clarifications to the protocol, interoperable examples,
and tests that demonstrate real decision or enforcement behavior.

## Development

Create a Python 3.11+ virtual environment, install requirements-dev.txt, and
run pytest. Keep protocol changes synchronized across spec/, schema/, examples,
and tests. Do not claim an implementation supports an action or security
property unless a test or documented adapter demonstrates it.

Before opening a pull request:

- run the full test suite;
- run the affected Core or Admission demo;
- update the relevant schema, specification, and examples together; and
- describe compatibility impact and known limitations.

Open a pull request with a concise description, test results, and any
compatibility impact. Please avoid unrelated formatting churn. Protocol
changes should be discussed as experimental proposals until independently
reviewed.
