"""Curses-based terminal rendering engine."""

import curses
import atexit


class TerminalRenderer:
    """Manages terminal rendering using curses library."""

    def __init__(self):
        self.stdscr = None
        self.height = 0
        self.width = 0
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

        self.height, self.width = self.stdscr.getmaxyx()

        try:
            if curses.has_colors():
                curses.start_color()
                curses.use_default_colors()
                curses.init_pair(1, curses.COLOR_GREEN, -1)
                curses.init_pair(2, curses.COLOR_CYAN, -1)
                curses.init_pair(3, curses.COLOR_YELLOW, -1)
        except curses.error:
            pass

    def _cleanup(self):
        """Restore terminal to normal state."""
        if self.stdscr:
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

    def draw_char(self, y, x, char, color_pair=0):
        """Draw a single character at position (y, x)."""
        if 0 <= y < self.height and 0 <= x < self.width:
            try:
                if color_pair > 0:
                    self.stdscr.addch(y, x, ord(char), curses.color_pair(color_pair))
                else:
                    self.stdscr.addch(y, x, ord(char))
            except curses.error:
                pass

    def draw_string(self, y, x, text, color_pair=0):
        """Draw a string starting at position (y, x)."""
        if 0 <= y < self.height:
            for i, char in enumerate(text):
                if x + i < self.width:
                    self.draw_char(y, x + i, char, color_pair)

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

    def get_dimensions(self):
        """Return terminal dimensions (height, width)."""
        return self.height, self.width

    def is_valid_position(self, y, x):
        """Check if position is within terminal bounds."""
        return 0 <= y < self.height and 0 <= x < self.width
