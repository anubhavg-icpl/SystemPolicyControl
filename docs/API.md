# SystemPolicyControl API Documentation

**For comprehensive codebase documentation, see [CODEBASE.md](CODEBASE.md)**

## Overview

The SystemPolicyControl agent provides a complete CRUD (Create, Read, Update, Delete) interface for managing macOS Gatekeeper configuration profiles.

## CLI Commands

### Create/Apply a Policy
```bash
system-policy-agent apply [options]
```

**Options:**
- `--profile-dir <path>` - Directory to write .mobileconfig files (default: data/profiles)
- `--state-path <path>` - JSON file tracking policy state (default: data/policy_state.json)
- `--profile-identifier <value>` - Base identifier for the profile (default: com.systempolicycontrol.policy)
- `--display-name <value>` - Payload display name (default: System Policy Control)
- `--organization <value>` - Organization string in profile
- `--description <value>` - Optional description
- `--allow-identified-developers <bool>` - Allow identified developers (default: true)
- `--enable-assessment <bool>` - Enable Gatekeeper assessment (default: true)
- `--enable-xprotect-malware-upload <bool>` - Enable XProtect malware upload (default: true)
- `--no-install` - Generate profile without installing

**Example:**
```bash
./bin/system-policy-agent apply \
  --profile-identifier com.example.policy \
  --display-name "My Policy" \
  --organization "Example Corp" \
  --allow-identified-developers true \
  --enable-assessment true \
  --no-install
```

### Remove a Policy
```bash
system-policy-agent remove <identifier>
```

**Options:**
- `--profile-dir <path>` - Directory containing the profile (default: data/profiles)
- `--state-path <path>` - JSON file tracking policy state (default: data/policy_state.json)

**Example:**
```bash
./bin/system-policy-agent remove com.example.policy
```

### List Profiles
```bash
system-policy-agent list
```

Returns JSON array of installed profiles:
```json
[
  {
    "PayloadIdentifier": "com.example.policy",
    "PayloadDisplayName": "My Policy",
    ...
  }
]
```

## REST API Endpoints

### GET /healthz
Health check endpoint.

**Response:** `200 OK` with `{"status": "ok"}`

### GET /policies
List all installed profiles.

**Response:** `200 OK` with `{"policies": [...]}`

### GET /policy
Get the current policy state.

**Response:**
- `200 OK` with policy state object
- `404 Not Found` if no policy exists

**Example Response:**
```json
{
  "policy": {
    "profile_identifier": "com.systempolicycontrol.policy",
    "display_name": "System Policy Control",
    "organization": "SystemPolicyControl",
    "allow_identified_developers": true,
    "enable_assessment": true,
    "enable_xprotect_malware_upload": true
  },
  "profile_path": "/path/to/profile.mobileconfig",
  "applied_at": "2026-01-28T14:00:00Z",
  "install_attempted": false,
  "install_succeeded": false
}
```

### POST /policy
Create and apply a new policy.

**Request Body:**
```json
{
  "profile_identifier": "com.example.policy",
  "display_name": "My Policy",
  "organization": "Example Corp",
  "allow_identified_developers": true,
  "enable_assessment": true,
  "enable_xprotect_malware_upload": false,
  "install": false
}
```

**Response:** `201 Created` with policy state object

### PUT /policy
Update an existing policy.

**Request Body:** Same as POST /policy

**Response:** `200 OK` with policy state object

### DELETE /policy
Remove the current policy.

**Response:** `200 OK` with `{"message": "Policy removed"}`

## Environment Variables

- `SPC_AGENT_PATH` - Path to system-policy-agent binary (default: bin/system-policy-agent)
- `SPC_STATE_PATH` - Path to policy state file (default: data/policy_state.json)
- `SPC_PROFILE_DIR` - Directory for .mobileconfig files (default: data/profiles)
- `SPC_API_HOST` - API server host (default: 127.0.0.1)
- `SPC_API_PORT` - API server port (default: 8000)

## Examples

### Using curl

**Create a policy:**
```bash
curl -X POST http://localhost:8000/policy \
  -H "Content-Type: application/json" \
  -d '{
    "profile_identifier": "com.example.policy",
    "display_name": "Example Policy",
    "organization": "Example",
    "allow_identified_developers": true,
    "enable_assessment": true,
    "install": false
  }'
```

**Get current policy:**
```bash
curl http://localhost:8000/policy
```

**List all profiles:**
```bash
curl http://localhost:8000/policies
```

**Update a policy:**
```bash
curl -X PUT http://localhost:8000/policy \
  -H "Content-Type: application/json" \
  -d '{
    "allow_identified_developers": false,
    "install": false
  }'
```

**Delete a policy:**
```bash
curl -X DELETE http://localhost:8000/policy
```

## Running the API Server

```bash
make run-api
```

Or with custom host/port:
```bash
SPC_API_HOST=0.0.0.0 SPC_API_PORT=8080 make run-api
```

## Verification

To verify that the API and Agent are properly integrated:

```bash
make verify
```

This script will:
1. Create a policy via the API
2. Verify the Agent generated a valid .mobileconfig file
3. Read the policy back from the state file
4. Update the policy
5. List all profiles
6. Delete the policy
7. Test direct Agent CLI invocation

You should see `✓ ALL VERIFICATIONS PASSED` if everything is working correctly.

## Architecture

### API → Agent Communication Flow

```
Client Request
       │
       ▼
   Python API (src/api/main.py)
       │
       ├─ Parses request
       ├─ Constructs agent arguments
       │
       ▼
   Subprocess call
       │
       ▼
   Swift Agent (bin/system-policy-agent)
       │
       ├─ Generates .mobileconfig profile
       ├─ Writes profile to data/profiles/
       ├─ (Optionally) installs via /usr/bin/profiles
       ├─ Writes state to data/policy_state.json
       │
       ▼
   Response to API
       │
       ├─ Reads state file
       ├─ Returns state to client
       │
       ▼
   Client Response
```

### State Management

The agent maintains state in `data/policy_state.json`:

```json
{
  "policy": {
    "profile_identifier": "com.example.policy",
    "display_name": "My Policy",
    ...
  },
  "profile_path": "/path/to/profile.mobileconfig",
  "applied_at": "2026-01-28T14:00:00Z",
  "install_attempted": false,
  "install_succeeded": false,
  "installer_stdout": "...",
  "installer_stderr": "..."
}
```

The API reads this state file after agent operations to return the current state to clients.

### Profile Files

Generated profiles are stored in `data/profiles/` with the format:
```
{profile_identifier}-{UUID}.mobileconfig
```

Example: `com.example.policy-3D7D5026-6009-4385-968B-E868B780838F.mobileconfig`

The agent can optionally install these profiles using `/usr/bin/profiles` on macOS.
