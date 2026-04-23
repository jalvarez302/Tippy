"""Snake animation logic and state management."""

import random
from collections import deque


class SnakeAnimation:
    """Manages snake movement and animation state."""

    DIRECTIONS = [
        (0, 1),   # Right
        (1, 0),   # Down
        (0, -1),  # Left
        (-1, 0),  # Up
    ]

    def __init__(self, height, width, initial_length=4):
        self.height = height
        self.width = width
        self.initial_length = initial_length

        self.body = deque()
        self.direction = random.choice(self.DIRECTIONS)
        self.next_direction = self.direction
        self.frame_count = 0
        self.max_length = initial_length

        self._initialize_snake()

    def _initialize_snake(self):
        """Initialize snake at center of screen."""
        center_y = self.height // 2
        center_x = self.width // 2

        for i in range(self.initial_length):
            self.body.append((center_y, center_x - i))

    def update(self):
        """Update snake position for next frame."""
        self.direction = self.next_direction
        self.frame_count += 1

        head_y, head_x = self.body[0]
        dy, dx = self.direction

        new_y = (head_y + dy) % self.height
        new_x = (head_x + dx) % self.width

        self.body.appendleft((new_y, new_x))

        if len(self.body) > self.max_length:
            self.body.pop()

    def set_direction(self, direction):
        """Set the next direction if valid (avoid reversing into self)."""
        if direction in self.DIRECTIONS:
            opposite_dir = (-direction[0], -direction[1])
            if opposite_dir != self.direction:
                self.next_direction = direction

    def random_direction(self):
        """Change to a random direction."""
        self.next_direction = random.choice(self.DIRECTIONS)

    def grow(self, amount=1):
        """Increase snake length."""
        self.max_length += amount

    def get_head(self):
        """Return head position (y, x)."""
        return self.body[0] if self.body else None

    def get_body(self):
        """Return list of body positions."""
        return list(self.body)

    def reset(self):
        """Reset snake to initial state."""
        self.body.clear()
        self.direction = random.choice(self.DIRECTIONS)
        self.next_direction = self.direction
        self.frame_count = 0
        self.max_length = self.initial_length
        self._initialize_snake()
