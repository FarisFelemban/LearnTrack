# LearnTrack

A flexible personal system for making software-engineering learning easier to continue.

The system rewards **evidence of learning**, not time spent sitting at a desk.

---

## 1. Core loop

1. Choose one small quest.
2. Work on it during a **20–30 minute run**.
3. Claim XP and Gold only after completing its definition of done.
4. Take a break. A break can be around **40 minutes** if that is what actually restores focus.
5. Start another run only when ready.

The objective is not to force long sessions. Several focused runs are better than hours of barely working.

---

## 2. The game system

### XP

- Represents permanent learning progress.
- Cannot be spent or lost.
- Determines the current level.
- Should come from learning, practicing, solving, and building.

### Gold

- An arbitrary game currency with no conversion to money or time.
- Earned alongside XP by completing quests and bosses.
- Spent in the Reward Shop.
- Never decreases unless a reward is purchased.

### Levels

- Show long-term progress.
- Unlock rewards and larger challenges.
- Do not directly grant rewards.

| Level | Total XP required |
| ---: | ---: |
| 1 | 0 XP |
| 2 | 100 XP |
| 3 | 250 XP |
| 4 | 500 XP |
| 5 | 850 XP |
| 6 | 1,300 XP |
| 7 | 1,900 XP |
| 8 | 2,600 XP |
| 9 | 3,500 XP |
| 10 | 4,600 XP |

Add later levels only when Level 10 is close. Future thresholds should gradually become farther apart.

---

## 3. Quest difficulty and rewards

Difficulty is based on the actual challenge, not how long something takes.

| Type | Typical task | XP | Gold |
| --- | --- | ---: | ---: |
| 🟢 Easy | Read one short section, review notes, or explain one basic idea | 10 | 5 |
| 🔵 Normal | Use a concept in a small exercise or write it from memory | 25 | 10 |
| 🟣 Hard | Combine concepts, debug a difficult issue, or solve independently | 50 | 20 |
| 🔴 Boss | Complete a project, major feature, or realistic assessment | 150–300 | 50–100 |

### Rules for fair XP

- No XP is awarded merely for studying for a certain amount of time.
- Every quest needs a clear **definition of done**.
- Looking at documentation is allowed unless the quest explicitly says otherwise.
- AI help is allowed unless the quest explicitly tests independent recall or problem-solving.
- Estimate the reward before starting; do not raise it afterward because the quest felt annoying.
- If a quest is too large for one run, split it into smaller quests.
- If a quest turns out to be much harder than expected, finish the current small objective and create a separate follow-up quest.

---

## 4. Quest design

A useful learning path normally follows:

> Learn → recall → practice → build

Examples for any topic:

- **Learn:** Read the relevant explanation and identify the main idea.
- **Recall:** Explain or write the idea without looking.
- **Practice:** Use it in a focused exercise.
- **Build:** Apply it in a real feature or project.

Bad quest:

> Study Docker for one hour.

Better quest:

> Run a container from an image and explain what the command's main options do.

### Bonus objectives

A quest can have optional objectives that reward extra effort without making the base quest feel endless.

```md
### 🔵 Understand Git branches

**Definition of done:** Create a branch, make one commit, and switch back safely.

- Base reward: +25 XP, +10 Gold
- [ ] Bonus: repeat without notes — +10 XP, +5 Gold
- [ ] Bonus: explain when a branch is useful — +10 XP, +5 Gold
```

The base quest is still a complete win. Bonuses are optional.

---

## 5. Boss fights

Bosses test whether several skills can be combined without following a complete step-by-step tutorial.

Documentation, targeted searches, and debugging resources are allowed. The point is to assemble the solution personally.

Bosses should:

- produce something that works;
- combine multiple previously learned concepts;
- have a checklist of requirements;
- be worth considerably more than passive learning quests;
- include optional constraints when useful.

```md
## 🔴 Boss — Project name

**Victory condition:** Describe what must work for the boss to count as complete.

### Requirements

- [ ] Requirement one
- [ ] Requirement two
- [ ] Requirement three

### Reward

- +___ XP
- +___ Gold

### Optional objectives

- [ ] Complete a section without AI: +___ XP, +___ Gold
- [ ] Add tests or documentation: +___ XP, +___ Gold
```

---

## 6. Learning paths

Each subject is a separate learning path. Adding PostgreSQL, Docker, Git, testing, cloud services, or another roadmap topic should not change the game system.

### Path status

- **Backlog:** Worth learning later.
- **Active:** Currently learning.
- **Paused:** Intentionally set aside without losing progress.
- **Completed:** The planned material and boss have been completed.

### Current paths

| Learning path | Status | Current objective | Path XP earned |
| --- | --- | --- | ---: |
| FastAPI | Active | Continue the Tasks API path | 0 |
| PostgreSQL | Backlog | Not planned yet | 0 |
| Docker | Backlog | Not planned yet | 0 |
| Git and GitHub | Backlog | Not planned yet | 0 |

Do not activate too many paths simultaneously. One main path and one smaller side path are usually enough.

### Template for a new learning path

Copy this entire section whenever a new roadmap topic is added:

```md
# Path: [Topic]

**Status:** Backlog / Active / Paused / Completed  
**Why I am learning it:** [Practical reason]  
**Path XP earned:** 0

## Goal

[What I should be capable of doing when this path is complete.]

## Quest line

### Stage 1 — Foundations

- [ ] 🟢 [Learn one core idea] — +10 XP, +5 Gold
- [ ] 🔵 [Recall or use that idea] — +25 XP, +10 Gold

### Stage 2 — Practical use

- [ ] 🔵 [Small practical exercise] — +25 XP, +10 Gold
- [ ] 🟣 [Combine multiple ideas] — +50 XP, +20 Gold

### Stage 3 — Boss preparation

- [ ] 🟣 [Independent challenge] — +50 XP, +20 Gold

## 🔴 Boss — [Project or assessment]

**Victory condition:** [Specific working result]

- [ ] [Requirement]
- [ ] [Requirement]
- [ ] [Requirement]

**Reward:** +___ XP, +___ Gold

## Notes and discoveries

- 
```

---

## 7. FastAPI path

**Status:** Active  
**Goal:** Build a complete Tasks API while understanding its important parts.  
**Path XP earned:** 0

### Stage 1 — Routes and inputs

- [ ] 🟢 Understand what a route is — +10 XP, +5 Gold
- [ ] 🔵 Create GET and POST routes from memory — +25 XP, +10 Gold
- [ ] 🟢 Understand path parameters — +10 XP, +5 Gold
- [ ] 🔵 Build a route using a path parameter — +25 XP, +10 Gold
- [ ] 🟢 Understand query parameters — +10 XP, +5 Gold
- [ ] 🔵 Add filtering through a query parameter — +25 XP, +10 Gold

### Stage 2 — Data and responses

- [ ] 🟢 Understand request bodies — +10 XP, +5 Gold
- [ ] 🔵 Create a Pydantic task model — +25 XP, +10 Gold
- [ ] 🔵 Add POST `/tasks` using the model — +25 XP, +10 Gold
- [ ] 🟢 Understand status codes — +10 XP, +5 Gold
- [ ] 🔵 Return appropriate success status codes — +25 XP, +10 Gold
- [ ] 🔵 Handle a missing task with an HTTP exception — +25 XP, +10 Gold

### Stage 3 — Complete operations

- [ ] 🔵 Add GET `/tasks` — +25 XP, +10 Gold
- [ ] 🔵 Add GET `/tasks/{id}` — +25 XP, +10 Gold
- [ ] 🟣 Add PUT `/tasks/{id}` — +50 XP, +20 Gold
- [ ] 🔵 Add DELETE `/tasks/{id}` — +25 XP, +10 Gold
- [ ] 🔵 Explore and test the automatic API docs — +25 XP, +10 Gold
- [ ] 🟣 Use basic dependency injection in one useful place — +50 XP, +20 Gold

## 🔴 Boss — Tasks API

**Victory condition:** Build and manually test a functioning Tasks API without following a complete project tutorial.

### Requirements

- [ ] Create a task
- [ ] List all tasks
- [ ] Get one task by ID
- [ ] Update a task
- [ ] Delete a task
- [ ] Include priority
- [ ] Include a due date
- [ ] Include completion status
- [ ] Use Pydantic validation
- [ ] Use sensible status codes
- [ ] Handle invalid or missing tasks
- [ ] Verify the endpoints through the automatic API docs

### Reward

- +300 XP
- +100 Gold

### Optional objectives

- [ ] Build most endpoints without AI-generated code — +75 XP, +30 Gold
- [ ] Add useful tests — +50 XP, +20 Gold
- [ ] Write a clear README — +25 XP, +10 Gold

---

## 8. Reward Shop

Rewards should feel desirable but not interfere with basic needs, sleep, relationships, or normal rest. Ordinary leisure is still allowed; the shop is for **extra or upgraded rewards**, not permission to live normally.

| Reward | Cost | Level required |
| --- | ---: | ---: |
| Extra hour of guilt-free gaming | 30 Gold | Level 1 |
| Watch a movie or several episodes | 45 Gold | Level 1 |
| Order a favorite snack or drink | 70 Gold | Level 2 |
| Full gaming evening | 100 Gold | Level 3 |
| Buy a small nonessential item | 180 Gold | Level 4 |
| Choose a larger personal reward | 350 Gold | Level 6 |
| Major custom reward | 600 Gold | Level 8 |

These prices are intentionally arbitrary. Change them after observing the system for several weeks, not after every purchase.

### Purchase log

| Date | Reward | Gold spent | Gold remaining |
| --- | --- | ---: | ---: |
|  |  |  |  |

---

## 9. Player sheet

| Stat | Current value |
| --- | ---: |
| Level | 1 |
| Total XP | 0 |
| Available Gold | 0 |
| Total Gold earned | 0 |
| Bosses defeated | 0 |

### Optional achievements

- [ ] **First Blood:** Complete the first project feature.
- [ ] **Bug Hunter:** Fix 10 bugs through personal investigation.
- [ ] **No Training Wheels:** Complete 5 tasks without AI help.
- [ ] **Documentation Diver:** Solve 5 problems using official documentation.
- [ ] **LeetCoder:** Complete 10 LeetCode problems.
- [ ] **API Apprentice:** Defeat the Tasks API boss.
- [ ] **Full Stack Starter:** Complete one project with a frontend, backend, and database.

Achievements are trophies only. They do not need XP or Gold rewards.

---

## 10. Quest log

### Available quests

Keep only a few immediately available quests here. The full roadmap belongs in the individual learning paths.

- [ ] [Quest] — +___ XP, +___ Gold
- [ ] [Quest] — +___ XP, +___ Gold
- [ ] [Quest] — +___ XP, +___ Gold

### Completed quests

| Date | Path | Quest | XP | Gold |
| --- | --- | --- | ---: | ---: |
|  |  |  |  |  |

### Current run

**Quest:**  
**Definition of done:**  
**Optional bonus:**  
**Result or evidence:**  

---

## 11. Maintenance rules

- Add a new learning path by copying the template in Section 6.
- Break roadmap items into quests that can usually be completed in one or two runs.
- Keep setup lightweight; the system exists to support learning.
- Rebalance rewards only after enough completed quests reveal a real problem.
- Pausing a path is allowed. Existing XP and Gold remain.
- Rest is allowed and does not create a penalty.
- When motivation is low, choose one Easy quest instead of inventing a punishment.
- When learning feels passive, convert the next quest into recall, practice, debugging, or building.
- When a topic becomes too broad, split it into paths. For example, split “Databases” into “SQL,” “PostgreSQL,” and “Database Design.”

The main rule is simple:

> Do not gamify the amount of suffering. Gamify evidence that something was learned or built.
