"""Terminal snake: a loading animation, a game, and a playable thinking screen."""

from .snake_loader import SnakeLoader
from .game import SnakeGame, play
from .thinking import ThinkingSnake, Worker, think
from .words import THINKING_WORDS

__all__ = [
    "SnakeLoader",
    "SnakeGame",
    "play",
    "ThinkingSnake",
    "Worker",
    "think",
    "THINKING_WORDS",
]
__version__ = "0.3.0"
