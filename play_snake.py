#!/usr/bin/env python3
"""Play snake in the terminal.

    python3 play_snake.py

Arrows or WASD steer, p pauses, r restarts after a crash, q quits.
"""

import argparse
import os
import sys

from terminal_loader import SnakeGame


def main():
    parser = argparse.ArgumentParser(description="Playable terminal snake game")
    parser.add_argument(
        "--speed",
        "--fps",
        dest="speed",
        type=float,
        default=None,
        help="Starting speed in cells per second; rises as you eat (default: 5.5)",
    )
    parser.add_argument(
        "--wrap",
        action="store_true",
        help="Pass through the walls instead of dying on them",
    )
    args = parser.parse_args()

    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print(
            "This game draws a full screen, so it needs a terminal it can take "
            "over.\n"
            "Right now its output is being captured by another program, which "
            "happens\n"
            "when you launch it from a tool that records command output (an IDE "
            "task\n"
            "runner, a CI step, or an assistant's shell).\n\n"
            "Open Terminal or iTerm and run it directly:\n\n"
            "    cd %s\n"
            "    python3 play_snake.py\n" % os.path.dirname(os.path.abspath(__file__)),
            file=sys.stderr,
        )
        return 1

    try:
        best = SnakeGame(fps=args.speed, wrap=args.wrap).start()
    except Exception as exc:
        print("Error: %s" % exc, file=sys.stderr)
        return 1

    print("\nThanks for playing. Best score: %d" % best)
    return 0


if __name__ == "__main__":
    sys.exit(main())
