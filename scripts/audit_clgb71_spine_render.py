#!/usr/bin/env python3
"""Inspect real Spine Editor PNG frames for a source-specific visual artifact.

This gate is intentionally NOT an artistic PASS oracle. It finds a suspicious
increase in the fully opaque flat cyan found in the approved PSD, then fails
closed on automatic art publication. It never changes the source PNGs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from PIL import Image, ImageChops
# The same official-Editor frame comparator is used by the validated audit.
# Explicitly resolve our own read-only sibling when imported by unittest.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_rendered_frames import official_motion_envelope, motion_envelope_similarity

CLIPS = ("shoot_up_01", "shoot_up_02")
TARGET_RGBA = (42, 255, 255, 255)
# Source-specific native-render calibration (clgb71, 2s, 24fps):
# actual unapproved editor run 42861463253 peaked at 5,705 / 6,636
# opaque flat-cyan pixels (9x / 10.62x setup), while corrected artistically
# better aimed/alpha-controlled run 42863805699 peaked at 1,711 / 628.
# These conservative values flag the former but leave the latter inspectable.
# Never interpret passing this detector as full artistic approval.
MIN_NEW_FLAT_PIXELS = 3_000
MIN_GROWTH_FACTOR = 5

def exact_rgba_count(image: Image.Image, rgba=TARGET_RGBA) -> int:
    rgba_image = image.convert("RGBA")
    mask = Image.new("L", rgba_image.size, 255)
    for channel, value in zip(rgba_image.split(), rgba):
        lookup = [255 if i == value else 0 for i in range(256)]
        mask = ImageChops.multiply(mask, channel.point(lookup))
    return mask.histogram()[255]

def review_frames(root: Path, minimum_pixels=MIN_NEW_FLAT_PIXELS,
                  minimum_ratio=MIN_GROWTH_FACTOR):
    outcomes = []
    findings = []
    motion_envelopes = {}
    for clip in CLIPS:
        frames = sorted((root / clip).glob("*.png"))
        if len(frames) < 3:
            raise ValueError(f"{clip}: required real Spine Editor frame sequence is absent")
        baseline = None
        max_pixels = -1
        peak = None
        for index, frame in enumerate(frames):
            with Image.open(frame) as im:
                im.load()
                pixels = exact_rgba_count(im)
                if im.size[0] < 16 or im.size[1] < 16:
                    raise ValueError(f"{clip}: invalid frame size")
            if index == 0:
                baseline = pixels
            if pixels > max_pixels:
                max_pixels, peak = pixels, frame.name
        growth = round(max_pixels / max(1, baseline), 2)
        anomaly = max_pixels >= minimum_pixels and growth >= minimum_ratio
        # 24+ real Editor frames are required before diagnosing clip-level
        # similarity. Tiny unit fixtures must not falsely claim full coverage.
        if len(frames) >= 24:
            motion_envelopes[clip] = official_motion_envelope(frames)
        outcome = {
            "clip": clip,
            "frames_checked": len(frames),
            "setup_flat_cyan_pixels": baseline,
            "peak_flat_cyan_pixels": max_pixels,
            "peak_frame": peak,
            "peak_to_setup_growth": growth,
            "flat_color_anomaly": anomaly,
        }
        outcomes.append(outcome)
        if anomaly:
            findings.append(
                f"{clip}: an untextured opaque cyan region grows {growth}x "
                f"from setup ({baseline} to {max_pixels} pixels) at {peak}"
            )
    similarity = None
    near_duplicate = False
    if len(motion_envelopes) == len(CLIPS):
        similarity = motion_envelope_similarity(
            motion_envelopes[CLIPS[0]], motion_envelopes[CLIPS[1]])
        near_duplicate = similarity >= .985
        if near_duplicate:
            findings.append(
                f"Official Editor 24fps shooting clips have near-duplicate "
                f"RGB motion envelopes: Pearson r={similarity:.6f} (limit .985). "
                "Distinct anticipation, shot accents and recovery are required."
            )
    return {
        "status": "REVIEW_REQUIRED" if findings else "NO_DETECTED_FLAT_CYAN_ANOMALY",
        "real_editor_motion_envelope_pearson_r":
            round(similarity, 6) if similarity is not None else None,
        "near_duplicate_threshold": .985,
        "near_duplicate_render_sequences": near_duplicate,
        "near_duplicate_evaluated_on_full_editor_frames": similarity is not None,
        "official_spine_render_reviewed": True,
        "clips": outcomes,
        "findings": findings,
        "source_artwork_modified": False,
        "editor_import_verified_by_this_test": False,
        "artistic_quality_approved": False,
        "release_ready": False,
        "reason": "This is a narrow render-regression detector, not a complete artistic approval.",
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--frames-dir", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    try:
        result = review_frames(args.frames_dir)
    except Exception as ex:
        result = {
            "status": "REVIEW_UNAVAILABLE",
            "reason": str(ex),
            "official_spine_render_reviewed": False,
            "artistic_quality_approved": False,
            "release_ready": False,
        }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("SPINE_ARTISTIC_RENDER_GUARD", json.dumps(result, ensure_ascii=False))
    if result["status"] != "NO_DETECTED_FLAT_CYAN_ANOMALY":
        sys.exit(1)

if __name__ == "__main__":
    main()
