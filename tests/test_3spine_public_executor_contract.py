from pathlib import Path
import re
import unittest

WORKFLOW = Path(".github/workflows/3spine-public-executor.yml")

class PublicExecutorContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = WORKFLOW.read_text(encoding="utf-8")

    def test_jobs_are_hosted_in_the_public_repository(self):
        self.assertIn("runs-on: ubuntu-24.04", self.source)
        self.assertNotRegex(self.source, r"(?m)^\s*runs-on:.*self-hosted")
        self.assertNotIn("workflow_call:", self.source)

    def test_public_runner_polls_every_five_minutes(self):
        self.assertIn("cron: '*/5 * * * *'", self.source)

    def test_all_reusable_jobs_are_pinned_to_a_real_public_runner_commit(self):
        refs = re.findall(r"uses: SpineAnimator/sa-public-runner/[^\s]+@([0-9a-f]{40})", self.source)
        self.assertEqual(len(refs), 8)
        self.assertTrue(all(re.fullmatch(r"[0-9a-f]{40}", ref) for ref in refs))
        self.assertNotIn("@undefined", self.source)

    def test_private_source_and_gateway_use_the_scoped_token(self):
        self.assertIn("token: ${{ secrets.SOURCE_REPO_TOKEN }}", self.source)
        self.assertIn("GH_TOKEN: ${{ secrets.SOURCE_REPO_TOKEN }}", self.source)
        self.assertNotIn("GH_TOKEN: ${{ github.token }}", self.source)
        self.assertIn("persist-credentials: false", self.source)

    def test_clgb71_reusable_job_has_read_only_actions_permission(self):
        self.assertIn("permissions:\n  contents: read\n  actions: read", self.source)

    def test_native_editor_is_started_only_for_queued_work(self):
        probe = self.source.index("python scripts/spine_mask_v2_ci.py --probe")
        install = self.source.index("Install Spine 4.3.26")
        self.assertLess(probe, install)
        self.assertIn("id: editor", self.source)
        self.assertIn("echo \\\"ready=false\\\" >> \\\"$GITHUB_OUTPUT\\\"", self.source)
        self.assertIn("if: steps.editor.outputs.ready == 'true'", self.source)

    def test_synthetic_roundtrip_is_manual_and_only_runs_when_queue_is_empty(self):
        self.assertIn("if: steps.next.outputs.found != 'true' && github.event_name == 'workflow_dispatch' && inputs.task == 'mask-native'", self.source)
        self.assertIn("python scripts/spine_mask_v2_ci.py --selftest", self.source)
        self.assertIn("if: steps.selftest_next.outputs.found == 'true' && steps.editor.outputs.ready == 'true' && github.event_name == 'workflow_dispatch' && inputs.task == 'mask-native'", self.source)
        self.assertIn("python scripts/spine_mask_v2_ci.py --read-selftest", self.source)

    def test_license_values_are_never_printed(self):
        self.assertNotRegex(self.source, r"(?im)^\s*(echo|printf).*\$SPINE_(LICENSE|LINUX_URL)")


if __name__ == "__main__":
    unittest.main()
