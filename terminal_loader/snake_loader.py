"""Main snake loading animation controller."""

import time
import signal
import random
from .renderer import TerminalRenderer
from .animation import SnakeAnimation


class SnakeLoader:
    """Displays an animated snake that eats letters to grow."""

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
        self.letters_eaten = 0
        self.food = {}  # {(y, x): letter_char}
        self._spawn_food()

    def _setup_signal_handlers(self):
        """Setup graceful exit on interrupt."""
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle keyboard interrupt gracefully."""
        self.stop()

    def _get_current_word(self):
        """Get the current word being eaten."""
        return self.LOADING_WORDS[self.word_index]

    def _spawn_food(self):
        """Spawn food letters for the current word."""
        word = self._get_current_word()
        self.food.clear()
        self.letters_eaten = 0

        for letter in word:
            while True:
                y = random.randint(0, self.play_height - 1)
                x = random.randint(0, self.play_width - 1)
                if (y, x) not in self.food and (y, x) not in self.snake.get_body():
                    self.food[(y, x)] = letter
                    break

    def _check_food_collision(self):
        """Check if snake head ate food, return True if food eaten."""
        head = self.snake.get_head()
        if head in self.food:
            self.snake.grow()
            del self.food[head]
            self.letters_eaten += 1

            word = self._get_current_word()
            if self.letters_eaten >= len(word):
                self.word_index = (self.word_index + 1) % len(self.LOADING_WORDS)
                self._spawn_food()

            return True
        return False

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
        head_y, head_x = self.snake.get_head()

        if self.food:
            target = random.choice(list(self.food.keys()))
            self.snake.chase_target(target[0], target[1])
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

        for i, (y, x) in enumerate(self.snake.get_body()):
            screen_y = y + 1
            screen_x = x + 1
            if i == 0:
                self.renderer.draw_char(screen_y, screen_x, "●", color_pair=1)
            else:
                self.renderer.draw_char(screen_y, screen_x, "○", color_pair=1)

        for (y, x), letter in self.food.items():
            screen_y = y + 1
            screen_x = x + 1
            self.renderer.draw_char(screen_y, screen_x, letter, color_pair=3)

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
