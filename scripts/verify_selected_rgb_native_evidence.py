#!/usr/bin/env python3
"""Fail-closed provenance and frame-coverage gate for the *selected* licensed RGB candidate.

Only reads evidence produced by trusted licensed Editor jobs. The separate image
auditor must decode and inspect every PNG; this gate never approves the artwork.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

PSD_SHA256 = "7adee866547a3b3cc9838b655cf70865980c5dba00313373cbf903fed776c7b2"
CLIPS = ("shoot_up_01", "shoot_up_02")
CANDIDATES = ("initial", "feedback", "feedback_2", "feedback_3")


def _read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected object: {path}")
    return data


def verify_selected_evidence(evidence_dir: Path) -> dict:
    root = Path(evidence_dir)
    selected = root / "selected-rgb"
    selection = _read_json(selected / "selection.json")
    verdict = _read_json(root / "rgb-feedback" / "final-verdict.json")
    editor = _read_json(selected / "editor-roundtrip-report.json")
    parity = _read_json(selected / "psd-editor-parity.json")
    candidate = selection.get("selected_candidate")
    if candidate not in CANDIDATES or candidate != verdict.get("selected_candidate"):
        raise ValueError("Selected RGB candidate differs from the native verdict")
    # Third-round feedback is only valid after the licensed Editor actually
    # rendered it and the strict, non-regressing native checks selected it.
    if candidate == "feedback_3" and (
            verdict.get("feedback_round_three_pass") is not True or
            verdict.get("feedback_round_three_pixel_nonregression") is not True or
            verdict.get("feedback_round_three_exact_rgba_parity") is not
                verdict.get("selected_exact_rgba_parity")):
        raise ValueError("Unverified third RGB feedback selection")
    if (selection.get("source_psd_sha256") != PSD_SHA256 or
            verdict.get("photoshop_reference_sha256") != PSD_SHA256):
        raise ValueError("Original clgb71 PSD SHA-256 mismatch")
    for field in ("selected_candidate_zip_sha256", "selected_native_zip_sha256"):
        if re.fullmatch(r"[0-9a-f]{64}", str(selection.get(field, ""))) is None:
            raise ValueError(f"Missing pinned {field}")
    if editor.get("source_archive_sha256") != selection["selected_candidate_zip_sha256"]:
        raise ValueError("Native Editor rendered a different RGB candidate archive")
    # Validate actual ZIP bytes, not just a SHA-shaped value in a JSON receipt.
    package_name = "clgb71-selected-licensed-rgb-candidate.zip"
    package = root / "editor" / package_name
    if not package.is_file():
        package = root / package_name  # private Draft Release fallback
    if not package.is_file():
        raise ValueError("Selected licensed native ZIP was not retained")
    with package.open("rb") as stream:
        archive_digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if archive_digest != selection["selected_native_zip_sha256"]:
        raise ValueError("Selected native ZIP checksum mismatch")
    with zipfile.ZipFile(package) as archive:
        if archive.testzip() is not None:
            raise ValueError("Corrupted selected licensed native ZIP")
        entries = archive.namelist()
        if (len(entries) != len(set(entries)) or
                len([p for p in entries if p.startswith("images/") and p.endswith(".png")]) != 38 or
                "clgb71-editor-4.3.26.spine" not in entries or
                "validation/licensed-selected-editor-report.json" not in entries or
                "validation/licensed-selected-rgb-parity.json" not in entries):
            raise ValueError("Selected native ZIP lacks the 38-layer licensed project")
        if json.loads(archive.read("validation/licensed-selected-editor-report.json")) != editor:
            raise ValueError("Selected native ZIP report differs from 98 frame receipt")
        if json.loads(archive.read("validation/licensed-selected-rgb-parity.json")) != parity:
            raise ValueError("Selected native ZIP parity differs from frame receipt")
    if (editor.get("editor_import_verified") is not True or
            editor.get("native_spine_project_verified") is not True or
            editor.get("roundtrip_spine_version") != "4.3.26" or
            editor.get("slots") != 38 or
            editor.get("slot_order_unchanged") is not True or
            editor.get("ik_constraints") != 2 or
            editor.get("animations") != list(CLIPS) or
            editor.get("spine_render_nonblank_frames_verified") is not True):
        raise ValueError("Selected RGB candidate lacks required licensed Editor roundtrip")
    if (editor.get("artistic_quality_approved") is not False or
            verdict.get("artistic_quality_approved") is not False or
            verdict.get("release_ready") is not False):
        raise ValueError("Unapproved RGB evidence must remain unapproved")
    if parity.get("absolute_pixel_parity_proven") is not verdict.get("selected_exact_rgba_parity"):
        raise ValueError("Selected candidate parity report differs from final verdict")
    official = editor.get("official_rendered_frames")
    if not isinstance(official, list) or len(official) != 98 or len(set(official)) != 98:
        raise ValueError("Exactly 98 distinct official PNG frames are required")
    all_frames = sorted((selected / "screenshots").rglob("*.png"))
    if len(all_frames) != 98:
        raise ValueError("Selected candidate has missing or extra PNG frames")
    for clip in CLIPS:
        expected = [f for f in official if f.startswith(f"screenshots/{clip}/") and f.endswith(".png")]
        actual = sorted((selected / "screenshots" / clip).glob("*.png"))
        if len(expected) != 49 or len(actual) != 49:
            raise ValueError(f"{clip}: expected 49 selected native frames")
    for name in official:
        rel = Path(name)
        if rel.is_absolute() or ".." in rel.parts or not (selected / rel).is_file():
            raise ValueError(f"Missing or unsafe official frame: {name}")
    return {
        "status": "SELECTED_NATIVE_RGB_EVIDENCE_VERIFIED",
        "source_psd_sha256": PSD_SHA256,
        "selected_candidate": candidate,
        "selected_native_frames": len(all_frames),
        "clip_frame_counts": {clip: 49 for clip in CLIPS},
        "exact_rgba_parity": verdict["selected_exact_rgba_parity"],
        "artistic_quality_approved": False,
        "release_ready": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = verify_selected_evidence(args.evidence_dir)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("SELECTED_NATIVE_RGB_EVIDENCE", json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
