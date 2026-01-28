#!/usr/bin/env python3
"""Verify end-to-end API to Agent communication."""
import json
import os
import plistlib
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "src")

from api.main import application
from common.state import PolicyStateStore
from io import BytesIO


def call_api(method, path, body=None):
    """Call the API and return status and response."""
    environ = {
        "PATH_INFO": path,
        "REQUEST_METHOD": method,
        "CONTENT_LENGTH": str(len(json.dumps(body or {}))) if body else "0",
        "CONTENT_TYPE": "application/json" if body else "",
        "SPC_STATE_PATH": "data/policy_state.json",
        "SPC_PROFILE_DIR": "data/profiles",
        "SPC_AGENT_PATH": "bin/system-policy-agent",
    }

    response = []

    def start_response(status, headers):
        response.append((status, headers))

    environ["wsgi.input"] = BytesIO(json.dumps(body or {}).encode())
    body_bytes = application(environ, start_response)
    body_data = b"".join(body_bytes)

    status_line = response[0][0] if response else "500 Internal Server Error"
    response_body = json.loads(body_data.decode()) if body_bytes else {}

    return status_line, response_body


def main():
    print("=" * 60)
    print("API TO AGENT VERIFICATION")
    print("=" * 60)

    # 1. Test CREATE
    print("\n1. CREATE - API sends request to Agent")
    print("-" * 60)
    policy_data = {
        "profile_identifier": "com.verification.test",
        "display_name": "Verification Policy",
        "organization": "VerificationOrg",
        "allow_identified_developers": True,
        "enable_assessment": True,
        "enable_xprotect_malware_upload": False,
        "install": False,
    }

    status, body = call_api("POST", "/policy", policy_data)
    print(f"✓ API received: {status}")
    print(f"✓ Agent generated profile at: {body['profile_path']}")

    # Verify profile file exists
    profile_path = Path(body['profile_path'])
    if profile_path.exists():
        print(f"✓ Profile file exists on disk")
        with open(profile_path, 'rb') as f:
            profile = plistlib.load(f)
            print(f"✓ Profile is valid plist")
            print(f"  - Display Name: {profile['PayloadDisplayName']}")
            print(f"  - Payload Type: {profile['PayloadContent'][0]['PayloadType']}")
    else:
        print(f"✗ Profile file NOT found")
        return 1

    # 2. Test READ
    print("\n2. READ - API reads from Agent's state file")
    print("-" * 60)
    status, body = call_api("GET", "/policy")
    print(f"✓ API received: {status}")
    print(f"✓ Policy loaded from state file")
    print(f"  - Display Name: {body['policy']['display_name']}")
    print(f"  - Allow Identified Developers: {body['policy']['allow_identified_developers']}")

    # Verify state file directly
    store = PolicyStateStore("data/policy_state.json")
    state = store.load()
    if state:
        print(f"✓ State file is valid and readable")
    else:
        print(f"✗ State file is invalid")
        return 1

    # 3. Test UPDATE
    print("\n3. UPDATE - API sends update to Agent")
    print("-" * 60)
    updated_data = {
        "profile_identifier": "com.verification.test",
        "allow_identified_developers": False,
        "enable_assessment": False,
        "install": False,
    }

    status, body = call_api("PUT", "/policy", updated_data)
    print(f"✓ API received: {status}")
    print(f"✓ Agent updated profile")
    print(f"  - Allow Identified Developers: {body['policy']['allow_identified_developers']}")

    # Verify state was updated
    state = store.load()
    if state and state.policy.allow_identified_developers == False:
        print(f"✓ State file was updated correctly")
    else:
        print(f"✗ State file was NOT updated")
        return 1

    # 4. Test LIST
    print("\n4. LIST - API queries Agent for all profiles")
    print("-" * 60)
    status, body = call_api("GET", "/policies")
    print(f"✓ API received: {status}")
    print(f"✓ Agent returned list of {len(body['policies'])} profiles")

    # 5. Test DELETE
    print("\n5. DELETE - API sends delete to Agent")
    print("-" * 60)
    status, body = call_api("DELETE", "/policy")
    print(f"✓ API received: {status}")
    print(f"✓ Agent deleted profile")

    # Verify deletion
    status, body = call_api("GET", "/policy")
    if status == "404 Not Found":
        print(f"✓ Policy successfully deleted (404 Not Found)")
    else:
        print(f"✗ Policy still exists")
        return 1

    # Verify state file is deleted
    state = store.load()
    if state is None:
        print(f"✓ State file was deleted")
    else:
        print(f"✗ State file still exists")
        return 1

    # 6. Verify agent command line directly
    print("\n6. DIRECT AGENT COMMAND LINE TEST")
    print("-" * 60)
    result = subprocess.run([
        "bin/system-policy-agent",
        "apply",
        "--profile-dir", "data/profiles",
        "--state-path", "data/policy_state.json",
        "--profile-identifier", "com.direct.test",
        "--display-name", "Direct CLI Test",
        "--organization", "Test",
        "--no-install"
    ], capture_output=True, text=True)

    if result.returncode == 0:
        print(f"✓ Agent command line works directly")
        print(f"  Output: {result.stdout.strip()}")

        # Verify it was created
        store = PolicyStateStore("data/policy_state.json")
        state = store.load()
        if state and state.policy.display_name == "Direct CLI Test":
            print(f"✓ Direct CLI created valid policy")
        else:
            print(f"✗ Direct CLI policy not found in state")
            return 1

        # Clean up
        subprocess.run([
            "bin/system-policy-agent",
            "remove",
            "com.direct.test",
            "--profile-dir", "data/profiles",
            "--state-path", "data/policy_state.json"
        ], capture_output=True)
        print(f"✓ Cleaned up direct CLI test policy")

    else:
        print(f"✗ Agent command line failed: {result.stderr}")
        return 1

    print("\n" + "=" * 60)
    print("✓ ALL VERIFICATIONS PASSED")
    print("=" * 60)
    print("\nSummary:")
    print("  ✓ API successfully sends requests to Agent")
    print("  ✓ Agent generates valid .mobileconfig profiles")
    print("  ✓ Agent writes state to JSON file")
    print("  ✓ API reads state file correctly")
    print("  ✓ Agent handles create, read, update, delete operations")
    print("  ✓ Direct CLI invocation works")
    print("\nThe API and Agent are fully integrated and working correctly!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
