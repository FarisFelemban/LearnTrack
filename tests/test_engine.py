from copy import deepcopy
import unittest

from learntrack.constants import LEVEL_THRESHOLDS
from learntrack.defaults import create_default_state
from learntrack.engine import GameEngine, GameRuleError, level_for_xp, next_level_progress, validate_state


class LevelTests(unittest.TestCase):
    def test_exact_thresholds_and_edges(self):
        for level, threshold in LEVEL_THRESHOLDS.items():
            self.assertEqual(level_for_xp(threshold), level)
            if level > 1:
                self.assertEqual(level_for_xp(threshold - 1), level - 1)
        self.assertEqual(level_for_xp(999999), 10)
        with self.assertRaises(GameRuleError):
            level_for_xp(-1)

    def test_next_level_progress(self):
        self.assertEqual(next_level_progress(175), (75, 150, 3))
        self.assertEqual(next_level_progress(4700), (100, 0, None))


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.state = create_default_state("Tester")
        self.engine = GameEngine(self.state)
        self.quest = self.state["quests"][0]

    def test_quest_requires_current_run_and_evidence(self):
        with self.assertRaisesRegex(GameRuleError, "Start"):
            self.engine.complete_quest(self.quest["id"], "proof")
        self.engine.start_run("quest", self.quest["id"])
        with self.assertRaisesRegex(GameRuleError, "Evidence"):
            self.engine.complete_quest(self.quest["id"], "  ")

    def test_quest_reward_duplicate_prevention_and_immutable_snapshot(self):
        self.quest["bonuses"] = [{"id": "bonus", "title": "Extra", "xp": 7, "gold": 3}]
        self.engine.start_run("quest", self.quest["id"])
        claim = self.engine.complete_quest(self.quest["id"], "I explained two routes.", ["bonus"])
        self.assertEqual((self.engine.progress["xp"], self.engine.progress["gold"]), (17, 8))
        self.assertEqual(claim["xp_awarded"], 17)
        self.quest["title"] = "Edited later"
        self.assertNotEqual(claim["snapshot"]["title"], self.quest["title"])
        self.engine.progress["current_run"] = {"kind": "quest", "item_id": self.quest["id"]}
        with self.assertRaisesRegex(GameRuleError, "already"):
            self.engine.complete_quest(self.quest["id"], "again")

    def test_switching_runs_neither_awards_nor_removes(self):
        second = self.state["quests"][1]
        self.engine.start_run("quest", self.quest["id"])
        previous = self.engine.start_run("quest", second["id"])
        self.assertEqual(previous["item_id"], self.quest["id"])
        self.assertEqual(self.quest["status"], "available")
        self.assertEqual(second["status"], "in_progress")
        self.assertEqual((self.engine.progress["xp"], self.engine.progress["gold"]), (0, 0))

    def test_boss_requires_all_mandatory_requirements(self):
        boss = self.state["bosses"][0]
        self.engine.start_run("boss", boss["id"])
        with self.assertRaisesRegex(GameRuleError, "mandatory"):
            self.engine.complete_boss(boss["id"], "working API", [boss["requirements"][0]["id"]])
        checked = [requirement["id"] for requirement in boss["requirements"]]
        claim = self.engine.complete_boss(boss["id"], "Tested every endpoint.", checked, ["useful-tests"])
        self.assertEqual(claim["xp_awarded"], 350)
        self.assertEqual(claim["gold_awarded"], 120)
        self.assertEqual(self.engine.path_xp("path-fastapi"), 350)

    def test_level_lock_affordability_and_repeat_purchase(self):
        reward = self.state["shop_rewards"][0]
        with self.assertRaisesRegex(GameRuleError, "enough"):
            self.engine.purchase_reward(reward["id"])
        self.engine.progress["gold"] = 90
        self.engine.purchase_reward(reward["id"])
        self.engine.purchase_reward(reward["id"])
        self.assertEqual(self.engine.progress["gold"], 30)
        self.assertEqual(len(self.engine.progress["purchases"]), 2)
        locked = self.state["shop_rewards"][-1]
        with self.assertRaisesRegex(GameRuleError, "Level 8"):
            self.engine.purchase_reward(locked["id"])

    def test_archive_preserves_claim_history(self):
        self.engine.start_run("quest", self.quest["id"])
        self.engine.complete_quest(self.quest["id"], "done")
        snapshot = deepcopy(self.engine.progress["quest_claims"][0])
        self.engine.archive("quests", self.quest["id"])
        self.assertTrue(self.quest["archived"])
        self.assertEqual(self.engine.progress["quest_claims"][0], snapshot)

    def test_timer_never_grants_rewards(self):
        self.engine.set_timer("focus", 20)
        self.engine.update_timer(0, False)
        self.assertEqual((self.engine.progress["xp"], self.engine.progress["gold"]), (0, 0))

    def test_custom_content(self):
        path = self.engine.add_path("Python", "backlog", "Plan it", "Learn Python")
        quest = self.engine.add_quest(
            {
                "path_id": path["id"], "title": "Lists", "stage": "Foundations", "difficulty": "easy",
                "xp": 10, "gold": 5, "definition_of_done": "Create and explain one list.",
                "bonuses": [{"title": "No notes", "xp": 5, "gold": 2}],
            }
        )
        self.assertEqual(quest["path_id"], path["id"])
        self.assertTrue(quest["bonuses"][0]["id"])

    def test_content_validation_rejects_broken_references_and_duplicates(self):
        broken = create_default_state()
        broken["quests"][0]["path_id"] = "missing-path"
        with self.assertRaisesRegex(GameRuleError, "missing path"):
            validate_state(broken)
        broken = create_default_state()
        broken["quests"][1]["id"] = broken["quests"][0]["id"]
        with self.assertRaisesRegex(GameRuleError, "Duplicate IDs"):
            validate_state(broken)


if __name__ == "__main__":
    unittest.main()
