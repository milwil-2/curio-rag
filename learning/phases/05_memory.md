# Phase 5 — Persistent Memory + Adaptation

> **Working software at the end of this phase:** Curio remembers you across sessions. Skip concepts you already mastered. Resurface concepts you struggled with weeks ago. Personalize lesson style based on observations the agent has logged about you over time.

---

## Why this phase

A tutor that doesn't remember you is a stranger every session. The interesting thing about an *adaptive* tutor is that session N+1 is shaped by everything that happened in sessions 1..N. That's not possible without persistent state.

This phase is also where Curio earns the word "agentic" in a deeper sense. The agent isn't just looping within a session — it's reading from and writing to a long-term memory store, which means decisions in session 1 affect outputs in session 10.

---

## Concepts to learn first

Read [[LEARNING_GUIDE#Memory in agents|LEARNING_GUIDE → Memory in agents]] — the four kinds of memory and which one(s) you're adding here.

Read [[LEARNING_GUIDE#SQLite|SQLite primer]] if you haven't used it before.

Optional but interesting: skim the Memory section of the [Generative Agents paper](https://arxiv.org/abs/2304.03442). It introduced the modern pattern of "retrieve relevant memories at decision time" rather than "stuff all memories into context."

`/concept agent memory` for an interactive explanation of the different memory types.

---

## What you're persisting

The minimum schema:

```sql
-- A topic you've studied (e.g. "thermodynamics")
CREATE TABLE topics (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    started_at TEXT NOT NULL
);

-- A concept within a topic (e.g. "entropy")
CREATE TABLE concepts (
    id INTEGER PRIMARY KEY,
    topic_id INTEGER REFERENCES topics(id),
    name TEXT NOT NULL,
    mastery REAL NOT NULL DEFAULT 0.0,  -- 0.0 to 1.0
    last_seen_at TEXT,
    UNIQUE(topic_id, name)
);

-- Each grading event
CREATE TABLE attempts (
    id INTEGER PRIMARY KEY,
    concept_id INTEGER REFERENCES concepts(id),
    score TEXT CHECK(score IN ('correct', 'partial', 'miss')),
    question TEXT,
    answer TEXT,
    feedback TEXT,
    ts TEXT NOT NULL
);

-- Free-text observations the agent records about the learner
CREATE TABLE observations (
    id INTEGER PRIMARY KEY,
    text TEXT NOT NULL,
    topic_id INTEGER REFERENCES topics(id),  -- nullable
    ts TEXT NOT NULL
);
```

`observations` is the most interesting table. After a session the agent can log things like *"Milan understands operators well but stumbles on dimensional analysis"* or *"prefers analogies to formal proofs."* On future sessions, these get retrieved and influence behavior.

---

## How mastery updates

Don't overthink this. Simple rule:

```
correct:  mastery := min(1.0, mastery + 0.30)
partial:  mastery := min(1.0, mastery + 0.10)
miss:     mastery := max(0.0, mastery - 0.10)
```

Plus: decay over time. A concept not seen in 30 days drops by some amount. This is the "spaced repetition" idea — you should revisit concepts before they're forgotten.

A real SRS system (SuperMemo / Anki) is more sophisticated; this approximation is enough for learning purposes.

---

## Modules to write

1. **`curio/memory/schema.sql`** — your DDL, run on app start (`CREATE TABLE IF NOT EXISTS`).
2. **`curio/memory/learner.py`** — repository functions:
   - `get_or_create_topic(name)` / `get_or_create_concept(topic, name)`
   - `record_attempt(concept_id, score, question, answer, feedback)` — also updates `concepts.mastery` and `concepts.last_seen_at`
   - `log_observation(text, topic_id=None)`
   - `get_concept_state(topic_id) -> list[ConceptState]` — for the planner
   - `get_observations(topic_id, limit=10)` — for the teacher
3. **`curio/agent/tools.py` (extend)** — add tools the agent can call:
   - `get_learner_state(topic)` — returns concept masteries + recent observations as JSON
   - `log_observation(text)` — store an agent observation
   - `mark_concept_mastered(name)` — manual override (rare)
4. **`curio/agent/planner.py` (modify)** — *before* generating a syllabus, the planner calls `get_learner_state` and adjusts: skip mastered concepts, prioritize weak ones, include any "this learner needs to revisit X" notes.
5. **`curio/agent/teacher.py` (modify)** — pull in 2-3 relevant observations as part of the lesson context. ("This learner prefers analogies.")

---

## Leading questions

1. **What goes in `observations`?** Too verbose and the agent floods the table; too sparse and it's useless. Try to think about *what would help future-you teach this person*. Often that's not "Milan got #3 wrong" but "Milan's intuition is more spatial than algebraic — analogies land better."

2. **When should the agent log an observation?** End of session? After a grade? On user request? You'll need to decide. (A nice pattern: the examiner can optionally log an observation after a grade.)

3. **How do you pick what observations are relevant to the current lesson?** All of them? Last 10? Embed observations and retrieve by similarity? (For Phase 5, simple is fine — get all observations for the topic, let Claude pick. You can get fancier later.)

4. **What about contradictions?** Session 3: "user struggles with calculus." Session 8: "user has a strong calculus background now." How does the agent resolve? (Hint: timestamps. Recent observations override older ones — but don't *delete* old ones; the contradiction itself is information.)

5. **Privacy.** Everything's local on your Mac, so privacy isn't a security issue. But you might want a `curio forget --topic <X>` command to start fresh. Worth a thought.

6. **What about across topics?** If Curio observes that you learn well from worked examples in physics, should that influence biology lessons? (Up to you. Cross-topic transfer is a deep question; start with topic-scoped observations.)

7. **How will you know it's working?** A 3-session test: study a topic on day 1 (struggle with concept X). Don't study on day 2. Day 3: does the agent open by revisiting X? If yes, memory works. If no, debug.

---

## Success criteria

- [ ] After Phase 4's `curio teach` session, `sqlite3 data/learner.db "SELECT * FROM attempts"` shows real rows
- [ ] After two sessions in a row, the second session's planner output reflects the first session's state (skips mastered concepts, surfaces weak ones)
- [ ] The agent logs at least one observation per session organically (no manual prompt to do so)
- [ ] You can run `curio forget --topic <name>` to reset and verify behavior changes
- [ ] You can answer [[LEARNING_GUIDE#After Phase 5|Roadmap → After Phase 5]] out loud
- [ ] The trace log shows the planner explicitly using `get_learner_state` results in its reasoning

---

## Stretch (optional)

- **Spaced repetition surfacing** — at the start of any session, the agent reviews any topic where mastered concepts haven't been seen in >14 days and offers a 5-minute refresh
- **Confidence-aware grading** — examiner outputs `{score, confidence}`; low-confidence grades don't update mastery as aggressively
- **Embedded observations** — embed each observation with BGE-small, retrieve the top-3 most relevant to the current concept (instead of dumping all)
- **A learner profile summary** — at the start of each session, the agent reads all observations and produces a short paragraph "what you know about this learner" that becomes part of the system prompt
- **Export your learning history** — a `curio history` command that produces a markdown summary of what you've studied, with mastery levels

---

## Hints

<details>
<summary>Hint 1 — SQLite schema setup pattern</summary>

```python
import sqlite3

def open_db(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row  # access columns by name
    with open("curio/memory/schema.sql") as f:
        conn.executescript(f.read())
    return conn
```
Schema-as-file is cleaner than schema-as-string.

</details>

<details>
<summary>Hint 2 — Don't use ORMs for this</summary>

SQLAlchemy is overkill. Pydantic models for the *domain types*, raw SQL via stdlib `sqlite3` for storage. The 80% of CRUD you need is 50 lines.

</details>

<details>
<summary>Hint 3 — How the tool returns shape choice matters</summary>

When `get_learner_state` returns to Claude, format the response in a way the LLM can use easily — e.g. structured Markdown:

```
## Concept mastery (topic: Thermodynamics)
- entropy: 0.8 (last seen 2 days ago)
- enthalpy: 0.3 (last seen 5 days ago)  ← WEAK, prioritize

## Recent observations
- (2 days ago) Prefers analogies to formulas
- (5 days ago) Struggled with derivations involving partial differentials
```
Better than a raw JSON blob — Claude parses both, but the markdown is more *salient* to the model's attention.

</details>

<details>
<summary>Hint 4 — Cookbook reference</summary>

`cookbook/09_sqlite_learner.py` has a minimal repository pattern. Build yours first.

</details>

---

Phase 5 is the longest learning curve so far because it forces you to think about state, contracts between sessions, and how the agent's *behavior* changes with persisted information. Take your time.
