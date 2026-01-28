"""Integration tests for API to Agent communication."""
import json
import os
import plistlib
import subprocess
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from api.main import application


class APIAgentIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        base = Path(self.temp_dir.name)
        self.state_path = base / "state.json"
        self.profile_dir = base / "profiles"

        # Set environment variables for API
        os.environ["SPC_STATE_PATH"] = str(self.state_path)
        os.environ["SPC_PROFILE_DIR"] = str(self.profile_dir)
        os.environ["SPC_AGENT_PATH"] = "bin/system-policy-agent"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        # Clean up environment variables
        os.environ.pop("SPC_STATE_PATH", None)
        os.environ.pop("SPC_PROFILE_DIR", None)

    def _call_api(self, method: str, path: str, body: dict | None = None) -> tuple[str, dict]:
        environ = {
            "PATH_INFO": path,
            "REQUEST_METHOD": method,
            "CONTENT_LENGTH": str(len(json.dumps(body or {}))) if body else "0",
            "CONTENT_TYPE": "application/json" if body else "",
            "SPC_STATE_PATH": str(self.state_path),
            "SPC_PROFILE_DIR": str(self.profile_dir),
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

    def test_api_creates_policy_via_agent(self) -> None:
        """Test that POST /policy calls agent and creates profile."""
        policy_data = {
            "profile_identifier": "com.test.integration",
            "display_name": "Integration Test",
            "organization": "TestOrg",
            "allow_identified_developers": True,
            "enable_assessment": True,
            "enable_xprotect_malware_upload": False,
            "install": False,
        }

        status, body = self._call_api("POST", "/policy", policy_data)

        self.assertEqual(status, "201 Created")
        self.assertIn("policy", body)
        self.assertEqual(body["policy"]["display_name"], "Integration Test")
        self.assertIn("profile_path", body)

        # Verify profile file was created by agent
        profile_path = Path(body["profile_path"])
        self.assertTrue(profile_path.exists())

        # Verify profile is valid plist
        with open(profile_path, "rb") as f:
            profile = plistlib.load(f)
            self.assertEqual(profile["PayloadDisplayName"], "Integration Test")
            self.assertEqual(
                profile["PayloadContent"][0]["PayloadType"], "com.apple.systempolicy.control"
            )

    def test_api_reads_policy_from_state_file(self) -> None:
        """Test that GET /policy reads from state file created by agent."""
        # Create policy first
        policy_data = {
            "profile_identifier": "com.test.read",
            "display_name": "Read Test",
            "organization": "TestOrg",
            "install": False,
        }
        self._call_api("POST", "/policy", policy_data)

        # Read it back
        status, body = self._call_api("GET", "/policy")

        self.assertEqual(status, "200 OK")
        self.assertIn("policy", body)
        self.assertEqual(body["policy"]["display_name"], "Read Test")

    def test_api_updates_policy_via_agent(self) -> None:
        """Test that PUT /policy calls agent to update profile."""
        # Create policy
        policy_data = {
            "profile_identifier": "com.test.update",
            "display_name": "Update Test",
            "organization": "TestOrg",
            "allow_identified_developers": True,
            "install": False,
        }
        self._call_api("POST", "/policy", policy_data)

        # Update it
        updated_data = {
            "profile_identifier": "com.test.update",
            "allow_identified_developers": False,
            "enable_assessment": False,
            "install": False,
        }
        status, body = self._call_api("PUT", "/policy", updated_data)

        self.assertEqual(status, "200 OK")
        self.assertFalse(body["policy"]["allow_identified_developers"])
        self.assertFalse(body["policy"]["enable_assessment"])

    def test_api_deletes_policy_via_agent(self) -> None:
        """Test that DELETE /policy calls agent to remove profile."""
        # Create policy
        policy_data = {
            "profile_identifier": "com.test.delete",
            "display_name": "Delete Test",
            "install": False,
        }
        self._call_api("POST", "/policy", policy_data)

        # Delete it
        status, body = self._call_api("DELETE", "/policy")

        self.assertEqual(status, "200 OK")
        self.assertIn("message", body)

        # Verify it's gone
        status, body = self._call_api("GET", "/policy")
        self.assertEqual(status, "404 Not Found")

    def test_api_lists_policies_via_agent(self) -> None:
        """Test that GET /policies calls agent list command."""
        status, body = self._call_api("GET", "/policies")

        self.assertEqual(status, "200 OK")
        self.assertIn("policies", body)
        self.assertIsInstance(body["policies"], list)


if __name__ == "__main__":
    unittest.main()
