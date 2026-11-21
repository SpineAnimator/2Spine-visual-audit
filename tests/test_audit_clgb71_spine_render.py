import importlib.util
from pathlib import Path
import tempfile
import unittest

from PIL import Image

SPEC = importlib.util.spec_from_file_location(
    "render_guard",
    Path(__file__).resolve().parents[1] / "scripts/audit_clgb71_spine_render.py"
)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)

class GuardTests(unittest.TestCase):
    def create(self, root, clip, labels):
        folder = root / clip
        folder.mkdir(parents=True)
        for i, cyan_square in enumerate(labels):
            img = Image.new("RGBA", (120, 120), (13, 12, 20, 0))
            if cyan_square:
                from PIL import ImageDraw
                ImageDraw.Draw(img).rectangle((0, 0, cyan_square - 1, cyan_square - 1),
                                               fill=module.TARGET_RGBA)
            img.save(folder / f"frame_{i:02}.png")

    def test_flat_cyan_growth_flags_review_not_approval(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for clip in module.CLIPS:
                self.create(root, clip, [2, 80, 80])
            outcome = module.review_frames(root, minimum_pixels=2000)
            self.assertEqual(outcome["status"], "REVIEW_REQUIRED")
            self.assertEqual(len(outcome["findings"]), 2)
            self.assertFalse(outcome["artistic_quality_approved"])
            self.assertFalse(outcome["release_ready"])

    def test_moderate_opaque_cyan_growth_is_detected_before_art_publication(self):
        # A previous 10k-pixel cutoff silently accepted a visibly hard-edged
        # cyan plate in real 2026-11-10 Editor captures (5,705 / 6,636 pixels).
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for clip in module.CLIPS:
                self.create(root, clip, [20, 75, 75])  # 400 -> 5,625 (14x)
            outcome = module.review_frames(root)
            self.assertEqual(outcome["status"], "REVIEW_REQUIRED")
            self.assertTrue(all(c["flat_color_anomaly"] for c in outcome["clips"]))
            self.assertFalse(outcome["release_ready"])

    def test_corrected_native_glow_cyan_density_stays_below_regression_gate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for clip in module.CLIPS:
                self.create(root, clip, [24, 40, 40])  # 576 -> 1,600 < 3,000
            outcome = module.review_frames(root)
            self.assertEqual(outcome["status"], "NO_DETECTED_FLAT_CYAN_ANOMALY")
            self.assertFalse(outcome["artistic_quality_approved"])

    def test_clean_frames_are_not_mislabeled_as_art_approved(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for clip in module.CLIPS:
                self.create(root, clip, [2, 3, 2])
            outcome = module.review_frames(root, minimum_pixels=2000)
            self.assertEqual(outcome["status"], "NO_DETECTED_FLAT_CYAN_ANOMALY")
            self.assertFalse(outcome["artistic_quality_approved"])
            self.assertFalse(outcome["release_ready"])

    def test_native_editor_publication_is_blocked_by_this_guard(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/verify-clgb71-editor-linux.yml").read_text()
        before_zip = workflow.index("Reject opaque cyan eruption in actual Editor frames")
        package = workflow.index("Package an independently licensed-Editor-verified native ZIP")
        self.assertLess(before_zip, package)
        self.assertIn("python3 scripts/audit_clgb71_spine_render.py", workflow)
        self.assertIn("--frames-dir work/editor/screenshots", workflow)
        self.assertIn("assert cyan_data['status'] == 'NO_DETECTED_FLAT_CYAN_ANOMALY'", workflow)
        self.assertIn("assert all(c['frames_checked'] >= 49 for c in cyan_data['clips'])", workflow)
        self.assertIn("z.write(cyan,'validation/render-anomaly-report.json')", workflow)
        self.assertIn("work/editor/render-anomaly-report.json", workflow)


    def test_25_real_frame_near_duplicate_is_not_art_approved(self):
        # Full-length picture motion identical across both clips is a hard
        # artistic review blocker even when neither has a cyan-plate eruption.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for clip in module.CLIPS:
                self.create(root, clip, [2 + i % 14 for i in range(26)])
            outcome = module.review_frames(root)
            self.assertEqual(outcome["status"], "REVIEW_REQUIRED")
            self.assertTrue(outcome["near_duplicate_render_sequences"])
            self.assertGreaterEqual(outcome["real_editor_motion_envelope_pearson_r"], .985)
            self.assertFalse(outcome["artistic_quality_approved"])
            self.assertFalse(outcome["release_ready"])

    def test_distinct_full_length_motion_does_not_grant_artistic_approval(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.create(root, module.CLIPS[0],
                        [2 + i for i in range(14)] + [14 - i for i in range(12)])
            self.create(root, module.CLIPS[1], [2 + i for i in range(26)])
            outcome = module.review_frames(root)
            self.assertTrue(outcome["near_duplicate_evaluated_on_full_editor_frames"])
            self.assertFalse(outcome["near_duplicate_render_sequences"])
            self.assertEqual(outcome["status"], "NO_DETECTED_FLAT_CYAN_ANOMALY")
            self.assertFalse(outcome["artistic_quality_approved"])

    def test_missing_clip_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.create(root, module.CLIPS[0], [2, 3, 2])
            with self.assertRaisesRegex(ValueError, "required real Spine Editor"):
                module.review_frames(root)

if __name__ == "__main__":
    unittest.main()
