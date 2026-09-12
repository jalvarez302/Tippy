#!/usr/bin/env python3
"""Play snake in the terminal.

    python3 play_snake.py

Arrows or WASD steer, p pauses, r restarts after a crash, q quits.
"""

import argparse
import sys

from terminal_loader import SnakeGame


def main():
    parser = argparse.ArgumentParser(description="Playable terminal snake game")
    parser.add_argument(
        "--fps",
        type=int,
        default=10,
        help="Starting speed in frames per second; rises as you eat (default: 10)",
    )
    parser.add_argument(
        "--wrap",
        action="store_true",
        help="Pass through the walls instead of dying on them",
    )
    args = parser.parse_args()

    if not sys.stdout.isatty():
        print("play_snake.py needs a real terminal.", file=sys.stderr)
        return 1

    try:
        best = SnakeGame(fps=args.fps, wrap=args.wrap).start()
    except Exception as exc:
        print("Error: %s" % exc, file=sys.stderr)
        return 1

    print("\nThanks for playing. Best score: %d" % best)
    return 0


if __name__ == "__main__":
    sys.exit(main())
