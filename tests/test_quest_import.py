import unittest

from learntrack.engine import GameRuleError
from learntrack.quest_import import build_quest_prompt, parse_quest_batch


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


if __name__ == "__main__":
    unittest.main()
