import json
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from create_native_frame_manifest import build_manifest, verify_manifest


class NativeFrameManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for clip in ("shoot_up_01", "shoot_up_02"):
            folder = self.root / clip
            folder.mkdir()
            for i in range(49):
                (folder / f"frame_{i:02d}.png").write_bytes(f"{clip}:{i}".encode())

    def test_all_98_frame_bytes_are_pinned(self):
        manifest = build_manifest(self.root, run_id=43707363636, head_sha="a" * 40)
        verify_manifest(self.root, manifest)
        self.assertEqual(manifest["frame_count"], 98)

    def test_modified_png_same_name_is_rejected(self):
        manifest = build_manifest(self.root, run_id=43707363636, head_sha="a" * 40)
        frame = self.root / "shoot_up_02/frame_48.png"
        frame.write_bytes(b"tampered but same filename")
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            verify_manifest(self.root, manifest)

    def test_missing_png_is_rejected(self):
        manifest = build_manifest(self.root, run_id=43707363636, head_sha="a" * 40)
        (self.root / "shoot_up_01/frame_00.png").unlink()
        with self.assertRaisesRegex(ValueError, "set differs"):
            verify_manifest(self.root, manifest)

    def test_extra_png_is_rejected(self):
        manifest = build_manifest(self.root, run_id=43707363636, head_sha="a" * 40)
        (self.root / "shoot_up_01/extra.png").write_bytes(b"extra")
        with self.assertRaisesRegex(ValueError, "set differs"):
            verify_manifest(self.root, manifest)

    def test_invalid_run_provenance_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "provenance"):
            build_manifest(self.root, run_id=0, head_sha="a" * 40)


    def test_cli_writes_valid_json_and_round_trips_verification(self):
        import subprocess
        import sys

        script = Path(__file__).resolve().parents[1] / "scripts" / "create_native_frame_manifest.py"
        manifest = self.root / "selected-native-frame-sha256.json"
        create = [
            sys.executable, str(script),
            "--frames", str(self.root),
            "--manifest", str(manifest),
            "--run-id", "43714831108",
            "--head-sha", "a" * 40,
        ]
        subprocess.run(create, check=True, capture_output=True, text=True)
        data = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertEqual(data["frame_count"], 98)
        verify = [
            sys.executable, str(script),
            "--frames", str(self.root),
            "--manifest", str(manifest),
            "--verify",
        ]
        subprocess.run(verify, check=True, capture_output=True, text=True)



if __name__ == "__main__":
    unittest.main()
