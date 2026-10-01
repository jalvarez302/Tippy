"""Main snake loading animation controller."""

import time
import signal
from .renderer import TerminalRenderer
from .animation import SnakeAnimation


class SnakeLoader:
    """Displays an animated snake that eats letters from persistent words."""

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
        # Longest word is 13 letters; the snake must stay comfortably
        # shorter than the play area or it degenerates into a solid bar.
        self.length_cap = max(8, min(20, self.play_width // 3))
        self.snake = SnakeAnimation(
            self.play_height,
            self.play_width,
            initial_length=5,
            length_cap=self.length_cap,
        )
        self.word_index = 0
        self.frame_count = 0
        self.letters_eaten = 0
        self.current_target = None
        self.word_letters = {}  # {(y, x): (letter_char, is_eaten)}
        self._setup_word()

    def _setup_signal_handlers(self):
        """Setup graceful exit on interrupt."""
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle keyboard interrupt gracefully."""
        self.stop()

    def _get_current_word(self):
        """Get the current word being eaten."""
        return self.LOADING_WORDS[self.word_index]

    def _setup_word(self):
        """Setup the current word with fixed screen positions."""
        word = self._get_current_word()
        self.word_letters.clear()
        self.letters_eaten = 0
        self.current_target = None
        # Each word is a fresh run: without this the snake only ever grows.
        self.snake.reset_length()

        height, width = self.renderer.get_dimensions()
        center_y = height // 2
        center_x = (width - len(word)) // 2

        for i, letter in enumerate(word):
            play_y = center_y - 1
            play_x = center_x + i - 1
            if 0 <= play_y < self.play_height and 0 <= play_x < self.play_width:
                self.word_letters[(play_y, play_x)] = [letter, False]

        if self.word_letters:
            self.current_target = list(self.word_letters.keys())[0]

    def _check_food_collision(self):
        """Check if snake head ate a letter."""
        head = self.snake.get_head()
        if head in self.word_letters:
            letter_data = self.word_letters[head]
            if not letter_data[1]:
                letter_data[1] = True
                self.snake.grow()
                self.letters_eaten += 1

                if self.letters_eaten >= len(self._get_current_word()):
                    self.word_index = (self.word_index + 1) % len(self.LOADING_WORDS)
                    self._setup_word()
                else:
                    self.current_target = None
                    for pos, (_, eaten) in self.word_letters.items():
                        if not eaten:
                            self.current_target = pos
                            break

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
        if self.current_target:
            self.snake.chase_target(self.current_target[0], self.current_target[1])
        else:
            self.snake.random_direction()

        self.snake.update()
        self.frame_count += 1
        self._check_food_collision()

    def _render(self):
        """Render the current frame."""
        self.renderer.clear()

        height, _ = self.renderer.get_dimensions()

        self.renderer.draw_border(color_pair=2)

        # Letters first: the snake draws over them, so the head stays visible
        # while it is sitting on the letter it is eating.
        for (y, x), (letter, eaten) in self.word_letters.items():
            if not eaten:
                self.renderer.draw_char(y + 1, x + 1, letter, color_pair=3)

        for i, (y, x) in enumerate(self.snake.get_body()):
            char = "●" if i == 0 else "○"
            self.renderer.draw_char(y + 1, x + 1, char, color_pair=1)

        current_word = self._get_current_word()
        progress = f"{self.letters_eaten}/{len(current_word)}"
        status_text = f"{current_word} {progress}"
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
