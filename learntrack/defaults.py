"""Bundled game content, kept separate from mutable player progress."""

from copy import deepcopy
from datetime import datetime

from .constants import SCHEMA_VERSION


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _quest(
    quest_id: str,
    stage: str,
    title: str,
    difficulty: str,
    xp: int,
    gold: int,
    definition: str,
) -> dict:
    return {
        "id": quest_id,
        "path_id": "path-fastapi",
        "stage": stage,
        "title": title,
        "difficulty": difficulty,
        "xp": xp,
        "gold": gold,
        "definition_of_done": definition,
        "bonuses": [],
        "status": "available",
        "archived": False,
    }


DEFAULT_PATHS = [
    {
        "id": "path-fastapi",
        "name": "FastAPI",
        "status": "active",
        "objective": "Continue the Tasks API path",
        "goal": "Build a complete Tasks API while understanding its important parts.",
        "archived": False,
    },
    {
        "id": "path-postgresql",
        "name": "PostgreSQL",
        "status": "backlog",
        "objective": "Not planned yet",
        "goal": "Plan this learning path when it becomes a priority.",
        "archived": False,
    },
    {
        "id": "path-docker",
        "name": "Docker",
        "status": "backlog",
        "objective": "Not planned yet",
        "goal": "Plan this learning path when it becomes a priority.",
        "archived": False,
    },
    {
        "id": "path-git-github",
        "name": "Git and GitHub",
        "status": "backlog",
        "objective": "Not planned yet",
        "goal": "Plan this learning path when it becomes a priority.",
        "archived": False,
    },
]

DEFAULT_QUESTS = [
    _quest(
        "fastapi-routes",
        "Stage 1 — Routes and inputs",
        "Understand what a route is",
        "easy",
        10,
        5,
        "In your own words, write what a route connects and identify the HTTP method and path in two FastAPI route examples.",
    ),
    _quest(
        "fastapi-get-post-memory",
        "Stage 1 — Routes and inputs",
        "Create GET and POST routes from memory",
        "normal",
        25,
        10,
        "Without copying a complete example, create one GET route and one POST route, run the app, and verify that both respond.",
    ),
    _quest(
        "fastapi-path-parameters",
        "Stage 1 — Routes and inputs",
        "Understand path parameters",
        "easy",
        10,
        5,
        "Explain when a path parameter is useful and correctly identify the parameter in a sample URL and route declaration.",
    ),
    _quest(
        "fastapi-path-route",
        "Stage 1 — Routes and inputs",
        "Build a route using a path parameter",
        "normal",
        25,
        10,
        "Create and run a route that accepts an ID in its path, uses the typed value, and returns it in a response.",
    ),
    _quest(
        "fastapi-query-parameters",
        "Stage 1 — Routes and inputs",
        "Understand query parameters",
        "easy",
        10,
        5,
        "Explain how query parameters differ from path parameters and give one practical filtering example.",
    ),
    _quest(
        "fastapi-query-filter",
        "Stage 1 — Routes and inputs",
        "Add filtering through a query parameter",
        "normal",
        25,
        10,
        "Add an optional query parameter that filters a small task list and verify both filtered and unfiltered requests.",
    ),
    _quest(
        "fastapi-request-bodies",
        "Stage 2 — Data and responses",
        "Understand request bodies",
        "easy",
        10,
        5,
        "Explain what belongs in a request body and trace how FastAPI turns one valid JSON body into a Python value.",
    ),
    _quest(
        "fastapi-pydantic-model",
        "Stage 2 — Data and responses",
        "Create a Pydantic task model",
        "normal",
        25,
        10,
        "Create a Task model with a title and at least two typed fields, then demonstrate one valid and one rejected input.",
    ),
    _quest(
        "fastapi-post-tasks",
        "Stage 2 — Data and responses",
        "Add POST /tasks using the model",
        "normal",
        25,
        10,
        "Create POST /tasks with the Task model, store the submitted task, and verify the returned task through the API docs.",
    ),
    _quest(
        "fastapi-status-codes",
        "Stage 2 — Data and responses",
        "Understand status codes",
        "easy",
        10,
        5,
        "Explain the purpose of 200, 201, 204, 404, and 422 and match each to a Tasks API situation.",
    ),
    _quest(
        "fastapi-success-codes",
        "Stage 2 — Data and responses",
        "Return appropriate success status codes",
        "normal",
        25,
        10,
        "Configure sensible success status codes for create and delete operations and verify the actual response codes.",
    ),
    _quest(
        "fastapi-http-exception",
        "Stage 2 — Data and responses",
        "Handle a missing task with an HTTP exception",
        "normal",
        25,
        10,
        "Request an unknown task ID and confirm the route raises an HTTPException with a 404 response and useful detail.",
    ),
    _quest(
        "fastapi-get-tasks",
        "Stage 3 — Complete operations",
        "Add GET /tasks",
        "normal",
        25,
        10,
        "Implement GET /tasks and verify that it returns the complete current task collection in a consistent shape.",
    ),
    _quest(
        "fastapi-get-task-id",
        "Stage 3 — Complete operations",
        "Add GET /tasks/{id}",
        "normal",
        25,
        10,
        "Implement GET /tasks/{id} and verify one successful lookup plus the missing-ID behavior.",
    ),
    _quest(
        "fastapi-put-task-id",
        "Stage 3 — Complete operations",
        "Add PUT /tasks/{id}",
        "hard",
        50,
        20,
        "Implement a full task update, preserve its ID, and verify successful validation, replacement, and missing-ID behavior.",
    ),
    _quest(
        "fastapi-delete-task-id",
        "Stage 3 — Complete operations",
        "Add DELETE /tasks/{id}",
        "normal",
        25,
        10,
        "Implement deletion, verify the success response, and confirm the removed task can no longer be retrieved.",
    ),
    _quest(
        "fastapi-api-docs",
        "Stage 3 — Complete operations",
        "Explore and test the automatic API docs",
        "normal",
        25,
        10,
        "Use the automatic docs to send at least one valid and one invalid request, then record what the generated schemas reveal.",
    ),
    _quest(
        "fastapi-dependency-injection",
        "Stage 3 — Complete operations",
        "Use basic dependency injection in one useful place",
        "hard",
        50,
        20,
        "Create a reusable dependency for one real concern, use Depends in a route, and verify that changing its output affects the route.",
    ),
]

DEFAULT_BOSSES = [
    {
        "id": "boss-tasks-api",
        "path_id": "path-fastapi",
        "title": "Tasks API",
        "victory_condition": "Build and manually test a functioning Tasks API without following a complete project tutorial.",
        "requirements": [
            {"id": "create", "text": "Create a task", "mandatory": True},
            {"id": "list", "text": "List all tasks", "mandatory": True},
            {"id": "get", "text": "Get one task by ID", "mandatory": True},
            {"id": "update", "text": "Update a task", "mandatory": True},
            {"id": "delete", "text": "Delete a task", "mandatory": True},
            {"id": "priority", "text": "Include priority", "mandatory": True},
            {"id": "due-date", "text": "Include a due date", "mandatory": True},
            {"id": "completion", "text": "Include completion status", "mandatory": True},
            {"id": "validation", "text": "Use Pydantic validation", "mandatory": True},
            {"id": "codes", "text": "Use sensible status codes", "mandatory": True},
            {"id": "invalid", "text": "Handle invalid or missing tasks", "mandatory": True},
            {"id": "docs", "text": "Verify the endpoints through the automatic API docs", "mandatory": True},
        ],
        "xp": 300,
        "gold": 100,
        "bonuses": [
            {"id": "mostly-no-ai", "title": "Build most endpoints without AI-generated code", "xp": 75, "gold": 30},
            {"id": "useful-tests", "title": "Add useful tests", "xp": 50, "gold": 20},
            {"id": "clear-readme", "title": "Write a clear README", "xp": 25, "gold": 10},
        ],
        "status": "available",
        "archived": False,
    }
]

DEFAULT_REWARDS = [
    {"id": "reward-gaming-hour", "title": "Extra hour of guilt-free gaming", "cost": 30, "level_required": 1, "archived": False},
    {"id": "reward-movie", "title": "Watch a movie or several episodes", "cost": 45, "level_required": 1, "archived": False},
    {"id": "reward-snack", "title": "Order a favorite snack or drink", "cost": 70, "level_required": 2, "archived": False},
    {"id": "reward-gaming-evening", "title": "Full gaming evening", "cost": 100, "level_required": 3, "archived": False},
    {"id": "reward-small-item", "title": "Buy a small nonessential item", "cost": 180, "level_required": 4, "archived": False},
    {"id": "reward-larger", "title": "Choose a larger personal reward", "cost": 350, "level_required": 6, "archived": False},
    {"id": "reward-major", "title": "Major custom reward", "cost": 600, "level_required": 8, "archived": False},
]


def create_default_state(player_name: str = "Adventurer") -> dict:
    """Return a fresh, fully independent player state."""
    timestamp = _now()
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": timestamp,
        "updated_at": timestamp,
        "profile": {
            "player_name": player_name.strip() or "Adventurer",
            "animations_enabled": True,
            "allow_custom_import_rewards": False,
            "show_current_run_background": True,
            "timer_presets": {"focus": [20, 25, 30], "break": 40},
        },
        "paths": deepcopy(DEFAULT_PATHS),
        "quests": deepcopy(DEFAULT_QUESTS),
        "bosses": deepcopy(DEFAULT_BOSSES),
        "shop_rewards": deepcopy(DEFAULT_REWARDS),
        "progress": {
            "xp": 0,
            "gold": 0,
            "total_gold_earned": 0,
            "current_run": None,
            "quest_claims": [],
            "boss_claims": [],
            "purchases": [],
            "activity": [],
            "timer": {
                "mode": "focus",
                "duration_seconds": 25 * 60,
                "remaining_seconds": 25 * 60,
                "running": False,
            },
        },
    }
