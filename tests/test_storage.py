import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from learntrack.defaults import create_default_state
from learntrack.engine import GameEngine, GameRuleError
from learntrack.storage import SaveCorruptionError, SaveManager


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "nested" / "progress.json"
        self.storage = SaveManager(self.path)

    def test_first_run_and_round_trip(self):
        self.assertIsNone(self.storage.load())
        state = create_default_state("Faris")
        engine = GameEngine(state)
        quest = state["quests"][0]
        engine.start_run("quest", quest["id"])
        engine.complete_quest(quest["id"], "Explained routes.")
        self.storage.save(state)
        loaded = self.storage.load()
        self.assertEqual(loaded["profile"]["player_name"], "Faris")
        self.assertEqual(loaded["progress"]["quest_claims"][0]["evidence"], "Explained routes.")

    def test_legacy_save_is_copied_without_removing_original(self):
        legacy_path = Path(self.temp.name) / "LearningRPG" / "progress.json"
        legacy_storage = SaveManager(legacy_path)
        legacy_storage.save(create_default_state("Legacy Player"))

        self.assertTrue(self.storage.migrate_from(legacy_path))

        self.assertTrue(legacy_path.exists())
        self.assertEqual(self.storage.load()["profile"]["player_name"], "Legacy Player")

    def test_legacy_save_never_overwrites_existing_learntrack_save(self):
        legacy_path = Path(self.temp.name) / "LearningRPG" / "progress.json"
        SaveManager(legacy_path).save(create_default_state("Legacy Player"))
        self.storage.save(create_default_state("Current Player"))

        self.assertFalse(self.storage.migrate_from(legacy_path))
        self.assertEqual(self.storage.load()["profile"]["player_name"], "Current Player")

    def test_timer_restores_paused_with_remaining_time(self):
        state = create_default_state()
        state["progress"]["timer"].update(remaining_seconds=321, running=True)
        self.storage.save(state)
        loaded = self.storage.load()
        self.assertEqual(loaded["progress"]["timer"]["remaining_seconds"], 321)
        self.assertFalse(loaded["progress"]["timer"]["running"])

    def test_malformed_save_is_preserved(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("{broken", encoding="utf-8")
        with self.assertRaises(SaveCorruptionError) as caught:
            self.storage.load()
        self.assertTrue(self.path.exists())
        self.assertTrue(caught.exception.backup_path.exists())
        self.assertEqual(caught.exception.backup_path.read_text(encoding="utf-8"), "{broken")

    def test_import_validation_and_backup(self):
        original = create_default_state("Original")
        self.storage.save(original)
        import_path = Path(self.temp.name) / "import.json"
        imported = create_default_state("Imported")
        import_path.write_text(json.dumps(imported), encoding="utf-8")
        parsed = self.storage.read_import(import_path)
        backup = self.storage.replace_with_import(parsed)
        self.assertIsNotNone(backup)
        self.assertTrue(backup.exists())
        self.assertEqual(self.storage.load()["profile"]["player_name"], "Imported")
        imported["schema_version"] = 999
        import_path.write_text(json.dumps(imported), encoding="utf-8")
        with self.assertRaises(GameRuleError):
            self.storage.read_import(import_path)

    def test_reset_backs_up_existing_save(self):
        self.storage.save(create_default_state("Old"))
        state, backup = self.storage.reset("Same Name")
        self.assertTrue(backup.exists())
        self.assertEqual(state["profile"]["player_name"], "Same Name")
        self.assertEqual(state["progress"]["xp"], 0)

    def test_autosaved_quest_to_shop_loop_survives_relaunch(self):
        state = create_default_state("Loop Tester")
        self.storage.save(state)
        engine = GameEngine(state, self.storage.save)
        # Four early quests earn exactly enough for the first shop reward.
        for quest in state["quests"][:4]:
            engine.start_run("quest", quest["id"])
            engine.complete_quest(quest["id"], f"Verified {quest['title']}.")
        reward = state["shop_rewards"][0]
        engine.purchase_reward(reward["id"])
        reloaded = self.storage.load()
        self.assertEqual(reloaded["progress"]["xp"], 70)
        self.assertEqual(reloaded["progress"]["gold"], 0)
        self.assertEqual(len(reloaded["progress"]["quest_claims"]), 4)
        self.assertEqual(reloaded["progress"]["purchases"][0]["reward_id"], reward["id"])


if __name__ == "__main__":
    unittest.main()
