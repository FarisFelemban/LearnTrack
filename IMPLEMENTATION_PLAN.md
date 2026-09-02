# LearnTrack Desktop Tracker — Implementation Plan

## Summary

Create a polished, resizable PySide6 desktop game launched with `python3 main.py`. It will turn `LearnTrack.md` into a dark cyber-RPG learning tracker with editable quests, evidence-based completion, XP, Gold, levels, bosses, rewards, focus timers, and persistent progress.

## Implementation Changes

- Build a modular PySide6 application with a root `main.py`, an internal `learntrack` package, bundled assets/default data, and a `requirements.txt` using PySide6 6.11+.
- Add a first-run profile setup requesting only the player's name; allow changing it later.
- Create these screens:
  - Dashboard: level, animated XP bar, Gold, active path, current quest, timer, recent activity, and quick actions.
  - Quest Board: filters by path, stage, difficulty, and status; quest details; start and complete actions.
  - Learning Paths: Backlog, Active, Paused, and Completed paths with per-path XP.
  - Bosses: requirement checklists, victory conditions, evidence, and larger rewards.
  - Reward Shop: level locks, affordability checks, purchase confirmation, and purchase history.
  - Journal/Profile: completed quests, evidence, earned rewards, overall statistics, and activity history.
  - Settings: player name, animation toggle, data export/import, and confirmed save reset.
- Seed all four paths from the document. Include the complete FastAPI quest line and Tasks API boss, preserving order, difficulty, XP, and Gold values.
- Add a practical, verifiable definition of done to each built-in FastAPI quest. Preserve the document's “learn → recall → practice → build” progression.
- Support adding and editing paths, quests, optional bonuses, bosses, boss requirements, and shop rewards.
- Archive completed or historically used content instead of deleting its history.
- Allow only one current quest/run at a time. Switching quests requires confirmation but does not award or remove anything.
- Require non-empty evidence and explicit confirmation before a quest can be claimed. Bosses additionally require every mandatory requirement to be checked.
- Prevent duplicate rewards. Optional objectives award their configured bonus only when selected during completion.
- Derive levels from the exact XP thresholds in the document. XP never decreases; Gold decreases only through confirmed shop purchases.
- Allow rewards to be purchased repeatedly when the player meets the level and Gold requirements.
- Add optional 20-, 25-, and 30-minute focus timers plus an offered 40-minute break timer. Timers never grant rewards or gate quest completion. Closing the app saves the remaining time and restores it paused.
- Use a cyber-RPG visual system: near-black/navy surfaces, cyan and magenta highlights, gold rewards, readable contrast, futuristic cards, and a consistent icon set.
- Generate and bundle one text-free cyber learning-guild dashboard backdrop. All remaining visuals will use Qt styling and code-drawn shapes, so the game requires no internet connection at runtime.
- Add restrained animations: navigation fades, card hover feedback, smooth XP/Gold counters, a circular timer, and short quest-completion/level-up particles. No audio will be included.

## Data and Interfaces

- Store default content separately from player progress.
- Automatically save to a readable, schema-versioned local JSON file after every meaningful change.
- Use stable IDs and immutable history snapshots so later edits do not rewrite previously earned rewards or evidence.
- Write saves atomically to reduce corruption risk. If loading fails, preserve the broken file as a backup and offer a clean reset rather than silently discarding it.
- Provide JSON export/import with validation and confirmation before replacing current progress.
- Document the only required setup and launch commands:
  - `python3 -m pip install -r requirements.txt`
  - `python3 main.py`

## Test Plan

- Unit-test level thresholds, path XP, quest/boss/bonus rewards, Gold spending, level locks, and duplicate-claim prevention.
- Test required evidence, boss checklists, content validation, archiving, timer restoration, and immutable history.
- Test first-run seeding, save/load round trips, imports, malformed saves, and reset behavior.
- Run PySide6 navigation and dialog smoke tests in offscreen mode.
- Launch `main.py` normally on macOS and verify resizing, focus behavior, artwork, animations, timer operation, persistence after relaunch, and the complete quest-to-shop gameplay loop.

## Assumptions

- V1 is a single-player offline desktop tracker.
- `LearnTrack.md` remains the design reference; gameplay writes only to JSON.
- Adventure maps, combat, quizzes, automated project-file verification, cloud sync, accounts, music, and sound effects are reserved for future versions.
- Level 10 remains the highest defined level. Additional XP is retained and displayed, but no new thresholds are invented.
- The current local environment—Python 3.14.6 with PySide6/Qt 6.11.1—is the primary target.
