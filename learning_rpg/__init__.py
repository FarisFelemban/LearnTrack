"""Learning RPG desktop tracker."""

from .engine import GameEngine, GameRuleError
from .storage import SaveCorruptionError, SaveManager

__all__ = ["GameEngine", "GameRuleError", "SaveCorruptionError", "SaveManager"]
__version__ = "1.0.0"
