"""A playable thinking screen: eat the status word while real work runs behind it.

The conceit is the one Claude Code already uses. While a task runs, the screen
shows a present-participle status word. Here that word is scattered across the
board as food, and the snake you steer has to eat it one letter at a time, in
order. Every letter you swallow becomes a segment of your body, so the snake
gradually spells out the word it just ate.

Nothing here blocks the work. The task runs on its own thread and the screen
closes when it finishes.
"""

import curses
import random
import signal
import subprocess
import threading
import time

from .animation import SnakeAnimation
from .renderer import TerminalRenderer
from .words import THINKING_WORDS, longest

C_SNAKE = 1
C_FRAME = 2
C_FOOD = 3
C_ALERT = 4
C_ACCENT = 5
C_TEXT = 6

MIN_ROWS = 14
MIN_COLS = 40

# Keep scattered letters this far apart (Manhattan) so the board stays readable.
LETTER_SPACING = 4


class Worker:
    """Runs the background task the screen is waiting on.

    Either a shell command or, with no command, a plain timer so the screen can
    be demoed on its own.
    """

    def __init__(self, command=None, seconds=None):
        self.command = command
        self.seconds = seconds
        self.done = threading.Event()
        self.returncode = None
        self.output = ""
        self.error = None
        self.started_at = None
        self._thread = None

    def start(self):
        self.started_at = time.time()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def _run(self):
        try:
            if self.command:
                proc = subprocess.run(
                    self.command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                self.returncode = proc.returncode
                self.output = proc.stdout or ""
            else:
                time.sleep(self.seconds if self.seconds is not None else 20)
                self.returncode = 0
        except Exception as exc:  # noqa: BLE001 - surfaced to the player verbatim
            self.error = str(exc)
            self.returncode = -1
        finally:
            self.done.set()

    @property
    def elapsed(self):
        return 0.0 if self.started_at is None else time.time() - self.started_at

    @property
    def label(self):
        if self.command:
            return " ".join(self.command)
        return "a %ds timer" % (self.seconds if self.seconds is not None else 20)


class ThinkingSnake:
    """The playable loading screen."""

    HEAD_CHAR = "●"

    BASE_FPS = 9
    MAX_FPS = 18
    LETTERS_PER_SPEEDUP = 6

    KEY_DIRECTIONS = {
        curses.KEY_UP: (-1, 0), curses.KEY_DOWN: (1, 0),
        curses.KEY_LEFT: (0, -1), curses.KEY_RIGHT: (0, 1),
        ord("w"): (-1, 0), ord("W"): (-1, 0),
        ord("s"): (1, 0), ord("S"): (1, 0),
        ord("a"): (0, -1), ord("A"): (0, -1),
        ord("d"): (0, 1), ord("D"): (0, 1),
        ord("k"): (-1, 0), ord("j"): (1, 0),
        ord("h"): (0, -1), ord("l"): (0, 1),
    }
    # Deliberately not ESC: arrow keys arrive as an escape sequence, and a
    # stray ESC would quit mid-game.
    QUIT_KEYS = {ord("q"), ord("Q")}
    PAUSE_KEYS = {ord("p"), ord("P"), ord(" ")}

    def __init__(self, worker, words=None, fps=None, wrap=False):
        self.worker = worker
        self.words = list(words or THINKING_WORDS)
        random.shuffle(self.words)
        self.wrap = wrap
        self.base_fps = fps or self.BASE_FPS

        self.renderer = TerminalRenderer()
        height, width = self.renderer.get_dimensions()
        # Rows: border, HUD, play area, status, border.
        self.play_height = height - 4
        self.play_width = width - 2
        self.too_small = height < MIN_ROWS or width < MIN_COLS

        self.words_done = 0
        self.letters_eaten = 0
        self.crashes = 0
        self.word_index = 0
        self.paused = False
        self.running = False
        self.finished_at = None
        # Frames left holding a completed word on screen. Without this the
        # snake spells the word and erases it in the same frame, so the whole
        # payoff of the mechanic is invisible.
        self.celebrate_frames = 0

        self._install_signal_handler()
        self._new_snake()
        self._load_word()

    # ---------------------------------------------------------------- setup

    def _install_signal_handler(self):
        try:
            signal.signal(signal.SIGINT, lambda *_: self.stop())
        except ValueError:
            pass

    def _new_snake(self):
        # Length 1: the snake starts as a bare seed and every segment it gains
        # after that is a letter, so the body is never padded with filler.
        self.snake = SnakeAnimation(
            max(1, self.play_height),
            max(1, self.play_width),
            initial_length=1,
            wrap=self.wrap,
        )
        # Letters swallowed so far, oldest first, so index i lines up with body
        # segment i. The head carries the first letter eaten and each new letter
        # is added behind it, so the word builds backward from the head.
        self.eaten_letters = []
        self.finishing = False

    @property
    def word(self):
        return self.words[self.word_index % len(self.words)]

    def _load_word(self):
        """Start the current word. Only its first letter goes on the board."""
        self.letter_index = 0
        self.finishing = False
        self._place_letter()

    def _place_letter(self):
        """Put the next letter somewhere free. One letter is on screen at a time."""
        if self.letter_index >= len(self.word):
            self.letter = None
            return
        spot = self._free_cell([])
        self.letter = None if spot is None else [spot, self.word[self.letter_index]]

    def _free_cell(self, taken):
        """Find an empty cell that is not crowding the snake or another letter."""
        for spacing in (LETTER_SPACING, 2, 1):
            for _ in range(400):
                y = random.randrange(self.play_height)
                x = random.randrange(self.play_width)
                if self.snake.is_occupied(y, x):
                    continue
                if any(abs(y - ty) + abs(x - tx) < spacing for ty, tx in taken):
                    continue
                return (y, x)
        # Last resort on a cramped board: any cell at all.
        free = [
            (y, x)
            for y in range(self.play_height)
            for x in range(self.play_width)
            if not self.snake.is_occupied(y, x) and (y, x) not in taken
        ]
        return random.choice(free) if free else None

    @property
    def target(self):
        """The letter on the board, or None when the word is done."""
        return self.letter

    @property
    def fps(self):
        step = self.letters_eaten // self.LETTERS_PER_SPEEDUP
        return min(self.MAX_FPS, self.base_fps + step)

    @property
    def eaten_text(self):
        """The part of the word already swallowed."""
        return self.word[: self.letter_index]

    # ----------------------------------------------------------------- loop

    def start(self):
        if self.too_small:
            self._render_too_small()
            self.worker.done.wait()
            return self._summary()

        self.running = True
        try:
            while self.running:
                self._handle_input()
                if not self.running:
                    break
                if self.worker.done.is_set() and self.finished_at is None:
                    self.finished_at = time.time()
                if not self.paused:
                    self._step()
                self._render()
                time.sleep(1 / self.fps)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
        return self._summary()

    def stop(self):
        self.running = False
        try:
            self.renderer.clear()
            self.renderer.refresh()
        except Exception:
            pass

    def _handle_input(self):
        for key in self.renderer.drain_keys():
            if key in self.QUIT_KEYS:
                self.running = False
                return
            if key in self.PAUSE_KEYS:
                self.paused = not self.paused
                continue
            direction = self.KEY_DIRECTIONS.get(key)
            if direction and self.snake.set_direction(direction):
                self.paused = False
                break

    def _step(self):
        if self.celebrate_frames > 0:
            self.celebrate_frames -= 1
            if self.celebrate_frames == 0:
                self._next_word()
            return

        alive = self.snake.update()
        if not alive:
            self._crash()
            return

        # After the last letter the snake is still one segment short, because a
        # snake grows into the cell ahead of it. Let it catch up before freezing,
        # or the held word would be missing its tail letter.
        if self.finishing:
            if len(self.snake.get_body()) >= len(self.eaten_letters):
                self._begin_hold()
            return

        target = self.target
        if target and self.snake.get_head() == tuple(target[0]):
            self._eat(target[1])

    def _eat(self, char):
        """Swallow a letter. The body is exactly the letters eaten so far."""
        self.eaten_letters.append(char)
        self.snake.max_length = max(1, len(self.eaten_letters))
        self.letter_index += 1
        self.letters_eaten += 1

        if self.letter_index >= len(self.word):
            # Clear the board: otherwise the letter just eaten stays drawn
            # through the finishing step and the whole hold.
            self.letter = None
            self.finishing = True
        else:
            self._place_letter()

    def _begin_hold(self):
        """Word complete. Freeze so the spelled-out snake can be read."""
        self.words_done += 1
        self.finishing = False
        self.celebrate_frames = max(8, int(self.fps * 1.6))

    def _next_word(self):
        """Digest the finished word and start the next one."""
        self.word_index += 1
        self.eaten_letters = []
        self.snake.reset_length()
        self._load_word()

    def _crash(self):
        """A crash costs the current word, not the session. The screen plays on."""
        self.crashes += 1
        self.celebrate_frames = 0
        self._new_snake()
        self._load_word()

    def _summary(self):
        return {
            "words": self.words_done,
            "letters": self.letters_eaten,
            "crashes": self.crashes,
            "returncode": self.worker.returncode,
            "output": self.worker.output,
            "error": self.worker.error,
            "elapsed": self.worker.elapsed,
        }

    # --------------------------------------------------------------- render

    def _render_too_small(self):
        self.renderer.clear()
        self.renderer.center_text("Window too small to play; still working.", y=0)
        self.renderer.center_text("Need %d rows x %d cols." % (MIN_ROWS, MIN_COLS), y=1)
        self.renderer.refresh()

    def _render(self):
        r = self.renderer
        height, width = r.get_dimensions()
        r.clear()
        r.draw_border(color_pair=C_FRAME)

        self._render_hud(r, width)
        self._render_letters(r)
        self._render_snake(r)
        self._render_status(r, height, width)

        r.refresh()

    def _render_hud(self, r, width):
        """Left: the word filling in as you eat it. Right: the task state."""
        eaten = self.eaten_text
        remaining = self.word[len(eaten):]

        x = 2
        r.draw_string(1, x, eaten, color_pair=C_SNAKE, attr=curses.A_BOLD)
        x += len(eaten)
        if remaining:
            r.draw_string(1, x, remaining[0], color_pair=C_FOOD, attr=curses.A_BOLD)
            r.draw_string(1, x + 1, remaining[1:], color_pair=C_FRAME, attr=curses.A_DIM)

        if self.worker.done.is_set():
            state, colour = "done in %.1fs" % self.worker.elapsed, C_SNAKE
        else:
            state, colour = "working %.0fs" % self.worker.elapsed, C_ACCENT
        right_x = width - len(state) - 2
        if right_x > 2 + len(self.word) + 2:
            r.draw_string(1, right_x, state, color_pair=colour)

    def _render_letters(self, r):
        """The single letter currently on offer."""
        if not self.letter:
            return
        (y, x), char = self.letter
        r.draw_char(y + 2, x + 1, char, C_FOOD, curses.A_BOLD)

    def _render_snake(self, r):
        """The snake is the word. Segment i carries the i-th letter eaten.

        The head leads with the first letter and the word trails behind it, so it
        reads in order when the snake is travelling left. Only an unfed snake
        draws a marker, and only because a single letter has to start somewhere.
        """
        body = self.snake.get_body()
        for i, (y, x) in enumerate(body):
            if i < len(self.eaten_letters):
                colour = C_ACCENT if i == 0 else C_SNAKE
                r.draw_char(y + 2, x + 1, self.eaten_letters[i], colour, curses.A_BOLD)
            else:
                r.draw_char(y + 2, x + 1, self.HEAD_CHAR, C_SNAKE, curses.A_BOLD)

    def _render_status(self, r, height, width):
        y = height - 2
        if self.worker.done.is_set():
            ok = self.worker.returncode == 0
            verb = "finished" if ok else "failed (exit %s)" % self.worker.returncode
            r.center_text("Claude %s  —  q to come back" % verb, y=y)
            return
        if self.celebrate_frames > 0:
            r.center_text("%s  ✓" % self.word, y=y)
            return
        if self.paused:
            r.center_text("PAUSED  —  any arrow resumes", y=y)
            return
        tally = "%d words · %d letters" % (self.words_done, self.letters_eaten)
        if self.crashes:
            tally += " · %d crashes" % self.crashes
        r.center_text("%s  —  p pause · q quit" % tally, y=y)


def think(command=None, seconds=None, fps=None, wrap=False, words=None):
    """Run a task behind a playable thinking screen. Returns a result dict."""
    worker = Worker(command=command, seconds=seconds).start()
    return ThinkingSnake(worker, words=words, fps=fps, wrap=wrap).start()
