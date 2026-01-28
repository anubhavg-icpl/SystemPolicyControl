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


if __name__ == "__main__":
    unittest.main()
