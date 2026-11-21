#!/usr/bin/env python3
"""Create/verify a SHA-256 receipt for the selected licensed Spine Editor PNG delivery.

This is a passive integrity check: it never generates or edits animation frames and
never grants artistic approval. The receipt binds every selected PNG path and byte
sequence to the successful native workflow run that supplied the evidence artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

CLIPS = ("shoot_up_01", "shoot_up_02")
EXPECTED_PER_CLIP = 49


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(frames_root: Path, *, run_id: int, head_sha: str) -> dict:
    root = Path(frames_root).resolve()
    entries = {}
    for clip in CLIPS:
        files = sorted((root / clip).glob("*.png"))
        if len(files) != EXPECTED_PER_CLIP:
            raise ValueError(f"{clip}: expected exactly {EXPECTED_PER_CLIP} PNGs, got {len(files)}")
        for path in files:
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"Unsafe frame file: {path}")
            rel = path.relative_to(root).as_posix()
            entries[rel] = sha256_file(path)
    all_pngs = sorted(p.relative_to(root).as_posix() for p in root.rglob("*.png"))
    if len(all_pngs) != 98 or set(all_pngs) != set(entries):
        raise ValueError("Selected frame set must contain exactly the 98 expected PNGs")
    if run_id <= 0 or len(head_sha) != 40 or any(c not in "0123456789abcdef" for c in head_sha):
        raise ValueError("Invalid native workflow provenance")
    return {
        "schema": "2spine.native-frame-sha256.v1",
        "native_run_id": run_id,
        "native_head_sha": head_sha,
        "frame_count": 98,
        "clip_frame_counts": {clip: EXPECTED_PER_CLIP for clip in CLIPS},
        "frames": entries,
    }


def verify_manifest(frames_root: Path, manifest: dict) -> None:
    if manifest.get("schema") != "2spine.native-frame-sha256.v1":
        raise ValueError("Unknown frame manifest schema")
    if manifest.get("frame_count") != 98 or manifest.get("clip_frame_counts") != {c: 49 for c in CLIPS}:
        raise ValueError("Frame manifest coverage is incomplete")
    frames = manifest.get("frames")
    if not isinstance(frames, dict) or len(frames) != 98:
        raise ValueError("Frame manifest must pin exactly 98 files")
    root = Path(frames_root).resolve()
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*.png")}
    if actual != set(frames):
        raise ValueError("Selected PNG set differs from SHA-256 manifest")
    for rel, expected in frames.items():
        path = (root / rel).resolve()
        if root not in path.parents or path.is_symlink():
            raise ValueError(f"Unsafe manifest path: {rel}")
        if not isinstance(expected, str) or len(expected) != 64:
            raise ValueError(f"Invalid SHA-256 for {rel}")
        if sha256_file(path) != expected:
            raise ValueError(f"Selected frame SHA-256 mismatch: {rel}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frames", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--run-id", type=int)
    parser.add_argument("--head-sha")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        verify_manifest(args.frames, json.loads(args.manifest.read_text(encoding="utf-8")))
        print("SELECTED_NATIVE_FRAME_SHA256_VERIFIED")
    else:
        if args.run_id is None or args.head_sha is None:
            parser.error("--run-id and --head-sha are required when creating a manifest")
        result = build_manifest(args.frames, run_id=args.run_id, head_sha=args.head_sha)
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        verify_manifest(args.frames, result)
        print("SELECTED_NATIVE_FRAME_SHA256_CREATED", args.run_id, len(result["frames"]))


if __name__ == "__main__":
    main()
