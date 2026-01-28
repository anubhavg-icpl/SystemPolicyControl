# Repository Guidelines

## Project Structure & Module Organization
Source lives in two roots: the Swift agent under `swift/SystemPolicyAgent/` (SwiftPM executable that generates and installs Gatekeeper profiles) and the Python control plane under `src/` (`common/` for shared models/state and `api/` for the WSGI shim). Compiled agent binaries are published to `bin/system-policy-agent`, while generated `.mobileconfig` files land in `data/profiles/` and persisted run state is stored in `data/policy_state.json`. Docs sit in `docs/`, and regression tests in `tests/`.

## Build, Test, and Development Commands
`make build-agent` compiles the Swift executable (copying it into `bin/`). `make run-agent ARGS="apply --no-install"` runs that binary with arbitrary flags (`apply --profile-dir data/profiles --state-path data/policy_state.json --allow-identified-developers true`). `make run-api` starts the Python WSGI server that shells out to the agent; set `SPC_AGENT_PATH`, `SPC_STATE_PATH`, or `SPC_PROFILE_DIR` to override defaults. `make test` depends on `build-agent` and executes the `unittest` suite, invoking the real binary to prove plist and state emission. `make clean` removes the venv, Swift build artifacts, `bin/`, and generated profiles/state.

## Coding Style & Naming Conventions
Swift code targets macOS 12+, uses Foundation, and should embrace value types plus explicit error handling (no force unwraps in agent paths). Follow Swift API Design Guidelines and keep files scoped under `Sources/SystemPolicyAgent`. Python modules stay 4-space indented, snake_case files, and avoid third-party deps unless absolutely needed—if you add one, note it in the pull request and `requirements.txt`. Keep shell-outs isolated so they can be substituted/mocked.

## Testing Guidelines
Every new agent feature ought to be covered via `tests/test_agent.py`, which spins up temp directories, runs the compiled binary with `--no-install`, and inspects the resulting plist + JSON. Mirror this style when adding new behaviors (e.g., extra payload keys). Avoid leaving residue by always writing fixtures under `tempfile.TemporaryDirectory()`. For API updates, add focused tests or manual steps (curl requests) that confirm `/policy` reflects the state written by the binary.

## Commit & Pull Request Guidelines
Use `type: summary` headers (`feat: add notarization toggle`, `fix: harden API agent lookup`). Reference issue IDs, include `make test` output, and attach snippets of generated payloads if you changed plist structure. PRs should explain required macOS entitlements or deployment considerations and highlight any new env vars (`SPC_*`).

## Security & Configuration Tips
Never commit shipping `.mobileconfig` profiles or signing materials. Place sanitized env samples in `docs/config.md` and describe any new knobs there. When running installs, the agent calls `/usr/bin/profiles`; document any elevation requirements in the PR and ensure error messages from that subprocess are preserved in `data/policy_state.json` for troubleshooting.
