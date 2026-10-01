# snake-thinking

Play snake while you wait, against the words Claude Code shows when it is
thinking. One letter of the current status word is on the board at a time, and
they come in order. Each letter you swallow becomes your snake, so the body is
the word rather than a chain of circles:

```
Ruminating
```

You start as a single marker and grow into the word, letter by letter. The head
carries the first letter you ate and each new letter is added behind it, so the
word builds backward from the head and reads in order when you are travelling
left. Finish it and the snake holds still for two seconds so you can read what
you spelled, glints, heats up and bursts apart. The next word starts from the
spark it leaves behind, while the explosion is still fading.

It draws in Claude's colours on a 256-colour terminal and falls back to plain
ones elsewhere. The seed you start each word as is Claude's own spinner glyph.

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
