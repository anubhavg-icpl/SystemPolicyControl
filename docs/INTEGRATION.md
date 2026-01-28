# API to Agent Integration Summary

## Overview

The SystemPolicyControl now features complete CRUD (Create, Read, Update, Delete) operations with seamless integration between the Python API and Swift Agent.

## Architecture

### Components

1. **Swift Agent** (`swift/SystemPolicyAgent/Sources/SystemPolicyAgent/main.swift`)
   - Standalone CLI executable
   - Generates Gatekeeper `.mobileconfig` profiles
   - Installs profiles via `/usr/bin/profiles`
   - Manages state in JSON file
   - Supports: `apply`, `remove`, `list` commands

2. **Python API** (`src/api/main.py`)
   - WSGI HTTP server
   - RESTful API endpoints
   - Shell-outs to Swift agent binary
   - Reads agent's state file for responses

3. **State Storage** (`data/policy_state.json`)
   - Single source of truth for current policy
   - Written by agent, read by API
   - Contains policy metadata, timestamps, installation results

### Communication Flow

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ HTTP Request
       ▼
┌──────────────────────┐
│   Python API        │
│   (src/api/main.py) │
└──────┬───────────────┘
       │ subprocess.run()
       ▼
┌────────────────────────┐
│   Swift Agent       │
│   (bin/system-     │
│   policy-agent)    │
└──────┬───────────────┘
       │
       ├─► Generates .mobileconfig
       ├─► Writes to data/profiles/
       ├─► (Optionally) Installs
       └─► Writes state.json
       │
       ▼
┌────────────────────────┐
│   State File        │
│   (data/policy_     │
│    state.json)      │
└──────┬───────────────┘
       │
       │ API reads file
       ▼
┌──────────────────────┐
│   HTTP Response     │
└──────┬──────────────┘
       │
       ▼
┌─────────────┐
│   Client    │
└─────────────┘
```

## API Endpoints

| Method | Endpoint | Action | Agent Command |
|--------|----------|---------|---------------|
| GET | `/healthz` | Health check | - |
| GET | `/policies` | List all profiles | `list` |
| GET | `/policy` | Get current policy | (reads state file) |
| POST | `/policy` | Create new policy | `apply` |
| PUT | `/policy` | Update existing policy | `apply` |
| DELETE | `/policy` | Delete policy | `remove <id>` |

## Agent Commands

### Create/Update (apply)
```bash
system-policy-agent apply \
  --profile-identifier com.example.policy \
  --display-name "My Policy" \
  --organization "Example" \
  --allow-identified-developers true \
  --enable-assessment true \
  --no-install
```

### Delete (remove)
```bash
system-policy-agent remove com.example.policy
```

### List (list)
```bash
system-policy-agent list
```

## Data Flow Examples

### Create Policy Flow

1. Client sends `POST /policy` with JSON payload
2. API parses payload, constructs subprocess arguments
3. API calls: `system-policy-agent apply --profile-id X --display-name Y ...`
4. Swift Agent:
   - Builds profile payload dictionary
   - Serializes to XML plist format
   - Writes `.mobileconfig` file to `data/profiles/`
   - Optionally installs via `/usr/bin/profiles`
   - Writes `data/policy_state.json` with metadata
5. Agent exits with success (0)
6. API reads `data/policy_state.json`
7. API returns JSON response with state to client
8. Client receives 201 Created with policy state

### Read Policy Flow

1. Client sends `GET /policy`
2. API reads `data/policy_state.json`
3. API parses JSON into PolicyState object
4. API returns 200 OK with policy state

### Delete Policy Flow

1. Client sends `DELETE /policy`
2. API loads current state to get profile identifier
3. API calls: `system-policy-agent remove com.example.policy`
4. Swift Agent:
   - Calls `/usr/bin/profiles -R -p com.example.policy`
   - Deletes profile files matching identifier
   - Deletes `data/policy_state.json`
5. Agent exits with success
6. API returns 200 OK with success message

## Verification

Run the verification script to ensure API and Agent are properly integrated:

```bash
make verify
```

This verifies:
- ✓ API sends requests to Agent correctly
- ✓ Agent generates valid `.mobileconfig` files
- ✓ Agent writes state to JSON file
- ✓ API reads state file correctly
- ✓ Agent handles create, read, update, delete operations
- ✓ Direct CLI invocation works

## Testing

### Unit Tests
```bash
make test
```

Runs 10 tests across:
- `tests/test_agent.py` - Agent CLI functionality (5 tests)
- `tests/test_api_agent_integration.py` - API→Agent integration (5 tests)

All tests use temporary directories and clean up after themselves.

### Integration Tests
```bash
python3 scripts/verify_integration.py
```

Tests full end-to-end flow:
1. Create policy via API
2. Verify profile file exists and is valid
3. Read policy back via API
4. Update policy via API
5. List all profiles
6. Delete policy via API
7. Verify state file is deleted
8. Test direct agent CLI invocation

## Environment Variables

The API respects these environment variables for configuration:

| Variable | Default | Description |
|----------|---------|-------------|
| `SPC_AGENT_PATH` | `bin/system-policy-agent` | Path to agent binary |
| `SPC_STATE_PATH` | `data/policy_state.json` | Path to state file |
| `SPC_PROFILE_DIR` | `data/profiles` | Directory for .mobileconfig files |
| `SPC_API_HOST` | `127.0.0.1` | API server host |
| `SPC_API_PORT` | `8000` | API server port |

## Security Considerations

1. **Profile Installation**: Requires root/sudo privileges on macOS
2. **State File**: Contains sensitive policy configuration
3. **Profile Files**: Should not be committed to version control
4. **No Authentication**: API has no auth - use behind firewall/reverse proxy

## Error Handling

### Agent Errors
- Invalid arguments → Exits with status 1, prints usage
- Write failures → Exits with status 1, prints error
- Installation failures → Writes to state file, exits with status 1

### API Errors
- Agent binary missing → 503 Service Unavailable
- Agent subprocess failure → 500 Internal Server Error with stderr
- Policy not found → 404 Not Found
- Invalid JSON → 400 Bad Request

## Files Modified

### Swift Agent
- `swift/SystemPolicyAgent/Sources/SystemPolicyAgent/main.swift`
  - Added `remove` and `list` actions
  - Added `removeProfile()`, `listProfiles()`, `deleteState()`, `deleteProfileFile()` functions
  - Updated argument parsing for multi-action support

### Python API
- `src/api/main.py`
  - Added GET `/policies` endpoint
  - Added PUT `/policy` endpoint
  - Added DELETE `/policy` endpoint
  - Updated to read environment variables per-request for testing

### Tests
- `tests/test_agent.py`
  - Added `test_list_profiles_returns_empty_when_no_profiles`
  - Added `test_remove_policy_deletes_state_file`

- `tests/test_api_agent_integration.py` (new file)
  - 5 integration tests covering full CRUD flow
  - Tests API→Agent communication
  - Verifies profile file generation and state management

### Documentation
- `docs/API.md` - Complete API reference
- `docs/INTEGRATION.md` - This document
- `scripts/verify_integration.py` - End-to-end verification script

## Summary

The API and Agent are now fully integrated with:

✓ Complete CRUD operations
✓ Seamless subprocess communication
✓ State file synchronization
✓ Valid profile generation
✓ Comprehensive test coverage
✓ Documentation and verification scripts

The system is ready for deployment and can manage macOS Gatekeeper profiles via HTTP API or direct CLI commands.
