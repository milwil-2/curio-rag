"""
SPOILER — only read this AFTER attempting Phase 5.

Minimal SQLite-backed learner state. Pattern: schema-in-.sql-file,
raw sqlite3 stdlib, Pydantic models for domain types.

No ORM needed — for single-user local state, raw SQL is cleaner.

Run:  python cookbook/09_sqlite_learner.py
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from pydantic import BaseModel

SCHEMA = """
CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    started_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS concepts (
    id INTEGER PRIMARY KEY,
    topic_id INTEGER NOT NULL REFERENCES topics(id),
    name TEXT NOT NULL,
    mastery REAL NOT NULL DEFAULT 0.0,
    last_seen_at TEXT,
    UNIQUE(topic_id, name)
);

CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY,
    concept_id INTEGER NOT NULL REFERENCES concepts(id),
    score TEXT NOT NULL CHECK(score IN ('correct', 'partial', 'miss')),
    question TEXT,
    answer TEXT,
    feedback TEXT,
    ts TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY,
    topic_id INTEGER REFERENCES topics(id),
    text TEXT NOT NULL,
    ts TEXT NOT NULL
);
"""

MASTERY_DELTAS = {"correct": 0.30, "partial": 0.10, "miss": -0.10}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def open_db(path: str):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# ---- Domain types (the shape your agent sees) ----

class ConceptState(BaseModel):
    name: str
    mastery: float
    last_seen_at: str | None


# ---- Repository functions ----

def get_or_create_topic(conn: sqlite3.Connection, name: str) -> int:
    row = conn.execute("SELECT id FROM topics WHERE name = ?", (name,)).fetchone()
    if row:
        return row["id"]
    cur = conn.execute("INSERT INTO topics (name, started_at) VALUES (?, ?)", (name, _now()))
    return cur.lastrowid


def get_or_create_concept(conn: sqlite3.Connection, topic_id: int, name: str) -> int:
    row = conn.execute(
        "SELECT id FROM concepts WHERE topic_id = ? AND name = ?", (topic_id, name)
    ).fetchone()
    if row:
        return row["id"]
    cur = conn.execute(
        "INSERT INTO concepts (topic_id, name) VALUES (?, ?)", (topic_id, name)
    )
    return cur.lastrowid


def record_attempt(
    conn: sqlite3.Connection,
    concept_id: int,
    score: str,
    question: str,
    answer: str,
    feedback: str,
) -> None:
    """Insert an attempt and update the concept's mastery + last_seen_at."""
    conn.execute(
        "INSERT INTO attempts (concept_id, score, question, answer, feedback, ts) VALUES (?, ?, ?, ?, ?, ?)",
        (concept_id, score, question, answer, feedback, _now()),
    )
    delta = MASTERY_DELTAS[score]
    conn.execute(
        "UPDATE concepts SET mastery = max(0.0, min(1.0, mastery + ?)), last_seen_at = ? WHERE id = ?",
        (delta, _now(), concept_id),
    )


def log_observation(conn: sqlite3.Connection, text: str, topic_id: int | None = None) -> None:
    conn.execute(
        "INSERT INTO observations (topic_id, text, ts) VALUES (?, ?, ?)",
        (topic_id, text, _now()),
    )


def get_concept_states(conn: sqlite3.Connection, topic_id: int) -> list[ConceptState]:
    rows = conn.execute(
        "SELECT name, mastery, last_seen_at FROM concepts WHERE topic_id = ? ORDER BY mastery ASC",
        (topic_id,),
    ).fetchall()
    return [ConceptState(**dict(r)) for r in rows]


def main() -> None:
    Path("./_cookbook_data").mkdir(exist_ok=True)
    with open_db("./_cookbook_data/learner_demo.db") as conn:
        topic_id = get_or_create_topic(conn, "thermodynamics")
        entropy_id = get_or_create_concept(conn, topic_id, "entropy")
        enthalpy_id = get_or_create_concept(conn, topic_id, "enthalpy")

        record_attempt(conn, entropy_id, "correct", "What is entropy?", "...", "Good")
        record_attempt(conn, enthalpy_id, "miss", "What is enthalpy?", "...", "Revisit definition")
        log_observation(conn, "User prefers analogies over equations", topic_id)

        states = get_concept_states(conn, topic_id)
        print("Concept states (weakest first):")
        for s in states:
            print(f"  {s.name:12s}  mastery={s.mastery:.2f}  last_seen={s.last_seen_at}")


if __name__ == "__main__":
    main()
