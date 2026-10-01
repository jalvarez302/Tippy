"""A playable thinking screen: eat the status word while real work runs behind it.

The conceit is the one Claude Code already uses. While a task runs, the screen
shows a present-participle status word. Here that word is scattered across the
board as food, and the snake you steer has to eat it one letter at a time, in
order. Every letter you swallow becomes a segment of your body, so the snake
gradually spells out the word it just ate.

Finish a word and the snake holds still so you can read it, glows, and bursts
apart. The next word starts from the spark it leaves behind.

Nothing here blocks the work. The task runs on its own thread and the screen
closes when it finishes.
"""

import curses
import math
import random
import signal
import subprocess
import threading
import time

from .animation import SnakeAnimation
from .renderer import TerminalRenderer
from .words import THINKING_WORDS

MIN_ROWS = 14
MIN_COLS = 40

# Keep a new letter this far (Manhattan) from the snake so it is never dropped
# right under the player's nose.
LETTER_SPACING = 4

# The glyphs Claude Code cycles through beside its status word. Played forward
# then back, so the seed breathes rather than jumping from the last to the first.
SPINNER = "·✢✳✶✻✽"
SPINNER_FRAMES = SPINNER + SPINNER[-2:0:-1]
SPINNER_FPS = 8

PLAY = "play"
HOLD = "hold"
BURST = "burst"


class Palette:
    """Colour pairs in Claude's colours, with a plain fallback for 8-colour terminals.

    Each entry is (xterm-256 colour, 8-colour fallback, attribute used with the
    fallback). Looking a name up gives (pair number, attribute) for the renderer.
    """

    FIRST_PAIR = 16

    NAMED = {
        "clay": (173, curses.COLOR_YELLOW, 0),
        "glow": (216, curses.COLOR_YELLOW, curses.A_BOLD),
        "spark": (230, curses.COLOR_WHITE, curses.A_BOLD),
        "text": (252, curses.COLOR_WHITE, 0),
        "muted": (245, curses.COLOR_WHITE, curses.A_DIM),
        "faint": (239, curses.COLOR_WHITE, curses.A_DIM),
        "ok": (108, curses.COLOR_GREEN, 0),
        "bad": (167, curses.COLOR_RED, 0),
    }

    # Particle ramps, fresh to spent. Fire is a finished word, ember is a crash.
    RAMPS = {
        "fire": [
            (230, curses.COLOR_WHITE, curses.A_BOLD),
            (223, curses.COLOR_YELLOW, curses.A_BOLD),
            (216, curses.COLOR_YELLOW, curses.A_BOLD),
            (209, curses.COLOR_YELLOW, 0),
            (173, curses.COLOR_YELLOW, 0),
            (137, curses.COLOR_RED, 0),
            (95, curses.COLOR_RED, curses.A_DIM),
            (59, curses.COLOR_WHITE, curses.A_DIM),
        ],
        "ember": [
            (224, curses.COLOR_WHITE, curses.A_BOLD),
            (210, curses.COLOR_RED, curses.A_BOLD),
            (167, curses.COLOR_RED, 0),
            (131, curses.COLOR_RED, 0),
            (95, curses.COLOR_RED, curses.A_DIM),
            (59, curses.COLOR_WHITE, curses.A_DIM),
        ],
    }

    def __init__(self):
        try:
            rich = curses.has_colors() and getattr(curses, "COLORS", 0) >= 256
        except curses.error:
            rich = False
        self.rich = rich
        self._next_pair = self.FIRST_PAIR
        self.styles = {name: self._define(spec) for name, spec in self.NAMED.items()}
        self.ramps = {
            name: [self._define(spec) for spec in specs]
            for name, specs in self.RAMPS.items()
        }

    def _define(self, spec):
        rich_colour, basic_colour, basic_attr = spec
        pair = self._next_pair
        self._next_pair += 1
        try:
            curses.init_pair(pair, rich_colour if self.rich else basic_colour, -1)
        except (curses.error, ValueError):
            return (0, basic_attr)
        return (pair, 0 if self.rich else basic_attr)

    def __getitem__(self, name):
        return self.styles[name]

    def ramp(self, name, fraction):
        """The style a fraction of the way along a fade, 0 fresh to 1 spent."""
        shades = self.ramps[name]
        return shades[min(len(shades) - 1, max(0, int(fraction * len(shades))))]


class Particle:
    """One spark of an explosion, in fractional cell coordinates."""

    __slots__ = ("y", "x", "vy", "vx", "age", "life", "glyphs", "ramp")

    # Velocity decays by e every 1/DRAG seconds, so a burst flies out fast and
    # settles rather than drifting off at constant speed.
    DRAG = 3.2

    def __init__(self, y, x, vy, vx, life, glyphs, ramp):
        self.y, self.x = y, x
        self.vy, self.vx = vy, vx
        self.age = 0.0
        self.life = life
        self.glyphs = glyphs
        self.ramp = ramp

    def update(self, dt):
        self.age += dt
        drag = math.exp(-self.DRAG * dt)
        self.vy *= drag
        self.vx *= drag
        self.y += self.vy * dt
        self.x += self.vx * dt
        return self.age < self.life

    @property
    def fraction(self):
        return min(1.0, self.age / self.life)

    @property
    def glyph(self):
        return self.glyphs[min(len(self.glyphs) - 1, int(self.fraction * len(self.glyphs)))]


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

    # Movement is measured in cells per second, separately from the redraw
    # rate. Tying the two together meant input was only sampled once per move,
    # so at a playable pace the controls felt a beat behind.
    BASE_SPEED = 6.5
    MAX_SPEED = 11.0
    SPEED_STEP = 0.5
    LETTERS_PER_SPEEDUP = 8
    # A terminal cell is about twice as tall as it is wide, so the same cells
    # per second looks twice as fast going up and down. Stretching vertical
    # steps evens the apparent speed out, which is most of what makes turns
    # feel smooth instead of lurching.
    VERTICAL_STRETCH = 1.6

    FRAME_RATE = 60
    # Cap catch-up so a stalled process cannot teleport the snake across the board.
    MAX_CATCHUP_STEPS = 3
    # Turns buffered while waiting for the next move, so a quick double tap round
    # a corner is not swallowed.
    MAX_QUEUED_TURNS = 3

    # A finished word: read it, watch it charge, watch it burst.
    HOLD_SECONDS = 2.0
    CHARGE_SECONDS = 0.5
    # Play resumes this long after the burst while the sparks are still fading,
    # so the next word starts inside the explosion rather than after a gap.
    BURST_FREEZE = 0.55
    CRASH_FREEZE = 0.75
    # A new letter on the board grows in through these before showing itself.
    POP_IN = "·✢✶"
    POP_IN_SECONDS = 0.21
    EAT_FLASH_SECONDS = 0.16

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
        self.base_speed = fps or self.BASE_SPEED

        self.renderer = TerminalRenderer()
        self.palette = Palette()
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
        self.turn_queue = []
        self.particles = []

        # The clock every timed effect reads. Set once per frame so a whole
        # frame is drawn against a single instant.
        self.now = time.monotonic()
        self.phase = PLAY
        self.phase_started = self.now
        self.phase_until = 0.0
        self.burst_kind = None
        self.ate_at = -1.0

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
        self.turn_queue = []

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
        self.letter_born = self.now
        if self.letter_index >= len(self.word):
            self.letter = None
            return
        spot = self._free_cell()
        self.letter = None if spot is None else [spot, self.word[self.letter_index]]

    def _free_cell(self):
        """Find an empty cell that is not crowding the snake's head."""
        head = self.snake.get_head()
        for spacing in (LETTER_SPACING, 2, 1):
            for _ in range(400):
                y = random.randrange(self.play_height)
                x = random.randrange(self.play_width)
                if self.snake.is_occupied(y, x):
                    continue
                if head and abs(y - head[0]) + abs(x - head[1]) < spacing:
                    continue
                return (y, x)
        # Last resort on a cramped board: any cell at all.
        free = [
            (y, x)
            for y in range(self.play_height)
            for x in range(self.play_width)
            if not self.snake.is_occupied(y, x)
        ]
        return random.choice(free) if free else None

    @property
    def target(self):
        """The letter on the board, or None when the word is done."""
        return self.letter

    @property
    def speed(self):
        """Cells per second, ramping gently as the round goes on."""
        step = self.letters_eaten // self.LETTERS_PER_SPEEDUP
        return min(self.MAX_SPEED, self.base_speed + step * self.SPEED_STEP)

    @property
    def step_interval(self):
        """Seconds until the next move, longer when that move is vertical."""
        heading = self.turn_queue[0] if self.turn_queue else self.snake.next_direction
        stretch = self.VERTICAL_STRETCH if heading[0] else 1.0
        return stretch / self.speed

    @property
    def holding(self):
        """True while a finished word is on screen, before it bursts."""
        return self.phase == HOLD

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
        frame = 1.0 / self.FRAME_RATE
        carried = 0.0
        last = time.monotonic()
        try:
            while self.running:
                now = time.monotonic()
                delta = now - last
                last = now
                self.now = now

                # Input and redraw happen every frame; the snake moves on its
                # own slower clock. That is what makes the controls feel
                # immediate while the motion itself stays calm.
                self._handle_input()
                if not self.running:
                    break
                if self.worker.done.is_set() and self.finished_at is None:
                    self.finished_at = now

                if self.phase != PLAY:
                    if now >= self.phase_until:
                        self._advance_phase()
                    carried = 0.0
                elif self.paused:
                    carried = 0.0
                else:
                    carried += delta
                    steps = 0
                    while (carried >= self.step_interval
                           and steps < self.MAX_CATCHUP_STEPS):
                        carried -= self.step_interval
                        self._step()
                        steps += 1
                        if self.phase != PLAY or not self.running:
                            carried = 0.0
                            break
                    if steps >= self.MAX_CATCHUP_STEPS:
                        carried = 0.0

                if not self.paused:
                    self._update_particles(delta)
                self._render()
                time.sleep(max(0.0, frame - (time.monotonic() - now)))
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
            if direction:
                self.paused = False
                if len(self.turn_queue) < self.MAX_QUEUED_TURNS:
                    self.turn_queue.append(direction)

    def _apply_queued_turn(self):
        """Take the next buffered turn the snake can legally make."""
        while self.turn_queue:
            direction = self.turn_queue.pop(0)
            if self.snake.set_direction(direction):
                return

    def _enter(self, phase, seconds):
        self.phase = phase
        self.phase_started = self.now
        self.phase_until = self.now + seconds

    def _advance_phase(self):
        """Move a finished word or a crash on to whatever comes next."""
        if self.phase == HOLD:
            self._explode_word()
        elif self.phase == BURST:
            if self.burst_kind == "word":
                self.word_index += 1
            self.burst_kind = None
            self.phase = PLAY
            self._load_word()

    def _step(self):
        self._apply_queued_turn()
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
        self.ate_at = self.now
        self._pop(*self.snake.get_head())

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
        self._enter(HOLD, self.HOLD_SECONDS)

    def _explode_word(self):
        """Blow the finished word apart and leave a seed where its head was."""
        cells = list(zip(self.snake.get_body(), self.eaten_letters))
        self._burst(cells, "fire", sparks=5, ring=True)
        self.eaten_letters = []
        self.snake.reset_length()
        # A turn pressed while reading the word is stale by now.
        self.turn_queue = self.turn_queue[-1:]
        self.burst_kind = "word"
        self._enter(BURST, self.BURST_FREEZE)

    def _crash(self):
        """A crash costs the current word, not the session. The screen plays on."""
        self.crashes += 1
        body = self.snake.get_body()
        letters = self.eaten_letters + [SPINNER[0]] * (len(body) - len(self.eaten_letters))
        self._burst(list(zip(body, letters)), "ember", sparks=3, ring=False)
        self._new_snake()
        self.letter = None
        self.burst_kind = "crash"
        self._enter(BURST, self.CRASH_FREEZE)

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

    # ------------------------------------------------------------ particles

    def _burst(self, cells, ramp, sparks, ring):
        """Explode a run of lettered cells outward from their middle.

        Each letter flies off whole and crumbles, throws a few sparks, and for a
        finished word a ring of dust races out ahead of it all. Horizontal speed
        is doubled because a cell is half as wide as it is tall, so the burst
        reads round rather than squashed.
        """
        if not cells:
            return
        cy = sum(y for (y, _), _ in cells) / len(cells)
        cx = sum(x for (_, x), _ in cells) / len(cells)

        for (y, x), char in cells:
            dy, dx = y - cy, (x - cx) / 2.0
            angle = math.atan2(dy, dx) if (dy or dx) else random.uniform(0, math.tau)
            angle += random.uniform(-0.5, 0.5)
            self._fling(y, x, angle, random.uniform(4.0, 8.0),
                        random.uniform(0.9, 1.3), [char] * 4 + ["✢", "·"], ramp)
            for _ in range(sparks):
                self._fling(y, x, random.uniform(0, math.tau), random.uniform(5.0, 14.0),
                            random.uniform(0.35, 0.85), ["✶", "✢", "+", "·"], ramp)

        if ring:
            count = 28
            for i in range(count):
                self._fling(cy, cx, math.tau * i / count, 17.0,
                            random.uniform(0.45, 0.6), ["·"], ramp)

    def _pop(self, y, x):
        """A small puff where a letter was swallowed."""
        for _ in range(6):
            self._fling(y, x, random.uniform(0, math.tau), random.uniform(4.0, 8.0),
                        random.uniform(0.2, 0.35), ["✢", "·"], "fire")

    def _fling(self, y, x, angle, speed, life, glyphs, ramp):
        self.particles.append(Particle(
            y, x, speed * math.sin(angle), 2.0 * speed * math.cos(angle),
            life, glyphs, ramp,
        ))

    def _update_particles(self, dt):
        self.particles = [p for p in self.particles if p.update(dt)]

    # --------------------------------------------------------------- render

    def _put(self, y, x, char, style, attr=0):
        """Draw at a play-area cell in a named or ramp style."""
        pair, base = self.palette[style] if isinstance(style, str) else style
        self.renderer.draw_char(y + 2, x + 1, char, pair, base | attr)

    def _text(self, y, x, text, style, attr=0):
        pair, base = self.palette[style]
        self.renderer.draw_string(y, x, text, pair, base | attr)

    def _centre(self, y, text, style, attr=0):
        width = self.renderer.get_dimensions()[1]
        self._text(y, max(1, (width - len(text)) // 2), text, style, attr)

    def _spinner(self):
        return SPINNER_FRAMES[int(self.now * SPINNER_FPS) % len(SPINNER_FRAMES)]

    def _shimmer(self, i, length, speed=16.0):
        """Brightness 0 to 1 of character i as a highlight sweeps along a word.

        The same glint Claude Code runs across its status word, only here it
        runs across the snake too.
        """
        span = length + 8
        band = (self.now - self.phase_started) * speed % span - 4
        return max(0.0, 1.0 - abs(i - band) / 1.8)

    @staticmethod
    def _level(brightness):
        if brightness > 0.66:
            return "spark"
        if brightness > 0.2:
            return "glow"
        return "clay"

    def _render_too_small(self):
        self.renderer.clear()
        self.renderer.center_text("Window too small to play; still working.", y=0)
        self.renderer.center_text("Need %d rows x %d cols." % (MIN_ROWS, MIN_COLS), y=1)
        self.renderer.refresh()

    def _render(self):
        r = self.renderer
        height, width = r.get_dimensions()
        r.clear()
        r.draw_border(color_pair=self.palette["faint"][0])

        self._render_hud(width)
        self._render_particles()
        self._render_letter()
        self._render_snake()
        self._render_status(height)

        r.refresh()

    def _render_hud(self, width):
        """Left: Claude's status line, filling in as you eat. Right: the task."""
        x = 2
        if self.worker.done.is_set():
            ok = self.worker.returncode == 0
            self._text(1, x, "✓" if ok else "✗", "ok" if ok else "bad", curses.A_BOLD)
        else:
            self._text(1, x, self._spinner(), "clay", curses.A_BOLD)
        x += 2

        word = self.word
        eaten = len(self.eaten_text) if self.phase == PLAY else len(word)
        for i, char in enumerate(word):
            if i < eaten:
                style = self._level(self._shimmer(i, len(word), speed=10.0))
                self._text(1, x + i, char, style, curses.A_BOLD)
            elif i == eaten:
                self._text(1, x + i, char, "glow", curses.A_BOLD | curses.A_UNDERLINE)
            else:
                self._text(1, x + i, char, "faint")
        self._text(1, x + len(word), "…", "muted")

        if self.worker.done.is_set():
            state, style = "done in %.1fs" % self.worker.elapsed, "ok"
        else:
            state, style = "%ds" % self.worker.elapsed, "muted"
        right_x = width - len(state) - 2
        if right_x > x + len(word) + 3:
            self._text(1, right_x, state, style)

    def _render_particles(self):
        # Oldest first, so the freshest sparks land on top.
        for p in sorted(self.particles, key=lambda p: -p.age):
            y, x = int(round(p.y)), int(round(p.x))
            if 0 <= y < self.play_height and 0 <= x < self.play_width:
                self._put(y, x, p.glyph, self.palette.ramp(p.ramp, p.fraction))

    def _render_letter(self):
        """The single letter on offer: grows in, then breathes."""
        if not self.letter:
            return
        (y, x), char = self.letter
        age = self.now - self.letter_born
        if age < self.POP_IN_SECONDS:
            glyph = self.POP_IN[int(age / self.POP_IN_SECONDS * len(self.POP_IN))]
            self._put(y, x, glyph, "glow", curses.A_BOLD)
            return
        breath = 0.5 + 0.5 * math.sin(age * math.tau * 0.9)
        self._put(y, x, char, self._level(breath), curses.A_BOLD)

    def _render_snake(self):
        """The snake is the word. Segment i carries the i-th letter eaten.

        The head leads with the first letter and the word trails behind it, so it
        reads in order when the snake is travelling left. An unfed snake is a
        single spinner glyph, the seed the next word grows from.
        """
        if self.phase == BURST and self.burst_kind == "crash":
            return
        body = self.snake.get_body()
        length = len(self.eaten_letters)

        charge = 0.0
        if self.phase == HOLD:
            left = self.phase_until - self.now
            charge = max(0.0, 1.0 - left / self.CHARGE_SECONDS)

        for i, (y, x) in enumerate(body):
            if i >= length:
                self._put(y, x, self._spinner(), "glow", curses.A_BOLD)
                continue
            if self.phase == HOLD:
                # Glint runs along the word, then the whole thing heats up.
                brightness = max(self._shimmer(i, length), charge)
                style = self._level(brightness)
            elif i == 0:
                fresh = self.now - self.ate_at < self.EAT_FLASH_SECONDS
                style = "spark" if fresh else "glow"
            else:
                style = "clay"
            self._put(y, x, self.eaten_letters[i], style, curses.A_BOLD)

    def _render_status(self, height):
        y = height - 2
        if self.worker.done.is_set():
            ok = self.worker.returncode == 0
            verb = "finished" if ok else "failed (exit %s)" % self.worker.returncode
            self._centre(y, "Claude %s  ·  q to come back" % verb,
                         "ok" if ok else "bad", curses.A_BOLD)
            return
        if self.phase == HOLD or (self.phase == BURST and self.burst_kind == "word"):
            self._centre(y, "✓ %s" % self.word, "glow", curses.A_BOLD)
            return
        if self.paused:
            self._centre(y, "paused  ·  any arrow resumes", "text")
            return
        tally = "%d words · %d letters" % (self.words_done, self.letters_eaten)
        if self.crashes:
            tally += " · %d crashes" % self.crashes
        self._centre(y, "%s  ·  p pause · q quit" % tally, "muted")


def think(command=None, seconds=None, fps=None, wrap=False, words=None):
    """Run a task behind a playable thinking screen. Returns a result dict."""
    worker = Worker(command=command, seconds=seconds).start()
    return ThinkingSnake(worker, words=words, fps=fps, wrap=wrap).start()
