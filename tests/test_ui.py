import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from learning_rpg.app import create_application
from learning_rpg.defaults import create_default_state
from learning_rpg.storage import SaveManager
from learning_rpg.ui.dialogs import BossDialog, CompletionDialog, PathDialog, QuestDialog, RewardDialog
from learning_rpg.ui.main_window import MainWindow


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


if __name__ == "__main__":
    unittest.main()
