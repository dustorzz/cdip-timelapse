#!/usr/bin/env python3
"""
CDIP Wave Model Timelapse Animator
Stitches 144 timestamped PNG frames into an animated GIF or MP4 at 15 fps.

144 frames × 30-min intervals = 72 hours (3 days) of wave data
144 frames ÷ 15 fps           = 9.6 seconds of timelapse

Requirements:
    pip install Pillow                  # required (GIF output)
    pip install opencv-python           # optional (MP4 output)

Usage:
    python cdip_animate.py                      # GIF, 15fps, last 144 frames
    python cdip_animate.py --format mp4         # MP4 instead of GIF
    python cdip_animate.py --format both        # produce both GIF and MP4
    python cdip_animate.py --frames /other/dir  # custom frames folder
    python cdip_animate.py --count 48           # use last N frames instead of 144
    python cdip_animate.py --fps 8              # override frame rate
    python cdip_animate.py --out my_timelapse   # custom output filename (no ext)
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import List


# ── Configuration ──────────────────────────────────────────────────────────────
FRAMES_DIR   = "cdip_frames"
TARGET_FRAMES = 144          # 72 hours at one frame per 30 min
FPS          = 15            # playback speed
DEFAULT_FMT  = "gif"         # "gif", "mp4", or "both"
OUTPUT_NAME  = "cdip_timelapse"
# ───────────────────────────────────────────────────────────────────────────────


def collect_frames(frames_dir: str, count: int) -> List[Path]:
    """Return the most-recent `count` PNG frames, sorted chronologically."""
    d = Path(frames_dir)
    if not d.exists():
        print(f"✗ Frames directory not found: {d.resolve()}")
        sys.exit(1)

    frames = sorted(d.glob("conception_*.png"))
    if not frames:
        print(f"✗ No frames found in {d.resolve()}")
        print("  Run  python cdip_capture.py  first to collect images.")
        sys.exit(1)

    if len(frames) < count:
        print(f"  ⚠  Only {len(frames)} frames available (target: {count}).")
        print(f"     Building timelapse with all available frames.\n")
    else:
        frames = frames[-count:]   # take the most recent `count` frames

    return frames


def parse_timestamp(path: Path) -> str:
    """Extract a human-readable timestamp from a filename like conception_20260514_210000.png"""
    try:
        stem = path.stem                      # e.g. "conception_20260514_210000"
        parts = stem.split("_")               # ["conception", "20260514", "210000"]
        date_str, time_str = parts[1], parts[2]
        dt = datetime.strptime(date_str + time_str, "%Y%m%d%H%M%S")
        return dt.strftime("%b %d %Y  %H:%M")
    except Exception:
        return path.stem


def make_gif(frames: List[Path], fps: int, output_name: str) -> str:
    """Create an animated GIF using Pillow."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("✗ Pillow not installed. Run:  pip install Pillow")
        sys.exit(1)

    duration_ms = int(1000 / fps)   # ms per frame
    output_path = f"{output_name}.gif"

    print(f"Building GIF  ({len(frames)} frames × {duration_ms}ms = "
          f"{len(frames)/fps:.1f}s at {fps}fps) ...")

    pil_frames = []
    for i, fp in enumerate(frames):
        img = Image.open(fp).convert("RGBA")

        # Stamp timestamp in top-right corner
        label = parse_timestamp(fp)
        draw  = ImageDraw.Draw(img)
        w, h  = img.size
        margin = 6
        # Simple white text with dark shadow for legibility
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            draw.text((w - 180 + dx, margin + dy), label, fill=(0, 0, 0, 200))
        draw.text((w - 180, margin), label, fill=(255, 255, 255, 240))

        pil_frames.append(img.convert("P", palette=Image.ADAPTIVE, colors=256))

        if (i + 1) % 20 == 0 or (i + 1) == len(frames):
            print(f"  Processed {i+1}/{len(frames)} frames...")

    pil_frames[0].save(
        output_path,
        save_all=True,
        append_images=pil_frames[1:],
        duration=duration_ms,
        loop=0,              # loop forever
        optimize=False,
    )

    size_mb = os.path.getsize(output_path) / 1_048_576
    print(f"  ✓  GIF saved → {output_path}  ({size_mb:.1f} MB)")
    return output_path


def make_mp4(frames: List[Path], fps: int, output_name: str) -> str:
    """Create an MP4 using OpenCV."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        print("✗ OpenCV not installed. Run:  pip install opencv-python")
        sys.exit(1)

    output_path = f"{output_name}.mp4"

    # Determine frame size from first image
    sample = cv2.imread(str(frames[0]))
    h, w   = sample.shape[:2]

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

    print(f"Building MP4  ({len(frames)} frames at {fps}fps = "
          f"{len(frames)/fps:.1f}s) ...")

    font       = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.55
    thickness  = 1

    for i, fp in enumerate(frames):
        frame = cv2.imread(str(fp))
        if frame is None:
            continue

        label = parse_timestamp(fp)
        # Shadow then white text
        cv2.putText(frame, label, (w - 215, 22), font, font_scale, (0, 0, 0),    thickness + 1, cv2.LINE_AA)
        cv2.putText(frame, label, (w - 215, 22), font, font_scale, (255,255,255), thickness,     cv2.LINE_AA)

        writer.write(frame)

        if (i + 1) % 20 == 0 or (i + 1) == len(frames):
            print(f"  Processed {i+1}/{len(frames)} frames...")

    writer.release()

    size_mb = os.path.getsize(output_path) / 1_048_576
    print(f"  ✓  MP4 saved → {output_path}  ({size_mb:.1f} MB)")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="CDIP wave model timelapse — 144 frames at 15fps"
    )
    parser.add_argument("--frames", default=FRAMES_DIR,
                        help=f"Folder containing PNG frames (default: {FRAMES_DIR})")
    parser.add_argument("--count", type=int, default=TARGET_FRAMES,
                        help=f"Number of most-recent frames to use (default: {TARGET_FRAMES})")
    parser.add_argument("--fps", type=int, default=FPS,
                        help=f"Frames per second (default: {FPS})")
    parser.add_argument("--format", choices=["gif", "mp4", "both"], default=DEFAULT_FMT,
                        help=f"Output format (default: {DEFAULT_FMT})")
    parser.add_argument("--out", default=OUTPUT_NAME,
                        help=f"Output filename without extension (default: {OUTPUT_NAME})")
    args = parser.parse_args()

    frames = collect_frames(args.frames, args.count)

    duration_s  = len(frames) / args.fps
    data_hours  = len(frames) * 0.5

    print("=" * 60)
    print("  CDIP Wave Model — Timelapse Animator")
    print("=" * 60)
    print(f"  Frames dir : {Path(args.frames).resolve()}")
    print(f"  Frames used: {len(frames)} (covers {data_hours:.0f} hrs of wave data)")
    print(f"  Playback   : {args.fps} fps  →  {duration_s:.1f} seconds")
    print(f"  Format     : {args.format.upper()}")
    print("=" * 60 + "\n")

    outputs = []
    if args.format in ("gif", "both"):
        outputs.append(make_gif(frames, args.fps, args.out))
    if args.format in ("mp4", "both"):
        outputs.append(make_mp4(frames, args.fps, args.out))

    print(f"\nDone! Output file(s):")
    for o in outputs:
        print(f"  → {os.path.abspath(o)}")


if __name__ == "__main__":
    main()
