from pathlib import Path
import re
import unittest

WORKFLOW = Path(".github/workflows/3spine-public-executor.yml")
PUBLIC_WORKFLOWS = {
    ".github/workflows/3spine-spine-link-full-cloud-public.yml": (
        ".github/workflows/3spine-spine-link-full-cloud-e2e.yml",
        "66b36481fc5cabdde98d786631903f20ea3900bd",
    ),
    ".github/workflows/3spine-computer-health-public.yml": (
        ".github/workflows/3spine-spine-link-computer-worker-health.yml",
        "fd9a27f90e7137d2b83490ed3b90a35c15c3ae03",
    ),
    ".github/workflows/3spine-legacy21-import-public.yml": (
        ".github/workflows/3spine-spine-link-legacy21-import.yml",
        "0b405ef63c3a39546050c7a06d6274165bb256f1",
    ),
    ".github/workflows/3spine-native-export-public.yml": (
        ".github/workflows/3spine-spine-link-native-export-smoke.yml",
        "b0c9bec0ebb59c5800c57cb9acdadf52bef3a5cd",
    ),
    ".github/workflows/3spine-convert-target-public.yml": (
        ".github/workflows/3spine-spine-link-convert-target-legacy.yml",
        "607f72feaec99689fb63988fad6e9c2f1f9e5971",
    ),
    ".github/workflows/3spine-latest20-public.yml": (
        ".github/workflows/3spine-spine-link-latest20-legacy-convert.yml",
        "1b3037c8ea93e507829f67583fc0ea29f7e70300",
    ),
    ".github/workflows/3spine-clgb71-audit-public.yml": (
        ".github/workflows/3spine-clgb71-render-artistic-audit.yml",
        "3ce6aad1f1ba81f04d4056bb0a4439818b4ebfec",
    ),
    ".github/workflows/3spine-converter-public.yml": (
        ".github/workflows/3spine-converter-test.yml",
        "c330365e58a3b8393e40de295505f66088a7a002",
    ),
}


class PublicExecutorContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = WORKFLOW.read_text(encoding="utf-8")

    def test_jobs_are_hosted_in_the_public_repository(self):
        self.assertIn("runs-on: ubuntu-24.04", self.source)
        self.assertNotRegex(self.source, r"(?m)^\s*runs-on:.*self-hosted")
        self.assertNotIn("workflow_call:", self.source)

    def test_private_source_has_no_self_hosted_runner_assignments(self):
        self.assertIn("THREESPINE_PRIVATE_SELF_HOSTED_RUNNERS_REMOVED_PASS", self.source)
        self.assertIn("runs-on:[[:space:]]*.*self-hosted", self.source)

    def test_public_runner_polls_every_five_minutes(self):
        self.assertIn("cron: '*/5 * * * *'", self.source)

    def test_all_reusable_jobs_are_pinned_to_public_runner_commits(self):
        for caller_path, (runner_path, expected_sha) in PUBLIC_WORKFLOWS.items():
            with self.subTest(caller=caller_path):
                caller = Path(caller_path).read_text(encoding="utf-8")
                match = re.search(
                    r"uses: SpineAnimator/sa-public-runner/[^\s]+@([0-9a-f]{40})",
                    caller,
                )
                self.assertIsNotNone(match, caller_path)
                self.assertEqual(match.group(1), expected_sha)
                self.assertIn("secrets: inherit", caller)
                reusable = Path("sa-public-runner", runner_path).read_text(encoding="utf-8")
                self.assertIn("workflow_call:", reusable)
                self.assertIn("runs-on: ubuntu-24.04", reusable)
                self.assertNotRegex(reusable, r"(?m)^\s*runs-on:.*self-hosted")

    def test_private_source_and_gateway_use_the_scoped_token(self):
        self.assertIn("token: ${{ secrets.SOURCE_REPO_TOKEN }}", self.source)
        self.assertIn("GH_TOKEN: ${{ secrets.SOURCE_REPO_TOKEN }}", self.source)
        self.assertNotIn("GH_TOKEN: ${{ github.token }}", self.source)
        self.assertIn("persist-credentials: false", self.source)

    def test_clgb71_public_executor_has_read_only_actions_permission(self):
        self.assertIn("permissions:\n  contents: read\n  actions: read", self.source)

    def test_native_editor_requires_secrets_and_processes_only_queued_work(self):
        probe = self.source.index("python scripts/spine_mask_v2_ci.py --probe")
        install = self.source.index("Install Spine 4.3.26")
        self.assertLess(probe, install)
        self.assertIn("id: editor", self.source)
        self.assertIn('echo "ready=false" >> "$GITHUB_OUTPUT"', self.source)
        self.assertIn("SPINE_MASK_NATIVE_WAITING_FOR_EDITOR_SECRETS", self.source)
        self.assertIn("Run standalone Spine Mask native import and save/reopen/export fixture", self.source)
        self.assertIn("if: (steps.next.outputs.found == 'true' || steps.selftest_next.outputs.found == 'true') && steps.editor.outputs.ready == 'true'", self.source)

    def test_native_geometry_regression_runs_on_public_ubuntu(self):
        self.assertIn("repository: SpineAnimator/spine-web-source", self.source)
        self.assertIn("path: 3spine/mask-public", self.source)
        self.assertIn("node --test tests/spine-mask-native.mjs", self.source)

    def test_synthetic_roundtrip_is_manual_and_only_runs_when_queue_is_empty(self):
        self.assertIn(
            "if: steps.next.outputs.found != 'true' && github.event_name == 'workflow_dispatch' && inputs.task == 'mask-native' && env.SPINE_LICENSE != '' && env.SPINE_LINUX_URL != ''",
            self.source,
        )
        self.assertIn("python scripts/spine_mask_v2_ci.py --selftest", self.source)
        self.assertIn(
            "if: steps.selftest_next.outputs.found == 'true' && steps.editor.outputs.ready == 'true' && github.event_name == 'workflow_dispatch' && inputs.task == 'mask-native'",
            self.source,
        )
        self.assertIn("python scripts/spine_mask_v2_ci.py --read-selftest", self.source)

    def test_license_values_are_never_printed(self):
        self.assertNotRegex(self.source, r"(?im)^\s*(echo|printf).*\$SPINE_(LICENSE|LINUX_URL)")


    def test_every_task_is_delegated_to_a_public_ubuntu_workflow(self):
        expected = [
            "SpineAnimator/sa-public-runner/.github/workflows/3spine-spine-link-full-cloud-e2e.yml@94465cbfb8f6b6e79135dc31db17711ff138c154",
            "SpineAnimator/sa-public-runner/.github/workflows/3spine-spine-link-computer-worker-health.yml@94465cbfb8f6b6e79135dc31db17711ff138c154",
            "SpineAnimator/sa-public-runner/.github/workflows/3spine-spine-link-legacy21-import.yml@94465cbfb8f6b6e79135dc31db17711ff138c154",
            "SpineAnimator/sa-public-runner/.github/workflows/3spine-spine-link-native-export-smoke.yml@94465cbfb8f6b6e79135dc31db17711ff138c154",
            "SpineAnimator/sa-public-runner/.github/workflows/3spine-spine-link-convert-target-legacy.yml@94465cbfb8f6b6e79135dc31db17711ff138c154",
            "SpineAnimator/sa-public-runner/.github/workflows/3spine-spine-link-latest20-legacy-convert.yml@94465cbfb8f6b6e79135dc31db17711ff138c154",
            "SpineAnimator/sa-public-runner/.github/workflows/3spine-clgb71-render-artistic-audit.yml@94465cbfb8f6b6e79135dc31db17711ff138c154",
            "SpineAnimator/sa-public-runner/.github/workflows/3spine-converter-test.yml@94465cbfb8f6b6e79135dc31db17711ff138c154",
            "SpineAnimator/sa-psd-tool-runner/.github/workflows/psd-validation.yml@14ab734df00e2efaa95e0463645bcfb48891c20f",
            "SpineAnimator/Spine-Link-project-export/.github/workflows/runner.yml@5f90a85ed706398cf99245f22271ba548f762e41",
        ]
        for reusable in expected:
            with self.subTest(reusable=reusable):
                self.assertIn("uses: " + reusable, self.source)
        self.assertGreaterEqual(self.source.count("secrets: inherit"), len(expected))
        self.assertIn("3spine-psd-validation", self.source)
        self.assertIn("3spine-spine-link-project-export", self.source)


if __name__ == "__main__":
    unittest.main()
