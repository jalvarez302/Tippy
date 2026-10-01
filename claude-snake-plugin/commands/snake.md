---
description: Play snake against the thinking words while a command runs
argument-hint: [command to run in the background]
allowed-tools: Bash
---

The user wants to play snake while a task runs.

A slash command cannot draw a full-screen curses game, because command output is
captured rather than attached to the terminal. So do not try to launch the game
yourself with Bash. It will fail the tty check and print a wall of text.

Instead, tell the user to run this in their own terminal window:

```
cd <repo root>
python3 think_snake.py -- $ARGUMENTS
```

With no arguments, suggest `python3 think_snake.py --seconds 60` so they get a
timed round to try it out.

Then explain the controls in one line: arrows or WASD steer, letters must be
eaten in order, `p` pauses, `q` quits.
