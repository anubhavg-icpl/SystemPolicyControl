import plistlib
import subprocess
import tempfile
import unittest
from pathlib import Path

from common.state import PolicyStateStore

AGENT_BIN = Path("bin/system-policy-agent")


class SystemPolicyAgentCLITests(unittest.TestCase):
    def setUp(self) -> None:
        if not AGENT_BIN.exists():
            self.skipTest("Swift agent binary missing; run `make build-agent`")
        self.temp_dir = tempfile.TemporaryDirectory()
        base = Path(self.temp_dir.name)
        self.state_path = base / "state.json"
        self.profile_dir = base / "profiles"
        self.store = PolicyStateStore(self.state_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _run_cli(self, extra_args: list[str] | None = None) -> None:
        args = [
            str(AGENT_BIN),
            "apply",
            "--profile-dir",
            str(self.profile_dir),
            "--state-path",
            str(self.state_path),
            "--profile-identifier",
            "com.example.policy",
            "--display-name",
            "Test Policy",
            "--organization",
            "UnitTests",
            "--allow-identified-developers",
            "true",
            "--enable-assessment",
            "true",
            "--enable-xprotect-malware-upload",
            "true",
            "--no-install",
        ]
        if extra_args:
            args.extend(extra_args)
        subprocess.run(args, check=True)

    def test_profile_includes_allow_flag_when_gatekeeper_enabled(self) -> None:
        self._run_cli()
        state = self.store.load()
        self.assertIsNotNone(state)
        assert state is not None
        with open(state.profile_path, "rb") as handle:
            profile = plistlib.load(handle)
        payload = profile["PayloadContent"][0]
        self.assertTrue(payload["EnableAssessment"])
        self.assertTrue(payload["AllowIdentifiedDevelopers"])

    def test_profile_omits_allow_flag_when_gatekeeper_disabled(self) -> None:
        self._run_cli(["--enable-assessment", "false"])
        state = self.store.load()
        assert state is not None
        with open(state.profile_path, "rb") as handle:
            profile = plistlib.load(handle)
        payload = profile["PayloadContent"][0]
        self.assertFalse(payload["EnableAssessment"])
        self.assertNotIn("AllowIdentifiedDevelopers", payload)

    def test_state_file_records_metadata(self) -> None:
        self._run_cli(["--description", "Unit test"])
        state = self.store.load()
        assert state is not None
        self.assertEqual(state.policy.description, "Unit test")
        self.assertFalse(state.install_attempted)
        self.assertTrue(Path(state.profile_path).exists())

    def test_list_profiles_returns_empty_when_no_profiles(self) -> None:
        result = subprocess.run([str(AGENT_BIN), "list"], capture_output=True, text=True, check=True)
        self.assertIn("[]", result.stdout.strip())

    def test_remove_policy_deletes_state_file(self) -> None:
        self._run_cli()
        state = self.store.load()
        assert state is not None
        self.assertTrue(state.policy.profile_identifier == "com.example.policy")

        remove_args = [
            str(AGENT_BIN),
            "remove",
            "com.example.policy",
            "--profile-dir",
            str(self.profile_dir),
            "--state-path",
            str(self.state_path),
        ]
        subprocess.run(remove_args, capture_output=True, text=True)

        state_after = self.store.load()
        self.assertIsNone(state_after)


if __name__ == "__main__":
    unittest.main()
