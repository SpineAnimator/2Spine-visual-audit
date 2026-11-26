from pathlib import Path
import unittest

WORKFLOW = Path(".github/workflows/3spine-public-executor.yml")


class PublicExecutorContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = WORKFLOW.read_text(encoding="utf-8")

    def test_executor_uses_only_github_hosted_ubuntu(self):
        self.assertIn("runs-on: ubuntu-24.04", self.source)
        self.assertNotRegex(self.source, r"(?m)^\s*runs-on:.*self-hosted")

    def test_schedule_polls_queue_at_five_minute_interval(self):
        self.assertIn("cron: '*/5 * * * *'", self.source)

    def test_private_checkout_uses_scoped_token_without_persisting_credentials(self):
        self.assertIn("token: ${{ secrets.SOURCE_REPO_TOKEN }}", self.source)
        self.assertIn("persist-credentials: false", self.source)
        self.assertIn("repository: vladleopold/3Spine-core", self.source)

    def test_private_github_api_uses_private_source_token(self):
        self.assertIn("GH_TOKEN: ${{ secrets.SOURCE_REPO_TOKEN }}", self.source)
        self.assertNotIn("GH_TOKEN: ${{ github.token }}", self.source)

    def test_editor_is_started_only_when_queue_contains_a_job(self):
        probe = self.source.index("python scripts/spine_mask_v2_ci.py --probe")
        require = self.source.index("Require licensed Spine Editor credentials")
        install = self.source.index("Install Spine 4.3.26")
        self.assertLess(probe, require)
        self.assertLess(require, install)
        self.assertIn("if: steps.next.outputs.found == 'true'", self.source)

    def test_license_values_are_not_printed(self):
        self.assertNotRegex(self.source, r"(?im)^\s*(echo|printf).*\$SPINE_(LICENSE|LINUX_URL)")
        self.assertNotIn("SPINE_LICENSE=", self.source.replace("SPINE_LICENSE: ${{ secrets.SPINE_LICENSE }}", ""))


if __name__ == "__main__":
    unittest.main()
