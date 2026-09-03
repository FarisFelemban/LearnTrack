"""LearnTrack desktop learning tracker."""

from .engine import GameEngine, GameRuleError
from .storage import SaveConflictError, SaveCorruptionError, SaveManager

__all__ = ["GameEngine", "GameRuleError", "SaveConflictError", "SaveCorruptionError", "SaveManager"]
__version__ = "1.0.0"
