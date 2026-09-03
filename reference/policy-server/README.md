# PlaceAuth SPP reference policy server

This is an experimental reference implementation of the SPP Core decision
surface, not a production authorization service or security boundary.

The server validates SPP requests and returns schema-valid decisions. Its
default local evaluator is intentionally dependency-light and deterministic.
Set \`SPP_ENGINE=opa\` to route the same prepared policy chain through the Rego
policy in \`policy/spp.rego\`.

From the repository root:

\`\`\`sh
python -m venv .venv
.venv/Scripts/activate
python -m pip install -r requirements.txt
python -m uvicorn --app-dir reference/policy-server/src spp.server:app
\`\`\`

The endpoint is \`POST http://127.0.0.1:8000/v1/decision\`; health is available
at \`GET /health\`.
