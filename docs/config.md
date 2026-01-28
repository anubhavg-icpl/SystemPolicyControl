# Configuration Reference

## SPC_AGENT_PATH (optional)
Filesystem path to the compiled Swift agent binary. Defaults to `bin/system-policy-agent`. The HTTP API (`src/api/main.py`) reads this value before invoking the agent.

## SPC_STATE_PATH (optional)
Overrides the JSON file used to store the last applied policy. Defaults to `data/policy_state.json`. Both the API and the agent must agree on this path.

## SPC_PROFILE_DIR (optional)
Directory where generated `.mobileconfig` files are written. Defaults to `data/profiles/`.

## SPC_API_HOST / SPC_API_PORT (optional)
Host and port for the built-in WSGI server exposed through `make run-api`.
