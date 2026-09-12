"""Terminal loader utilities: an autonomous snake loading animation and a playable snake game."""

from .snake_loader import SnakeLoader
from .game import SnakeGame, play

__all__ = ["SnakeLoader", "SnakeGame", "play"]
__version__ = "0.2.0"
