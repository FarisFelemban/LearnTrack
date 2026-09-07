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

    def test_reset_in_progress_quest_returns_it_to_available(self):
        self.engine.start_run("quest", self.quest["id"])

        self.engine.reset_quest(self.quest["id"])

        self.assertEqual(self.quest["status"], "available")
        self.assertIsNone(self.engine.progress["current_run"])
        self.assertEqual((self.engine.progress["xp"], self.engine.progress["gold"]), (0, 0))

    def test_completed_quest_can_be_replayed_without_more_rewards(self):
        self.engine.start_run("quest", self.quest["id"])
        original = self.engine.complete_quest(self.quest["id"], "Original proof")
        original_totals = (self.engine.progress["xp"], self.engine.progress["gold"])

        self.engine.reset_quest(self.quest["id"])
        self.engine.start_run("quest", self.quest["id"])
        with self.assertRaisesRegex(GameRuleError, "Evidence"):
            self.engine.complete_quest(self.quest["id"], " ")
        replay = self.engine.complete_quest(self.quest["id"], "Fresh replay proof")

        self.assertEqual((self.engine.progress["xp"], self.engine.progress["gold"]), original_totals)
        self.assertFalse(original.get("is_replay", False))
        self.assertTrue(replay["is_replay"])
        self.assertEqual((replay["xp_awarded"], replay["gold_awarded"]), (0, 0))
        self.assertEqual(len(self.engine.progress["quest_claims"]), 2)
        self.assertEqual(self.quest["status"], "completed")

        self.engine.reset_quest(self.quest["id"])
        self.engine.start_run("quest", self.quest["id"])
        second_replay = self.engine.complete_quest(self.quest["id"], "Another replay")
        self.assertTrue(second_replay["is_replay"])
        self.assertEqual((self.engine.progress["xp"], self.engine.progress["gold"]), original_totals)
        self.assertEqual(len(self.engine.progress["quest_claims"]), 3)
        validate_state(self.state)

    def test_reset_rejects_available_and_archived_quests(self):
        with self.assertRaisesRegex(GameRuleError, "in-progress or completed"):
            self.engine.reset_quest(self.quest["id"])
        self.engine.archive("quests", self.quest["id"])
        with self.assertRaisesRegex(GameRuleError, "Archived"):
            self.engine.reset_quest(self.quest["id"])

    def test_timer_never_grants_rewards(self):
        self.engine.set_timer("focus", 20)
        self.engine.update_timer(0, False)
        self.assertEqual((self.engine.progress["xp"], self.engine.progress["gold"]), (0, 0))

    def test_dashboard_background_and_timer_presets_are_saved_preferences(self):
        self.assertTrue(self.state["profile"]["show_current_run_background"])
        self.assertEqual(self.engine.timer_presets, ((20, 25, 30), 40))

        self.engine.set_current_run_background(False)
        self.engine.set_timer_presets((15, 35, 50), 60)

        self.assertFalse(self.state["profile"]["show_current_run_background"])
        self.assertEqual(self.engine.timer_presets, ((15, 35, 50), 60))
        validate_state(self.state)

    def test_timer_presets_require_three_values_in_the_supported_range(self):
        with self.assertRaisesRegex(GameRuleError, "exactly three"):
            self.engine.set_timer_presets((20, 30), 40)
        for values in (((0, 25, 30), 40), ((20, 25, 1441), 40), ((20, 25, 30), 0)):
            with self.assertRaisesRegex(GameRuleError, "1,440"):
                self.engine.set_timer_presets(*values)

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

    def test_standard_batch_import_is_balanced_and_atomic(self):
        before = len(self.state["quests"])
        raw = [
            {
                "stage": "Stage 1 — Basics",
                "title": "Learn values",
                "difficulty": "Easy",
                "definition_of_done": "Explain and use one value.",
                "xp": 999,
                "gold": 999,
            },
            {
                "stage": "Stage 2 — Practice",
                "title": "Build a small example",
                "difficulty": "hard",
                "definition_of_done": "Build and test the example.",
            },
        ]

        imported = self.engine.import_quests("path-fastapi", raw)

        self.assertEqual(len(self.state["quests"]), before + 2)
        self.assertEqual((imported[0]["xp"], imported[0]["gold"]), (10, 5))
        self.assertEqual((imported[1]["xp"], imported[1]["gold"]), (50, 20))
        self.assertEqual(imported[0]["bonuses"], [])
        self.assertTrue(all(item["status"] == "available" for item in imported))

        broken = raw + [{"stage": "", "title": "Broken", "difficulty": "easy", "definition_of_done": "Done"}]
        count_before_failure = len(self.state["quests"])
        with self.assertRaisesRegex(GameRuleError, "Quest 1 duplicates"):
            self.engine.import_quests("path-fastapi", broken)
        self.assertEqual(len(self.state["quests"]), count_before_failure)

    def test_batch_import_rejects_duplicates_and_oversized_batches(self):
        item = {
            "stage": "A Stage",
            "title": "A Quest",
            "difficulty": "normal",
            "definition_of_done": "Show a result.",
        }
        with self.assertRaisesRegex(GameRuleError, "Quest 2 duplicates"):
            self.engine.prepare_quest_import("path-fastapi", [item, dict(item)])
        with self.assertRaisesRegex(GameRuleError, "at most 100"):
            self.engine.prepare_quest_import("path-fastapi", [dict(item, title=f"Quest {i}") for i in range(101)])

    def test_batch_import_previews_without_saving_and_saves_once(self):
        changes = []
        engine = GameEngine(self.state, lambda state: changes.append(len(state["quests"])))
        batch = [
            {
                "stage": "Import Stage",
                "title": "Atomic quest",
                "difficulty": "easy",
                "definition_of_done": "Verify one atomic import.",
            }
        ]
        engine.prepare_quest_import("path-fastapi", batch)
        self.assertEqual(changes, [])
        engine.import_quests("path-fastapi", batch)
        self.assertEqual(changes, [19])

    def test_custom_batch_import_uses_supplied_rewards_and_bonuses(self):
        self.engine.set_custom_import_rewards(True)
        imported = self.engine.import_quests(
            "path-fastapi",
            [
                {
                    "stage": "Custom Stage",
                    "title": "Custom rewards",
                    "difficulty": "normal",
                    "xp": 37,
                    "gold": 14,
                    "definition_of_done": "Verify the custom result.",
                    "bonuses": [{"title": "Stretch goal", "xp": 8, "gold": 3}],
                }
            ],
        )
        self.assertEqual((imported[0]["xp"], imported[0]["gold"]), (37, 14))
        self.assertEqual((imported[0]["bonuses"][0]["xp"], imported[0]["bonuses"][0]["gold"]), (8, 3))
        self.assertTrue(imported[0]["bonuses"][0]["id"])

        with self.assertRaisesRegex(GameRuleError, "XP must be"):
            self.engine.prepare_quest_import(
                "path-fastapi",
                [{"stage": "Other", "title": "Missing rewards", "difficulty": "easy", "definition_of_done": "Done"}],
            )

    def test_standard_boss_import_is_balanced_and_atomic(self):
        before = len(self.state["bosses"])
        raw = [
            {
                "title": "Service Mastery",
                "victory_condition": "Build and verify a working service.",
                "requirements": [
                    {"text": "Implement the service", "mandatory": True},
                    {"text": "Document one tradeoff", "mandatory": False},
                ],
                "xp": 999,
                "gold": 999,
            }
        ]

        prepared = self.engine.prepare_boss_import("path-fastapi", raw)
        self.assertEqual(len(self.state["bosses"]), before)
        imported = self.engine.import_bosses("path-fastapi", raw)

        self.assertEqual(len(self.state["bosses"]), before + 1)
        self.assertEqual((imported[0]["xp"], imported[0]["gold"]), (150, 50))
        self.assertEqual(imported[0]["bonuses"], [])
        self.assertTrue(all(requirement["id"] for requirement in imported[0]["requirements"]))
        self.assertEqual(imported[0]["status"], "available")

        broken = raw + [{"title": "Broken", "victory_condition": "Done", "requirements": []}]
        count_before_failure = len(self.state["bosses"])
        with self.assertRaisesRegex(GameRuleError, "Boss 1 duplicates"):
            self.engine.import_bosses("path-fastapi", broken)
        self.assertEqual(len(self.state["bosses"]), count_before_failure)

    def test_boss_import_validates_requirements_and_duplicates(self):
        boss = {
            "title": "Unique Boss",
            "victory_condition": "Prove the result.",
            "requirements": [{"text": "Show the result", "mandatory": True}],
        }
        with self.assertRaisesRegex(GameRuleError, "Boss 2 duplicates"):
            self.engine.prepare_boss_import("path-fastapi", [boss, dict(boss)])
        invalid_flag = dict(
            boss,
            title="Another Boss",
            requirements=[{"text": "Show the result", "mandatory": "yes"}],
        )
        with self.assertRaisesRegex(GameRuleError, "true or false"):
            self.engine.prepare_boss_import("path-fastapi", [invalid_flag])

    def test_custom_boss_import_uses_supplied_rewards_and_bonuses(self):
        self.engine.set_custom_import_rewards(True)
        imported = self.engine.import_bosses(
            "path-fastapi",
            [
                {
                    "title": "Custom Boss",
                    "victory_condition": "Complete the custom challenge.",
                    "requirements": [{"text": "Finish it", "mandatory": True}],
                    "xp": 275,
                    "gold": 90,
                    "bonuses": [{"title": "Stretch goal", "xp": 25, "gold": 10}],
                }
            ],
        )
        self.assertEqual((imported[0]["xp"], imported[0]["gold"]), (275, 90))
        self.assertEqual((imported[0]["bonuses"][0]["xp"], imported[0]["bonuses"][0]["gold"]), (25, 10))
        self.assertTrue(imported[0]["bonuses"][0]["id"])

    def test_old_profile_without_custom_import_setting_remains_valid(self):
        self.state["profile"].pop("allow_custom_import_rewards")
        self.state["profile"].pop("show_current_run_background")
        self.state["profile"].pop("timer_presets")
        validate_state(self.state)
        engine = GameEngine(self.state)
        self.assertFalse(engine.state["profile"].get("allow_custom_import_rewards", False))
        self.assertTrue(engine.state["profile"].get("show_current_run_background", True))
        self.assertEqual(engine.timer_presets, ((20, 25, 30), 40))

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
