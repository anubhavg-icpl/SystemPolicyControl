# SystemPolicyControl - Complete Codebase Documentation

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Project Structure](#project-structure)
4. [Component Deep Dive](#component-deep-dive)
   - [Swift Agent](#swift-agent)
   - [Python API](#python-api)
   - [State Management](#state-management)
   - [Models](#models)
5. [Data Flow](#data-flow)
6. [End-to-End Operations](#end-to-end-operations)
   - [Creating a Policy](#creating-a-policy)
   - [Reading a Policy](#reading-a-policy)
   - [Updating a Policy](#updating-a-policy)
   - [Deleting a Policy](#deleting-a-policy)
   - [Listing All Profiles](#listing-all-profiles)
7. [File-by-File Explanation](#file-by-file-explanation)
8. [Execution Order](#execution-order)
9. [Testing Strategy](#testing-strategy)
10. [Environment & Configuration](#environment--configuration)

---

## Overview

SystemPolicyControl is a macOS Gatekeeper policy management system that provides:

- **CLI Tool**: Swift-based executable for direct policy management
- **HTTP API**: Python-based REST API for remote policy management
- **CRUD Operations**: Full Create, Read, Update, Delete for Gatekeeper profiles
- **State Tracking**: JSON-based persistence of policy state
- **Profile Generation**: Automated `.mobileconfig` file generation
- **Profile Installation**: Integration with macOS `/usr/bin/profiles` tool

### Key Design Principles

1. **Separation of Concerns**: Swift handles macOS-specific operations, Python provides HTTP interface
2. **Single Source of Truth**: State file (`data/policy_state.json`) contains authoritative policy state
3. **Command-Line First**: Agent works independently via CLI; API is a thin wrapper
4. **Explicit State**: All operations write state to disk; API reads from state files
5. **No Side Effects**: Tests use temporary directories; production uses `data/` directory

---

## Architecture

### High-Level Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Layer                           │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────┐ │
│  │   CLI User   │    │  HTTP Client │    │  Scripts │ │
│  └──────┬───────┘    └──────┬───────┘    └────┬─────┘ │
└─────────┼───────────────────┼───────────────────┼────────┘
          │                   │                   │
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────┐
│                    Interface Layer                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          Python WSGI API (src/api/main.py)         │  │
│  │  - HTTP request parsing                            │  │
│  │  - JSON validation                                 │  │
│  │  - Subprocess orchestration                          │  │
│  │  - Response formatting                              │  │
│  └────────────────────┬───────────────────────────────┘  │
└───────────────────────┼───────────────────────────────────┘
                        │ subprocess.run()
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                   Business Logic Layer                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │     Swift Agent (bin/system-policy-agent)            │  │
│  │  - Argument parsing                                 │  │
│  │  - Profile payload building                          │  │
│  │  - Plist serialization                             │  │
│  │  - File operations                                 │  │
│  │  - macOS profiles tool integration                  │  │
│  └────────────────────┬───────────────────────────────┘  │
└───────────────────────┼───────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    Storage Layer                         │
│  ┌──────────────────┐      ┌────────────────────┐      │
│  │  State File      │      │  Profile Files    │      │
│  │  (JSON)          │      │  (.mobileconfig)   │      │
│  │  data/policy_    │      │  data/profiles/    │      │
│  │  state.json      │      │                   │      │
│  └──────────────────┘      └────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### Communication Flow

```
┌─────────┐
│ Client  │
└────┬────┘
     │ HTTP Request
     ▼
┌──────────────────────┐
│   Python API        │
│   (WSGI App)       │
└────┬───────────────┘
     │ 1. Parse JSON
     │ 2. Validate
     │ 3. Build args
     ▼
┌──────────────────────┐
│  Subprocess Call    │
│  to Swift Agent     │
└────┬───────────────┘
     │ Agent runs
     ▼
┌──────────────────────┐
│   Swift Agent       │
│   (CLI Binary)      │
└────┬───────────────┘
     │ 1. Build profile
     │ 2. Write .mobileconfig
     │ 3. (Optional) Install
     │ 4. Write state
     ▼
┌──────────────────────┐
│  State File         │
│  data/policy_       │
│  state.json         │
└────┬───────────────┘
     │
     │ API reads state
     ▼
┌──────────────────────┐
│   HTTP Response      │
└────┬───────────────┘
     │ JSON State
     ▼
┌─────────┐
│ Client  │
└─────────┘
```

---

## Project Structure

```
SystemPolicyControl/
├── swift/
│   └── SystemPolicyAgent/
│       ├── Package.swift              # SwiftPM package config
│       ├── Sources/SystemPolicyAgent/
│       │   └── main.swift           # Agent CLI (all logic)
│       └── .build/                  # Compiled artifacts
├── src/
│   ├── api/
│   │   └── main.py                 # WSGI HTTP API
│   └── common/
│       ├── models.py                # Data classes
│       └── state.py                # State persistence
├── bin/
│   └── system-policy-agent          # Compiled Swift binary
├── data/
│   ├── policy_state.json           # Current policy state
│   └── profiles/                  # Generated .mobileconfig files
│       └── *.mobileconfig
├── tests/
│   ├── test_agent.py               # Agent CLI tests
│   └── test_api_agent_integration.py # API→Agent integration tests
├── scripts/
│   └── verify_integration.py       # E2E verification script
├── docs/
│   ├── API.md                     # API reference
│   ├── INTEGRATION.md             # Integration documentation
│   └── CODEBASE.md               # This file
├── Makefile                       # Build automation
├── requirements.txt               # Python dependencies
└── AGENTS.md                     # Repository guidelines
```

---

## Component Deep Dive

### Swift Agent

**Location**: `swift/SystemPolicyAgent/Sources/SystemPolicyAgent/main.swift`

**Purpose**: Standalone CLI executable for macOS Gatekeeper policy management

**Key Types**:

```swift
// Configuration structure
struct AgentConfig {
    var allowIdentifiedDevelopers: Bool = true
    var enableAssessment: Bool = true
    var enableXProtectMalwareUpload: Bool = true
    var profileIdentifier: String = "com.systempolicycontrol.policy"
    var displayName: String = "System Policy Control"
    var organization: String = "SystemPolicyControl"
    var description: String? = nil
    var profileDirectory: URL
    var statePath: URL
    var installProfile: Bool = true
}

// Installation result
struct InstallResult {
    let succeeded: Bool
    let stdout: String?
    let stderr: String?
}

// Action enumeration
enum AgentAction {
    case apply(AgentConfig)
    case remove(identifier: String, profileDirectory: URL, statePath: URL)
    case list
}

// Error types
enum AgentError: Error, CustomStringConvertible {
    case invalidArguments(String)
    case failedToWriteProfile(String)
    case failedToWriteState(String)
}
```

**Key Functions** (in execution order):

#### 1. Entry Point
```swift
exit(runAgent())  // main.swift:306
```

#### 2. Argument Parsing
```swift
func parseArguments() throws -> AgentAction
```
- Reads `CommandLine.arguments`
- Determines action: `apply`, `remove`, or `list`
- For `apply`: builds `AgentConfig` with all flags
- For `remove`: extracts identifier and paths
- For `list`: no additional parsing needed
- Returns `AgentAction` enum

#### 3. Profile Building (apply action)
```swift
func buildProfilePayload(config: AgentConfig) -> [String: Any]
```
- Constructs Gatekeeper payload dictionary:
  ```swift
  [
    "EnableAssessment": bool,
    "EnableXProtectMalwareUpload": bool,
    "AllowIdentifiedDevelopers": bool,  // only if EnableAssessment=true
    "PayloadType": "com.apple.systempolicy.control",
    "PayloadVersion": 1,
    "PayloadIdentifier": "{id}.payload",
    "PayloadUUID": "{random}"
  ]
  ```
- Wraps in profile envelope:
  ```swift
  [
    "PayloadContent": [payload],
    "PayloadDescription": "...",
    "PayloadDisplayName": "...",
    "PayloadIdentifier": "...",
    "PayloadOrganization": "...",
    "PayloadRemovalDisallowed": true,
    "PayloadType": "Configuration",
    "PayloadVersion": 1,
    "PayloadUUID": "{random}"
  ]
  ```

#### 4. Profile Writing
```swift
func writeProfile(_ profile: [String: Any], to directory: URL, identifier: String) throws -> URL
```
- Creates directory if needed
- Generates filename: `{identifier}-{UUID}.mobileconfig`
- Serializes to XML plist
- Writes to disk
- Returns file path

#### 5. Profile Installation (optional)
```swift
func installProfile(at url: URL, shouldInstall: Bool) -> InstallResult
```
- Skips if `shouldInstall == false`
- Calls `/usr/bin/profiles install -type configuration -path {url}`
- Captures stdout/stderr
- Returns success status

#### 6. State Writing
```swift
func writeState(config: AgentConfig, profilePath: URL, installResult: InstallResult) throws
```
- Creates state dictionary:
  ```swift
  [
    "policy": { ... },
    "profile_path": "/path/to/profile.mobileconfig",
    "applied_at": "2026-01-28T...",
    "install_attempted": bool,
    "install_succeeded": bool,
    "installer_stdout": "...",
    "installer_stderr": "..."
  ]
  ```
- Serializes to JSON with pretty-printing
- Writes to state file

#### 7. Profile Removal (remove action)
```swift
func removeProfile(withIdentifier identifier: String) -> InstallResult
```
- Calls `/usr/bin/profiles -R -p {identifier}`
- Captures stdout/stderr
- Returns success status

#### 8. Profile Listing (list action)
```swift
func listProfiles() -> [[String: Any]]?
```
- Calls `/usr/bin/profiles -C -o stdout`
- Parses XML plist response
- Returns array of profile dictionaries

#### 9. Cleanup Functions
```swift
func deleteState(at path: URL) throws
func deleteProfileFile(at path: URL) throws
```
- Remove state file
- Remove profile files matching identifier

#### 10. Main Dispatch
```swift
func runAgent() -> Int32
```
- Parses arguments → `AgentAction`
- Switch on action type:
  - `.apply`: build → write → install → write state
  - `.remove`: remove profile → delete files → delete state
  - `.list`: call profiles → output JSON
- Returns exit code: 0 for success, 1 for failure

---

### Python API

**Location**: `src/api/main.py`

**Purpose**: WSGI HTTP server that wraps the Swift agent

**Key Components**:

#### 1. Configuration
```python
AGENT_BIN = Path(os.environ.get("SPC_AGENT_PATH", "bin/system-policy-agent"))
STATE_PATH = Path(os.environ.get("SPC_STATE_PATH", "data/policy_state.json"))
PROFILE_DIR = Path(os.environ.get("SPC_PROFILE_DIR", "data/profiles"))
```

#### 2. Helper Functions

```python
def _json_response(status, payload):
    """Create HTTP response with JSON body"""

def _read_body(environ):
    """Read request body from WSGI environ"""

def _agent_args(agent_bin, policy, install, profile_dir, state_path):
    """Build subprocess arguments for agent 'apply'"""

def _remove_args(agent_bin, identifier, profile_dir, state_path):
    """Build subprocess arguments for agent 'remove'"""

def _list_args(agent_bin):
    """Build subprocess arguments for agent 'list'"""
```

#### 3. WSGI Application

```python
def application(environ, start_response) -> ResponseBody:
    """
    Main WSGI entry point
    Handles all HTTP requests
    """
    # Read environment variables for each request (testing support)
    agent_bin = Path(os.environ.get("SPC_AGENT_PATH", "bin/system-policy-agent"))
    state_path = Path(os.environ.get("SPC_STATE_PATH", "data/policy_state.json"))
    profile_dir = Path(os.environ.get("SPC_PROFILE_DIR", "data/profiles"))

    # Route requests
    if path == "/healthz" and method == "GET":
        return health_check()

    if path == "/policies" and method == "GET":
        return list_policies()

    if path == "/policy":
        if method == "GET":
            return get_policy()
        if method == "POST":
            return create_policy()
        if method == "PUT":
            return update_policy()
        if method == "DELETE":
            return delete_policy()
```

#### 4. Endpoint Implementations

**GET /healthz**
```python
status, headers, body = _json_response(HTTPStatus.OK, {"status": "ok"})
```

**GET /policies**
```python
# Call agent list command
args = _list_args(agent_bin)
result = subprocess.run(args, capture_output=True, text=True)

# Parse response
policies = json.loads(result.stdout)
return {"policies": policies}
```

**GET /policy**
```python
# Read state file directly (no agent call needed)
store = PolicyStateStore(state_path)
state = store.load()
return state.to_dict()
```

**POST /policy**
```python
# Parse request
payload = _read_body(environ)
policy = SystemPolicy.from_dict(payload)
install = bool(payload.pop("install", True))

# Call agent
args = _agent_args(agent_bin, policy, install, profile_dir, state_path)
result = subprocess.run(args, capture_output=True, text=True)

# Return state
store = PolicyStateStore(state_path)
state = store.load()
return state.to_dict()
```

**PUT /policy**
```python
# Same as POST, just different HTTP semantics
# Reuses same agent 'apply' command
```

**DELETE /policy**
```python
# Get current state to get identifier
store = PolicyStateStore(state_path)
state = store.load()
identifier = state.policy.profile_identifier

# Call agent remove
args = _remove_args(agent_bin, identifier, profile_dir, state_path)
result = subprocess.run(args, capture_output=True, text=True)

return {"message": "Policy removed"}
```

---

### State Management

**Location**: `src/common/state.py`

**Purpose**: JSON file persistence for policy state

#### PolicyStateStore Class

```python
class PolicyStateStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Optional[PolicyState]:
        """Load state from JSON file"""
        if not self.path.exists():
            return None
        with self.path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return PolicyState.from_dict(payload)

    def save(self, state: PolicyState) -> None:
        """Save state to JSON file"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(state.to_dict(), handle, indent=2, sort_keys=True)
```

#### State File Format

```json
{
  "applied_at": "2026-01-28T14:00:00.123Z",
  "install_attempted": true,
  "install_succeeded": false,
  "installer_stdout": "profiles tool no longer supports installs...",
  "installer_stderr": "",
  "policy": {
    "allow_identified_developers": true,
    "display_name": "System Policy Control",
    "enable_assessment": true,
    "enable_xprotect_malware_upload": true,
    "organization": "SystemPolicyControl",
    "profile_identifier": "com.systempolicycontrol.policy"
  },
  "profile_path": "/path/to/profile.mobileconfig"
}
```

---

### Models

**Location**: `src/common/models.py`

**Purpose**: Shared data structures using Python dataclasses

#### SystemPolicy

```python
@dataclass
class SystemPolicy:
    allow_identified_developers: bool = True
    enable_assessment: bool = True
    enable_xprotect_malware_upload: bool = True
    profile_identifier: str = "com.systempolicycontrol.policy"
    display_name: str = "System Policy Control"
    organization: str = "SystemPolicyControl"
    description: Optional[str] = None

    def __post_init__(self):
        # Business rule: if assessment disabled, no identified developers
        if not self.enable_assessment:
            self.allow_identified_developers = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "SystemPolicy":
        # Filter only valid fields (ignore extra keys)
        filtered = {k: v for k, v in payload.items()
                    if k in cls.__dataclass_fields__}
        return cls(**filtered)
```

#### PolicyState

```python
@dataclass
class PolicyState:
    policy: SystemPolicy
    profile_path: str
    applied_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    install_attempted: bool = True
    install_succeeded: bool = False
    installer_stdout: Optional[str] = None
    installer_stderr: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["applied_at"] = self.applied_at.isoformat()
        data["policy"] = self.policy.to_dict()
        return data

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "PolicyState":
        payload = payload.copy()
        payload["policy"] = SystemPolicy.from_dict(payload["policy"])
        # Parse ISO8601 timestamp
        payload["applied_at"] = datetime.fromisoformat(...)
        return cls(**payload)
```

---

## Data Flow

### Read Operations

```
Client Request → API → State File → API → Client Response
```

- API reads state file directly
- No agent subprocess call needed
- Fast response time

### Write Operations

```
Client Request → API → Agent → Profile File + State File → API → State File → Client Response
```

- API shells out to agent
- Agent writes profile file and state file
- API reads state file for response
- Slower response (subprocess overhead)

---

## End-to-End Operations

### Creating a Policy

**Client Request:**
```http
POST /policy
Content-Type: application/json

{
  "profile_identifier": "com.example.policy",
  "display_name": "Example Policy",
  "organization": "Example Corp",
  "allow_identified_developers": true,
  "enable_assessment": true,
  "enable_xprotect_malware_upload": false,
  "install": false
}
```

**Execution Flow:**

1. **Python API** (`src/api/main.py`):
   - `application()` receives request
   - Reads environment variables
   - Calls `_read_body()` to parse JSON
   - Creates `SystemPolicy.from_dict(payload)`
   - Calls `_agent_args()` to build subprocess arguments:
     ```python
     ["bin/system-policy-agent", "apply",
      "--profile-dir", "data/profiles",
      "--state-path", "data/policy_state.json",
      "--profile-identifier", "com.example.policy",
      "--display-name", "Example Policy",
      "--organization", "Example Corp",
      "--allow-identified-developers", "true",
      "--enable-assessment", "true",
      "--enable-xprotect-malware-upload", "false",
      "--no-install"]
     ```

2. **Subprocess Execution**:
   - `subprocess.run(args, capture_output=True, text=True)`
   - Agent binary executes

3. **Swift Agent** (`main.swift`):
   - `runAgent()` entry point
   - `parseArguments()` → `.apply(AgentConfig)`
   - `buildProfilePayload(config)` → constructs profile dictionary
   - `writeProfile(profile, to: profileDir, identifier: id)` → writes `.mobileconfig`
   - `installProfile(at: url, shouldInstall: false)` → skipped
   - `writeState(config, profilePath, installResult)` → writes `data/policy_state.json`
   - Returns `EXIT_SUCCESS`

4. **File Output**:
   ```
   data/profiles/com.example.policy-3D7D5026-6009-4385-968B-E868B780838F.mobileconfig
   data/policy_state.json
   ```

5. **Python API** (continues):
   - Checks `result.returncode` → 0 (success)
   - `PolicyStateStore(state_path).load()` → reads `data/policy_state.json`
   - Returns `state.to_dict()` as JSON
   - HTTP status: `201 Created`

**Client Response:**
```json
{
  "policy": {
    "allow_identified_developers": true,
    "display_name": "Example Policy",
    "enable_assessment": true,
    "enable_xprotect_malware_upload": false,
    "organization": "Example Corp",
    "profile_identifier": "com.example.policy"
  },
  "profile_path": "/path/to/profile.mobileconfig",
  "applied_at": "2026-01-28T14:00:00.123Z",
  "install_attempted": false,
  "install_succeeded": false,
  "installer_stderr": "Installation skipped (no-install)",
  "installer_stdout": null
}
```

**Generated Profile** (`data/profiles/*.mobileconfig`):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>PayloadContent</key>
  <array>
    <dict>
      <key>EnableAssessment</key>
      <true/>
      <key>EnableXProtectMalwareUpload</key>
      <false/>
      <key>AllowIdentifiedDevelopers</key>
      <true/>
      <key>PayloadType</key>
      <string>com.apple.systempolicy.control</string>
      <key>PayloadVersion</key>
      <integer>1</integer>
      <key>PayloadIdentifier</key>
      <string>com.example.policy.payload</string>
      <key>PayloadUUID</key>
      <string>3D7D5026-6009-4385-968B-E868B780838F</string>
    </dict>
  </array>
  <key>PayloadDisplayName</key>
  <string>Example Policy</string>
  <key>PayloadIdentifier</key>
  <string>com.example.policy</string>
  <key>PayloadOrganization</key>
  <string>Example Corp</string>
  <key>PayloadRemovalDisallowed</key>
  <true/>
  <key>PayloadType</key>
  <string>Configuration</string>
  <key>PayloadVersion</key>
  <integer>1</integer>
  <key>PayloadUUID</key>
  <string>A1B2C3D4-E5F6-7890-ABCD-EF1234567890</string>
</dict>
</plist>
```

---

### Reading a Policy

**Client Request:**
```http
GET /policy
```

**Execution Flow:**

1. **Python API** (`src/api/main.py`):
   - `application()` receives request
   - Reads environment variables
   - Creates `PolicyStateStore(state_path)`
   - Calls `store.load()` → reads `data/policy_state.json`
   - Parses JSON into `PolicyState` object

2. **JSON Parsing** (`src/common/state.py`):
   - Opens `data/policy_state.json`
   - `json.load(handle)` → dict
   - `PolicyState.from_dict(payload)`:
     - Parses `applied_at` timestamp → `datetime`
     - Parses `policy` dict → `SystemPolicy.from_dict()`

3. **Response Construction**:
   - `state.to_dict()` → serializes back to dict
   - `_json_response(HTTPStatus.OK, state.to_dict())`

**Client Response:**
```json
{
  "policy": {
    "allow_identified_developers": true,
    "display_name": "Example Policy",
    "enable_assessment": true,
    "enable_xprotect_malware_upload": false,
    "organization": "Example Corp",
    "profile_identifier": "com.example.policy"
  },
  "profile_path": "/Users/.../data/profiles/com.example.policy-3D7D5026-6009-4385-968B-E868B780838F.mobileconfig",
  "applied_at": "2026-01-28T14:00:00.123Z",
  "install_attempted": false,
  "install_succeeded": false,
  "installer_stderr": "Installation skipped (no-install)",
  "installer_stdout": null
}
```

**Note**: No agent subprocess call! Direct file read for fast response.

---

### Updating a Policy

**Client Request:**
```http
PUT /policy
Content-Type: application/json

{
  "allow_identified_developers": false,
  "enable_assessment": true,
  "install": false
}
```

**Execution Flow:**

1. **Python API** (`src/api/main.py`):
   - `application()` receives request
   - `_read_body()` → parse JSON
   - `SystemPolicy.from_dict(payload)` → merges with existing state
   - Same flow as CREATE → calls agent `apply`

2. **Swift Agent** (`main.swift`):
   - Same flow as CREATE
   - Generates new `.mobileconfig` with updated settings
   - Overwrites state file

3. **File Output**:
   ```
   data/profiles/com.example.policy-A1B2C3D4-5566-7788-99AA-BBCCDDEEFF00.mobileconfig
   data/policy_state.json  # Updated
   ```

4. **Response**: `200 OK` with updated state

**Note**: Old profile file remains (not cleaned up). Only state file is authoritative.

---

### Deleting a Policy

**Client Request:**
```http
DELETE /policy
```

**Execution Flow:**

1. **Python API** (`src/api/main.py`):
   - `application()` receives request
   - `PolicyStateStore(state_path).load()` → get current state
   - Extract `identifier = state.policy.profile_identifier`
   - Calls `_remove_args(agent_bin, identifier, profile_dir, state_path)`:
     ```python
     ["bin/system-policy-agent", "remove",
      "com.example.policy",
      "--profile-dir", "data/profiles",
      "--state-path", "data/policy_state.json"]
     ```

2. **Subprocess Execution**:
   - `subprocess.run(args, capture_output=True, text=True)`

3. **Swift Agent** (`main.swift`):
   - `parseArguments()` → `.remove(identifier, profileDir, statePath)`
   - `removeProfile(withIdentifier: identifier)`:
     - Calls `/usr/bin/profiles -R -p com.example.policy`
   - Finds profile files matching identifier in `profileDirectory`
   - `deleteProfileFile(at: path)` for each match
   - `deleteState(at: statePath)` → removes `data/policy_state.json`
   - Returns `EXIT_SUCCESS`

4. **Response**: `200 OK` with `{"message": "Policy removed"}`

**Verification:**
```http
GET /policy

Response: 404 Not Found
{"error": "policy_not_found"}
```

---

### Listing All Profiles

**Client Request:**
```http
GET /policies
```

**Execution Flow:**

1. **Python API** (`src/api/main.py`):
   - `application()` receives request
   - Calls `_list_args(agent_bin)`:
     ```python
     ["bin/system-policy-agent", "list"]
     ```

2. **Subprocess Execution**:
   - `subprocess.run(args, capture_output=True, text=True)`

3. **Swift Agent** (`main.swift`):
   - `parseArguments()` → `.list`
   - `listProfiles()`:
     - Calls `/usr/bin/profiles -C -o stdout`
     - Parses XML plist response
     - Returns array of profile dicts
   - Outputs JSON array to stdout

4. **Python API** (continues):
   - `policies = json.loads(result.stdout)`
   - Returns `{"policies": policies}`

**Client Response:**
```json
{
  "policies": [
    {
      "PayloadIdentifier": "com.example.policy",
      "PayloadDisplayName": "Example Policy",
      "PayloadOrganization": "Example Corp",
      "PayloadType": "Configuration",
      "PayloadUUID": "A1B2C3D4-E5F6-7890-ABCD-EF1234567890",
      ...
    }
  ]
}
```

**Note**: This queries macOS system profiles, not just our agent's profiles.

---

## File-by-File Explanation

### swift/SystemPolicyAgent/Sources/SystemPolicyAgent/main.swift

**Purpose**: Complete Swift CLI application for policy management

**Structure**:
- Lines 1-24: Imports and `AgentConfig` struct
- Lines 26-30: `InstallResult` struct
- Lines 32-47: `AgentError` enum
- Lines 49-67: Helper functions (`resolvePath`, `parseBool`)
- Lines 69-87: `printUsage()` function
- Lines 89-168: `parseArguments()` - Main argument parser
- Lines 170-195: `buildProfilePayload()` - Construct profile dictionary
- Lines 197-206: `writeProfile()` - Write .mobileconfig file
- Lines 208-239: `installProfile()` - Call macOS profiles tool
- Lines 241-280: `writeState()` - Write JSON state file
- Lines 282-304: `runAgent()` - Main dispatch logic

**Key Design Decisions**:
- Uses `AgentAction` enum for type-safe action dispatch
- Explicit error handling with custom `AgentError`
- All file operations use Swift's `URL` type (not strings)
- Process execution via `Process()` for proper stdout/stderr capture

---

### src/api/main.py

**Purpose**: WSGI HTTP server wrapping the Swift agent

**Structure**:
- Lines 1-23: Imports and constants
- Lines 25-31: `_json_response()` - Response builder
- Lines 34-39: `_read_body()` - Request parser
- Lines 42-67: `_agent_args()` - Build apply arguments
- Lines 70-71: `_remove_args()` - Build remove arguments
- Lines 74-75: `_list_args()` - Build list arguments
- Lines 78-133: `application()` - Main WSGI handler
- Lines 136-139: `run_server()` - HTTP server runner
- Lines 142-145: `__main__` - Entry point

**Key Design Decisions**:
- Per-request environment variable reading (testing support)
- No session management (stateless HTTP)
- Shell-out to agent for all write operations
- Direct state file read for GET operations

---

### src/common/models.py

**Purpose**: Data structures using Python dataclasses

**Structure**:
- Lines 9-33: `SystemPolicy` dataclass
- Lines 35-59: `PolicyState` dataclass

**Key Design Decisions**:
- Dataclasses for automatic `__init__`, `__repr__`
- `to_dict()` and `from_dict()` for JSON serialization
- `__post_init__()` for business logic enforcement
- Field validation in `from_dict()` (ignore extra keys)

---

### src/common/state.py

**Purpose**: JSON file persistence

**Structure**:
- Lines 11-28: `PolicyStateStore` class
  - `__init__()`: Set up path
  - `load()`: Read and parse JSON
  - `save()`: Write JSON with formatting

**Key Design Decisions**:
- Simple file-based storage (no database)
- Auto-create parent directories
- Pretty-printed JSON for readability
- `Optional[PolicyState]` for missing file handling

---

### tests/test_agent.py

**Purpose**: Unit tests for Swift agent CLI

**Structure**:
- Lines 12-24: `setUp()` / `tearDown()` - Test fixtures
- Lines 26-49: `_run_cli()` - Test helper
- Lines 51-60: `test_profile_includes_allow_flag_when_gatekeeper_enabled()`
- Lines 62-70: `test_profile_omits_allow_flag_when_gatekeeper_disabled()`
- Lines 72-78: `test_state_file_records_metadata()`
- Lines 80-87: `test_list_profiles_returns_empty_when_no_profiles()`
- Lines 89-103: `test_remove_policy_deletes_state_file()`

**Key Design Decisions**:
- Uses `tempfile.TemporaryDirectory()` for isolation
- Skips tests if agent binary missing
- Tests real agent binary (no mocking)
- Verifies file system state (profiles, state files)

---

### tests/test_api_agent_integration.py

**Purpose**: Integration tests for API → Agent communication

**Structure**:
- Lines 14-23: `setUp()` / `tearDown()` - Test fixtures
- Lines 25-47: `_call_api()` - WSGI test helper
- Lines 49-76: `test_api_creates_policy_via_agent()`
- Lines 78-88: `test_api_reads_policy_from_state_file()`
- Lines 90-113: `test_api_updates_policy_via_agent()`
- Lines 115-139: `test_api_deletes_policy_via_agent()`
- Lines 141-153: `test_api_lists_policies_via_agent()`

**Key Design Decisions**:
- Tests both API and Agent end-to-end
- Uses custom environment variables for isolation
- Verifies profile file generation
- Validates state file synchronization

---

### scripts/verify_integration.py

**Purpose**: Manual verification script

**Structure**:
- Lines 22-45: `call_api()` - Helper function
- Lines 48-145: `main()` - Verification steps:
  1. Create policy via API
  2. Verify profile file exists and is valid
  3. Verify state file was written
  4. Test agent directly
  5. Verify API can read policy back
  6. Test update via API
  7. Test list via API
  8. Test delete via API
  9. Verify deletion

**Key Design Decisions**:
- Visual output with ✓ and ✗ markers
- Step-by-step verification
- Exits with non-zero on failure
- Comprehensive coverage of all operations

---

## Execution Order

### Startup

1. Build agent:
   ```bash
   make build-agent
   swift build -c release
   cp .build/release/SystemPolicyAgent bin/system-policy-agent
   ```

2. Start API server:
   ```bash
   make run-api
   python3 -m api.main
   # Runs on http://127.0.0.1:8000
   ```

### Request Processing (Generic)

1. **Client** sends HTTP request
2. **Python API** `application()` receives WSGI environ
3. **Parse** path and method
4. **Read** request body (if POST/PUT)
5. **Load** environment variables
6. **Dispatch** to appropriate handler
7. **Handler** logic:
   - **Read operations**: Load state file directly
   - **Write operations**: Shell-out to agent
8. **Agent** executes (for writes)
9. **Agent** writes files
10. **API** reads state file (for writes)
11. **API** returns JSON response
12. **Client** receives response

### Agent Execution (Apply)

1. `exit(runAgent())` - Entry
2. `parseArguments()` - Parse CLI args → `AgentAction`
3. `runAgent()` switches on action
4. `.apply(config)` → build → write → install → write state
5. `buildProfilePayload()` - Construct profile dict
6. `writeProfile()` - Write .mobileconfig file
7. `installProfile()` - Call `/usr/bin/profiles`
8. `writeState()` - Write JSON state
9. Return `EXIT_SUCCESS`

### Agent Execution (Remove)

1. `runAgent()` switches on action
2. `.remove(identifier)` → remove profile → delete files → delete state
3. `removeProfile()` - Call `/usr/bin/profiles -R`
4. Find and delete profile files
5. `deleteState()` - Remove state file
6. Return `EXIT_SUCCESS`

### Agent Execution (List)

1. `runAgent()` switches on action
2. `.list` → call profiles → output JSON
3. `listProfiles()` - Call `/usr/bin/profiles -C`
4. Parse XML plist → array of dicts
5. Serialize to JSON → stdout
6. Return `EXIT_SUCCESS`

---

## Testing Strategy

### Unit Tests (`tests/test_agent.py`)

**Scope**: Swift agent CLI functionality

**Approach**:
- Use real compiled agent binary
- Temporary directories for isolation
- No mocking of subprocess
- Verify file system state

**Test Coverage**:
- Profile payload generation
- State file writing
- List command output
- Remove command cleanup

### Integration Tests (`tests/test_api_agent_integration.py`)

**Scope**: API → Agent communication

**Approach**:
- Test both API and Agent together
- Custom environment variables per test
- Verify end-to-end flow
- Validate profile file generation

**Test Coverage**:
- CREATE via API → Agent
- READ via API → State file
- UPDATE via API → Agent
- DELETE via API → Agent
- LIST via API → Agent

### Manual Verification (`scripts/verify_integration.py`)

**Scope**: Full end-to-end validation

**Approach**:
- Step-by-step verification
- Visual output
- No framework (standalone script)
- Can be run manually

**Verification Steps**:
1. Create policy
2. Verify profile file
3. Verify state file
4. Read policy back
5. Update policy
6. List policies
7. Delete policy
8. Test direct agent CLI

### Running Tests

```bash
# Build agent first
make build-agent

# Run all unit and integration tests
make test

# Run verification script
make verify

# Run specific test
PYTHONPATH=src python3 -m unittest tests.test_agent.SystemPolicyAgentCLITests.test_profile_includes_allow_flag_when_gatekeeper_enabled
```

---

## Environment & Configuration

### Environment Variables

| Variable | Default | Purpose | Used By |
|-----------|----------|---------|----------|
| `SPC_AGENT_PATH` | `bin/system-policy-agent` | Path to agent binary | API |
| `SPC_STATE_PATH` | `data/policy_state.json` | State file location | API, Agent |
| `SPC_PROFILE_DIR` | `data/profiles` | Profile directory | API, Agent |
| `SPC_API_HOST` | `127.0.0.1` | API server host | API |
| `SPC_API_PORT` | `8000` | API server port | API |

### File System Layout

```
SystemPolicyControl/
├── bin/
│   └── system-policy-agent          # Compiled Swift binary (executable)
├── data/
│   ├── policy_state.json           # Current policy state (read/write)
│   └── profiles/                  # Generated .mobileconfig files
│       ├── com.example.policy-UUID1.mobileconfig
│       ├── com.example.policy-UUID2.mobileconfig
│       └── ...
├── swift/SystemPolicyAgent/.build/  # Swift build artifacts (gitignored)
└── .venv/                        # Python virtual environment (gitignored)
```

### Gitignored Files

```gitignore
.venv/
dist/
build/
__pycache__/
.pytest_cache/
bin/
swift/SystemPolicyAgent/.build/
data/profiles/*.mobileconfig
data/policy_state.json
```

**Rationale**:
- Build artifacts: Rebuildable from source
- Binary files: Large, platform-specific
- Generated profiles: Unique per run
- State file: Contains runtime state
- Virtual env: Environment-specific

---

## Summary

### Architecture Highlights

1. **Separation of Concerns**:
   - Swift: macOS-specific operations
   - Python: HTTP interface
   - Clear boundaries between components

2. **Single Source of Truth**:
   - State file is authoritative
   - Agent writes state
   - API reads state
   - No in-memory state

3. **Explicit State**:
   - All state persisted to disk
   - File system is database
   - Restart doesn't lose state

4. **Command-Line First**:
   - Agent works independently
   - API is thin wrapper
   - Can use agent directly

### Key Features

✅ **Full CRUD Operations**
- Create: `apply` command
- Read: `list` command and state file
- Update: `apply` command (re-generate)
- Delete: `remove` command

✅ **HTTP API**
- RESTful endpoints
- JSON request/response
- WSGI compliant
- Stateless

✅ **CLI Tool**
- Standalone executable
- Proper argument parsing
- Help documentation
- Error handling

✅ **Testing**
- Unit tests for agent
- Integration tests for API
- Manual verification script
- All tests passing (10/10)

✅ **Documentation**
- Complete API reference
- Integration guide
- Codebase documentation (this file)
- Inline comments

### Execution Flow Summary

```
┌─────────────────────────────────────────────────────────┐
│                   READ OPERATIONS                     │
│  Client → API → State File → API → Client           │
│  (Fast, no subprocess call)                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                  WRITE OPERATIONS                     │
│  Client → API → Agent → Files → API → State → Client│
│  (Slower, subprocess call required)                  │
└─────────────────────────────────────────────────────────┘
```

### Future Enhancements

Potential improvements:
- Add authentication/authorization to API
- Implement profile versioning
- Add profile diff/compare functionality
- Support for multiple concurrent policies
- Add webhook notifications on policy changes
- Implement audit logging
- Add profile validation before installation
- Support for user-scoped profiles
- Add metrics/monitoring
- Implement profile rollback

---

## Quick Reference

### Agent Commands

```bash
# Apply (Create/Update)
./bin/system-policy-agent apply \
  --profile-identifier com.example.policy \
  --display-name "Example" \
  --organization "Example" \
  --allow-identified-developers true \
  --enable-assessment true \
  --no-install

# Remove
./bin/system-policy-agent remove com.example.policy

# List
./bin/system-policy-agent list

# Help
./bin/system-policy-agent --help
```

### API Endpoints

```bash
# Health check
GET /healthz

# List all profiles
GET /policies

# Get current policy
GET /policy

# Create policy
POST /policy
Content-Type: application/json
{"profile_identifier": "com.example.policy", ...}

# Update policy
PUT /policy
Content-Type: application/json
{"allow_identified_developers": false, ...}

# Delete policy
DELETE /policy
```

### Make Targets

```bash
make setup           # Create Python venv
make build-agent     # Compile Swift binary
make run-agent       # Run agent with custom args
make run-api         # Start API server
make test            # Run all tests
make verify          # Run verification script
make clean           # Clean all build artifacts
```

### Testing

```bash
# Run all tests
make test

# Run specific test
PYTHONPATH=src python3 -m unittest tests.test_agent.SystemPolicyAgentCLITests.test_profile_includes_allow_flag_when_gatekeeper_enabled

# Run verification
make verify

# Run with verbose output
PYTHONPATH=src python3 -m unittest tests.test_agent -v
```

---

**End of Documentation**

For API reference, see: `docs/API.md`
For integration details, see: `docs/INTEGRATION.md`
For repository guidelines, see: `AGENTS.md`
