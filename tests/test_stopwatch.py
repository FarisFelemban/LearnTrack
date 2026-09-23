from copy import deepcopy
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from learntrack.app import create_application
from learntrack.defaults import create_default_state
from learntrack.engine import GameEngine, GameRuleError, validate_state
from learntrack.storage import SaveManager
from learntrack.ui.dialogs import StopwatchSettingsDialog
from learntrack.ui.main_window import MainWindow
from learntrack.ui.widgets import format_clock_time


class StopwatchEngineTests(unittest.TestCase):
    def setUp(self):
        self.state = create_default_state()
        self.engine = GameEngine(self.state)
        self.engine.select_clock("stopwatch")

    def test_independent_clocks_categories_and_totals(self):
        engine = self.engine
        engine.set_stopwatch_running(True)
        engine.advance_stopwatch(75)
        self.assertIsNotNone(engine.focus_tracking_started_on)
        engine.select_stopwatch_mode("break")
        engine.advance_stopwatch(10)
        self.assertEqual(engine.stopwatch["break_seconds"], 0)
        engine.set_stopwatch_running(True)
        engine.advance_stopwatch(12)
        engine.select_clock("timer")
        engine.update_timer(100, True)
        engine.advance_timer(5)
        engine.select_clock("stopwatch")
        self.assertFalse(engine.progress["timer"]["running"])
        self.assertEqual(engine.progress["timer"]["remaining_seconds"], 95)
        engine.select_stopwatch_mode("focus")
        self.assertEqual(engine.stopwatch["focus_seconds"], 75)
        engine.reset_stopwatch()
        self.assertEqual(engine.stopwatch["break_seconds"], 12)
        self.assertEqual(engine.timer_totals, {"focus_seconds": 80, "break_seconds": 12})

    def test_check_in_boundary_waiting_and_responses(self):
        engine = self.engine
        engine.set_check_in_settings(True, 1)
        engine.set_stopwatch_running(True)
        self.assertFalse(engine.advance_stopwatch(59))
        self.assertTrue(engine.advance_stopwatch(100))
        self.assertFalse(engine.stopwatch["running"])
        engine.advance_stopwatch(500)
        self.assertEqual(engine.timer_totals["focus_seconds"], 60)
        engine.answer_check_in(False)
        self.assertFalse(engine.stopwatch["running"])
        engine.set_stopwatch_running(True)
        self.assertTrue(engine.advance_stopwatch(60))
        engine.answer_check_in(True)
        self.assertTrue(engine.stopwatch["running"])
        self.assertFalse(engine.advance_stopwatch(1))
        self.assertEqual(engine.timer_totals["focus_seconds"], 121)

    def test_partial_interval_pause_switch_settings_and_reset(self):
        engine = self.engine
        engine.set_check_in_settings(True, 1)
        engine.set_stopwatch_running(True)
        engine.advance_stopwatch(25)
        engine.set_stopwatch_running(False)
        engine.advance_stopwatch(20)
        engine.select_stopwatch_mode("break")
        engine.set_stopwatch_running(True)
        self.assertFalse(engine.advance_stopwatch(100))
        engine.select_clock("timer")
        engine.select_clock("stopwatch")
        engine.select_stopwatch_mode("focus")
        engine.set_stopwatch_running(True)
        self.assertEqual(engine.stopwatch["check_in_seconds"], 25)
        self.assertTrue(engine.advance_stopwatch(35))
        engine.set_check_in_settings(True, 2)
        self.assertFalse(engine.stopwatch["running"])
        self.assertEqual(engine.stopwatch["check_in_seconds"], 0)
        engine.set_stopwatch_running(True)
        engine.advance_stopwatch(15)
        engine.reset_stopwatch()
        self.assertEqual(engine.stopwatch["check_in_seconds"], 0)

    def test_disabled_and_long_duration(self):
        self.engine.set_stopwatch_running(True)
        self.assertFalse(self.engine.advance_stopwatch(100 * 3600 + 65))
        self.assertEqual(format_clock_time(self.engine.stopwatch["focus_seconds"], True), "100:01:05")
        self.assertEqual(format_clock_time(3599, True), "59:59")
        self.assertEqual(format_clock_time(3600, True), "1:00:00")

    def test_old_save_and_invalid_fields(self):
        old = deepcopy(self.state)
        del old["progress"]["clock_type"]
        del old["progress"]["stopwatch"]
        engine = GameEngine(old)
        self.assertEqual(engine.clock_type, "timer")
        self.assertFalse(engine.stopwatch["check_in_enabled"])
        for field, value in (("focus_seconds", -1), ("break_seconds", True),
                             ("check_in_minutes", 0), ("check_in_minutes", 1441),
                             ("running", 1), ("mode", "invalid")):
            state = deepcopy(self.state)
            state["progress"]["stopwatch"][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(GameRuleError):
                validate_state(state)

    def test_save_import_and_relaunch_pause_and_preserve_interval(self):
        engine = self.engine
        engine.set_check_in_settings(True, 1)
        engine.set_stopwatch_running(True)
        engine.advance_stopwatch(25)
        with TemporaryDirectory() as directory:
            storage = SaveManager(Path(directory) / "progress.json")
            storage.save(self.state)
            for restored in (storage.load(), storage.read_import(storage.path)):
                watch = restored["progress"]["stopwatch"]
                self.assertFalse(watch["running"])
                self.assertEqual(watch["focus_seconds"], 25)
                self.assertEqual(watch["check_in_seconds"], 25)
                self.assertEqual(restored["progress"]["clock_type"], "stopwatch")
            engine.advance_stopwatch(35)
            storage.save(self.state)
            self.assertEqual(storage.load()["progress"]["stopwatch"]["check_in_seconds"], 0)


class StopwatchUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_application([])

    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.storage = SaveManager(Path(temp.name) / "progress.json")
        self.window = MainWindow(create_default_state(), self.storage)
        self.addCleanup(self.window.close)
        self.panel = self.window.screens["dashboard"].timer_panel
        self.panel.stopwatch_button.click()

    def trigger_check_in(self):
        self.window.engine.set_check_in_settings(True, 1)
        self.panel.toggle()
        self.window.engine.advance_stopwatch(59)
        self.panel._tick()
        return self.window._check_in_dialog

    def test_popup_pauses_and_yes_resumes_shared_mini(self):
        dialog = self.trigger_check_in()
        self.assertIsNotNone(dialog)
        self.assertFalse(self.window.engine.stopwatch["running"])
        self.assertFalse(self.storage.load()["progress"]["stopwatch"]["running"])
        self.assertEqual(self.window.mini_timer.time_label.text(), "01:00")
        self.assertTrue(dialog.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        self.window._show_check_in()
        self.assertIs(self.window._check_in_dialog, dialog)
        dialog.button(QMessageBox.StandardButton.Yes).click()
        self.assertTrue(self.window.engine.stopwatch["running"])
        self.window.mini_timer.toggle_button.click()
        self.assertFalse(self.window.engine.stopwatch["running"])

    def test_no_close_and_stale_response(self):
        dialog = self.trigger_check_in()
        dialog.button(QMessageBox.StandardButton.No).click()
        self.assertFalse(self.window.engine.stopwatch["running"])
        self.panel.toggle()
        self.window.engine.advance_stopwatch(59)
        self.panel._tick()
        self.window._check_in_dialog.close()
        self.assertFalse(self.window.engine.stopwatch["running"])
        self.assertEqual(self.window.engine.stopwatch["check_in_seconds"], 0)
        self.panel.toggle()
        self.window.engine.advance_stopwatch(59)
        self.panel._tick()
        dialog = self.window._check_in_dialog
        self.window._dismiss_check_in()
        self.window.engine.state = create_default_state()
        dialog.done(QMessageBox.StandardButton.Yes)
        self.assertFalse(self.window.engine.stopwatch["running"])

    def test_settings_and_layout(self):
        dialog = StopwatchSettingsDialog(False, 30)
        self.assertFalse(dialog.minutes.isEnabled())
        dialog.enabled.setChecked(True)
        self.assertTrue(dialog.minutes.isEnabled())
        self.assertEqual(dialog.data(), (True, 30))
        dialog.close()
        for timer_only in (False, True):
            self.window.engine.set_timer_only_mode(timer_only)
            self.window.refresh_all()
            self.window.resize(980, 680)
            self.window.show()
            self.app.processEvents()
            self.assertEqual(self.window.width(), 980)
            self.assertEqual(self.panel.presets_button.text(), "Settings…")
            self.assertTrue(self.panel.focus_buttons[0].isHidden())
            self.assertFalse(self.panel.category_buttons[0].isHidden())
            self.panel.begin_duration_edit()
            self.assertTrue(self.panel.dial.editor.isHidden())
        self.panel.stopwatch_button.click()
        self.assertEqual(self.panel.presets_button.text(), "Presets…")


if __name__ == "__main__":
    unittest.main()
