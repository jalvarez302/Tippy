"""Main snake loading animation controller."""

import time
import signal
from .renderer import TerminalRenderer
from .animation import SnakeAnimation


class SnakeLoader:
    """Displays an animated snake during loading operations."""

    LOADING_WORDS = [
        "Loading",
        "Contemplating",
        "Processing",
        "Thinking",
        "Concocting",
        "Analyzing",
        "Computing",
        "Orchestrating",
    ]

    def __init__(self, fps=10, message="Loading..."):
        self.fps = fps
        self.message = message
        self.renderer = TerminalRenderer()
        self.running = False
        self._setup_signal_handlers()

        height, width = self.renderer.get_dimensions()
        self.play_height = max(1, height - 3)
        self.play_width = max(1, width - 2)
        self.snake = SnakeAnimation(
            self.play_height, self.play_width, initial_length=5
        )
        self.word_index = 0
        self.frame_count = 0

    def _setup_signal_handlers(self):
        """Setup graceful exit on interrupt."""
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle keyboard interrupt gracefully."""
        self.stop()

    def start(self, duration=None):
        """Start the loading animation.

        Args:
            duration: Optional duration in seconds. If None, runs until stop() is called.
        """
        self.running = True
        start_time = time.time()

        try:
            while self.running:
                if duration and (time.time() - start_time) > duration:
                    break

                self._update()
                self._render()
                time.sleep(1 / self.fps)

        finally:
            self.stop()

    def stop(self):
        """Stop the animation."""
        self.running = False
        self.renderer.clear()
        self.renderer.refresh()

    def _update(self):
        """Update animation state."""
        self.snake.random_direction()
        self.snake.update()
        self.frame_count += 1

        words_per_cycle = self.fps * 2
        if self.frame_count % words_per_cycle == 0:
            self.word_index = (self.word_index + 1) % len(self.LOADING_WORDS)

    def _render(self):
        """Render the current frame."""
        self.renderer.clear()

        height, _ = self.renderer.get_dimensions()

        self.renderer.draw_border(color_pair=2)

        for i, (y, x) in enumerate(self.snake.get_body()):
            screen_y = y + 1
            screen_x = x + 1
            if i == 0:
                self.renderer.draw_char(screen_y, screen_x, "●", color_pair=1)
            else:
                self.renderer.draw_char(screen_y, screen_x, "○", color_pair=1)

        current_word = self.LOADING_WORDS[self.word_index]
        status_text = f"{current_word}..."
        self.renderer.center_text(status_text, y=height - 2)

        self.renderer.refresh()

    def run_demo(self, duration=10):
        """Run a demo of the loading animation.

        Args:
            duration: Duration in seconds to run the demo.
        """
        print(f"Starting snake loader demo for {duration} seconds...")
        print("Press Ctrl+C to stop.")
        self.start(duration=duration)
        print("Demo complete!")
