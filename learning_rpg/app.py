"""Application setup and first-run/corruption recovery flows."""

from __future__ import annotations

import sys

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from .defaults import create_default_state
from .storage import SaveCorruptionError, SaveManager
from .ui.dialogs import NameSetupDialog
from .ui.main_window import MainWindow
from .ui.theme import APP_STYLE


def create_application(argv: list[str] | None = None) -> QApplication:
    QCoreApplication.setOrganizationName("LearningGuild")
    QCoreApplication.setApplicationName("LearningRPG")
    app = QApplication.instance() or QApplication(argv if argv is not None else sys.argv)
    app.setApplicationDisplayName("Learning RPG")
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)
    return app


def load_or_create_state(storage: SaveManager, parent=None) -> dict | None:
    try:
        state = storage.load()
    except SaveCorruptionError as exc:
        answer = QMessageBox.critical(
            parent,
            "Save file needs attention",
            f"{exc}\n\nThe broken file was preserved at:\n{exc.backup_path}\n\nStart with clean progress?",
            QMessageBox.StandardButton.Reset | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Reset:
            return None
        state = create_default_state()
        storage.save(state)
        return state
    if state is not None:
        return state
    dialog = NameSetupDialog(parent)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    state = create_default_state(dialog.player_name)
    storage.save(state)
    return state


def run() -> int:
    app = create_application()
    storage = SaveManager()
    state = load_or_create_state(storage)
    if state is None:
        return 0
    window = MainWindow(state, storage)
    window.show()
    window.raise_()
    window.activateWindow()
    return app.exec()
