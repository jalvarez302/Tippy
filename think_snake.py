#!/usr/bin/env python3
"""Play snake against Claude's thinking words while a real task runs behind it.

    python3 think_snake.py --seconds 45
    python3 think_snake.py -- npm test
    python3 think_snake.py -- pytest -q

The task runs on a background thread. The status word is scattered across the
board one letter at a time, and every letter you eat becomes part of your snake,
so the body spells out the word you just chewed through. When the task finishes
the screen says so and waits for you to quit.
"""

import argparse
import os
import sys

from terminal_loader.thinking import think

NO_TTY_MESSAGE = """\
This screen takes over the terminal, so it needs one it can draw on.
Right now its output is being captured by another program, which happens when
you launch it from a tool that records command output (an IDE task runner, a CI
step, or an assistant's shell).

Open Terminal or iTerm and run it directly:

    cd %s
    python3 think_snake.py --seconds 45
"""


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Playable thinking screen for long-running tasks",
        epilog="Put the command to run after a bare --, e.g. think_snake.py -- npm test",
    )
    parser.add_argument(
        "--seconds",
        type=float,
        default=None,
        help="With no command, how long to pretend to think (default: 20)",
    )
    parser.add_argument(
        "--speed",
        "--fps",
        dest="speed",
        type=float,
        default=None,
        help="Starting speed in cells per second; rises as you eat (default: 4.5)",
    )
    parser.add_argument(
        "--wrap", action="store_true", help="Pass through walls instead of crashing"
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command to run in the background, after --",
    )
    args = parser.parse_args(argv)

    command = [a for a in args.command if a != "--"] or None
    if command is None and args.seconds is None:
        args.seconds = 20

    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print(NO_TTY_MESSAGE % os.path.dirname(os.path.abspath(__file__)), file=sys.stderr)
        return 1

    result = think(
        command=command, seconds=args.seconds, fps=args.speed, wrap=args.wrap
    )

    print(
        "\nYou ate %d words (%d letters) in %.1fs, with %d crashes."
        % (
            result["words"],
            result["letters"],
            result["elapsed"],
            result["crashes"],
        )
    )

    if result["error"]:
        print("Task error: %s" % result["error"], file=sys.stderr)
        return 1

    if command:
        if result["output"]:
            print("\n--- %s ---" % " ".join(command))
            print(result["output"].rstrip())
        code = result["returncode"] or 0
        print("\nExit code: %d" % code)
        return code

    return 0


if __name__ == "__main__":
    sys.exit(main())
