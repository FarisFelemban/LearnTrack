"""Readable, validated, and atomic JSON persistence."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths

from .defaults import create_default_state
from .engine import GameRuleError, validate_state


class SaveCorruptionError(RuntimeError):
    """A save could not be loaded and was preserved as a backup."""

    def __init__(self, message: str, backup_path: Path):
        super().__init__(message)
        self.backup_path = backup_path


class SaveConflictError(RuntimeError):
    """Saving was stopped to avoid overwriting a cloud-sync conflict."""


class SaveManager:
    """Own the local save location and all file replacement operations."""

    SYNC_PATH_SETTING = "save_data/progress_path"

    def __init__(self, save_path: str | Path | None = None):
        if save_path is None:
            root = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
            save_path = root / "progress.json"
        self.path = Path(save_path).expanduser().resolve()
        self._known_signature = self._file_signature()
        self._session_backup: Path | None = None

    @property
    def exists(self) -> bool:
        return self.path.exists()

    @classmethod
    def configured_path(cls) -> Path | None:
        """Return the user-selected save path, if one has been configured."""
        value = QSettings().value(cls.SYNC_PATH_SETTING)
        return Path(value).expanduser().resolve() if isinstance(value, str) and value else None

    @classmethod
    def remember_path(cls, path: str | Path) -> None:
        """Remember a chosen save path without putting device settings in progress.json."""
        settings = QSettings()
        settings.setValue(cls.SYNC_PATH_SETTING, str(Path(path).expanduser().resolve()))
        settings.sync()

    @property
    def last_updated(self) -> datetime | None:
        """Return the current save's local modification time, if it exists."""
        try:
            return datetime.fromtimestamp(self.path.stat().st_mtime).astimezone()
        except FileNotFoundError:
            return None

    @property
    def session_backup(self) -> Path | None:
        """Return the automatic restore point created during this app session."""
        return self._session_backup

    def migrate_from(self, legacy_path: str | Path) -> bool:
        """Copy a legacy save into this manager's location without removing it."""
        legacy_path = Path(legacy_path).expanduser().resolve()
        if self.exists or not legacy_path.exists() or legacy_path == self.path:
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "wb",
                dir=self.path.parent,
                prefix=f".{self.path.name}.migration-",
                suffix=".tmp",
                delete=False,
            ) as destination, legacy_path.open("rb") as source:
                temp_path = Path(destination.name)
                shutil.copyfileobj(source, destination)
                destination.flush()
                os.fsync(destination.fileno())
            os.replace(temp_path, self.path)
            self._known_signature = self._file_signature()
            return True
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink()

    def load(self) -> dict | None:
        if not self.path.exists():
            return None
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                state = json.load(handle)
            validate_state(state)
            # A running timer always comes back paused after relaunch.
            state["progress"]["timer"]["running"] = False
            self._known_signature = self._file_signature()
            return state
        except (OSError, json.JSONDecodeError, GameRuleError, TypeError, KeyError) as exc:
            backup = self._backup(self.path, "broken")
            raise SaveCorruptionError(
                f"The save could not be loaded: {exc}", backup
            ) from exc

    def save(self, state: dict) -> None:
        """Save state unless a cloud service changed the file since it was loaded."""
        validate_state(state)
        self._ensure_sync_safe()
        if self.path.exists() and self._session_backup is None:
            self._session_backup = self._backup(self.path, "pre-save")
        self._write(state)

    def _write(self, state: dict) -> None:
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
            self._known_signature = self._file_signature()
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
            raise GameRuleError(f"This file is not a valid LearnTrack save: {exc}") from exc

    def replace_with_import(self, state: dict) -> Path | None:
        validate_state(state)
        self._ensure_sync_safe()
        backup = self._backup(self.path, "pre-import") if self.path.exists() else None
        self._write(state)
        return backup

    def reset(self, player_name: str = "Adventurer") -> tuple[dict, Path | None]:
        self._ensure_sync_safe()
        backup = self._backup(self.path, "pre-reset") if self.path.exists() else None
        state = create_default_state(player_name)
        self._write(state)
        return state, backup

    def _ensure_sync_safe(self) -> None:
        conflicts = self._conflict_copies()
        if conflicts:
            names = ", ".join(conflict.name for conflict in conflicts)
            raise SaveConflictError(
                "Saving was stopped because a cloud-sync conflict copy was found: "
                f"{names}. Review the conflicting files before continuing."
            )
        current_signature = self._file_signature()
        if self._known_signature is not None and current_signature != self._known_signature:
            raise SaveConflictError(
                "Saving was stopped because progress.json changed outside LearnTrack. "
                "A newer cloud-synced version may be available."
            )

    def _conflict_copies(self) -> list[Path]:
        if not self.path.parent.exists():
            return []
        return sorted(
            entry
            for entry in self.path.parent.glob(f"{self.path.stem}*.json")
            if entry != self.path and "conflict" in entry.stem.casefold()
        )

    def _file_signature(self) -> tuple[int, int] | None:
        try:
            stat = self.path.stat()
        except FileNotFoundError:
            return None
        return stat.st_mtime_ns, stat.st_size

    @staticmethod
    def _backup(source: Path, label: str) -> Path:
        timestamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S-%f")
        backup = source.with_name(f"{source.stem}.{label}-{timestamp}{source.suffix}.bak")
        shutil.copy2(source, backup)
        return backup
