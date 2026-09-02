"""Readable, validated, and atomic JSON persistence."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QStandardPaths

from .defaults import create_default_state
from .engine import GameRuleError, validate_state


class SaveCorruptionError(RuntimeError):
    """A save could not be loaded and was preserved as a backup."""

    def __init__(self, message: str, backup_path: Path):
        super().__init__(message)
        self.backup_path = backup_path


class SaveManager:
    """Own the local save location and all file replacement operations."""

    def __init__(self, save_path: str | Path | None = None):
        if save_path is None:
            root = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
            save_path = root / "progress.json"
        self.path = Path(save_path).expanduser().resolve()

    @property
    def exists(self) -> bool:
        return self.path.exists()

    def load(self) -> dict | None:
        if not self.path.exists():
            return None
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                state = json.load(handle)
            validate_state(state)
            # A running timer always comes back paused after relaunch.
            state["progress"]["timer"]["running"] = False
            return state
        except (OSError, json.JSONDecodeError, GameRuleError, TypeError, KeyError) as exc:
            backup = self._backup(self.path, "broken")
            raise SaveCorruptionError(
                f"The save could not be loaded: {exc}", backup
            ) from exc

    def save(self, state: dict) -> None:
        validate_state(state)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temp_path = Path(handle.name)
                json.dump(state, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, self.path)
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink()

    def export_to(self, destination: str | Path, state: dict) -> Path:
        validate_state(state)
        destination = Path(destination).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        return destination

    def read_import(self, source: str | Path) -> dict:
        source = Path(source).expanduser().resolve()
        try:
            with source.open("r", encoding="utf-8") as handle:
                state = json.load(handle)
            validate_state(state)
            state["progress"]["timer"]["running"] = False
            return state
        except (OSError, json.JSONDecodeError, GameRuleError, TypeError, KeyError) as exc:
            raise GameRuleError(f"This file is not a valid Learning RPG save: {exc}") from exc

    def replace_with_import(self, state: dict) -> Path | None:
        validate_state(state)
        backup = self._backup(self.path, "pre-import") if self.path.exists() else None
        self.save(state)
        return backup

    def reset(self, player_name: str = "Adventurer") -> tuple[dict, Path | None]:
        backup = self._backup(self.path, "pre-reset") if self.path.exists() else None
        state = create_default_state(player_name)
        self.save(state)
        return state, backup

    @staticmethod
    def _backup(source: Path, label: str) -> Path:
        timestamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S-%f")
        backup = source.with_name(f"{source.stem}.{label}-{timestamp}{source.suffix}.bak")
        shutil.copy2(source, backup)
        return backup
