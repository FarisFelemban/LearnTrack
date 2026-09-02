# LearnTrack

A single-player, offline desktop game that turns software-engineering learning into small, evidence-based quests. It was made specifically for Faris.

The game tracks permanent XP, spendable Gold, exact level thresholds, learning paths, bosses, optional objectives, focus timers, personal rewards, and a readable activity journal. Time alone never grants rewards: every quest needs evidence that its definition of done was completed.

## Setup and launch

Python 3.14 is the primary target. From this repository, install the one dependency:

```bash
python3 -m pip install -r requirements.txt
```

Then launch the game:

```bash
python3 main.py
```

On the first run, the game asks only for your player name. Progress saves automatically after every meaningful change in the operating system's normal application-data folder. A running timer is restored paused after relaunch.

## Included gameplay

- Dashboard with level progress, current run, activity, and 20/25/30-minute focus timers or a 40-minute break timer
- Filterable Quest Board with the complete FastAPI quest line from `LearnTrack.md`
- Editable learning paths, quests, bonuses, bosses, requirements, and shop rewards
- Evidence and confirmation before claims, mandatory boss checklists, and duplicate-claim protection
- Repeatable shop purchases with Level and Gold checks
- Journal with immutable completion snapshots, evidence, purchases, and overall statistics
- Validated JSON export/import, automatic atomic saves, corruption backups, and confirmed reset

Completed or historically used content is archived instead of removing its history. XP never decreases, and Gold only decreases through a confirmed shop purchase.

## Tests

The automated tests use Python's built-in test runner. Qt runs offscreen, so they do not open windows:

```bash
QT_QPA_PLATFORM=offscreen python3 -m unittest discover -s tests -v
```

`LearnTrack.md` remains the design reference. Player activity is written only to the local JSON save.
