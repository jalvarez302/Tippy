# snake-thinking

Play snake while you wait, against the words Claude Code shows when it is
thinking. The current status word is scattered across the board one letter at a
time. You eat them in order, and each letter you swallow becomes a segment of
your snake, so the body gradually spells out the word.

```
○○○Ruminating
```

Finish a word and the snake freezes for a beat so you can read it, then digests
and the next word scatters.

## Run it

```
python3 think_snake.py --seconds 60          # timed round
python3 think_snake.py -- npm test           # play while a real command runs
python3 think_snake.py -- pytest -q
```

The command runs on a background thread. When it finishes, the screen says so
and waits for you to quit, then prints the captured output and the exit code.

Arrows or WASD steer. `p` pauses. `q` quits. Crashing into a wall or yourself
costs the current word and restarts it; the session keeps going, because the
point is to pass the time rather than to lose.

## What is real and what is not

This is shaped like a Claude Code plugin and carries a real manifest and slash
command, but it does not hook the actual loading indicator. Claude Code does not
expose the spinner for plugins to replace, and a slash command has its output
captured, so it cannot hand a curses program the terminal. The honest version of
this idea is what you get here: a standalone screen you start yourself, which
wraps the slow command you were going to run anyway.

## Layout

| Path | What it is |
|---|---|
| `.claude-plugin/plugin.json` | Plugin manifest |
| `commands/snake.md` | The `/snake` slash command |
| `../terminal_loader/thinking.py` | The screen and its game loop |
| `../terminal_loader/words.py` | The thinking vocabulary |
| `../think_snake.py` | Entry point |
