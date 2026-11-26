from pathlib import Path
import unittest

WORKFLOW = Path(".github/workflows/3spine-public-executor.yml")


class PublicExecutorContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = WORKFLOW.read_text(encoding="utf-8")

    def test_jobs_run_only_on_github_hosted_ubuntu(self):
        self.assertIn("runs-on: ubuntu-24.04", self.source)
        self.assertNotRegex(self.source, r"(?m)^\s*runs-on:.*self-hosted")
        self.assertNotIn("workflow_call:", self.source)

    def test_public_runner_polls_every_five_minutes(self):
        self.assertIn("cron: '*/5 * * * *'", self.source)

    def test_private_source_checkout_is_scoped_and_non_persistent(self):
        self.assertIn("repository: vladleopold/3Spine-core", self.source)
        self.assertIn("token: ${{ secrets.SOURCE_REPO_TOKEN }}", self.source)
        self.assertIn("persist-credentials: false", self.source)

    def test_private_gateway_api_uses_private_source_token(self):
        self.assertIn("GH_TOKEN: ${{ secrets.SOURCE_REPO_TOKEN }}", self.source)
        self.assertNotIn("GH_TOKEN: ${{ github.token }}", self.source)

    def test_editor_is_only_installed_for_a_real_queued_job(self):
        probe = self.source.index("python scripts/spine_mask_v2_ci.py --probe")
        require = self.source.index("Require licensed Editor credentials when a queued project needs processing")
        install = self.source.index("Install Spine 4.3.26")
        self.assertLess(probe, require)
        self.assertLess(require, install)
        self.assertIn("if: steps.next.outputs.found == 'true'", self.source)

    def test_synthetic_roundtrip_is_manual_only(self):
        self.assertIn("if: github.event_name == 'workflow_dispatch' && inputs.task == 'mask-native'", self.source)
        self.assertIn("python scripts/spine_mask_v2_ci.py --selftest", self.source)
        self.assertIn("if: steps.next.outputs.found == 'true' && github.event_name == 'workflow_dispatch' && inputs.task == 'mask-native'", self.source)

    def test_license_values_are_never_printed(self):
        self.assertNotRegex(self.source, r"(?im)^\s*(echo|printf).*\$SPINE_(LICENSE|LINUX_URL)")
        self.assertNotIn("SPINE_LICENSE=", self.source.replace("SPINE_LICENSE: ${{ secrets.SPINE_LICENSE }}", ""))


if __name__ == "__main__":
    unittest.main()
