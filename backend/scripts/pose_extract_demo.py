#!/usr/bin/env python3
"""
Pose Extraction Demo CLI

Usage:
    python backend/scripts/pose_extract_demo.py /path/to/video.mp4
    python backend/scripts/pose_extract_demo.py /path/to/video.mp4 --sample-fps 5 --output /tmp/output.json

Extracts pose keypoints from a video and writes results to JSON.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.services.pose_service import extract_pose_keypoints_from_video

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Extract pose keypoints from video using MediaPipe",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  %(prog)s video.mp4
  %(prog)s video.mp4 --sample-fps 5 --output /tmp/poses.json
  %(prog)s video.mp4 --max-width 480
        """,
    )

    parser.add_argument("video_path", help="Path to video file")
    parser.add_argument(
        "--sample-fps",
        type=int,
        default=10,
        help="Sample every Nth frame (default: 10)",
    )
    parser.add_argument(
        "--max-width",
        type=int,
        default=640,
        help="Max frame width for downscaling (default: 640)",
    )
    parser.add_argument(
        "--output",
        help="Output JSON file path (default: <video_name>_poses.json in same dir)",
    )

    args = parser.parse_args()

    video_path = Path(args.video_path)

    # Validate input
    if not video_path.exists():
        logger.error(f"Video file not found: {video_path}")
        return 1

    logger.info(f"Processing video: {video_path}")
    logger.info(f"Sample rate: every {args.sample_fps} frame(s)")
    logger.info(f"Max width: {args.max_width}px")

    try:
        # Extract poses
        result = extract_pose_keypoints_from_video(
            video_path=str(video_path),
            sample_fps=args.sample_fps,
            max_width=args.max_width,
        )

        # Determine output path
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = video_path.parent / f"{video_path.stem}_poses.json"

        # Write JSON
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)

        logger.info(f"✓ Results written to: {output_path}")

        # Print summary
        print("\n" + "=" * 60)
        print("POSE EXTRACTION SUMMARY")
        print("=" * 60)
        print(f"Video:                  {video_path.name}")
        print(f"Total frames:           {result['total_frames']}")
        print(f"Sampled frames:         {result['sampled_frames']}")
        print(f"Frames with pose:       {result['frames_with_pose']}")
        print(f"Detection rate:         {result['detection_rate_percent']:.1f}%")
        print(f"Model:                  {result['model']}")
        print(f"Video FPS:              {result['video_fps']:.1f}")
        print(f"Output file:            {output_path}")
        print("=" * 60 + "\n")

        return 0

    except FileNotFoundError as e:
        logger.error(f"File error: {e}")
        return 1
    except ValueError as e:
        logger.error(f"Video error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
