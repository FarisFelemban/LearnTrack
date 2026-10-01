from copy import deepcopy
from datetime import date
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPoint
from PySide6.QtGui import QHelpEvent
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QScrollArea

from learntrack.app import create_application
from learntrack.defaults import create_default_state
from learntrack.engine import GameEngine, GameRuleError, validate_state
from learntrack.storage import SaveManager
from learntrack.ui.dialogs import SubtractTimerTimeDialog
from learntrack.ui.heatmap import FocusHeatmapGrid, focus_intensity, format_focus_hours
from learntrack.ui.main_window import MainWindow


class DailyFocusEngineTests(unittest.TestCase):
    def setUp(self):
        self.state = create_default_state()
        self.engine = GameEngine(self.state)

    def test_countdown_and_stopwatch_share_history_without_breaks_or_resets(self):
        engine = self.engine
        engine.set_timer_seconds("focus", 2000)
        engine.update_timer(2000, True)
        engine.advance_timer(1800)
        engine.update_timer(200, False)
        engine.advance_timer(100)
        engine.set_timer_seconds("break", 20)
        engine.update_timer(20, True)
        engine.advance_timer(50)
        engine.select_clock("stopwatch")
        engine.set_stopwatch_running(True)
        engine.advance_stopwatch(3600)
        engine.reset_stopwatch()
        engine.select_stopwatch_mode("break")
        engine.set_stopwatch_running(True)
        engine.advance_stopwatch(10)
        engine.set_stopwatch_running(False)
        engine.advance_stopwatch(100)
        self.assertEqual(engine.daily_focus_seconds, {date.today().isoformat(): 5400})
        self.assertEqual(engine.timer_totals, {"focus_seconds": 5400, "break_seconds": 30})
        self.assertEqual(engine.undated_focus_seconds, 0)
        self.assertEqual((engine.progress["xp"], engine.progress["gold"]), (0, 0))

    def test_focus_ticks_follow_local_date_through_midnight_for_both_clocks(self):
        for clock in ("timer", "stopwatch"):
            with self.subTest(clock=clock):
                engine = GameEngine(create_default_state())
                engine.select_clock(clock)
                if clock == "timer":
                    engine.update_timer(1500, True)
                    tick = engine.advance_timer
                else:
                    engine.set_stopwatch_running(True)
                    tick = engine.advance_stopwatch
                with patch("learntrack.engine.date", wraps=date) as local_date:
                    local_date.today.return_value = date(2024, 12, 31)
                    tick()
                    local_date.today.return_value = date(2025, 1, 1)
                    tick(2)
                self.assertEqual(engine.daily_focus_seconds, {"2024-12-31": 1, "2025-01-01": 2})

    def test_check_ins_only_record_time_until_the_pause(self):
        engine = self.engine
        engine.select_clock("stopwatch")
        engine.set_check_in_settings(True, 1)
        engine.set_stopwatch_running(True)
        self.assertTrue(engine.advance_stopwatch(120))
        engine.advance_stopwatch(500)
        self.assertEqual(engine.daily_focus_seconds, {date.today().isoformat(): 60})
        engine.answer_check_in(True)
        engine.advance_stopwatch(10)
        self.assertEqual(engine.daily_focus_seconds[date.today().isoformat()], 70)

    def test_legacy_totals_remain_undated_until_new_focus_ticks(self):
        del self.state["progress"]["daily_focus_seconds"]
        self.state["progress"]["timer_totals"]["focus_seconds"] = 3600
        self.engine.set_focus_tracking_start("2024-01-01")
        self.assertEqual(self.engine.daily_focus_seconds, {})
        self.assertEqual(self.engine.undated_focus_seconds, 3600)
        self.engine.update_timer(1500, True)
        self.engine.advance_timer(5)
        self.assertEqual(self.engine.daily_focus_seconds, {date.today().isoformat(): 5})
        self.assertEqual(self.engine.undated_focus_seconds, 3600)

    def test_selected_day_and_undated_corrections_are_separate(self):
        self.state["progress"]["timer_totals"] = {"focus_seconds": 150, "break_seconds": 30}
        self.state["progress"]["daily_focus_seconds"] = {"2024-01-01": 50, "2024-01-02": 60}
        self.engine.subtract_timer_time("focus", 20, focus_date="2024-01-01")
        self.assertEqual(self.engine.daily_focus_seconds, {"2024-01-01": 30, "2024-01-02": 60})
        self.assertEqual(self.engine.undated_focus_seconds, 40)
        self.engine.subtract_timer_time("focus", 40)
        self.engine.subtract_timer_time("break", 30)
        self.assertEqual(self.engine.timer_totals, {"focus_seconds": 90, "break_seconds": 0})
        self.assertEqual(self.engine.undated_focus_seconds, 0)
        self.engine.subtract_timer_time("focus", 30, focus_date="2024-01-01")
        self.assertEqual(self.engine.daily_focus_seconds["2024-01-01"], 0)
        validate_state(self.state)

    def test_invalid_corrections_do_not_partially_change_state(self):
        self.state["progress"]["timer_totals"] = {"focus_seconds": 100, "break_seconds": 30}
        self.state["progress"]["daily_focus_seconds"] = {"2024-01-01": 80}
        before = deepcopy(self.state)
        for mode, seconds, day in (("focus", 81, "2024-01-01"), ("focus", 21, None),
                                   ("focus", 1, "2024-01-02"), ("focus", 1, "bad"),
                                   ("focus", 1, 123), ("focus", 1, "20240101"),
                                   ("break", 1, "2024-01-01")):
            with self.subTest(mode=mode, day=day), self.assertRaises(GameRuleError):
                self.engine.subtract_timer_time(mode, seconds, focus_date=day)
            self.assertEqual(self.state, before)

    def test_invalid_history_is_rejected(self):
        invalid = (None, [], {"bad": 0}, {"2024-02-30": 0}, {"20240229": 0}, {123: 0},
                   {"2024-02-29": True}, {"2024-02-29": -1}, {"2024-02-29": 0.5},
                   {"2024-02-29": "1"}, {"2024-02-29": 101})
        for history in invalid:
            with self.subTest(history=history):
                state = create_default_state()
                state["progress"]["timer_totals"]["focus_seconds"] = 100
                state["progress"]["daily_focus_seconds"] = history
                with self.assertRaises(GameRuleError):
                    validate_state(state)

    def test_stopwatch_history_survives_shared_save_export_import_and_reset(self):
        with TemporaryDirectory() as directory:
            storage = SaveManager(Path(directory) / "shared" / "progress.json")
            engine = GameEngine(self.state, storage.save)
            engine.select_clock("stopwatch")
            engine.set_stopwatch_running(True)
            engine.advance_stopwatch(5400)
            loaded = SaveManager(storage.path).load()
            self.assertFalse(loaded["progress"]["stopwatch"]["running"])
            self.assertEqual(loaded["progress"]["daily_focus_seconds"], {date.today().isoformat(): 5400})
            export = Path(directory) / "export.json"
            storage.export_to(export, loaded)
            imported = storage.read_import(export)
            storage.replace_with_import(imported)
            self.assertEqual(storage.load()["progress"]["daily_focus_seconds"], engine.daily_focus_seconds)
            reset, _ = storage.reset()
            self.assertEqual(reset["progress"]["daily_focus_seconds"], {})


class HeatmapUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_application([])

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = create_default_state()
        self.state["profile"]["animations_enabled"] = False
        self.storage = SaveManager(Path(self.temp.name) / "progress.json")
        self.window = MainWindow(self.state, self.storage)
        self.addCleanup(self.window.close)
        self.dashboard = self.window.screens["dashboard"]

    def test_rounding_and_intensity_boundaries(self):
        for seconds, text in ((0, "0 hours"), (1, "0 hours"), (180, "0.1 hours"),
                              (1800, "0.5 hours"), (3600, "1 hour"), (5400, "1.5 hours"),
                              (6000, "1.7 hours"), (7200, "2 hours")):
            self.assertEqual(format_focus_hours(seconds), text)
        for seconds, intensity in ((0, 0), (1, 1), (3599, 1), (3600, 2), (7199, 2),
                                   (7200, 3), (14399, 3), (14400, 4)):
            self.assertEqual(focus_intensity(seconds), intensity)

    def test_calendar_cells_and_tooltips_cover_leap_years_and_partial_weeks(self):
        grid = FocusHeatmapGrid()
        self.addCleanup(grid.close)
        grid.resize(670, 154)
        for year, days in ((2023, 365), (2024, 366), (2000, 366)):
            grid.set_data(year, {}, date(2026, 10, 1))
            cells = grid.day_cells()
            self.assertEqual(len(cells), days)
            self.assertEqual(cells[0][0], date(year, 1, 1))
            self.assertEqual(cells[-1][0], date(year, 12, 31))
            self.assertTrue(all(grid.rect().contains(rect.toAlignedRect()) for _, rect in cells))
        grid.set_data(2024, {"2024-02-29": 5400}, date(2024, 3, 1))
        self.assertIn("1.5 hours of focus", grid.tooltip_for_day(date(2024, 2, 29)))
        self.assertIn("0 hours of focus", grid.tooltip_for_day(date(2024, 2, 28)))
        grid.set_data(2024, {"2024-02-29": 5400}, date(2024, 2, 28))
        self.assertIn("Future date", grid.tooltip_for_day(date(2024, 2, 29)))
        rect = next(rect for day, rect in grid.day_cells() if day == date(2024, 2, 29))
        event = QHelpEvent(QEvent.Type.ToolTip, rect.center().toPoint(), QPoint(50, 50))
        with patch("learntrack.ui.heatmap.QToolTip.showText") as show:
            self.app.sendEvent(grid, event)
        self.assertIn("Future date", show.call_args.args[1])

    def test_year_selection_survives_live_ticks_and_corrections(self):
        heatmap = self.dashboard.heatmap
        self.state["progress"]["timer_totals"]["focus_seconds"] = 9000
        self.state["progress"]["daily_focus_seconds"] = {"2024-02-29": 5400}
        heatmap.refresh()
        self.assertEqual(heatmap.year_selector.currentData(), date.today().year)
        heatmap.year_selector.setCurrentIndex(heatmap.year_selector.findData(2024))
        self.dashboard.timer_panel.toggle()
        self.dashboard.timer_panel._tick()
        self.assertEqual(heatmap.grid.year, 2024)
        self.assertEqual(heatmap.year_selector.currentData(), 2024)
        self.assertEqual(self.storage.load()["progress"]["daily_focus_seconds"][date.today().isoformat()], 1)
        self.window.engine.subtract_timer_time("focus", 3600)
        self.window.refresh_all()
        self.assertEqual(heatmap.grid.year, 2024)

    def test_dashboard_fits_with_long_text_and_timer_only_keeps_heatmap(self):
        path_name = "A very long learning path name " * 20
        title = "A very long current run title " * 20
        details = "A lengthy definition of done that should stay in its preview " * 30
        self.state["paths"][0]["name"] = path_name
        self.state["paths"][0]["status"] = "active"
        self.state["quests"][0]["title"] = title
        self.state["quests"][0]["definition_of_done"] = details
        self.window.engine.start_run("quest", self.state["quests"][0]["id"])
        self.window.refresh_all()
        self.window.show()
        scroll = self.dashboard.findChild(QScrollArea)
        for width, height in ((980, 680), (1120, 760), (1280, 820)):
            self.window.resize(width, height)
            self.app.processEvents()
            self.assertEqual(scroll.horizontalScrollBar().maximum(), 0)
            heatmap_bottom = self.dashboard.heatmap.mapTo(scroll.viewport(), self.dashboard.heatmap.rect().bottomRight())
            self.assertLessEqual(heatmap_bottom.y(), scroll.viewport().height())
            self.assertLess(self.dashboard.xp_bar.width(), scroll.viewport().width() * 0.75)
            self.assertEqual(self.dashboard.hero.height(), 200)
            for button in self.dashboard.hero.findChildren(type(self.dashboard.current_action)):
                self.assertGreaterEqual(button.width(), button.minimumSizeHint().width())
                self.assertTrue(self.dashboard.hero.rect().contains(button.geometry()))
            self.assertEqual(self.dashboard.current_title.toolTip(), title)
            self.assertIn(details, self.dashboard.current_details.toolTip())
            self.assertEqual(self.dashboard.path_card.value_label.toolTip(), "")
        self.assertFalse(any(label.text().startswith("Welcome back") for label in self.dashboard.findChildren(QLabel)))
        self.window.engine.set_timer_only_mode(True)
        self.window.refresh_all()
        self.app.processEvents()
        self.assertTrue(self.dashboard.left_column.isHidden())
        self.assertTrue(self.dashboard.heatmap.isVisible())
        self.assertTrue(self.dashboard.timer_panel.isVisible())
        self.state["profile"]["show_current_run_background"] = False
        self.window.engine.set_timer_only_mode(False)
        self.window.refresh_all()
        self.assertFalse(self.dashboard.hero.artwork_visible)

    def test_focus_source_defaults_and_rechecks_before_confirmation(self):
        today = date.today().isoformat()
        self.state["progress"]["timer_totals"]["focus_seconds"] = 100
        self.state["progress"]["daily_focus_seconds"] = {"2024-01-01": 30, today: 30}
        dialog = SubtractTimerTimeDialog(self.window.engine, "focus", self.window)
        self.addCleanup(dialog.close)
        self.assertEqual(dialog.focus_source.currentData(), today)
        dialog.seconds.setValue(25)
        self.assertTrue(dialog.buttons.button(QDialogButtonBox.StandardButton.Save).isEnabled())
        self.window.engine.subtract_timer_time("focus", 20, focus_date=today)
        before = deepcopy(self.state)
        with patch("learntrack.ui.dialogs.QMessageBox.warning") as warning:
            dialog.accept()
        warning.assert_called_once()
        self.assertEqual(self.state, before)
        self.assertFalse(dialog.buttons.button(QDialogButtonBox.StandardButton.Save).isEnabled())
        dialog.seconds.setValue(5)
        self.assertIn("Selected balance after subtraction: 0h 00m 05s", dialog.preview.text())
        dialog.accept()
        self.assertEqual(dialog.result(), QDialog.DialogCode.Accepted)
        self.assertEqual(self.window.engine.daily_focus_seconds[today], 5)
        self.assertEqual(self.window.engine.undated_focus_seconds, 40)
        self.assertEqual(self.storage.load()["progress"]["daily_focus_seconds"][today], 5)

    def test_older_date_undated_selection_and_cancel(self):
        self.state["progress"]["timer_totals"]["focus_seconds"] = 100
        self.state["progress"]["daily_focus_seconds"] = {"2024-01-01": 30, "2024-01-02": 40}
        dialog = SubtractTimerTimeDialog(self.window.engine, "focus", self.window)
        self.addCleanup(dialog.close)
        self.assertEqual(dialog.focus_source.currentData(), "2024-01-02")
        dialog.focus_source.setCurrentIndex(dialog.focus_source.findData(None))
        dialog.seconds.setValue(31)
        self.assertFalse(dialog.buttons.button(QDialogButtonBox.StandardButton.Save).isEnabled())
        dialog.seconds.setValue(30)
        self.assertIn("Selected balance: 0h 00m 30s", dialog.preview.text())
        before = deepcopy(self.state)
        dialog.reject()
        self.assertEqual(self.state, before)
        self.state["progress"]["daily_focus_seconds"] = {}
        undated = SubtractTimerTimeDialog(self.window.engine, "focus", self.window)
        self.addCleanup(undated.close)
        self.assertIsNone(undated.focus_source.currentData())
        self.assertEqual(undated.focus_source.currentText(), "Older undated time")


if __name__ == "__main__":
    unittest.main()
