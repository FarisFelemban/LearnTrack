"""Application setup and first-run/corruption recovery flows."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QStandardPaths, Qt
from PySide6.QtGui import QFont, QFontDatabase, QIcon
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from .constants import (
    APPLICATION_NAME,
    APP_ICON_PATH,
    FONT_PATHS,
    LEGACY_APPLICATION_NAME,
    LEGACY_ORGANIZATION_NAME,
    ORGANIZATION_NAME,
)
from .defaults import create_default_state
from .storage import SaveCorruptionError, SaveManager
from .ui.dialogs import NameSetupDialog
from .ui.main_window import MainWindow
from .ui.theme import APP_STYLE, WindowsTitleBarStyler


def create_application(argv: list[str] | None = None) -> QApplication:
    # Resolve the old location before switching Qt to LearnTrack's new identity.
    QCoreApplication.setOrganizationName(LEGACY_ORGANIZATION_NAME)
    QCoreApplication.setApplicationName(LEGACY_APPLICATION_NAME)
    app = QApplication.instance() or QApplication(argv if argv is not None else sys.argv)
    legacy_save_path = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / "progress.json"
    QCoreApplication.setOrganizationName(ORGANIZATION_NAME)
    QCoreApplication.setApplicationName(APPLICATION_NAME)
    app.setProperty("legacySavePath", str(legacy_save_path))
    for font_path in FONT_PATHS:
        QFontDatabase.addApplicationFont(str(font_path))
    app.setApplicationDisplayName("LearnTrack")
    app.setWindowIcon(QIcon(str(APP_ICON_PATH)))
    app.setStyle("Fusion")
    application_font = QFont()
    application_font.setFamilies(["Inter", "Segoe UI Symbol"])
    app.setFont(application_font)
    app.setStyleSheet(APP_STYLE)
    title_bar_styler = WindowsTitleBarStyler(app)
    app.installEventFilter(title_bar_styler)
    app.setProperty("titleBarStyler", title_bar_styler)
    return app


def load_or_create_state(storage: SaveManager, parent=None, legacy_save_path: str | Path | None = None) -> dict | None:
    if legacy_save_path is not None:
        try:
            storage.migrate_from(legacy_save_path)
        except OSError as exc:
            QMessageBox.critical(
                parent,
                "Progress migration failed",
                "LearnTrack could not copy your existing Learning RPG progress. "
                f"The original save has not been removed.\n\n{exc}",
            )
            return None
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
    state = load_or_create_state(storage, legacy_save_path=app.property("legacySavePath"))
    if state is None:
        return 0
    window = MainWindow(state, storage)
    window.show()
    window.raise_()
    window.activateWindow()
    return app.exec()
