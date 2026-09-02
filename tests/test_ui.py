import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtTest import QTest

from learntrack.app import create_application
from learntrack.defaults import create_default_state
from learntrack.storage import SaveManager
from learntrack.ui.dialogs import BossDialog, CompletionDialog, PathDialog, QuestDialog, RewardDialog
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

    def test_bundled_inter_font_is_registered(self):
        self.assertIn("Inter", QFontDatabase.families())

    def test_application_uses_learntrack_identity(self):
        self.assertEqual(QCoreApplication.organizationName(), "LearnTrack")
        self.assertEqual(QCoreApplication.applicationName(), "LearnTrack")
        self.assertEqual(self.app.applicationDisplayName(), "LearnTrack")
        self.assertEqual(self.window.windowTitle(), "LearnTrack")

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
