"""Parsing and prompt generation for user-driven AI content imports."""

from __future__ import annotations

import json

from .engine import GameRuleError


def parse_quest_batch(text: str) -> list[dict]:
    """Read the documented JSON object, allowing one surrounding code fence."""

    content = text.strip()
    if content.startswith("```") and content.endswith("```"):
        lines = content.splitlines()
        if len(lines) >= 3 and lines[0].strip().lower() in ("```", "```json") and lines[-1].strip() == "```":
            content = "\n".join(lines[1:-1]).strip()
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise GameRuleError(f"The pasted response is not valid JSON (line {exc.lineno}, column {exc.colno}).") from exc
    if not isinstance(payload, dict) or set(payload) != {"quests"}:
        raise GameRuleError('The top level must be one JSON object containing only a "quests" list.')
    quests = payload["quests"]
    if not isinstance(quests, list):
        raise GameRuleError('"quests" must be a JSON list.')
    return quests


def parse_boss_batch(text: str) -> list[dict]:
    """Read a boss JSON object, allowing one surrounding code fence."""

    content = text.strip()
    if content.startswith("```") and content.endswith("```"):
        lines = content.splitlines()
        if len(lines) >= 3 and lines[0].strip().lower() in ("```", "```json") and lines[-1].strip() == "```":
            content = "\n".join(lines[1:-1]).strip()
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise GameRuleError(f"The pasted response is not valid JSON (line {exc.lineno}, column {exc.colno}).") from exc
    if not isinstance(payload, dict) or set(payload) != {"bosses"}:
        raise GameRuleError('The top level must be one JSON object containing only a "bosses" list.')
    bosses = payload["bosses"]
    if not isinstance(bosses, list):
        raise GameRuleError('"bosses" must be a JSON list.')
    return bosses


def build_quest_prompt(topic: str, path_name: str, custom_rewards: bool) -> str:
    """Build the exact prompt users copy into their preferred AI tool."""

    if custom_rewards:
        example = {
            "quests": [
                {
                    "stage": "Stage 1 — Foundations",
                    "title": "Example quest",
                    "difficulty": "easy",
                    "xp": 10,
                    "gold": 5,
                    "definition_of_done": "A specific, verifiable result.",
                    "bonuses": [{"title": "Optional challenge", "xp": 5, "gold": 2}],
                }
            ]
        }
        reward_rules = (
            "Choose balanced non-negative whole-number XP and Gold values. Bonuses are optional; each bonus must have "
            "a title and non-negative whole-number XP and Gold values."
        )
    else:
        example = {
            "quests": [
                {
                    "stage": "Stage 1 — Foundations",
                    "title": "Example quest",
                    "difficulty": "easy",
                    "definition_of_done": "A specific, verifiable result.",
                }
            ]
        }
        reward_rules = (
            "Do not include XP, Gold, or bonuses. LearnTrack assigns rewards automatically: Easy 10 XP/5 Gold, "
            "Normal 25 XP/10 Gold, and Hard 50 XP/20 Gold."
        )
    schema = json.dumps(example, indent=2, ensure_ascii=False)
    return (
        "Create a progressive set of learning quests for LearnTrack.\n\n"
        f"Learning path: {path_name.strip()}\n"
        f"Learning topic: {topic.strip()}\n\n"
        "Decide how many quests are appropriate for useful coverage, up to 100. Organize them into clearly named "
        "stages, order them from beginner foundations to practical application, and make every definition_of_done "
        "specific and verifiable. Use only easy, normal, or hard for difficulty. Avoid duplicate stage/title pairs.\n\n"
        f"{reward_rules}\n\n"
        "Return only valid JSON matching this exact shape, with no explanation or Markdown fences:\n"
        f"{schema}"
    )


def build_boss_prompt(topic: str, path_name: str, custom_rewards: bool) -> str:
    """Build the exact boss-generation prompt users copy into an AI tool."""

    boss = {
        "title": "Example boss",
        "victory_condition": "A specific, verifiable result that proves mastery.",
        "requirements": [
            {"text": "Complete a required part of the challenge", "mandatory": True},
            {"text": "Complete an optional stretch requirement", "mandatory": False},
        ],
    }
    if custom_rewards:
        boss.update(
            {
                "xp": 150,
                "gold": 50,
                "bonuses": [{"title": "Optional objective", "xp": 25, "gold": 10}],
            }
        )
        reward_rules = (
            "Choose balanced non-negative whole-number XP and Gold values. Bonuses are optional; each bonus must have "
            "a title and non-negative whole-number XP and Gold values."
        )
    else:
        reward_rules = (
            "Do not include XP, Gold, or bonuses. LearnTrack assigns every boss a standard reward of 150 XP and 50 Gold."
        )
    schema = json.dumps({"bosses": [boss]}, indent=2, ensure_ascii=False)
    return (
        "Create a set of mastery bosses for LearnTrack.\n\n"
        f"Learning path: {path_name.strip()}\n"
        f"Learning topic: {topic.strip()}\n\n"
        "Decide how many bosses are appropriate, up to 100. Each boss should test practical mastery, have a unique "
        "title, a specific and verifiable victory condition, and at least one requirement. Set mandatory to true for "
        "every requirement needed for victory and false only for optional checklist items.\n\n"
        f"{reward_rules}\n\n"
        "Return only valid JSON matching this exact shape, with no explanation or Markdown fences:\n"
        f"{schema}"
    )
