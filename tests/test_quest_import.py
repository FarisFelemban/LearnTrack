import unittest

from learntrack.engine import GameRuleError
from learntrack.quest_import import build_boss_prompt, build_quest_prompt, parse_boss_batch, parse_quest_batch


class QuestImportFormatTests(unittest.TestCase):
    def test_plain_and_fenced_json_are_accepted(self):
        body = '{"quests": [{"title": "One"}]}'
        self.assertEqual(parse_quest_batch(body)[0]["title"], "One")
        self.assertEqual(parse_quest_batch(f"```json\n{body}\n```")[0]["title"], "One")

    def test_invalid_json_and_wrong_top_level_are_rejected(self):
        with self.assertRaisesRegex(GameRuleError, "not valid JSON"):
            parse_quest_batch("not json")
        with self.assertRaisesRegex(GameRuleError, "top level"):
            parse_quest_batch('{"quests": [], "explanation": "extra"}')

    def test_prompt_changes_with_custom_reward_setting(self):
        balanced = build_quest_prompt("Lists", "Python", False)
        custom = build_quest_prompt("Lists", "Python", True)
        self.assertIn("Learning topic: Lists", balanced)
        self.assertIn("Do not include XP", balanced)
        self.assertNotIn('"bonuses"', balanced)
        self.assertIn('"xp"', custom)
        self.assertIn('"bonuses"', custom)

    def test_boss_plain_and_fenced_json_are_accepted(self):
        body = '{"bosses": [{"title": "Final challenge"}]}'
        self.assertEqual(parse_boss_batch(body)[0]["title"], "Final challenge")
        self.assertEqual(parse_boss_batch(f"```json\n{body}\n```")[0]["title"], "Final challenge")

    def test_boss_parser_rejects_wrong_top_level(self):
        with self.assertRaisesRegex(GameRuleError, "top level"):
            parse_boss_batch('{"quests": []}')

    def test_boss_prompt_changes_with_custom_reward_setting(self):
        standard = build_boss_prompt("FastAPI mastery", "Python", False)
        custom = build_boss_prompt("FastAPI mastery", "Python", True)
        self.assertIn("Learning topic: FastAPI mastery", standard)
        self.assertIn("150 XP and 50 Gold", standard)
        self.assertNotIn('"bonuses"', standard)
        self.assertIn('"requirements"', standard)
        self.assertIn('"xp"', custom)
        self.assertIn('"bonuses"', custom)


if __name__ == "__main__":
    unittest.main()
