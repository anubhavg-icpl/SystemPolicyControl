# SystemPolicyControl

A macOS Gatekeeper policy management system with full CRUD operations via CLI and REST API.

## Overview

SystemPolicyControl provides automated management of macOS Gatekeeper configuration profiles:

- **CLI Tool**: Swift-based executable for direct policy management
- **HTTP API**: Python-based REST API for remote policy management
- **Full CRUD**: Create, Read, Update, Delete operations
- **State Tracking**: JSON-based persistence
- **Profile Generation**: Automated `.mobileconfig` file creation
- **Profile Installation**: Integration with macOS `/usr/bin/profiles`

## Features

✅ **Complete CRUD Operations**
- Create/Apply policies
- Read policy state
- Update existing policies
- Delete policies
- List all installed profiles

✅ **Dual Interface**
- Command-line tool (Swift)
- HTTP REST API (Python WSGI)

✅ **Robust Testing**
- Unit tests (10 tests, all passing)
- Integration tests
- End-to-end verification script

✅ **Comprehensive Documentation**
- API reference
- Codebase documentation
- Integration guide
- Architecture diagrams

## Quick Start

### Prerequisites

- macOS 12+
- Xcode Command Line Tools (for Swift compilation)
- Python 3.8+
- Swift 5.9+

### Installation

```bash
# Clone repository
git clone https://github.com/anubhavg-icpl/SystemPolicyControl.git
cd SystemPolicyControl

# Build Swift agent
make build-agent

# Set up Python virtual environment
make setup
```

### Usage

#### Via CLI

```bash
# Create/Apply a policy
./bin/system-policy-agent apply \
  --profile-identifier com.example.policy \
  --display-name "Example Policy" \
  --organization "Example Corp" \
  --allow-identified-developers true \
  --enable-assessment true \
  --no-install

# Remove a policy
./bin/system-policy-agent remove com.example.policy

# List all profiles
./bin/system-policy-agent list
```

#### Via API

```bash
# Start API server
make run-api

# In another terminal:
curl -X POST http://localhost:8000/policy \
  -H "Content-Type: application/json" \
  -d '{
    "profile_identifier": "com.example.policy",
    "display_name": "Example Policy",
    "organization": "Example Corp",
    "allow_identified_developers": true,
    "enable_assessment": true,
    "install": false
  }'

# Read policy
curl http://localhost:8000/policy

# Update policy
curl -X PUT http://localhost:8000/policy \
  -H "Content-Type: application/json" \
  -d '{"allow_identified_developers": false}'

# Delete policy
curl -X DELETE http://localhost:8000/policy
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/healthz` | Health check |
| GET | `/policies` | List all installed profiles |
| GET | `/policy` | Get current policy state |
| POST | `/policy` | Create new policy |
| PUT | `/policy` | Update existing policy |
| DELETE | `/policy` | Delete current policy |

See [docs/API.md](docs/API.md) for complete API reference.

## Architecture

```
Client → Python API → Swift Agent → .mobileconfig + State File → API → Client
```

### Components

1. **Swift Agent** (`swift/SystemPolicyAgent/Sources/SystemPolicyAgent/main.swift`)
   - CLI executable
   - Generates Gatekeeper profiles
   - Manages state files
   - Supports: `apply`, `remove`, `list` commands

2. **Python API** (`src/api/main.py`)
   - WSGI HTTP server
   - RESTful endpoints
   - Shell-outs to agent binary
   - Reads state file for responses

3. **State Storage** (`data/policy_state.json`)
   - Single source of truth
   - Written by agent
   - Read by API

See [docs/CODEBASE.md](docs/CODEBASE.md) for complete architecture documentation.

## Documentation

| Document | Description |
|----------|-------------|
| [CODEBASE.md](docs/CODEBASE.md) | Complete codebase documentation (1,463 lines) |
| [API.md](docs/API.md) | REST API reference with examples |
| [INTEGRATION.md](docs/INTEGRATION.md) | API-to-Agent integration details |
| [AGENTS.md](docs/AGENTS.md) | Repository guidelines |

## Testing

```bash
# Run all tests
make test

# Run verification script
make verify

# Run specific test
PYTHONPATH=src python3 -m unittest tests.test_agent.SystemPolicyAgentCLITests.test_profile_includes_allow_flag_when_gatekeeper_enabled
```

### Test Results

All tests passing: **10/10 ✓**

```
tests/test_agent.py                      5 tests (agent CLI)
tests/test_api_agent_integration.py       5 tests (API→Agent integration)
```

## Development

### Build

```bash
make build-agent    # Compile Swift binary
make setup          # Create Python venv
make build          # Build everything
```

### Run

```bash
make run-agent      # Run agent with custom args
make run-api        # Start API server (http://127.0.0.1:8000)
```

### Clean

```bash
make clean          # Remove all build artifacts and generated files
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SPC_AGENT_PATH` | `bin/system-policy-agent` | Path to agent binary |
| `SPC_STATE_PATH` | `data/policy_state.json` | Path to state file |
| `SPC_PROFILE_DIR` | `data/profiles` | Directory for .mobileconfig files |
| `SPC_API_HOST` | `127.0.0.1` | API server host |
| `SPC_API_PORT` | `8000` | API server port |

## File Structure

```
SystemPolicyControl/
├── swift/SystemPolicyAgent/    # Swift agent source
├── src/                       # Python API and models
│   ├── api/                   # HTTP API
│   └── common/                # Shared models
├── bin/                       # Compiled agent binary
├── data/                      # Runtime data
│   ├── policy_state.json       # Policy state
│   └── profiles/              # .mobileconfig files
├── tests/                     # Test suite
├── scripts/                   # Utility scripts
├── docs/                      # Documentation
├── Makefile                   # Build automation
└── requirements.txt           # Python dependencies
```

## Security Considerations

1. **Profile Installation**: Requires root/sudo privileges
2. **State File**: Contains sensitive policy configuration
3. **Profile Files**: Should not be committed to version control
4. **No Authentication**: API has no auth - use behind firewall/reverse proxy

## Contributing

Follow repository guidelines in [AGENTS.md](AGENTS.md):

- Swift code targets macOS 12+
- Use Foundation, value types, explicit error handling
- Python modules stay 4-space indented, snake_case files
- Test every new feature
- Use conventional commit messages: `type: summary`

## License

[Add your license here]

## Credits

Built with:
- Swift 5.9+ for macOS integration
- Python 3.8+ for HTTP API
- Standard libraries only (no third-party dependencies)

---

**Documentation Index**:
- [Complete Codebase Documentation](docs/CODEBASE.md) - 1,463 lines of detailed explanations
- [API Reference](docs/API.md) - REST API endpoints and examples
- [Integration Guide](docs/INTEGRATION.md) - API-to-Agent communication
- [Repository Guidelines](AGENTS.md) - Development practices
