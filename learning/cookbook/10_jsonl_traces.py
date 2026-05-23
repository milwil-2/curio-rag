"""
SPOILER — only read this AFTER attempting Phase 6.

Minimal JSONL trace writer for agent observability. One row per agent turn.
Default to text excerpts (full text gets huge fast); add a `verbose` flag if
you need full reconstruction.

Run:  python cookbook/10_jsonl_traces.py
"""

import json
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class TraceRecord:
    """One row of agent trace."""
    ts: str
    session_id: str
    phase: str            # "planner" | "teacher" | "examiner" | "agent_loop" | ...
    iteration: int
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    tools_called: list[dict[str, Any]] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    latency_ms: int = 0
    text_excerpt: str = ""  # first ~200 chars of model output


class Tracer:
    def __init__(self, trace_dir: str = "traces") -> None:
        self.path = Path(trace_dir)
        self.path.mkdir(exist_ok=True)
        self.session_id = (
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            + "-"
            + uuid.uuid4().hex[:6]
        )
        self.file = self.path / f"{self.session_id}.jsonl"

    def write(self, record: TraceRecord) -> None:
        with self.file.open("a") as f:
            f.write(json.dumps(asdict(record)) + "\n")

    @contextmanager
    def turn(self, phase: str, iteration: int, model: str):
        """Time a turn and write a record when the context exits."""
        rec = TraceRecord(
            ts=datetime.now(timezone.utc).isoformat(),
            session_id=self.session_id,
            phase=phase,
            iteration=iteration,
            model=model,
        )
        t0 = time.perf_counter()
        try:
            yield rec
        finally:
            rec.latency_ms = int((time.perf_counter() - t0) * 1000)
            self.write(rec)


def main() -> None:
    tracer = Tracer(trace_dir="./_cookbook_data/traces")

    # Simulate two turns of an agent loop.
    with tracer.turn(phase="agent_loop", iteration=0, model="claude-sonnet-4-6") as rec:
        time.sleep(0.05)
        rec.input_tokens = 1200
        rec.output_tokens = 80
        rec.tools_called = [{"name": "search_corpus", "input": {"query": "entropy"}}]
        rec.tool_results = [{"name": "search_corpus", "num_results": 5}]
        rec.text_excerpt = "I'll search for entropy first."

    with tracer.turn(phase="agent_loop", iteration=1, model="claude-sonnet-4-6") as rec:
        time.sleep(0.03)
        rec.input_tokens = 2800
        rec.output_tokens = 350
        rec.text_excerpt = "Entropy is a measure of disorder..."

    print(f"Wrote trace to {tracer.file}")
    print(tracer.file.read_text())


if __name__ == "__main__":
    main()
