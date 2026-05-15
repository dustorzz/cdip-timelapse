#!/usr/bin/env python3
"""
CDIP Wave Model Image Capture Script
Captures the Scripps/CDIP Conception wave model image every 30 minutes
and saves timestamped copies to a local folder.

Requirements:
    pip install requests Pillow schedule

Usage:
    python cdip_capture.py            # runs every 30 min (default)
    python cdip_capture.py --once     # capture one image and exit
"""

import os
import time
import argparse
import requests
import schedule
from datetime import datetime
from PIL import Image
from io import BytesIO

# ── Configuration ──────────────────────────────────────────────────────────────
IMAGE_URL    = "https://cdip.ucsd.edu/recent/model_images/conception.png"
OUTPUT_DIR   = "cdip_frames"
INTERVAL_MIN = 30          # matches CDIP's 30-minute buoy update cycle
TIMEOUT_SEC  = 15
# ───────────────────────────────────────────────────────────────────────────────


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def frame_count():
    """Return how many PNG frames are currently saved."""
    if not os.path.isdir(OUTPUT_DIR):
        return 0
    return len([f for f in os.listdir(OUTPUT_DIR) if f.endswith(".png")])


def capture_image():
    """Download the current CDIP image and save it with a timestamp filename."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = f"conception_{timestamp}.png"
    filepath  = os.path.join(OUTPUT_DIR, filename)

    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Fetching image...", end=" ")
        response = requests.get(IMAGE_URL, timeout=TIMEOUT_SEC)
        response.raise_for_status()

        img = Image.open(BytesIO(response.content))
        img.save(filepath)

        count = frame_count()
        hours = count * 0.5
        print(f"Saved → {filename}  |  Total frames: {count}  ({hours:.1f} hrs of data)")
        return filepath

    except requests.exceptions.RequestException as e:
        print(f"\n  ✗ Network error: {e}")
    except Exception as e:
        print(f"\n  ✗ Error saving image: {e}")

    return None


def run_scheduler():
    """Schedule captures every 30 minutes, matching CDIP's update cycle."""
    print("=" * 60)
    print("  CDIP Wave Model — Image Capture")
    print("=" * 60)
    print(f"  URL      : {IMAGE_URL}")
    print(f"  Interval : every {INTERVAL_MIN} minutes (matches CDIP update cycle)")
    print(f"  Output   : {os.path.abspath(OUTPUT_DIR)}/")
    print(f"  Target   : 144 frames = 72 hours (3 days) of data")
    print(f"  At 15fps : 144 frames = ~9.6 seconds of timelapse")
    print(f"  Press Ctrl+C to stop.")
    print("=" * 60 + "\n")

    # Capture immediately on start, then every 30 min
    capture_image()
    schedule.every(INTERVAL_MIN).minutes.do(capture_image)

    try:
        while True:
            schedule.run_pending()
            time.sleep(10)
    except KeyboardInterrupt:
        count = frame_count()
        print(f"\nCapture stopped. {count} frames saved to '{OUTPUT_DIR}/'")
        if count > 0:
            print(f"Run  python cdip_animate.py  to create your timelapse.")


def main():
    parser = argparse.ArgumentParser(description="CDIP wave model image capture — 30 min interval")
    parser.add_argument("--once", action="store_true",
                        help="Capture a single image and exit")
    args = parser.parse_args()

    ensure_output_dir()

    if args.once:
        capture_image()
    else:
        run_scheduler()


if __name__ == "__main__":
    main()
