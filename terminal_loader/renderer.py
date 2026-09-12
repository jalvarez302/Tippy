"""Curses-based terminal rendering engine."""

import curses
import atexit
import locale

locale.setlocale(locale.LC_ALL, "")


class TerminalRenderer:
    """Manages terminal rendering using curses library."""

    def __init__(self):
        self.stdscr = None
        self.height = 0
        self.width = 0
        self._raw_keys = []
        self._esc_frames = 0
        self._init_curses()
        atexit.register(self._cleanup)

    def _init_curses(self):
        """Initialize curses and terminal settings."""
        self.stdscr = curses.initscr()
        try:
            curses.cbreak()
        except curses.error:
            pass
        try:
            curses.noecho()
        except curses.error:
            pass

        self.stdscr.nodelay(True)
        self.stdscr.timeout(0)
        try:
            self.stdscr.keypad(True)
        except curses.error:
            pass
        try:
            curses.curs_set(0)
        except curses.error:
            pass

        self.height, self.width = self.stdscr.getmaxyx()

        try:
            if curses.has_colors():
                curses.start_color()
                curses.use_default_colors()
                curses.init_pair(1, curses.COLOR_GREEN, -1)
                curses.init_pair(2, curses.COLOR_CYAN, -1)
                curses.init_pair(3, curses.COLOR_YELLOW, -1)
                curses.init_pair(4, curses.COLOR_RED, -1)
                curses.init_pair(5, curses.COLOR_MAGENTA, -1)
                curses.init_pair(6, curses.COLOR_WHITE, -1)
        except curses.error:
            pass

    def _cleanup(self):
        """Restore terminal to normal state."""
        if self.stdscr:
            try:
                curses.curs_set(1)
            except curses.error:
                pass
            try:
                curses.echo()
            except curses.error:
                pass
            try:
                curses.nocbreak()
            except curses.error:
                pass
            try:
                curses.endwin()
            except curses.error:
                pass

    def clear(self):
        """Clear the entire screen."""
        self.stdscr.clear()

    def refresh(self):
        """Refresh the display."""
        self.stdscr.refresh()

    def draw_char(self, y, x, char, color_pair=0, attr=0):
        """Draw a single character at position (y, x). Supports Unicode.

        attr takes curses attributes such as curses.A_BOLD or curses.A_DIM.
        """
        if 0 <= y < self.height and 0 <= x < self.width - 1:
            try:
                self.stdscr.addstr(y, x, char, curses.color_pair(color_pair) | attr)
            except curses.error:
                pass

    def draw_string(self, y, x, text, color_pair=0, attr=0):
        """Draw a string starting at position (y, x)."""
        if 0 <= y < self.height and 0 <= x < self.width:
            try:
                max_len = self.width - x - 1
                truncated = text[:max_len] if max_len > 0 else ""
                if truncated:
                    self.stdscr.addstr(
                        y, x, truncated, curses.color_pair(color_pair) | attr
                    )
            except curses.error:
                pass

    def draw_border(self, color_pair=0):
        """Draw a border around the screen."""
        for x in range(self.width):
            self.draw_char(0, x, "─", color_pair)
            self.draw_char(self.height - 1, x, "─", color_pair)

        for y in range(self.height):
            self.draw_char(y, 0, "│", color_pair)
            self.draw_char(y, self.width - 1, "│", color_pair)

        self.draw_char(0, 0, "┌", color_pair)
        self.draw_char(0, self.width - 1, "┐", color_pair)
        self.draw_char(self.height - 1, 0, "└", color_pair)
        self.draw_char(self.height - 1, self.width - 1, "┘", color_pair)

    def center_text(self, text, y=None):
        """Draw text centered horizontally, optionally at specific y position."""
        if y is None:
            y = self.height // 2

        x = max(0, (self.width - len(text)) // 2)
        self.draw_string(y, x, text, color_pair=2)

    def get_key(self):
        """Return the next queued key, or None if nothing is waiting.

        Never blocks: the screen is in nodelay mode, so curses returns -1 when
        the input queue is empty.
        """
        try:
            key = self.stdscr.getch()
        except curses.error:
            return None
        return None if key == -1 else key

    # Raw escape sequences for the arrow keys, in both normal and application
    # cursor mode. In nodelay mode ncurses will not wait for the rest of a
    # sequence, so it hands back ESC, then "[", then the letter, and the caller
    # sees a bare ESC press that was never made.
    ESC_SEQUENCES = {
        (0x5B, 0x41): curses.KEY_UP,
        (0x5B, 0x42): curses.KEY_DOWN,
        (0x5B, 0x43): curses.KEY_RIGHT,
        (0x5B, 0x44): curses.KEY_LEFT,
        (0x4F, 0x41): curses.KEY_UP,
        (0x4F, 0x42): curses.KEY_DOWN,
        (0x4F, 0x43): curses.KEY_RIGHT,
        (0x4F, 0x44): curses.KEY_LEFT,
    }

    # Frames to hold a lone ESC waiting for the rest of a sequence before
    # deciding it really was just the escape key.
    ESC_PATIENCE = 2

    def drain_keys(self, limit=32):
        """Return every key queued since the last call, oldest first.

        A slow frame can let several presses pile up; reading them all keeps the
        snake from replaying stale input for seconds after the player stopped.
        Escape sequences are reassembled here, across frames when a sequence is
        split over two reads.
        """
        for _ in range(limit):
            key = self.get_key()
            if key is None:
                break
            self._raw_keys.append(key)

        keys = []
        while self._raw_keys:
            key = self._raw_keys[0]
            if key != 0x1B:
                keys.append(key)
                self._raw_keys.pop(0)
                continue

            pair = tuple(self._raw_keys[1:3])
            if len(pair) == 2:
                translated = self.ESC_SEQUENCES.get(pair)
                del self._raw_keys[0:3]
                self._esc_frames = 0
                if translated is not None:
                    keys.append(translated)
                # An unrecognised sequence is swallowed rather than guessed at.
                continue

            # Sequence is still arriving. Wait a frame or two before calling it
            # a real escape key press.
            if self._esc_frames < self.ESC_PATIENCE:
                self._esc_frames += 1
                break
            self._raw_keys.pop(0)
            self._esc_frames = 0
            keys.append(0x1B)

        return keys

    def flush_input(self):
        """Discard anything sitting in the input queue."""
        self._raw_keys = []
        self._esc_frames = 0
        try:
            curses.flushinp()
        except curses.error:
            pass

    def get_dimensions(self):
        """Return terminal dimensions (height, width)."""
        return self.height, self.width

    def is_valid_position(self, y, x):
        """Check if position is within terminal bounds."""
        return 0 <= y < self.height and 0 <= x < self.width
