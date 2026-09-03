import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox, QPushButton

from learntrack.app import create_application
from learntrack.constants import APP_ICON_PATH
from learntrack.defaults import create_default_state
from learntrack.storage import SaveManager
from learntrack.ui.dialogs import (
    BossDialog,
    CompletionDialog,
    PathDialog,
    QuestDialog,
    QuestImportDialog,
    RewardDialog,
    TimerPresetsDialog,
)
from learntrack.ui.main_window import MainWindow


class UISmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_application([])

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = create_default_state("UI Tester")
        self.storage = SaveManager(Path(self.temp.name) / "progress.json")
        self.storage.save(self.state)
        self.window = MainWindow(self.state, self.storage)
        self.addCleanup(self.window.close)

    def test_application_uses_bundled_icon(self):
        self.assertTrue(APP_ICON_PATH.is_file())
        self.assertFalse(self.app.windowIcon().isNull())

    def test_all_navigation_screens_show(self):
        self.window.show()
        for name, screen in self.window.screens.items():
            self.window.navigate(name)
            self.app.processEvents()
            self.assertIs(self.window.stack.currentWidget(), screen)
            self.assertTrue(self.window.nav_buttons[name].isChecked())

    def test_core_dialogs_construct(self):
        paths = self.state["paths"]
        dialogs = [
            PathDialog(self.window),
            QuestDialog(paths, self.window, self.state["quests"][0]),
            BossDialog(paths, self.window, self.state["bosses"][0]),
            RewardDialog(self.window, self.state["shop_rewards"][0]),
            CompletionDialog(self.state["quests"][0], self.window),
            CompletionDialog(self.state["bosses"][0], self.window, boss=True),
            TimerPresetsDialog((20, 25, 30), 40, self.window),
        ]
        for dialog in dialogs:
            dialog.show()
            self.app.processEvents()
            self.assertTrue(dialog.isVisible())
            dialog.close()

    def test_dashboard_contains_bundled_backdrop_and_seeded_content(self):
        dashboard = self.window.screens["dashboard"]
        self.assertFalse(dashboard.hero.pixmap.isNull())
        self.assertEqual(len(self.state["quests"]), 18)
        self.assertEqual(self.state["quests"][0]["title"], "Understand what a route is")
        self.assertEqual(self.state["quests"][-1]["title"], "Use basic dependency injection in one useful place")

    def test_resizing_and_live_timer_tick(self):
        self.window.show()
        self.window.resize(1024, 700)
        self.app.processEvents()
        self.assertEqual((self.window.width(), self.window.height()), (1024, 700))
        timer_panel = self.window.screens["dashboard"].timer_panel
        timer_panel.choose("focus", 20)
        timer_panel.toggle()
        timer_panel._tick()
        self.assertEqual(self.state["progress"]["timer"]["remaining_seconds"], 1199)
        self.assertTrue(self.state["progress"]["timer"]["running"])
        self.assertEqual((self.state["progress"]["xp"], self.state["progress"]["gold"]), (0, 0))

    def test_custom_timer_is_saved_paused(self):
        timer_panel = self.window.screens["dashboard"].timer_panel
        timer_panel.begin_duration_edit()
        self.assertFalse(timer_panel.dial.editor.isHidden())
        timer_panel.apply_edited_duration("47:30")

        timer = self.state["progress"]["timer"]
        self.assertEqual(timer["duration_seconds"], 47 * 60 + 30)
        self.assertEqual(timer["remaining_seconds"], 47 * 60 + 30)
        self.assertFalse(timer["running"])
        self.assertTrue(timer_panel.dial.editor.isHidden())
        self.assertEqual(self.storage.load()["progress"]["timer"], timer)

    def test_invalid_inline_timer_value_stays_editable(self):
        timer_panel = self.window.screens["dashboard"].timer_panel
        timer_panel.begin_duration_edit()
        timer_panel.apply_edited_duration("10:99")

        self.assertFalse(timer_panel.dial.editor.isHidden())
        self.assertTrue(timer_panel.dial.editor.property("invalid"))
        timer_panel.dial.leave_edit_mode()

    def test_clicking_outside_saves_and_closes_timer_editor(self):
        self.window.show()
        timer_panel = self.window.screens["dashboard"].timer_panel
        timer_panel.begin_duration_edit()
        timer_panel.dial.editor.setText("12:34")

        QTest.mouseClick(timer_panel.start_button, Qt.MouseButton.LeftButton)
        self.app.processEvents()

        timer = self.state["progress"]["timer"]
        self.assertTrue(timer_panel.dial.editor.isHidden())
        self.assertEqual(timer["duration_seconds"], 12 * 60 + 34)
        self.assertTrue(timer["running"])

    def test_clicking_outside_discards_an_invalid_timer_value(self):
        self.window.show()
        dashboard = self.window.screens["dashboard"]
        timer_panel = dashboard.timer_panel
        original_timer = dict(self.state["progress"]["timer"])
        timer_panel.begin_duration_edit()
        timer_panel.dial.editor.setText("not a time")

        QTest.mouseClick(dashboard.greeting, Qt.MouseButton.LeftButton)
        self.app.processEvents()

        self.assertTrue(timer_panel.dial.editor.isHidden())
        self.assertEqual(self.state["progress"]["timer"]["duration_seconds"], original_timer["duration_seconds"])

    def test_reward_shop_hides_default_row_numbers(self):
        shop = self.window.screens["shop"]
        self.assertTrue(shop.table.verticalHeader().isHidden())
        self.assertTrue(shop.history.verticalHeader().isHidden())

    def test_player_journal_hides_default_row_numbers(self):
        journal = self.window.screens["journal"]
        self.assertTrue(journal.claims_table.verticalHeader().isHidden())
        self.assertTrue(journal.reward_table.verticalHeader().isHidden())

    def test_player_journal_labels_reward_free_replays_separately(self):
        quest = self.state["quests"][0]
        self.window.engine.start_run("quest", quest["id"])
        self.window.engine.complete_quest(quest["id"], "Original completion")
        self.window.engine.reset_quest(quest["id"])
        self.window.engine.start_run("quest", quest["id"])
        self.window.engine.complete_quest(quest["id"], "Replay completion")
        journal = self.window.screens["journal"]
        journal.refresh()
        self.assertIn("1 quests", journal.stats.text())
        self.assertIn("1 replays", journal.stats.text())
        self.assertEqual(journal.claims_table.item(0, 2).text(), "Quest Replay")
        self.assertEqual(journal.claims_table.item(0, 4).text(), "+0 XP, +0 Gold")

    def test_navigation_switches_without_fade_effect(self):
        self.window.navigate("quests")
        self.app.processEvents()
        self.assertIsNone(self.window.screens["quests"].graphicsEffect())
        self.assertFalse(hasattr(self.window, "fade"))

    def test_quest_import_controls_exist_in_board_and_settings(self):
        for screen_name in ("quests", "settings"):
            labels = {button.text() for button in self.window.screens[screen_name].findChildren(QPushButton)}
            self.assertIn("Generate and import quests…", labels)

    def test_quest_import_dialog_copies_previews_and_imports(self):
        original_count = len(self.state["quests"])
        dialog = QuestImportDialog(self.window.engine, self.window, "path-fastapi")
        self.addCleanup(dialog.close)
        dialog.topic.setText("Testing FastAPI services")
        dialog.copy_prompt()
        self.assertIn("Learning topic: Testing FastAPI services", self.app.clipboard().text())
        dialog.response.setPlainText(
            json.dumps(
                {
                    "quests": [
                        {
                            "stage": "Stage 4 — Testing",
                            "title": "Test one endpoint",
                            "difficulty": "normal",
                            "definition_of_done": "Write and run a passing endpoint test.",
                        }
                    ]
                }
            )
        )

        dialog.preview_import()

        self.assertEqual(dialog.path.currentData(), "path-fastapi")
        self.assertEqual(dialog.preview_table.rowCount(), 1)
        self.assertTrue(dialog.import_button.isEnabled())
        self.assertEqual(dialog.preview_table.item(0, 3).text(), "25 XP / 10 Gold")
        with patch("learntrack.ui.dialogs.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
            dialog.import_preview()
        self.assertEqual(dialog.imported_count, 1)
        self.assertEqual(len(self.state["quests"]), original_count + 1)

    def test_custom_import_reward_setting_defaults_off_and_saves(self):
        settings = self.window.screens["settings"]
        self.assertFalse(settings.custom_import_rewards.isChecked())
        settings.custom_import_rewards.setChecked(True)
        self.assertTrue(self.state["profile"]["allow_custom_import_rewards"])
        self.assertTrue(self.storage.load()["profile"]["allow_custom_import_rewards"])

    def test_current_run_artwork_setting_updates_dashboard_and_saves(self):
        settings = self.window.screens["settings"]
        dashboard = self.window.screens["dashboard"]
        self.assertTrue(settings.current_run_background.isChecked())
        self.assertTrue(dashboard.hero.artwork_visible)

        settings.current_run_background.setChecked(False)

        self.assertFalse(dashboard.hero.artwork_visible)
        self.assertFalse(self.state["profile"]["show_current_run_background"])
        self.assertFalse(self.storage.load()["profile"]["show_current_run_background"])

    def test_timer_presets_update_shortcuts_and_selected_duration(self):
        timer_panel = self.window.screens["dashboard"].timer_panel
        self.window.engine.set_timer_presets((15, 35, 50), 60)
        timer_panel.refresh_preset_buttons()
        self.assertEqual([button.text() for button in timer_panel.focus_buttons], ["15m", "35m", "50m"])
        self.assertEqual(timer_panel.break_button.text(), "60m break")
        self.assertEqual(timer_panel.presets_button.text(), "Presets…")

        QTest.mouseClick(timer_panel.focus_buttons[1], Qt.MouseButton.LeftButton)
        self.assertEqual(self.state["progress"]["timer"]["duration_seconds"], 35 * 60)
        QTest.mouseClick(timer_panel.break_button, Qt.MouseButton.LeftButton)
        self.assertEqual(self.state["progress"]["timer"]["duration_seconds"], 60 * 60)

    def test_timer_preset_dialog_returns_four_edited_values(self):
        dialog = TimerPresetsDialog((20, 25, 30), 40, self.window)
        self.addCleanup(dialog.close)
        for editor, minutes in zip(dialog.focus_inputs, (10, 45, 90)):
            editor.setValue(minutes)
        dialog.break_input.setValue(75)
        self.assertEqual(dialog.data(), ((10, 45, 90), 75))

    def test_bundled_inter_font_is_registered(self):
        self.assertIn("Inter", QFontDatabase.families())

    def test_application_uses_learntrack_identity(self):
        self.assertEqual(QCoreApplication.organizationName(), "LearnTrack")
        self.assertEqual(QCoreApplication.applicationName(), "LearnTrack")
        self.assertEqual(self.app.applicationDisplayName(), "LearnTrack")
        self.assertEqual(self.window.windowTitle(), "LearnTrack")

    def test_settings_shows_save_status(self):
        settings = self.window.screens["settings"]
        self.assertIn("Last saved:", settings.save_status.text())
        self.assertIn(str(self.storage.path), settings.save_status.text())

    def test_choose_empty_sync_folder_copies_current_progress(self):
        sync_folder = Path(self.temp.name) / "Google Drive" / "LearnTrack"
        sync_folder.mkdir(parents=True)
        destination = sync_folder / "progress.json"
        with (
            patch("learntrack.ui.main_window.QFileDialog.getExistingDirectory", return_value=str(sync_folder)),
            patch("learntrack.ui.main_window.QMessageBox.information"),
            patch("learntrack.ui.main_window.SaveManager.remember_path"),
        ):
            self.window.choose_sync_folder()

        self.assertEqual(self.window.storage.path, destination.resolve())
        self.assertTrue(destination.exists())
        self.assertEqual(self.window.storage.load()["profile"]["player_name"], "UI Tester")

    def test_choose_existing_sync_folder_uses_shared_progress(self):
        sync_folder = Path(self.temp.name) / "Google Drive" / "LearnTrack"
        sync_folder.mkdir(parents=True)
        destination = sync_folder / "progress.json"
        SaveManager(destination).save(create_default_state("Shared Player"))
        with (
            patch("learntrack.ui.main_window.QFileDialog.getExistingDirectory", return_value=str(sync_folder)),
            patch("learntrack.ui.main_window.QMessageBox.warning", return_value=QMessageBox.StandardButton.Yes),
            patch("learntrack.ui.main_window.QMessageBox.information"),
            patch("learntrack.ui.main_window.SaveManager.remember_path"),
        ):
            self.window.choose_sync_folder()

        self.assertEqual(self.window.storage.path, destination.resolve())
        self.assertEqual(self.window.engine.state["profile"]["player_name"], "Shared Player")

    def test_navigation_uses_requested_menu_icons(self):
        self.assertEqual(self.window.nav_buttons["settings"].text(), "Settings")
        self.assertFalse(self.window.nav_buttons["settings"].icon().isNull())
        self.assertFalse(self.window.nav_buttons["quests"].icon().isNull())

    def test_closing_pauses_and_saves_running_timer(self):
        timer_panel = self.window.screens["dashboard"].timer_panel
        timer_panel.choose("focus", 20)
        timer_panel.toggle()
        timer_panel._tick()

        self.window.close()

        saved_timer = self.storage.load()["progress"]["timer"]
        self.assertEqual(saved_timer["remaining_seconds"], 1199)
        self.assertFalse(saved_timer["running"])


if __name__ == "__main__":
    unittest.main()
