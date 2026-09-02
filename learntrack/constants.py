"""Shared constants for game rules and presentation."""

from pathlib import Path

SCHEMA_VERSION = 1
APPLICATION_NAME = "LearnTrack"
ORGANIZATION_NAME = "LearnTrack"
LEGACY_APPLICATION_NAME = "LearningRPG"
LEGACY_ORGANIZATION_NAME = "LearningGuild"

LEVEL_THRESHOLDS = {
    1: 0,
    2: 100,
    3: 250,
    4: 500,
    5: 850,
    6: 1300,
    7: 1900,
    8: 2600,
    9: 3500,
    10: 4600,
}

DIFFICULTIES = {
    "easy": {"label": "Easy", "xp": 10, "gold": 5, "color": "#52e08b"},
    "normal": {"label": "Normal", "xp": 25, "gold": 10, "color": "#3da8ff"},
    "hard": {"label": "Hard", "xp": 50, "gold": 20, "color": "#c36cff"},
    "boss": {"label": "Boss", "xp": 150, "gold": 50, "color": "#ff5370"},
}

PATH_STATUSES = ("backlog", "active", "paused", "completed")
QUEST_STATUSES = ("available", "in_progress", "completed", "archived")
TIMER_DURATIONS = (20, 25, 30)
BREAK_DURATION = 40

PACKAGE_DIR = Path(__file__).resolve().parent
ASSET_DIR = PACKAGE_DIR / "assets"
BACKDROP_PATH = ASSET_DIR / "cyber_guild_backdrop.png"
APP_ICON_PATH = ASSET_DIR / "LearnTrack-cyan-ring-icon.ico"
FONT_PATHS = tuple(
    ASSET_DIR / "fonts" / filename
    for filename in (
        "Inter-Regular.ttf",
        "Inter-Medium.ttf",
        "Inter-SemiBold.ttf",
        "Inter-Bold.ttf",
    )
)
