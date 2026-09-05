"""Main window, navigation, and file-level workflows."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from ..defaults import create_default_state
from ..engine import GameEngine, GameRuleError
from ..storage import SaveConflictError, SaveCorruptionError, SaveManager
from .screens import (
    BossesScreen,
    DashboardScreen,
    JournalScreen,
    PathsScreen,
    QuestBoardScreen,
    SettingsScreen,
    ShopScreen,
)
from .widgets import CelebrationOverlay, MiniTimerWindow


def _quest_board_icon() -> QIcon:
    """Draw a board containing two wavy list lines."""

    def draw(color: str) -> QPixmap:
        pixmap = QPixmap(22, 22)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(color), 1.7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawRoundedRect(QRectF(2.5, 3.5, 17, 15), 2, 2)
        for y in (8.5, 13.5):
            wave = QPainterPath(QPointF(5.5, y))
            wave.cubicTo(7, y - 1.5, 8.5, y + 1.5, 10, y)
            wave.cubicTo(11.5, y - 1.5, 13, y + 1.5, 14.5, y)
            wave.cubicTo(15.3, y - 0.7, 16, y - 0.5, 16.5, y)
            painter.drawPath(wave)
        painter.end()
        return pixmap

    icon = QIcon()
    icon.addPixmap(draw("#89a3b9"), QIcon.Mode.Normal, QIcon.State.Off)
    icon.addPixmap(draw("#58e8ff"), QIcon.Mode.Normal, QIcon.State.On)
    return icon


def _hamburger_icon() -> QIcon:
    """Draw the familiar three-line menu icon without relying on a font glyph."""

    def draw(color: str) -> QPixmap:
        pixmap = QPixmap(22, 22)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(color), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for y in (6, 11, 16):
            painter.drawLine(QPointF(3.5, y), QPointF(18.5, y))
        painter.end()
        return pixmap

    icon = QIcon()
    icon.addPixmap(draw("#89a3b9"), QIcon.Mode.Normal, QIcon.State.Off)
    icon.addPixmap(draw("#58e8ff"), QIcon.Mode.Normal, QIcon.State.On)
    return icon


class MainWindow(QMainWindow):
    def __init__(self, state: dict, storage: SaveManager):
        super().__init__()
        self.storage = storage
        self._saving_paused_reason: str | None = None
        self.engine = GameEngine(state, self._autosave)
        self.setWindowTitle("LearnTrack")
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
            "quests": "Quest Board",
            "paths": "⌁  Learning Paths",
            "bosses": "◆  Bosses",
            "shop": "◉  Reward Shop",
            "journal": "▤  Journal / Profile",
            "settings": "Settings",
        }
        for key, screen in self.screens.items():
            self.stack.addWidget(screen)
            button = QPushButton(labels[key])
            button.setObjectName("navButton")
            button.setCheckable(True)
            if key == "quests":
                button.setIcon(_quest_board_icon())
                button.setIconSize(QSize(19, 19))
            elif key == "settings":
                button.setIcon(_hamburger_icon())
                button.setIconSize(QSize(19, 19))
            button.clicked.connect(lambda checked=False, name=key: self.navigate(name))
            self.nav_buttons[key] = button
            nav_layout.addWidget(button)
            screen.changed.connect(self.refresh_all)
        nav_layout.addStretch()
        layout.addWidget(sidebar)
        layout.addWidget(self.stack, 1)
        self.overlay = CelebrationOverlay(root)
        self.mini_timer = MiniTimerWindow()
        self.mini_timer.hide_requested.connect(self._hide_mini_timer)
        self._mini_timer_hidden = False
        self._mini_timer_positioned = False
        self._setup_tray_icon()
        self.screens["dashboard"].navigate.connect(self.navigate)
        timer_panel = self.screens["dashboard"].timer_panel
        self.mini_timer.toggle_requested.connect(timer_panel.toggle)
        timer_panel.timer_started.connect(self._timer_started)
        timer_panel.timer_finished.connect(self._timer_finished)
        timer_panel.mini_timer_requested.connect(self._show_mini_timer)
        self.screens["quests"].completed.connect(self.celebrate)
        self.screens["bosses"].completed.connect(self.celebrate)
        settings = self.screens["settings"]
        settings.export_requested.connect(self.export_save)
        settings.import_requested.connect(self.import_save)
        settings.reset_requested.connect(self.reset_save)
        settings.sync_folder_requested.connect(self.choose_sync_folder)
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

    def refresh_all(self) -> None:
        for screen in self.screens.values():
            screen.refresh()
        self._refresh_save_status()
        self._sync_timer_surfaces()

    def _setup_tray_icon(self) -> None:
        self.tray_icon = QSystemTrayIcon(self.windowIcon(), self)
        self.tray_icon.setToolTip("LearnTrack — Timer paused")
        tray_menu = QMenu(self)

        show_app_action = QAction("Show LearnTrack", self)
        show_app_action.triggered.connect(self._show_main_window)
        tray_menu.addAction(show_app_action)

        self.show_mini_action = QAction("Show mini timer", self)
        self.show_mini_action.triggered.connect(self._show_mini_timer)
        tray_menu.addAction(self.show_mini_action)
        tray_menu.addSeparator()

        quit_action = QAction("Quit LearnTrack", self)
        quit_action.triggered.connect(self.close)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._tray_activated)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon.show()

    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_main_window()

    def _show_main_window(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _timer_started(self) -> None:
        self._mini_timer_hidden = False
        self._show_mini_timer()

    def _timer_finished(self, mode: str) -> None:
        mode_name = "Break" if mode == "break" else "Focus"
        self._sync_timer_surfaces()
        if self.tray_icon.isVisible() and QSystemTrayIcon.supportsMessages():
            self.tray_icon.showMessage(
                "LearnTrack timer finished",
                f"Your {mode_name.lower()} timer is complete.",
                QSystemTrayIcon.MessageIcon.Information,
                10_000,
            )
        QApplication.alert(self, 5_000)

    def _sync_timer_surfaces(self) -> None:
        timer = self.engine.progress["timer"]
        remaining = timer["remaining_seconds"]
        mode = timer["mode"]
        running = timer["running"]
        self.mini_timer.set_timer(remaining, mode, running)

        minutes, seconds = divmod(remaining, 60)
        mode_name = "Break" if mode == "break" else "Focus"
        if remaining == 0:
            tooltip = f"LearnTrack — {mode_name} timer complete"
        elif running:
            tooltip = f"LearnTrack — {mode_name} {minutes:02d}:{seconds:02d} remaining"
        else:
            tooltip = f"LearnTrack — Timer paused at {minutes:02d}:{seconds:02d}"
        self.tray_icon.setToolTip(tooltip)

        if running and not self._mini_timer_hidden and not self.mini_timer.isVisible():
            self._show_mini_timer()

    def _position_mini_timer(self) -> None:
        if self._mini_timer_positioned:
            return
        available = self.screen().availableGeometry()
        self.mini_timer.move(
            available.right() - self.mini_timer.width() - 24,
            available.top() + 24,
        )
        self._mini_timer_positioned = True

    def _show_mini_timer(self) -> None:
        self._mini_timer_hidden = False
        self._position_mini_timer()
        self.mini_timer.show()
        self._sync_timer_surfaces()

    def _hide_mini_timer(self) -> None:
        self._mini_timer_hidden = True
        self.mini_timer.hide()

    def celebrate(self, level_up: bool) -> None:
        if self.engine.state["profile"].get("animations_enabled", True):
            self.overlay.burst(level_up)

    def _autosave(self, state: dict) -> None:
        if self._saving_paused_reason:
            return
        try:
            self.storage.save(state)
            self._refresh_save_status()
        except SaveConflictError as exc:
            self._saving_paused_reason = str(exc)
            self._refresh_save_status()
            QMessageBox.warning(
                self,
                "Cloud save needs attention",
                f"{exc}\n\nNo changes were written. Export your current in-app progress before resolving the conflict.",
            )
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Progress could not be saved",
                f"The latest change is still open in the app, but writing the save failed:\n\n{exc}",
            )

    def _refresh_save_status(self) -> None:
        updated = self.storage.last_updated
        if self._saving_paused_reason:
            status = "Saving paused — cloud conflict detected."
        elif updated is None:
            status = "No progress save has been created yet."
        else:
            status = f"Last saved: {updated:%b %d, %Y at %I:%M %p}"
        self.screens["settings"].set_save_status(status, self.storage.path, self.storage.session_backup)

    def choose_sync_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Choose Dropbox, Google Drive, or another synced folder",
            str(self.storage.path.parent),
        )
        if not folder:
            return
        destination = Path(folder).expanduser().resolve() / "progress.json"
        if destination == self.storage.path:
            QMessageBox.information(self, "Sync folder unchanged", "LearnTrack already saves in this folder.")
            return
        synced_storage = SaveManager(destination)
        if synced_storage.exists:
            try:
                synced_state = synced_storage.load()
            except SaveCorruptionError as exc:
                QMessageBox.warning(self, "Synced save could not be used", str(exc))
                return
            answer = QMessageBox.warning(
                self,
                "Use existing synced progress?",
                "This folder already contains a LearnTrack save. Use that shared progress on this device?\n\n"
                "Your current device save will remain in its old location as a backup.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            self.storage = synced_storage
            self.engine.state = synced_state
            self._saving_paused_reason = None
            SaveManager.remember_path(destination)
            self.refresh_all()
            QMessageBox.information(self, "Synced save selected", f"LearnTrack now uses:\n{destination}")
            return
        try:
            synced_storage.save(self.engine.state)
            self.storage = synced_storage
            self._saving_paused_reason = None
            SaveManager.remember_path(destination)
            self.refresh_all()
            QMessageBox.information(
                self,
                "Synced save selected",
                f"Your progress was copied to:\n{destination}\n\nThe original local save was kept as a backup.",
            )
        except (OSError, GameRuleError, SaveConflictError) as exc:
            QMessageBox.warning(self, "Could not choose synced folder", str(exc))

    def export_save(self) -> None:
        safe_name = "".join(character if character.isalnum() else "-" for character in self.engine.state["profile"]["player_name"]).strip("-")
        suggested = str(Path.home() / f"learntrack-{safe_name or 'player'}-{datetime.now():%Y-%m-%d}.json")
        destination, _ = QFileDialog.getSaveFileName(self, "Export LearnTrack save", suggested, "JSON files (*.json)")
        if not destination:
            return
        try:
            path = self.storage.export_to(destination, self.engine.state)
            QMessageBox.information(self, "Save exported", f"Your progress was exported to:\n{path}")
        except (OSError, GameRuleError) as exc:
            QMessageBox.warning(self, "Export failed", str(exc))

    def import_save(self) -> None:
        source, _ = QFileDialog.getOpenFileName(self, "Import LearnTrack save", str(Path.home()), "JSON files (*.json)")
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
            self._saving_paused_reason = None
            self.refresh_all()
            detail = f"\n\nPrevious save backup:\n{backup}" if backup else ""
            QMessageBox.information(self, "Import complete", "Progress was imported successfully." + detail)
        except (OSError, GameRuleError, SaveConflictError) as exc:
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
            self._saving_paused_reason = None
            self.refresh_all()
            self.navigate("dashboard")
            QMessageBox.information(self, "Progress reset", f"Fresh progress is ready.\n\nPrevious save backup:\n{backup}")
        except (OSError, SaveConflictError) as exc:
            QMessageBox.warning(self, "Reset failed", str(exc))

    def closeEvent(self, event):  # noqa: N802 - Qt API
        self.screens["dashboard"].timer_panel.clock.stop()
        timer = self.engine.progress["timer"]
        # Restored timers are deliberately paused, never silently running.
        self.engine.update_timer(timer["remaining_seconds"], False)
        self.mini_timer.shutdown()
        self.tray_icon.hide()
        event.accept()
