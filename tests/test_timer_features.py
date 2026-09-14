from copy import deepcopy
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialogButtonBox, QMessageBox

from learntrack.app import create_application
from learntrack.defaults import create_default_state
from learntrack.engine import GameEngine, GameRuleError, validate_state
from learntrack.storage import SaveManager
from learntrack.ui.dialogs import SubtractTimerTimeDialog, format_timer_total
from learntrack.ui.main_window import MainWindow


class TimerEngineTests(unittest.TestCase):
    def setUp(self):
        self.state = create_default_state("Timer tester")
        self.engine = GameEngine(self.state)

    def start(self, mode="focus", seconds=10):
        self.engine.set_timer_seconds(mode, seconds)
        self.engine.update_timer(seconds, True)

    def test_partial_sessions_and_completion_count_separately(self):
        self.start()
        self.engine.advance_timer(3)
        self.start("break", 2)
        self.engine.advance_timer(10)
        self.engine.advance_timer()
        self.assertEqual(self.engine.timer_totals, {"focus_seconds": 3, "break_seconds": 2})
        self.assertFalse(self.engine.progress["timer"]["running"])
        self.assertEqual(self.engine.progress["timer"]["remaining_seconds"], 0)
        self.assertEqual(self.engine.progress["xp"], 0)
        self.assertEqual(self.engine.progress["gold"], 0)

    def test_pause_duration_edits_and_reset_do_not_add_or_remove_time(self):
        self.start()
        self.engine.advance_timer(3)
        self.engine.update_timer(7, False)
        self.engine.advance_timer(100)
        self.engine.update_timer(10, False)
        self.engine.set_timer_seconds("focus", 90)
        self.engine.set_timer_presets((15, 20, 25), 5)
        self.assertEqual(self.engine.timer_totals["focus_seconds"], 3)
        self.engine.update_timer(90, True)
        self.engine.advance_timer(2)
        self.assertEqual(self.engine.timer_totals["focus_seconds"], 5)

    def test_mode_switch_preserves_timer_and_game_progress(self):
        self.engine.start_run("quest", self.state["quests"][0]["id"])
        self.start()
        before = deepcopy(self.engine.progress)
        self.engine.set_timer_only_mode(True)
        self.assertEqual(self.engine.progress, before)
        self.engine.advance_timer()
        self.engine.set_timer_only_mode(False)
        self.engine.advance_timer()
        self.assertEqual(self.engine.timer_totals["focus_seconds"], 2)

    def test_subtraction_preserves_countdown_and_allows_more_time(self):
        self.start()
        self.engine.advance_timer(4)
        countdown = deepcopy(self.engine.progress["timer"])
        self.engine.subtract_timer_time("focus", 3)
        self.assertEqual(self.engine.progress["timer"], countdown)
        self.engine.advance_timer()
        self.assertEqual(self.engine.timer_totals["focus_seconds"], 2)
        self.engine.subtract_timer_time("focus", 2)
        self.assertEqual(self.engine.timer_totals["focus_seconds"], 0)

    def test_invalid_subtractions_leave_state_unchanged(self):
        self.start()
        self.engine.advance_timer(3)
        before = deepcopy(self.state)
        for mode, seconds in (("focus", 0), ("focus", -1), ("focus", 4),
                              ("focus", True), ("focus", 1.5), ("focus", "1"),
                              ("break", 1), ("invalid", 1)):
            with self.subTest(mode=mode, seconds=seconds):
                with self.assertRaises(GameRuleError):
                    self.engine.subtract_timer_time(mode, seconds)
                self.assertEqual(self.state, before)

    def test_old_saves_default_to_normal_mode_and_zero_totals(self):
        del self.state["profile"]["timer_only_mode"]
        del self.state["progress"]["timer_totals"]
        engine = GameEngine(self.state)
        self.assertFalse(engine.timer_only_mode)
        self.assertEqual(engine.timer_totals, {"focus_seconds": 0, "break_seconds": 0})
        engine.update_timer(1500, True)
        engine.advance_timer()
        self.assertEqual(engine.timer_totals["focus_seconds"], 1)

    def test_supplied_mode_and_totals_are_strictly_validated(self):
        for invalid in (None, 1, "false"):
            state = deepcopy(self.state)
            state["profile"]["timer_only_mode"] = invalid
            with self.assertRaises(GameRuleError):
                validate_state(state)
        for invalid in (None, [], {}, {"focus_seconds": 1},
                        {"focus_seconds": -1, "break_seconds": 0},
                        {"focus_seconds": True, "break_seconds": 0},
                        {"focus_seconds": 1.5, "break_seconds": 0}):
            state = deepcopy(self.state)
            state["progress"]["timer_totals"] = invalid
            with self.assertRaises(GameRuleError):
                validate_state(state)

    def test_tick_saves_countdown_and_total_in_one_change(self):
        self.start()
        saves = []
        self.engine.on_change = lambda state: saves.append(deepcopy(state))
        self.engine.advance_timer()
        self.assertEqual(len(saves), 1)
        self.assertEqual(saves[0]["progress"]["timer"]["remaining_seconds"], 9)
        self.assertEqual(saves[0]["progress"]["timer_totals"]["focus_seconds"], 1)


class TimerStorageTests(unittest.TestCase):
    def test_shared_save_relaunch_export_import_and_reset(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "shared" / "progress.json"
            desktop = SaveManager(path)
            engine = GameEngine(create_default_state(), desktop.save)
            engine.set_timer_only_mode(True)
            engine.update_timer(1500, True)
            engine.advance_timer(12)
            engine.set_timer_seconds("break", 30)
            engine.update_timer(30, True)
            engine.advance_timer(5)
            engine.update_timer(25, False)

            laptop = SaveManager(path)
            loaded = laptop.load()
            self.assertTrue(loaded["profile"]["timer_only_mode"])
            self.assertEqual(loaded["progress"]["timer_totals"], {"focus_seconds": 12, "break_seconds": 5})
            laptop_engine = GameEngine(loaded, laptop.save)
            laptop_engine.subtract_timer_time("focus", 2)
            laptop_engine.update_timer(25, True)
            laptop_engine.advance_timer()
            laptop_engine.set_timer_only_mode(False)

            export = Path(directory) / "export.json"
            laptop.export_to(export, loaded)
            imported = laptop.read_import(export)
            self.assertFalse(imported["profile"]["timer_only_mode"])
            self.assertFalse(imported["progress"]["timer"]["running"])
            self.assertEqual(imported["progress"]["timer_totals"], {"focus_seconds": 10, "break_seconds": 6})
            reloaded = SaveManager(path).load()
            self.assertEqual(reloaded["progress"], imported["progress"])
            reset, backup = laptop.reset()
            self.assertTrue(backup.is_file())
            self.assertFalse(reset["profile"]["timer_only_mode"])
            self.assertEqual(reset["progress"]["timer_totals"], {"focus_seconds": 0, "break_seconds": 0})


class TimerUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_application([])

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.storage = SaveManager(Path(self.temp.name) / "progress.json")
        self.state = create_default_state("Timer tester")
        self.state["profile"]["animations_enabled"] = False
        self.window = MainWindow(self.state, self.storage)
        self.addCleanup(self.window.close)
        self.panel = self.window.screens["dashboard"].timer_panel
        self.journal = self.window.screens["journal"]
        self.settings = self.window.screens["settings"]

    def test_mode_switch_retains_one_running_timer_and_restricts_navigation(self):
        self.window.show()
        self.panel.toggle()
        self.panel._tick()
        self.window.navigate("settings")
        self.settings.timer_only.setChecked(True)
        self.app.processEvents()
        self.assertTrue(self.state["progress"]["timer"]["running"])
        self.assertTrue(self.panel.clock.isActive())
        self.assertEqual(self.window.nav_buttons["dashboard"].text(), "Timer")
        self.assertEqual(self.window.nav_buttons["journal"].text(), "Total Time")
        for key in ("quests", "paths", "bosses", "shop"):
            self.assertTrue(self.window.nav_buttons[key].isHidden())
            self.window.navigate(key)
            self.assertIs(self.window.stack.currentWidget(), self.settings)
        for widget in self.settings.game_widgets:
            self.assertTrue(widget.isHidden())
        self.window.navigate("dashboard")
        for widget in self.window.screens["dashboard"].game_widgets:
            self.assertTrue(widget.isHidden())
        self.assertEqual(len(self.panel.findChildren(QTimer)), 1)
        self.assertTrue(self.storage.load()["profile"]["timer_only_mode"])

        self.window.navigate("journal")
        self.assertIs(self.journal.tabs.currentWidget(), self.journal.total_time_page)
        self.assertTrue(self.journal.tabs.tabBar().isHidden())
        self.assertTrue(self.journal.stats.isHidden())
        self.settings.timer_only.setChecked(False)
        self.assertFalse(self.journal.tabs.tabBar().isHidden())
        self.assertTrue(all(self.journal.tabs.isTabVisible(i) for i in range(4)))
        self.assertTrue(self.panel.clock.isActive())
        self.assertEqual(self.state["progress"]["timer_totals"]["focus_seconds"], 1)

    def test_relaunch_selects_saved_mode_and_keeps_timer_paused(self):
        self.settings.timer_only.setChecked(True)
        self.panel.toggle()
        self.panel._tick()
        self.window.close()
        storage = SaveManager(self.storage.path)
        reopened = MainWindow(storage.load(), storage)
        try:
            self.assertEqual(reopened.nav_buttons["dashboard"].text(), "Timer")
            self.assertTrue(reopened.nav_buttons["quests"].isHidden())
            self.assertFalse(reopened.engine.progress["timer"]["running"])
            self.assertEqual(reopened.engine.timer_totals["focus_seconds"], 1)
        finally:
            reopened.close()
        # Avoid a second close saving through the old manager after the relaunch.
        self.window.storage = storage

    def test_reset_and_restart_do_not_erase_or_duplicate_recorded_time(self):
        self.window.engine.set_timer_seconds("focus", 2)
        self.panel.refresh()
        with patch.object(self.window, "_timer_finished"):
            self.panel.toggle()
            self.panel._tick()
            self.panel.reset()
            self.panel._tick()  # A queued tick after pausing must do nothing.
            self.assertEqual(self.window.engine.timer_totals["focus_seconds"], 1)
            self.panel.toggle()
            self.panel._tick()
            self.panel._tick()
            self.panel._tick()  # Completion must be counted only once.
            self.assertEqual(self.window.engine.timer_totals["focus_seconds"], 3)
            self.panel.toggle()
            self.panel._tick()
            self.assertEqual(self.window.engine.timer_totals["focus_seconds"], 4)

    def test_mini_timer_pause_and_resume_use_the_same_totals(self):
        self.window.show()
        self.panel.choose("break", 1)
        self.panel.toggle()
        self.panel._tick()
        QTest.mouseClick(self.window.mini_timer.toggle_button, Qt.MouseButton.LeftButton)
        self.panel._tick()
        self.assertEqual(self.window.engine.timer_totals["break_seconds"], 1)
        QTest.mouseClick(self.window.mini_timer.toggle_button, Qt.MouseButton.LeftButton)
        self.panel._tick()
        self.assertEqual(self.window.engine.timer_totals, {"focus_seconds": 0, "break_seconds": 2})

    def test_subtraction_dialog_preview_confirmation_and_cancel(self):
        self.state["progress"]["timer_totals"]["focus_seconds"] = 100 * 3600 + 65
        self.window.refresh_all()
        self.assertEqual(self.journal.total_labels["focus"].text(), "100h 01m 05s")
        self.assertFalse(self.journal.subtract_buttons["break"].isEnabled())
        dialog = SubtractTimerTimeDialog(self.window.engine, "focus", self.window)
        self.addCleanup(dialog.close)
        save = dialog.buttons.button(QDialogButtonBox.StandardButton.Save)
        self.assertFalse(save.isEnabled())
        dialog.hours.setValue(101)
        self.assertFalse(save.isEnabled())
        dialog.hours.setValue(1)
        dialog.seconds.setValue(5)
        self.assertIn("99h 01m 00s", dialog.preview.text())
        self.assertTrue(save.isEnabled())
        before = deepcopy(self.state["progress"])
        dialog.reject()
        self.assertEqual(self.state["progress"], before)

        # Exercise the actual Total Time button and its modal confirmation flow.
        def confirm():
            active = self.journal.subtraction_dialog
            active.hours.setValue(100)
            active.minutes.setValue(1)
            active.seconds.setValue(5)
            active.buttons.button(QDialogButtonBox.StandardButton.Save).click()

        QTimer.singleShot(0, confirm)
        self.journal.subtract_buttons["focus"].click()
        self.assertEqual(self.window.engine.timer_totals["focus_seconds"], 0)
        self.assertFalse(self.journal.subtract_buttons["focus"].isEnabled())
        self.assertEqual(self.storage.load()["progress"]["timer_totals"]["focus_seconds"], 0)

    def test_preview_updates_while_timer_runs_and_deduction_keeps_it_running(self):
        self.panel.toggle()
        self.panel._tick()
        dialog = SubtractTimerTimeDialog(self.window.engine, "focus", self.journal)
        self.addCleanup(dialog.close)
        self.journal.subtraction_dialog = dialog
        dialog.seconds.setValue(1)
        self.panel._tick()
        self.assertIn("After subtraction: 0h 00m 01s", dialog.preview.text())
        countdown = deepcopy(self.state["progress"]["timer"])
        dialog.accept()
        self.assertEqual(self.state["progress"]["timer"], countdown)
        self.assertTrue(self.panel.clock.isActive())
        self.journal.subtraction_dialog = None

    def test_loading_shared_mode_restricts_current_game_page_and_reset_restores_it(self):
        shared_path = Path(self.temp.name) / "shared" / "progress.json"
        shared_state = create_default_state()
        shared_state["profile"]["timer_only_mode"] = True
        shared_state["progress"]["timer_totals"]["focus_seconds"] = 42
        SaveManager(shared_path).save(shared_state)
        self.window.navigate("quests")
        with (
            patch("learntrack.ui.main_window.QFileDialog.getExistingDirectory", return_value=str(shared_path.parent)),
            patch("learntrack.ui.main_window.QMessageBox.warning", return_value=QMessageBox.StandardButton.Yes),
            patch("learntrack.ui.main_window.QMessageBox.information"),
            patch.object(SaveManager, "remember_path"),
        ):
            self.window.choose_sync_folder()
        self.assertIs(self.window.stack.currentWidget(), self.window.screens["dashboard"])
        self.assertEqual(self.window.nav_buttons["dashboard"].text(), "Timer")
        self.assertEqual(self.journal.total_labels["focus"].text(), "0h 00m 42s")
        with (
            patch("learntrack.ui.main_window.QMessageBox.warning", return_value=QMessageBox.StandardButton.Reset),
            patch("learntrack.ui.main_window.QMessageBox.information"),
        ):
            self.window.reset_save()
        self.assertFalse(self.window.engine.timer_only_mode)
        self.assertFalse(self.window.nav_buttons["quests"].isHidden())
        self.assertEqual(self.window.engine.timer_totals["focus_seconds"], 0)

    def test_import_applies_mode_totals_and_pauses_previous_timer(self):
        source = Path(self.temp.name) / "import.json"
        imported = create_default_state()
        imported["profile"]["timer_only_mode"] = True
        imported["progress"]["timer_totals"]["break_seconds"] = 85
        SaveManager(source).save(imported)
        self.panel.toggle()
        with (
            patch("learntrack.ui.main_window.QFileDialog.getOpenFileName", return_value=(str(source), "")),
            patch("learntrack.ui.main_window.QMessageBox.warning", return_value=QMessageBox.StandardButton.Yes),
            patch("learntrack.ui.main_window.QMessageBox.information"),
        ):
            self.window.import_save()
        self.assertEqual(self.window.nav_buttons["dashboard"].text(), "Timer")
        self.assertEqual(self.journal.total_labels["break"].text(), "0h 01m 25s")
        self.assertFalse(self.panel.clock.isActive())

    def test_both_layouts_and_totals_fit_at_minimum_window_size(self):
        self.window.show()
        for enabled in (False, True):
            self.settings.timer_only.setChecked(enabled)
            self.window.resize(980, 680)
            for page in ("dashboard", "journal", "settings"):
                self.window.navigate(page)
                self.app.processEvents()
                self.assertEqual((self.window.width(), self.window.height()), (980, 680))
            self.window.navigate("journal")
            self.journal.tabs.setCurrentWidget(self.journal.total_time_page)
            self.app.processEvents()
            for button in self.journal.subtract_buttons.values():
                self.assertGreaterEqual(button.width(), button.minimumSizeHint().width())
                self.assertTrue(button.parentWidget().rect().contains(button.geometry()))
        self.assertEqual(format_timer_total(1000 * 3600), "1,000h 00m 00s")


if __name__ == "__main__":
    unittest.main()
