"""Snake animation logic and state management."""

import random
from collections import deque


class SnakeAnimation:
    """Manages snake movement and animation state.

    Handles both the autonomous loader snake (wrapping, capped length) and the
    player-controlled game snake (solid walls, unbounded growth, self collision).
    """

    DIRECTIONS = [
        (0, 1),   # Right
        (1, 0),   # Down
        (0, -1),  # Left
        (-1, 0),  # Up
    ]

    # Reasons update() can report a death.
    ALIVE = None
    DIED_WALL = "wall"
    DIED_SELF = "self"

    def __init__(self, height, width, initial_length=4, wrap=True, length_cap=None):
        self.height = height
        self.width = width
        self.initial_length = initial_length
        self.wrap = wrap
        self.length_cap = length_cap

        self.body = deque()
        self.occupied = set()
        # Body extends left of the head, so Right is the only safe opening
        # heading; anything else walks the snake into its own neck on frame 1.
        self.direction = (0, 1)
        self.next_direction = self.direction
        self.frame_count = 0
        self.max_length = initial_length
        self.death_reason = self.ALIVE

        self._initialize_snake()

    def _initialize_snake(self):
        """Initialize snake at center of screen."""
        center_y = self.height // 2
        center_x = self.width // 2

        self.body.clear()
        self.occupied.clear()
        for i in range(self.initial_length):
            x = center_x - i
            if not self.wrap:
                x = max(0, x)
            segment = (center_y, x)
            self.body.append(segment)
            self.occupied.add(segment)

    def update(self):
        """Advance the snake one step.

        Returns:
            True if the snake is still alive, False if it just died. A wrapping
            snake never dies, so it always returns True.
        """
        self.direction = self.next_direction
        self.frame_count += 1

        head_y, head_x = self.body[0]
        dy, dx = self.direction
        new_y = head_y + dy
        new_x = head_x + dx

        if self.wrap:
            new_y %= self.height
            new_x %= self.width
        elif not (0 <= new_y < self.height and 0 <= new_x < self.width):
            self.death_reason = self.DIED_WALL
            return False

        new_head = (new_y, new_x)

        # The tail cell frees up on this same step unless the snake is growing
        # into it, so running straight into your own tail is legal.
        growing = len(self.body) < self.max_length
        tail = self.body[-1]
        if new_head in self.occupied and not (new_head == tail and not growing):
            if not self.wrap:
                self.death_reason = self.DIED_SELF
                return False

        self.body.appendleft(new_head)
        self.occupied.add(new_head)

        if len(self.body) > self.max_length:
            removed = self.body.pop()
            if removed not in self.body:
                self.occupied.discard(removed)

        return True

    def chase_target(self, target_y, target_x):
        """Move toward target using a Manhattan distance heuristic."""
        head_y, head_x = self.body[0]

        candidates = []
        for index, (dy, dx) in enumerate(self.DIRECTIONS):
            new_y = head_y + dy
            new_x = head_x + dx
            if self.wrap:
                new_y %= self.height
                new_x %= self.width
            elif not (0 <= new_y < self.height and 0 <= new_x < self.width):
                continue
            dist = abs(new_y - target_y) + abs(new_x - target_x)
            candidates.append((dist, index, (dy, dx)))

        if candidates:
            candidates.sort()
            self.next_direction = candidates[0][2]

    def random_direction(self):
        """Pick a new random direction, avoiding immediate reversal."""
        opposite = (-self.direction[0], -self.direction[1])
        valid = [d for d in self.DIRECTIONS if d != opposite]
        self.next_direction = random.choice(valid)

    def set_direction(self, direction):
        """Queue a direction for the next update, rejecting a 180 degree turn.

        Compares against the direction actually travelled last step, not the
        queued one, so two fast key presses in one frame cannot reverse the
        snake into its own neck.

        Returns:
            True if the direction was accepted.
        """
        if direction not in self.DIRECTIONS:
            return False
        if len(self.body) > 1 and direction == (-self.direction[0], -self.direction[1]):
            return False
        self.next_direction = direction
        return True

    def grow(self, amount=1):
        """Increase snake length, respecting length_cap when one is set."""
        self.max_length += amount
        if self.length_cap is not None:
            self.max_length = min(self.max_length, self.length_cap)

    def reset_length(self):
        """Trim the snake back to its starting length."""
        self.max_length = self.initial_length
        while len(self.body) > self.max_length:
            removed = self.body.pop()
            if removed not in self.body:
                self.occupied.discard(removed)

    def is_occupied(self, y, x):
        """Return True if a cell is covered by the snake."""
        return (y, x) in self.occupied

    def get_head(self):
        """Return head position (y, x)."""
        return self.body[0] if self.body else None

    def get_body(self):
        """Return list of body positions."""
        return list(self.body)

    def reset(self):
        """Reset snake to initial state."""
        self.direction = (0, 1)
        self.next_direction = self.direction
        self.frame_count = 0
        self.max_length = self.initial_length
        self.death_reason = self.ALIVE
        self._initialize_snake()
