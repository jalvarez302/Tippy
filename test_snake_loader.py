#!/usr/bin/env python3
"""Test script to run the snake loader animation."""

import sys
import argparse
from terminal_loader import SnakeLoader


def main():
    parser = argparse.ArgumentParser(
        description="Snake game-style loading animation for terminal"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=15,
        help="Duration in seconds to run the animation (default: 15)",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=10,
        help="Animation frames per second (default: 10)",
    )

    args = parser.parse_args()

    try:
        loader = SnakeLoader(fps=args.fps, message="Loading...")
        print(f"\nStarting snake loader animation ({args.duration}s)...")
        print("Press Ctrl+C to stop.\n")
        loader.start(duration=args.duration)
        print("\nAnimation complete!")
    except KeyboardInterrupt:
        print("\n\nAnimation stopped.")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
