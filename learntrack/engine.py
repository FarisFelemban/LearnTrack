"""Pure game rules for LearnTrack.

The UI only asks this class to perform actions; reward and history rules live
here so they can be tested without opening a window.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Callable, Iterable
from uuid import uuid4

from .constants import (
    BREAK_DURATION,
    DIFFICULTIES,
    LEVEL_THRESHOLDS,
    PATH_STATUSES,
    QUEST_STATUSES,
    SCHEMA_VERSION,
    TIMER_DURATIONS,
)


class GameRuleError(ValueError):
    """Raised when an action would break a game rule."""


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def level_for_xp(xp: int) -> int:
    """Return the highest defined level reached by *xp*."""
    if xp < 0:
        raise GameRuleError("XP cannot be negative.")
    return max(level for level, threshold in LEVEL_THRESHOLDS.items() if xp >= threshold)


def next_level_progress(xp: int) -> tuple[int, int, int | None]:
    """Return XP within this level, span to the next level, and next level."""
    level = level_for_xp(xp)
    if level == max(LEVEL_THRESHOLDS):
        return xp - LEVEL_THRESHOLDS[level], 0, None
    start = LEVEL_THRESHOLDS[level]
    end = LEVEL_THRESHOLDS[level + 1]
    return xp - start, end - start, level + 1


def validate_state(state: object) -> None:
    """Validate the structure and important references of an imported save."""
    if not isinstance(state, dict):
        raise GameRuleError("The save must be a JSON object.")
    required = {
        "schema_version",
        "profile",
        "paths",
        "quests",
        "bosses",
        "shop_rewards",
        "progress",
    }
    missing = required.difference(state)
    if missing:
        raise GameRuleError(f"Save is missing: {', '.join(sorted(missing))}.")
    if state["schema_version"] != SCHEMA_VERSION:
        raise GameRuleError(
            f"Unsupported save schema {state['schema_version']!r}; expected {SCHEMA_VERSION}."
        )
    if not isinstance(state["profile"], dict) or not str(state["profile"].get("player_name", "")).strip():
        raise GameRuleError("The player name cannot be empty.")
    if "allow_custom_import_rewards" in state["profile"] and not isinstance(
        state["profile"]["allow_custom_import_rewards"], bool
    ):
        raise GameRuleError("The custom import rewards setting must be true or false.")
    if "show_current_run_background" in state["profile"] and not isinstance(
        state["profile"]["show_current_run_background"], bool
    ):
        raise GameRuleError("The current-run background setting must be true or false.")
    if "timer_presets" in state["profile"]:
        presets = state["profile"]["timer_presets"]
        if not isinstance(presets, dict) or set(presets) != {"focus", "break"}:
            raise GameRuleError("Timer presets must contain focus and break values.")
        focus_presets = presets["focus"]
        if not isinstance(focus_presets, list) or len(focus_presets) != 3:
            raise GameRuleError("Timer presets need exactly three focus values.")
        timer_values = focus_presets + [presets["break"]]
        if any(isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 1440 for value in timer_values):
            raise GameRuleError("Every timer preset must be a whole number from 1 to 1,440 minutes.")
    for collection in ("paths", "quests", "bosses", "shop_rewards"):
        if not isinstance(state[collection], list):
            raise GameRuleError(f"'{collection}' must be a list.")
        ids = [item.get("id") for item in state[collection] if isinstance(item, dict)]
        if len(ids) != len(state[collection]) or any(not isinstance(item_id, str) or not item_id for item_id in ids):
            raise GameRuleError(f"Every {collection} item needs a non-empty ID.")
        if len(ids) != len(set(ids)):
            raise GameRuleError(f"Duplicate IDs found in {collection}.")

    path_ids = {path["id"] for path in state["paths"]}
    for path in state["paths"]:
        if path.get("status") not in PATH_STATUSES:
            raise GameRuleError(f"Invalid status on path '{path['id']}'.")
    for collection in ("quests", "bosses"):
        for item in state[collection]:
            if item.get("path_id") not in path_ids:
                raise GameRuleError(f"{collection[:-1].title()} '{item['id']}' refers to a missing path.")
            for field in ("xp", "gold"):
                if not isinstance(item.get(field), int) or item[field] < 0:
                    raise GameRuleError(f"{collection[:-1].title()} '{item['id']}' has invalid {field}.")
            bonuses = item.get("bonuses", [])
            if not isinstance(bonuses, list) or any(not isinstance(bonus, dict) for bonus in bonuses):
                raise GameRuleError(f"Invalid bonuses on '{item['id']}'.")
            bonus_ids = [bonus.get("id") for bonus in bonuses]
            if any(not bonus_id for bonus_id in bonus_ids) or len(bonus_ids) != len(set(bonus_ids)):
                raise GameRuleError(f"Bonus IDs must be present and unique on '{item['id']}'.")
            for bonus in bonuses:
                if not str(bonus.get("title", "")).strip():
                    raise GameRuleError(f"A bonus on '{item['id']}' needs a title.")
                for field in ("xp", "gold"):
                    if not isinstance(bonus.get(field), int) or bonus[field] < 0:
                        raise GameRuleError(f"A bonus on '{item['id']}' has invalid {field}.")
            if not str(item.get("title", "")).strip():
                raise GameRuleError(f"{collection[:-1].title()} '{item['id']}' needs a title.")
            if item.get("status") not in QUEST_STATUSES:
                raise GameRuleError(f"{collection[:-1].title()} '{item['id']}' has an invalid status.")
    for quest in state["quests"]:
        if quest.get("difficulty") not in set(DIFFICULTIES).difference({"boss"}):
            raise GameRuleError(f"Quest '{quest['id']}' has an invalid difficulty.")
        if not str(quest.get("stage", "")).strip() or not str(quest.get("definition_of_done", "")).strip():
            raise GameRuleError(f"Quest '{quest['id']}' needs a stage and definition of done.")
    for boss in state["bosses"]:
        requirements = boss.get("requirements")
        if not isinstance(requirements, list):
            raise GameRuleError(f"Boss '{boss['id']}' has invalid requirements.")
        requirement_ids = [requirement.get("id") for requirement in requirements if isinstance(requirement, dict)]
        if len(requirement_ids) != len(requirements) or any(not item for item in requirement_ids):
            raise GameRuleError(f"Boss '{boss['id']}' has a requirement without an ID.")
        if len(requirement_ids) != len(set(requirement_ids)):
            raise GameRuleError(f"Boss '{boss['id']}' has duplicate requirement IDs.")
        if not requirements or not str(boss.get("victory_condition", "")).strip():
            raise GameRuleError(f"Boss '{boss['id']}' needs a victory condition and requirements.")
        if any(not str(requirement.get("text", "")).strip() for requirement in requirements):
            raise GameRuleError(f"Boss '{boss['id']}' has an empty requirement.")
    for reward in state["shop_rewards"]:
        if not str(reward.get("title", "")).strip():
            raise GameRuleError(f"Reward '{reward['id']}' needs a title.")
        if not isinstance(reward.get("cost"), int) or reward["cost"] < 0:
            raise GameRuleError(f"Reward '{reward['id']}' has an invalid cost.")
        if not isinstance(reward.get("level_required"), int) or reward["level_required"] < 1:
            raise GameRuleError(f"Reward '{reward['id']}' has an invalid level requirement.")

    progress = state["progress"]
    if not isinstance(progress, dict):
        raise GameRuleError("Progress must be an object.")
    for field in ("xp", "gold", "total_gold_earned"):
        if not isinstance(progress.get(field), int) or progress[field] < 0:
            raise GameRuleError(f"Progress field '{field}' must be a non-negative integer.")
    for field in ("quest_claims", "boss_claims", "purchases", "activity"):
        if not isinstance(progress.get(field), list):
            raise GameRuleError(f"Progress field '{field}' must be a list.")
    for field in ("quest_claims", "boss_claims"):
        claims = progress[field]
        claim_ids = [claim.get("id") for claim in claims if isinstance(claim, dict)]
        if len(claim_ids) != len(claims) or any(not claim_id for claim_id in claim_ids):
            raise GameRuleError(f"Progress field '{field}' contains an invalid claim.")
        if len(claim_ids) != len(set(claim_ids)):
            raise GameRuleError(f"Progress field '{field}' contains duplicate claims.")
        rewarded_items = [claim.get("item_id") for claim in claims if not claim.get("is_replay", False)]
        if len(rewarded_items) != len(set(rewarded_items)):
            raise GameRuleError(f"Progress field '{field}' contains duplicate rewarded claims.")
        if field == "boss_claims" and any(claim.get("is_replay", False) for claim in claims):
            raise GameRuleError("Boss claims cannot be replays.")
        rewarded_item_ids = set(rewarded_items)
        for claim in claims:
            if not str(claim.get("evidence", "")).strip() or not isinstance(claim.get("snapshot"), dict):
                raise GameRuleError("Every completion claim needs evidence and a content snapshot.")
            if "is_replay" in claim and not isinstance(claim["is_replay"], bool):
                raise GameRuleError("A replay marker must be true or false.")
            if claim.get("is_replay", False):
                if claim.get("item_id") not in rewarded_item_ids:
                    raise GameRuleError("A quest replay needs an earlier rewarded completion.")
                if claim.get("xp_awarded") != 0 or claim.get("gold_awarded") != 0:
                    raise GameRuleError("Quest replays cannot award XP or Gold.")
    timer = progress.get("timer")
    if not isinstance(timer, dict):
        raise GameRuleError("Timer data is missing.")
    if timer.get("mode") not in ("focus", "break"):
        raise GameRuleError("Timer mode must be 'focus' or 'break'.")
    for field in ("duration_seconds", "remaining_seconds"):
        if not isinstance(timer.get(field), int) or timer[field] < 0:
            raise GameRuleError(f"Timer field '{field}' is invalid.")
    if timer["remaining_seconds"] > timer["duration_seconds"]:
        raise GameRuleError("Timer remaining time exceeds its duration.")
    current = progress.get("current_run")
    if current is not None:
        if not isinstance(current, dict) or current.get("kind") not in ("quest", "boss"):
            raise GameRuleError("The current run is invalid.")
        collection = state["quests"] if current["kind"] == "quest" else state["bosses"]
        if current.get("item_id") not in {item["id"] for item in collection}:
            raise GameRuleError("The current run refers to missing content.")


class GameEngine:
    """Apply game actions to one mutable state dictionary."""

    def __init__(self, state: dict, on_change: Callable[[dict], None] | None = None):
        validate_state(state)
        self.state = state
        self.on_change = on_change

    @property
    def progress(self) -> dict:
        return self.state["progress"]

    @property
    def level(self) -> int:
        return level_for_xp(self.progress["xp"])

    @property
    def timer_presets(self) -> tuple[tuple[int, int, int], int]:
        presets = self.state["profile"].get("timer_presets")
        if presets is None:
            return tuple(TIMER_DURATIONS), BREAK_DURATION
        return tuple(presets["focus"]), presets["break"]

    def _changed(self) -> None:
        self.state["updated_at"] = now_iso()
        if self.on_change:
            self.on_change(self.state)

    def _activity(self, message: str, kind: str) -> None:
        self.progress["activity"].insert(
            0,
            {"id": str(uuid4()), "timestamp": now_iso(), "kind": kind, "message": message},
        )
        del self.progress["activity"][200:]

    def _find(self, collection: str, item_id: str) -> dict:
        for item in self.state[collection]:
            if item["id"] == item_id:
                return item
        raise GameRuleError(f"Unknown {collection[:-1]} ID: {item_id}")

    def set_player_name(self, name: str) -> None:
        name = name.strip()
        if not name:
            raise GameRuleError("Player name cannot be empty.")
        self.state["profile"]["player_name"] = name
        self._changed()

    def set_animations(self, enabled: bool) -> None:
        self.state["profile"]["animations_enabled"] = bool(enabled)
        self._changed()

    def set_custom_import_rewards(self, enabled: bool) -> None:
        self.state["profile"]["allow_custom_import_rewards"] = bool(enabled)
        self._changed()

    def set_current_run_background(self, enabled: bool) -> None:
        self.state["profile"]["show_current_run_background"] = bool(enabled)
        self._changed()

    def set_timer_presets(self, focus_minutes: Iterable[int], break_minutes: int) -> None:
        focus_values = list(focus_minutes)
        if len(focus_values) != 3:
            raise GameRuleError("Choose exactly three focus timer values.")
        values = focus_values + [break_minutes]
        if any(isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 1440 for value in values):
            raise GameRuleError("Timer values must be whole minutes from 1 to 1,440.")
        self.state["profile"]["timer_presets"] = {"focus": focus_values, "break": break_minutes}
        self._changed()

    def path_xp(self, path_id: str) -> int:
        claims = self.progress["quest_claims"] + self.progress["boss_claims"]
        return sum(claim["xp_awarded"] for claim in claims if claim["path_id"] == path_id)

    def start_run(self, kind: str, item_id: str) -> dict | None:
        if kind not in ("quest", "boss"):
            raise GameRuleError("A run must be a quest or boss.")
        collection = "quests" if kind == "quest" else "bosses"
        item = self._find(collection, item_id)
        if item.get("archived") or item.get("status") == "completed":
            raise GameRuleError("Archived or completed content cannot be started.")
        previous = deepcopy(self.progress.get("current_run"))
        if previous and previous["kind"] == kind and previous["item_id"] == item_id:
            return previous
        if previous:
            old_collection = "quests" if previous["kind"] == "quest" else "bosses"
            try:
                old_item = self._find(old_collection, previous["item_id"])
                if old_item.get("status") == "in_progress":
                    old_item["status"] = "available"
            except GameRuleError:
                pass
        item["status"] = "in_progress"
        self.progress["current_run"] = {
            "kind": kind,
            "item_id": item_id,
            "started_at": now_iso(),
        }
        self._activity(f"Started {kind}: {item['title']}", "run_started")
        self._changed()
        return previous

    def clear_current_run(self) -> None:
        current = self.progress.get("current_run")
        if not current:
            return
        collection = "quests" if current["kind"] == "quest" else "bosses"
        try:
            item = self._find(collection, current["item_id"])
            if item.get("status") == "in_progress":
                item["status"] = "available"
        except GameRuleError:
            pass
        self.progress["current_run"] = None
        self._activity("Cleared the current run", "run_cleared")
        self._changed()

    def _require_current(self, kind: str, item_id: str) -> None:
        current = self.progress.get("current_run")
        if not current or current.get("kind") != kind or current.get("item_id") != item_id:
            raise GameRuleError(f"Start this {kind} before claiming it.")

    @staticmethod
    def _selected_bonuses(item: dict, selected_ids: Iterable[str]) -> list[dict]:
        selected_ids = list(selected_ids)
        if len(selected_ids) != len(set(selected_ids)):
            raise GameRuleError("A bonus cannot be selected twice.")
        available = {bonus["id"]: bonus for bonus in item.get("bonuses", [])}
        unknown = set(selected_ids).difference(available)
        if unknown:
            raise GameRuleError("One or more selected bonuses do not exist.")
        return [deepcopy(available[bonus_id]) for bonus_id in selected_ids]

    def _award_claim(self, kind: str, item: dict, evidence: str, bonuses: list[dict]) -> dict:
        evidence = evidence.strip()
        if not evidence:
            raise GameRuleError("Evidence is required before claiming a reward.")
        claims_key = "quest_claims" if kind == "quest" else "boss_claims"
        if any(claim["item_id"] == item["id"] for claim in self.progress[claims_key]):
            raise GameRuleError("This reward has already been claimed.")
        bonus_xp = sum(bonus["xp"] for bonus in bonuses)
        bonus_gold = sum(bonus["gold"] for bonus in bonuses)
        xp_awarded = item["xp"] + bonus_xp
        gold_awarded = item["gold"] + bonus_gold
        previous_level = self.level
        claim = {
            "id": str(uuid4()),
            "kind": kind,
            "item_id": item["id"],
            "path_id": item["path_id"],
            "completed_at": now_iso(),
            "evidence": evidence,
            "xp_awarded": xp_awarded,
            "gold_awarded": gold_awarded,
            "selected_bonuses": bonuses,
            "snapshot": deepcopy(item),
        }
        self.progress[claims_key].insert(0, claim)
        self.progress["xp"] += xp_awarded
        self.progress["gold"] += gold_awarded
        self.progress["total_gold_earned"] += gold_awarded
        item["status"] = "completed"
        self.progress["current_run"] = None
        self._activity(
            f"Completed {item['title']} (+{xp_awarded} XP, +{gold_awarded} Gold)",
            f"{kind}_completed",
        )
        claim["level_before"] = previous_level
        claim["level_after"] = self.level
        self._changed()
        return claim

    def complete_quest(self, quest_id: str, evidence: str, bonus_ids: Iterable[str] = ()) -> dict:
        self._require_current("quest", quest_id)
        quest = self._find("quests", quest_id)
        bonus_ids = list(bonus_ids)
        previous_claims = [claim for claim in self.progress["quest_claims"] if claim["item_id"] == quest_id]
        if previous_claims:
            if quest.get("status") != "in_progress":
                raise GameRuleError("This reward has already been claimed. Reset the quest before replaying it.")
            if bonus_ids:
                raise GameRuleError("Quest replays cannot claim bonus rewards.")
            return self._record_quest_replay(quest, evidence)
        bonuses = self._selected_bonuses(quest, bonus_ids)
        return self._award_claim("quest", quest, evidence, bonuses)

    def _record_quest_replay(self, quest: dict, evidence: str) -> dict:
        evidence = evidence.strip()
        if not evidence:
            raise GameRuleError("Evidence is required before completing a replay.")
        current_level = self.level
        claim = {
            "id": str(uuid4()),
            "kind": "quest",
            "item_id": quest["id"],
            "path_id": quest["path_id"],
            "completed_at": now_iso(),
            "evidence": evidence,
            "xp_awarded": 0,
            "gold_awarded": 0,
            "selected_bonuses": [],
            "snapshot": deepcopy(quest),
            "is_replay": True,
            "level_before": current_level,
            "level_after": current_level,
        }
        self.progress["quest_claims"].insert(0, claim)
        quest["status"] = "completed"
        self.progress["current_run"] = None
        self._activity(f"Replayed quest: {quest['title']} (no additional rewards)", "quest_replayed")
        self._changed()
        return claim

    def complete_boss(
        self,
        boss_id: str,
        evidence: str,
        checked_requirement_ids: Iterable[str],
        bonus_ids: Iterable[str] = (),
    ) -> dict:
        self._require_current("boss", boss_id)
        boss = self._find("bosses", boss_id)
        checked = set(checked_requirement_ids)
        mandatory = {item["id"] for item in boss["requirements"] if item.get("mandatory", True)}
        if not mandatory.issubset(checked):
            raise GameRuleError("Every mandatory boss requirement must be checked.")
        known = {item["id"] for item in boss["requirements"]}
        if not checked.issubset(known):
            raise GameRuleError("One or more checked requirements do not exist.")
        bonuses = self._selected_bonuses(boss, bonus_ids)
        claim = self._award_claim("boss", boss, evidence, bonuses)
        claim["checked_requirement_ids"] = sorted(checked)
        self._changed()
        return claim

    def purchase_reward(self, reward_id: str) -> dict:
        reward = self._find("shop_rewards", reward_id)
        if reward.get("archived"):
            raise GameRuleError("Archived rewards cannot be purchased.")
        if self.level < reward["level_required"]:
            raise GameRuleError(f"This reward unlocks at Level {reward['level_required']}.")
        if self.progress["gold"] < reward["cost"]:
            raise GameRuleError("You do not have enough Gold for this reward.")
        self.progress["gold"] -= reward["cost"]
        purchase = {
            "id": str(uuid4()),
            "reward_id": reward["id"],
            "purchased_at": now_iso(),
            "gold_spent": reward["cost"],
            "gold_remaining": self.progress["gold"],
            "snapshot": deepcopy(reward),
        }
        self.progress["purchases"].insert(0, purchase)
        self._activity(f"Purchased {reward['title']} (-{reward['cost']} Gold)", "purchase")
        self._changed()
        return purchase

    def add_path(self, name: str, status: str, objective: str, goal: str) -> dict:
        if not name.strip():
            raise GameRuleError("Path name is required.")
        if status not in PATH_STATUSES:
            raise GameRuleError("Invalid path status.")
        item = {
            "id": f"path-{uuid4()}",
            "name": name.strip(),
            "status": status,
            "objective": objective.strip(),
            "goal": goal.strip(),
            "archived": False,
        }
        self.state["paths"].append(item)
        self._activity(f"Added learning path: {item['name']}", "content_added")
        self._changed()
        return item

    def update_path(self, path_id: str, **fields: object) -> None:
        item = self._find("paths", path_id)
        if "name" in fields and not str(fields["name"]).strip():
            raise GameRuleError("Path name is required.")
        if "status" in fields and fields["status"] not in PATH_STATUSES:
            raise GameRuleError("Invalid path status.")
        for key in ("name", "status", "objective", "goal"):
            if key in fields:
                item[key] = str(fields[key]).strip()
        self._changed()

    def add_quest(self, data: dict) -> dict:
        self._find("paths", data.get("path_id", ""))
        required = ("title", "stage", "difficulty", "definition_of_done")
        if any(not str(data.get(field, "")).strip() for field in required):
            raise GameRuleError("Title, stage, difficulty, and definition of done are required.")
        if data["difficulty"] not in set(DIFFICULTIES).difference({"boss"}):
            raise GameRuleError("Invalid quest difficulty.")
        item = {
            "id": f"quest-{uuid4()}",
            "path_id": data["path_id"],
            "stage": str(data["stage"]).strip(),
            "title": str(data["title"]).strip(),
            "difficulty": str(data["difficulty"]),
            "xp": self._non_negative_int(data.get("xp"), "XP"),
            "gold": self._non_negative_int(data.get("gold"), "Gold"),
            "definition_of_done": str(data["definition_of_done"]).strip(),
            "bonuses": self._normalise_bonuses(data.get("bonuses", [])),
            "status": "available",
            "archived": False,
        }
        self.state["quests"].append(item)
        self._activity(f"Added quest: {item['title']}", "content_added")
        self._changed()
        return item

    def prepare_quest_import(self, path_id: str, quests: object) -> list[dict]:
        """Validate and normalize a quest batch without changing player state."""

        path = self._find("paths", path_id)
        if path.get("archived"):
            raise GameRuleError("Choose a learning path that is not archived.")
        if not isinstance(quests, list) or not quests:
            raise GameRuleError("The import needs at least one quest.")
        if len(quests) > 100:
            raise GameRuleError("A single import can contain at most 100 quests.")

        custom_rewards = self.state["profile"].get("allow_custom_import_rewards", False)
        known_keys = {
            self._quest_import_key(item.get("stage", ""), item.get("title", ""))
            for item in self.state["quests"]
            if item.get("path_id") == path_id
        }
        prepared = []
        for index, data in enumerate(quests, start=1):
            prefix = f"Quest {index}"
            if not isinstance(data, dict):
                raise GameRuleError(f"{prefix} must be a JSON object.")
            values = {}
            for field, label in (
                ("stage", "stage"),
                ("title", "title"),
                ("definition_of_done", "definition of done"),
            ):
                value = data.get(field)
                if not isinstance(value, str) or not value.strip():
                    raise GameRuleError(f"{prefix} needs a non-empty {label}.")
                values[field] = value.strip()
            difficulty = data.get("difficulty")
            if not isinstance(difficulty, str) or difficulty.strip().lower() not in {"easy", "normal", "hard"}:
                raise GameRuleError(f"{prefix} difficulty must be easy, normal, or hard.")
            difficulty = difficulty.strip().lower()
            duplicate_key = self._quest_import_key(values["stage"], values["title"])
            if duplicate_key in known_keys:
                raise GameRuleError(f"{prefix} duplicates an existing or earlier quest in this learning path.")
            known_keys.add(duplicate_key)

            if custom_rewards:
                try:
                    xp = self._strict_non_negative_int(data.get("xp"), "XP")
                    gold = self._strict_non_negative_int(data.get("gold"), "Gold")
                    bonuses = data.get("bonuses", [])
                    if not isinstance(bonuses, list) or any(not isinstance(bonus, dict) for bonus in bonuses):
                        raise GameRuleError("Bonuses must be a JSON list.")
                    for bonus in bonuses:
                        if not isinstance(bonus.get("title"), str) or not bonus["title"].strip():
                            raise GameRuleError("Every bonus needs a title.")
                        self._strict_non_negative_int(bonus.get("xp"), "Bonus XP")
                        self._strict_non_negative_int(bonus.get("gold"), "Bonus Gold")
                    bonuses = self._normalise_bonuses(bonuses)
                except GameRuleError as exc:
                    raise GameRuleError(f"{prefix}: {exc}") from exc
            else:
                xp = DIFFICULTIES[difficulty]["xp"]
                gold = DIFFICULTIES[difficulty]["gold"]
                bonuses = []

            prepared.append(
                {
                    "id": f"quest-{uuid4()}",
                    "path_id": path_id,
                    "stage": values["stage"],
                    "title": values["title"],
                    "difficulty": difficulty,
                    "xp": xp,
                    "gold": gold,
                    "definition_of_done": values["definition_of_done"],
                    "bonuses": bonuses,
                    "status": "available",
                    "archived": False,
                }
            )
        return prepared

    def import_quests(self, path_id: str, quests: object) -> list[dict]:
        """Atomically add a fully validated batch of user-generated quests."""

        prepared = self.prepare_quest_import(path_id, quests)
        self.state["quests"].extend(prepared)
        path = self._find("paths", path_id)
        self._activity(f"Imported {len(prepared)} quests into {path['name']}", "content_imported")
        self._changed()
        return prepared

    def reset_quest(self, quest_id: str) -> None:
        quest = self._find("quests", quest_id)
        if quest.get("archived") or quest.get("status") == "archived":
            raise GameRuleError("Archived quests cannot be reset.")
        if quest.get("status") not in ("in_progress", "completed"):
            raise GameRuleError("Only in-progress or completed quests can be reset.")
        was_completed = quest["status"] == "completed"
        quest["status"] = "available"
        current = self.progress.get("current_run")
        if current and current.get("kind") == "quest" and current.get("item_id") == quest_id:
            self.progress["current_run"] = None
        action = "Opened quest for a reward-free replay" if was_completed else "Reset in-progress quest"
        self._activity(f"{action}: {quest['title']}", "quest_reset")
        self._changed()

    def update_quest(self, quest_id: str, data: dict) -> None:
        item = self._find("quests", quest_id)
        updated = self._quest_update_data(data)
        item.update(updated)
        self._changed()

    def add_boss(self, data: dict) -> dict:
        self._find("paths", data.get("path_id", ""))
        if not str(data.get("title", "")).strip() or not str(data.get("victory_condition", "")).strip():
            raise GameRuleError("Boss title and victory condition are required.")
        requirements = self._normalise_requirements(data.get("requirements", []))
        if not requirements:
            raise GameRuleError("A boss needs at least one requirement.")
        item = {
            "id": f"boss-{uuid4()}",
            "path_id": data["path_id"],
            "title": str(data["title"]).strip(),
            "victory_condition": str(data["victory_condition"]).strip(),
            "requirements": requirements,
            "xp": self._non_negative_int(data.get("xp"), "XP"),
            "gold": self._non_negative_int(data.get("gold"), "Gold"),
            "bonuses": self._normalise_bonuses(data.get("bonuses", [])),
            "status": "available",
            "archived": False,
        }
        self.state["bosses"].append(item)
        self._activity(f"Added boss: {item['title']}", "content_added")
        self._changed()
        return item

    def update_boss(self, boss_id: str, data: dict) -> None:
        item = self._find("bosses", boss_id)
        if not str(data.get("title", "")).strip() or not str(data.get("victory_condition", "")).strip():
            raise GameRuleError("Boss title and victory condition are required.")
        requirements = self._normalise_requirements(data.get("requirements", []))
        if not requirements:
            raise GameRuleError("A boss needs at least one requirement.")
        item.update(
            {
                "path_id": data["path_id"],
                "title": str(data["title"]).strip(),
                "victory_condition": str(data["victory_condition"]).strip(),
                "requirements": requirements,
                "xp": self._non_negative_int(data.get("xp"), "XP"),
                "gold": self._non_negative_int(data.get("gold"), "Gold"),
                "bonuses": self._normalise_bonuses(data.get("bonuses", [])),
            }
        )
        self._changed()

    def add_shop_reward(self, title: str, cost: int, level_required: int) -> dict:
        if not title.strip():
            raise GameRuleError("Reward title is required.")
        item = {
            "id": f"reward-{uuid4()}",
            "title": title.strip(),
            "cost": self._non_negative_int(cost, "Cost"),
            "level_required": max(1, self._non_negative_int(level_required, "Level")),
            "archived": False,
        }
        self.state["shop_rewards"].append(item)
        self._activity(f"Added shop reward: {item['title']}", "content_added")
        self._changed()
        return item

    def update_shop_reward(self, reward_id: str, title: str, cost: int, level_required: int) -> None:
        item = self._find("shop_rewards", reward_id)
        if not title.strip():
            raise GameRuleError("Reward title is required.")
        item.update(
            title=title.strip(),
            cost=self._non_negative_int(cost, "Cost"),
            level_required=max(1, self._non_negative_int(level_required, "Level")),
        )
        self._changed()

    def archive(self, collection: str, item_id: str) -> None:
        if collection not in ("paths", "quests", "bosses", "shop_rewards"):
            raise GameRuleError("This content cannot be archived.")
        item = self._find(collection, item_id)
        item["archived"] = True
        if collection in ("quests", "bosses") and item.get("status") != "completed":
            item["status"] = "archived"
        current = self.progress.get("current_run")
        singular = "quest" if collection == "quests" else "boss" if collection == "bosses" else None
        if current and singular == current["kind"] and current["item_id"] == item_id:
            self.progress["current_run"] = None
        self._activity(f"Archived {item.get('title', item.get('name', 'content'))}", "content_archived")
        self._changed()

    def set_timer(self, mode: str, minutes: int) -> None:
        if mode not in ("focus", "break") or minutes <= 0:
            raise GameRuleError("Choose a valid timer mode and duration.")
        self.set_timer_seconds(mode, int(minutes * 60))

    def set_timer_seconds(self, mode: str, seconds: int) -> None:
        if mode not in ("focus", "break") or not isinstance(seconds, int) or seconds <= 0:
            raise GameRuleError("Choose a valid timer mode and duration.")
        self.progress["timer"] = {
            "mode": mode,
            "duration_seconds": seconds,
            "remaining_seconds": seconds,
            "running": False,
        }
        self._changed()

    def update_timer(self, remaining_seconds: int, running: bool) -> None:
        timer = self.progress["timer"]
        timer["remaining_seconds"] = max(0, min(int(remaining_seconds), timer["duration_seconds"]))
        timer["running"] = bool(running) and timer["remaining_seconds"] > 0
        self._changed()

    def _quest_update_data(self, data: dict) -> dict:
        self._find("paths", data.get("path_id", ""))
        required = ("title", "stage", "difficulty", "definition_of_done")
        if any(not str(data.get(field, "")).strip() for field in required):
            raise GameRuleError("Title, stage, difficulty, and definition of done are required.")
        if data["difficulty"] not in set(DIFFICULTIES).difference({"boss"}):
            raise GameRuleError("Invalid quest difficulty.")
        return {
            "path_id": data["path_id"],
            "stage": str(data["stage"]).strip(),
            "title": str(data["title"]).strip(),
            "difficulty": str(data["difficulty"]),
            "xp": self._non_negative_int(data.get("xp"), "XP"),
            "gold": self._non_negative_int(data.get("gold"), "Gold"),
            "definition_of_done": str(data["definition_of_done"]).strip(),
            "bonuses": self._normalise_bonuses(data.get("bonuses", [])),
        }

    @staticmethod
    def _non_negative_int(value: object, label: str) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError) as exc:
            raise GameRuleError(f"{label} must be a whole number.") from exc
        if number < 0:
            raise GameRuleError(f"{label} cannot be negative.")
        return number

    @staticmethod
    def _strict_non_negative_int(value: object, label: str) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise GameRuleError(f"{label} must be a whole number.")
        if value < 0:
            raise GameRuleError(f"{label} cannot be negative.")
        return value

    @staticmethod
    def _quest_import_key(stage: object, title: object) -> tuple[str, str]:
        normalize = lambda value: " ".join(str(value).split()).casefold()
        return normalize(stage), normalize(title)

    @classmethod
    def _normalise_bonuses(cls, bonuses: Iterable[dict]) -> list[dict]:
        result = []
        for bonus in bonuses:
            title = str(bonus.get("title", "")).strip()
            if not title:
                raise GameRuleError("Every bonus needs a title.")
            result.append(
                {
                    "id": str(bonus.get("id") or f"bonus-{uuid4()}"),
                    "title": title,
                    "xp": cls._non_negative_int(bonus.get("xp"), "Bonus XP"),
                    "gold": cls._non_negative_int(bonus.get("gold"), "Bonus Gold"),
                }
            )
        return result

    @staticmethod
    def _normalise_requirements(requirements: Iterable[dict]) -> list[dict]:
        result = []
        for requirement in requirements:
            text = str(requirement.get("text", "")).strip()
            if not text:
                raise GameRuleError("Every boss requirement needs text.")
            result.append(
                {
                    "id": str(requirement.get("id") or f"requirement-{uuid4()}"),
                    "text": text,
                    "mandatory": bool(requirement.get("mandatory", True)),
                }
            )
        return result
