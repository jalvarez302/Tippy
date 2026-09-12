"""Playable snake game built on the terminal_loader rendering stack."""

import curses
import random
import signal
import time

from .animation import SnakeAnimation
from .renderer import TerminalRenderer

# Colour pairs defined by TerminalRenderer.
C_SNAKE = 1
C_FRAME = 2
C_FOOD = 3
C_ALERT = 4
C_ACCENT = 5
C_TEXT = 6

MIN_HEIGHT = 12
MIN_WIDTH = 34


class SnakeGame:
    """Arrow-key snake with walls, self collision, scoring and restart.

    The autonomous loading animation lives in SnakeLoader; this is the mode a
    person actually steers.
    """

    HEAD_CHAR = "●"
    BODY_CHAR = "○"
    FOOD_CHAR = "◆"

    # Movement is cells per second, kept separate from the redraw rate so input
    # is sampled every frame rather than once per move.
    BASE_SPEED = 5.5
    MAX_SPEED = 10.0
    SPEED_STEP = 0.55
    FOOD_PER_SPEEDUP = 4
    POINTS_PER_FOOD = 10

    FRAME_RATE = 60
    MAX_CATCHUP_STEPS = 3
    MAX_QUEUED_TURNS = 3

    # Every accepted steering key, mapped to a (dy, dx) heading.
    KEY_DIRECTIONS = {
        curses.KEY_UP: (-1, 0),
        curses.KEY_DOWN: (1, 0),
        curses.KEY_LEFT: (0, -1),
        curses.KEY_RIGHT: (0, 1),
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
    RESTART_KEYS = {ord("r"), ord("R")}

    def __init__(self, fps=None, wrap=False):
        self.renderer = TerminalRenderer()
        self.wrap = wrap
        self.base_speed = fps or self.BASE_SPEED

        height, width = self.renderer.get_dimensions()
        # Rows: top border, HUD, play area, status line, bottom border.
        self.play_height = height - 4
        self.play_width = width - 2
        self.too_small = self.play_height < MIN_HEIGHT - 4 or width < MIN_WIDTH

        self.high_score = 0
        self.running = False
        self._install_signal_handler()
        self._new_round()

    # ---------------------------------------------------------------- setup

    def _install_signal_handler(self):
        try:
            signal.signal(signal.SIGINT, lambda *_: self.stop())
        except ValueError:
            # Not on the main thread; the KeyboardInterrupt handler still covers us.
            pass

    def _new_round(self):
        """Reset score, snake and food for a fresh game."""
        self.snake = SnakeAnimation(
            max(1, self.play_height),
            max(1, self.play_width),
            initial_length=4,
            wrap=self.wrap,
        )
        self.score = 0
        self.food_eaten = 0
        self.turn_queue = []
        self.paused = False
        self.game_over = False
        self.death_reason = None
        self.food = None
        self._spawn_food()

    def _spawn_food(self):
        """Place food on a random cell the snake does not occupy."""
        free = [
            (y, x)
            for y in range(self.play_height)
            for x in range(self.play_width)
            if not self.snake.is_occupied(y, x)
        ]
        self.food = random.choice(free) if free else None

    @property
    def speed(self):
        """Cells per second. Ramps with every few pellets, then plateaus."""
        step = self.food_eaten // self.FOOD_PER_SPEEDUP
        return min(self.MAX_SPEED, self.base_speed + step * self.SPEED_STEP)

    @property
    def step_interval(self):
        return 1.0 / self.speed

    @property
    def speed_level(self):
        return 1 + self.food_eaten // self.FOOD_PER_SPEEDUP

    # ----------------------------------------------------------------- loop

    def start(self):
        """Run the game until the player quits."""
        if self.too_small:
            self._render_too_small()
            time.sleep(2.5)
            return 0

        self.running = True
        frame = 1.0 / self.FRAME_RATE
        carried = 0.0
        last = time.monotonic()
        try:
            while self.running:
                now = time.monotonic()
                delta = now - last
                last = now

                self._handle_input()
                if not self.running:
                    break

                if self.paused or self.game_over:
                    carried = 0.0
                else:
                    carried += delta
                    steps = 0
                    while (carried >= self.step_interval
                           and steps < self.MAX_CATCHUP_STEPS):
                        carried -= self.step_interval
                        self._step()
                        steps += 1
                        if self.game_over:
                            carried = 0.0
                            break
                    if steps >= self.MAX_CATCHUP_STEPS:
                        carried = 0.0

                self._render()
                time.sleep(max(0.0, frame - (time.monotonic() - now)))
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
        return self.high_score

    def stop(self):
        """Stop the loop and hand the terminal back."""
        self.running = False
        try:
            self.renderer.clear()
            self.renderer.refresh()
        except Exception:
            pass

    def _handle_input(self):
        """Apply every key queued since the last frame."""
        for key in self.renderer.drain_keys():
            if key in self.QUIT_KEYS:
                self.running = False
                return
            if self.game_over:
                if key in self.RESTART_KEYS:
                    self._new_round()
                continue
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

    def _step(self):
        """Advance one tick of play."""
        self._apply_queued_turn()
        alive = self.snake.update()
        if not alive:
            self.game_over = True
            self.death_reason = self.snake.death_reason
            self.high_score = max(self.high_score, self.score)
            return

        if self.food and self.snake.get_head() == self.food:
            self.snake.grow()
            self.score += self.POINTS_PER_FOOD
            self.food_eaten += 1
            self._spawn_food()
            if self.food is None:
                # Board filled: a win, scored as a game over.
                self.game_over = True
                self.death_reason = "win"
                self.high_score = max(self.high_score, self.score)

    # --------------------------------------------------------------- render

    def _render_too_small(self):
        self.renderer.clear()
        self.renderer.center_text("Terminal too small to play.", y=0)
        self.renderer.center_text(
            "Need at least %d rows x %d columns." % (MIN_HEIGHT, MIN_WIDTH), y=1
        )
        self.renderer.refresh()

    def _render(self):
        r = self.renderer
        height, width = r.get_dimensions()
        r.clear()
        r.draw_border(color_pair=C_FRAME)

        # HUD across the top, inside the border.
        hud = "SCORE %-5d LEN %-4d SPEED %d" % (
            self.score,
            len(self.snake.get_body()),
            self.speed_level,
        )
        r.draw_string(1, 2, hud, color_pair=C_TEXT)

        # Right-align the session best, but only when it clears the HUD; on a
        # narrow terminal the two used to overwrite each other mid-word.
        if self.high_score:
            best = "BEST %d" % self.high_score
            best_x = width - len(best) - 2
            if best_x >= 2 + len(hud) + 2:
                r.draw_string(1, best_x, best, color_pair=C_ACCENT)

        # Food first, so the snake head always draws on top of it.
        if self.food:
            r.draw_char(self.food[0] + 2, self.food[1] + 1, self.FOOD_CHAR, C_FOOD)

        body = self.snake.get_body()
        for i, (y, x) in enumerate(body):
            char = self.HEAD_CHAR if i == 0 else self.BODY_CHAR
            colour = C_ALERT if (self.game_over and i == 0) else C_SNAKE
            r.draw_char(y + 2, x + 1, char, colour)

        # Status line above the bottom border.
        status_y = height - 2
        if self.game_over:
            r.center_text(self._game_over_text(), y=status_y)
        elif self.paused:
            r.center_text("PAUSED  —  any arrow resumes", y=status_y)
        else:
            r.center_text("arrows/wasd move  ·  p pause  ·  q quit", y=status_y)

        if self.game_over:
            self._render_overlay()

        r.refresh()

    def _game_over_text(self):
        if self.death_reason == "win":
            return "BOARD CLEARED  —  r restart  ·  q quit"
        return "GAME OVER  —  r restart  ·  q quit"

    def _render_overlay(self):
        """Centre a short result panel over the play area."""
        r = self.renderer
        height, width = r.get_dimensions()
        if self.death_reason == "win":
            headline = "BOARD CLEARED"
        elif self.death_reason == SnakeAnimation.DIED_SELF:
            headline = "ATE YOURSELF"
        else:
            headline = "HIT THE WALL"

        lines = [
            (headline, C_ALERT),
            ("score %d" % self.score, C_TEXT),
            ("best %d" % self.high_score, C_ACCENT),
        ]
        panel_w = max(len(text) for text, _ in lines) + 6
        top = max(2, height // 2 - 3)
        left = max(1, (width - panel_w) // 2)

        for i in range(len(lines) + 2):
            r.draw_string(top + i, left, " " * panel_w, color_pair=0)
        for i, (text, colour) in enumerate(lines):
            r.draw_string(
                top + 1 + i, left + (panel_w - len(text)) // 2, text, color_pair=colour
            )


def play(fps=None, wrap=False):
    """Launch the game. Returns the best score of the session."""
    return SnakeGame(fps=fps, wrap=wrap).start()
