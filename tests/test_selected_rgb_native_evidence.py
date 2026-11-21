#!/usr/bin/env python3
"""Negative provenance tests: never mistake the first RGB feedback for selected second pass."""
import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from verify_selected_rgb_native_evidence import PSD_SHA256, verify_selected_evidence


def create_evidence(root: Path):
    native_candidate_sha = "a" * 64
    (root / "selected-rgb" / "screenshots").mkdir(parents=True)
    (root / "rgb-feedback").mkdir()
    verdict = {
        "selected_candidate": "feedback_2",
        "photoshop_reference_sha256": PSD_SHA256,
        "selected_exact_rgba_parity": False,
        "artistic_quality_approved": False,
        "release_ready": False,
    }
    selection = {
        "selected_candidate": "feedback_2",
        "source_psd_sha256": PSD_SHA256,
        "selected_candidate_zip_sha256": native_candidate_sha,
        "selected_native_zip_sha256": "b" * 64,
    }
    names = []
    for clip in ("shoot_up_01", "shoot_up_02"):
        folder = root / "selected-rgb" / "screenshots" / clip
        folder.mkdir(parents=True)
        for i in range(49):
            name = f"screenshots/{clip}/image_{i:02d}.png"
            names.append(name)
            (root / "selected-rgb" / name).write_bytes(b"placeholder, read by separate image gate")
    report = {
        "source_archive_sha256": native_candidate_sha,
        "editor_import_verified": True,
        "native_spine_project_verified": True,
        "roundtrip_spine_version": "4.3.26",
        "slots": 38,
        "slot_order_unchanged": True,
        "ik_constraints": 2,
        "animations": ["shoot_up_01", "shoot_up_02"],
        "spine_render_nonblank_frames_verified": True,
        "artistic_quality_approved": False,
        "official_rendered_frames": names,
    }
    documents = {
        "rgb-feedback/final-verdict.json": verdict,
        "selected-rgb/selection.json": selection,
        "selected-rgb/editor-roundtrip-report.json": report,
        "selected-rgb/psd-editor-parity.json": {"absolute_pixel_parity_proven": False},
    }
    for path, value in documents.items():
        (root / path).write_text(json.dumps(value), encoding="utf-8")
    (root / "editor").mkdir()
    package = root / "editor/clgb71-selected-licensed-rgb-candidate.zip"
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
        for i in range(38):
            archive.writestr(f"images/layer_{i:02d}.png", b"source layer marker")
        archive.writestr("clgb71-editor-4.3.26.spine", b"licensed project marker")
        archive.writestr("validation/licensed-selected-editor-report.json", json.dumps(report))
        archive.writestr("validation/licensed-selected-rgb-parity.json",
                         json.dumps({"absolute_pixel_parity_proven": False}))
    selection["selected_native_zip_sha256"] = hashlib.sha256(package.read_bytes()).hexdigest()
    (root / "selected-rgb/selection.json").write_text(json.dumps(selection), encoding="utf-8")


class TestSelectedNativeEvidence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        create_evidence(self.root)

    def mutate(self, path, key, value):
        file = self.root / path
        data = json.loads(file.read_text(encoding="utf-8"))
        data[key] = value
        file.write_text(json.dumps(data), encoding="utf-8")

    def test_valid_native_selection_is_technical_only(self):
        result = verify_selected_evidence(self.root)
        self.assertEqual(result["selected_native_frames"], 98)
        self.assertFalse(result["artistic_quality_approved"])
        self.assertFalse(result["release_ready"])

    def test_selected_second_pass_must_match_verdict(self):
        self.mutate("selected-rgb/selection.json", "selected_candidate", "feedback")
        with self.assertRaisesRegex(ValueError, "Selected RGB candidate"):
            verify_selected_evidence(self.root)

    def test_verified_third_feedback_is_accepted_without_art_approval(self):
        self.mutate("selected-rgb/selection.json", "selected_candidate", "feedback_3")
        self.mutate("rgb-feedback/final-verdict.json", "selected_candidate", "feedback_3")
        self.mutate("rgb-feedback/final-verdict.json", "feedback_round_three_pass", True)
        self.mutate("rgb-feedback/final-verdict.json",
                    "feedback_round_three_pixel_nonregression", True)
        self.mutate("rgb-feedback/final-verdict.json",
                    "feedback_round_three_exact_rgba_parity", False)
        receipt = verify_selected_evidence(self.root)
        self.assertEqual(receipt["selected_candidate"], "feedback_3")
        self.assertEqual(receipt["selected_native_frames"], 98)
        self.assertFalse(receipt["artistic_quality_approved"])

    def test_unverified_third_feedback_must_be_rejected(self):
        self.mutate("selected-rgb/selection.json", "selected_candidate", "feedback_3")
        self.mutate("rgb-feedback/final-verdict.json", "selected_candidate", "feedback_3")
        with self.assertRaisesRegex(ValueError, "Unverified third RGB feedback"):
            verify_selected_evidence(self.root)

    def test_fourth_feedback_cannot_be_claimed_without_schema_support(self):
        self.mutate("selected-rgb/selection.json", "selected_candidate", "feedback_4")
        self.mutate("rgb-feedback/final-verdict.json", "selected_candidate", "feedback_4")
        with self.assertRaisesRegex(ValueError, "Selected RGB candidate"):
            verify_selected_evidence(self.root)

    def test_source_psd_mismatch_rejected(self):
        self.mutate("rgb-feedback/final-verdict.json", "photoshop_reference_sha256", "f" * 64)
        with self.assertRaisesRegex(ValueError, "PSD SHA-256"):
            verify_selected_evidence(self.root)

    def test_native_candidate_digest_mismatch_rejected(self):
        self.mutate("selected-rgb/selection.json", "selected_candidate_zip_sha256", "e" * 64)
        with self.assertRaisesRegex(ValueError, "different RGB candidate"):
            verify_selected_evidence(self.root)

    def test_selected_native_zip_bytes_are_hash_verified(self):
        package = self.root / "editor/clgb71-selected-licensed-rgb-candidate.zip"
        package.write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            verify_selected_evidence(self.root)

    def test_selected_native_zip_embedded_editor_report_is_verified(self):
        package = self.root / "editor/clgb71-selected-licensed-rgb-candidate.zip"
        with zipfile.ZipFile(package, "a", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("validation/licensed-selected-rgb-parity.json",
                             json.dumps({"absolute_pixel_parity_proven": True}))
        self.mutate("selected-rgb/selection.json", "selected_native_zip_sha256",
                    hashlib.sha256(package.read_bytes()).hexdigest())
        with self.assertRaisesRegex(ValueError, "Selected native ZIP lacks"):
            verify_selected_evidence(self.root)

    def test_missing_selected_frame_rejected(self):
        (self.root / "selected-rgb/screenshots/shoot_up_02/image_48.png").unlink()
        with self.assertRaisesRegex(ValueError, "missing or extra"):
            verify_selected_evidence(self.root)

    def test_false_artistic_approval_rejected(self):
        self.mutate("rgb-feedback/final-verdict.json", "artistic_quality_approved", True)
        with self.assertRaisesRegex(ValueError, "unapproved"):
            verify_selected_evidence(self.root)

    def test_exact_rgba_parity_mismatch_rejected(self):
        self.mutate("rgb-feedback/final-verdict.json", "selected_exact_rgba_parity", True)
        with self.assertRaisesRegex(ValueError, "parity report"):
            verify_selected_evidence(self.root)


if __name__ == "__main__":
    unittest.main()
