"""Main window, navigation, and file-level workflows."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..defaults import create_default_state
from ..engine import GameEngine, GameRuleError
from ..storage import SaveManager
from .screens import (
    BossesScreen,
    DashboardScreen,
    JournalScreen,
    PathsScreen,
    QuestBoardScreen,
    SettingsScreen,
    ShopScreen,
)
from .widgets import CelebrationOverlay, FadeController


class MainWindow(QMainWindow):
    def __init__(self, state: dict, storage: SaveManager):
        super().__init__()
        self.storage = storage
        self.engine = GameEngine(state, self._autosave)
        self.setWindowTitle("Learning RPG")
        self.setMinimumSize(980, 680)
        self.resize(1280, 820)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(210)
        nav_layout = QVBoxLayout(sidebar)
        nav_layout.setContentsMargins(0, 22, 0, 16)
        brand = QLabel("  LEARNING\n  RPG")
        brand.setStyleSheet("font-size:21px;font-weight:800;color:#54e8ff;letter-spacing:2px;padding:8px 12px")
        nav_layout.addWidget(brand)
        tagline = QLabel("  EVIDENCE EARNS POWER")
        tagline.setObjectName("muted")
        tagline.setStyleSheet("font-size:9px;color:#6d8398;padding:0 12px 18px 12px")
        nav_layout.addWidget(tagline)
        self.stack = QStackedWidget()
        self.screens = {
            "dashboard": DashboardScreen(self.engine),
            "quests": QuestBoardScreen(self.engine),
            "paths": PathsScreen(self.engine),
            "bosses": BossesScreen(self.engine),
            "shop": ShopScreen(self.engine),
            "journal": JournalScreen(self.engine),
            "settings": SettingsScreen(self.engine),
        }
        self.nav_buttons: dict[str, QPushButton] = {}
        labels = {
            "dashboard": "◈  Dashboard",
            "quests": "◇  Quest Board",
            "paths": "⌁  Learning Paths",
            "bosses": "◆  Bosses",
            "shop": "◉  Reward Shop",
            "journal": "▤  Journal / Profile",
            "settings": "⚙  Settings",
        }
        for key, screen in self.screens.items():
            self.stack.addWidget(screen)
            button = QPushButton(labels[key])
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, name=key: self.navigate(name))
            self.nav_buttons[key] = button
            nav_layout.addWidget(button)
            screen.changed.connect(self.refresh_all)
        nav_layout.addStretch()
        footer = QLabel("  Learn → Recall\n  Practice → Build")
        footer.setObjectName("muted")
        footer.setStyleSheet("padding:12px;line-height:1.5")
        nav_layout.addWidget(footer)
        layout.addWidget(sidebar)
        layout.addWidget(self.stack, 1)
        self.fade = FadeController()
        self.overlay = CelebrationOverlay(root)
        self.screens["dashboard"].navigate.connect(self.navigate)
        self.screens["quests"].completed.connect(self.celebrate)
        self.screens["bosses"].completed.connect(self.celebrate)
        settings = self.screens["settings"]
        settings.export_requested.connect(self.export_save)
        settings.import_requested.connect(self.import_save)
        settings.reset_requested.connect(self.reset_save)
        self.navigate("dashboard")
        self.refresh_all()

    def navigate(self, name: str) -> None:
        if name not in self.screens:
            return
        screen = self.screens[name]
        screen.refresh()
        self.stack.setCurrentWidget(screen)
        for key, button in self.nav_buttons.items():
            button.setChecked(key == name)
        self.fade.fade_in(screen, self.engine.state["profile"].get("animations_enabled", True))

    def refresh_all(self) -> None:
        for screen in self.screens.values():
            screen.refresh()

    def celebrate(self, level_up: bool) -> None:
        if self.engine.state["profile"].get("animations_enabled", True):
            self.overlay.burst(level_up)

    def _autosave(self, state: dict) -> None:
        try:
            self.storage.save(state)
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Progress could not be saved",
                f"The latest change is still open in the app, but writing the save failed:\n\n{exc}",
            )

    def export_save(self) -> None:
        safe_name = "".join(character if character.isalnum() else "-" for character in self.engine.state["profile"]["player_name"]).strip("-")
        suggested = str(Path.home() / f"learning-rpg-{safe_name or 'player'}-{datetime.now():%Y-%m-%d}.json")
        destination, _ = QFileDialog.getSaveFileName(self, "Export Learning RPG save", suggested, "JSON files (*.json)")
        if not destination:
            return
        try:
            path = self.storage.export_to(destination, self.engine.state)
            QMessageBox.information(self, "Save exported", f"Your progress was exported to:\n{path}")
        except (OSError, GameRuleError) as exc:
            QMessageBox.warning(self, "Export failed", str(exc))

    def import_save(self) -> None:
        source, _ = QFileDialog.getOpenFileName(self, "Import Learning RPG save", str(Path.home()), "JSON files (*.json)")
        if not source:
            return
        try:
            imported = self.storage.read_import(source)
        except GameRuleError as exc:
            QMessageBox.warning(self, "Import rejected", str(exc))
            return
        answer = QMessageBox.warning(
            self,
            "Replace current progress?",
            f"Import the save for “{imported['profile']['player_name']}”?\n\nCurrent progress will be backed up before replacement.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            backup = self.storage.replace_with_import(imported)
            self.engine.state = imported
            self.refresh_all()
            detail = f"\n\nPrevious save backup:\n{backup}" if backup else ""
            QMessageBox.information(self, "Import complete", "Progress was imported successfully." + detail)
        except (OSError, GameRuleError) as exc:
            QMessageBox.warning(self, "Import failed", str(exc))

    def reset_save(self) -> None:
        answer = QMessageBox.warning(
            self,
            "Reset all progress?",
            "This resets XP, Gold, history, timers, and edited content to the bundled defaults.\n\nA backup is created first. Continue?",
            QMessageBox.StandardButton.Reset | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Reset:
            return
        try:
            current_name = self.engine.state["profile"]["player_name"]
            state, backup = self.storage.reset(current_name)
            self.engine.state = state
            self.refresh_all()
            self.navigate("dashboard")
            QMessageBox.information(self, "Progress reset", f"Fresh progress is ready.\n\nPrevious save backup:\n{backup}")
        except OSError as exc:
            QMessageBox.warning(self, "Reset failed", str(exc))

    def closeEvent(self, event):  # noqa: N802 - Qt API
        timer = self.engine.progress["timer"]
        # Restored timers are deliberately paused, never silently running.
        self.engine.update_timer(timer["remaining_seconds"], False)
        event.accept()
