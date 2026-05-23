# Phase 6 — Evals + Observability

> **Working software at the end of this phase:** `make eval` produces numeric scores for both retrieval (recall@k) and lesson quality (LLM-as-judge rubric). A structured trace log lets you reconstruct any session for debugging. You can intentionally regress a parameter and *see the regression in the numbers*, not just feel it.

---

## Why this phase

Up to here, you've evaluated by vibes. "The lessons feel pretty good." That worked because you were building, not optimizing.

Now you have a real product, and the moment you start tuning (different chunk sizes? different rerankers? different models? different prompts?) vibes will mislead you. You'll change something, it'll feel better on the question you tested, and you won't notice it got worse on three other questions.

The fix is the same fix that turns hobbyist code into engineering: **automated tests with numeric outputs**. For LLM systems, those tests are *evals*.

This phase also adds observability — structured logs of every agent turn so when something goes wrong, you can reconstruct it.

---

## Concepts to learn first

Re-read [[LEARNING_GUIDE#Evals and LLM-as-judge|LEARNING_GUIDE → Evals and LLM-as-judge]] carefully. The Eugene Yan post in the [[LEARNING_GUIDE#Phase 6|Phase 6 reading list]] is the best practitioner-level overview I know.

`/concept LLM-as-judge` if you want a focused walkthrough.

---

## Two evals to build

### A. Retrieval eval (extend Phase 2)

You built recall@5 in Phase 2. Now formalize and extend:
- Add recall@1, recall@10, recall@20
- Add **MRR** (Mean Reciprocal Rank): for each query, score `1/rank_of_first_correct`. Averages to a single number that rewards "the right answer was very high in the ranking."
- Add a per-query breakdown so you can see *which* queries fail

### B. Lesson quality eval (new)

For 10-20 fixed concepts, generate a lesson via the teacher, then ask Claude (acting as judge) to score it 1-5 on:
- **Accuracy** — does it match the source material?
- **Clarity** — is the explanation easy to follow?
- **Pedagogical structure** — concept → intuition → example → check, or some equivalent?

The judge gets: `(concept_name, source_chunks_used, lesson_output, rubric)`. It returns structured scores via tool use.

---

## Modules to write / change

1. **`evals/retrieval_eval.py`** (extend) — add MRR, recall@k for multiple k, per-query CSV output
2. **`evals/lesson_eval.py`** (new) — generate lessons for fixed concepts, score with judge, output `{concept, accuracy, clarity, structure}` rows
3. **`evals/judge.py`** — the LLM-as-judge prompt + structured-output call. Reusable.
4. **`evals/fixtures/test_concepts.json`** — 10-20 fixed concepts with their expected source chunks (so you can grade accuracy by "did the lesson cite/use the expected chunks")
5. **`curio/obs/trace.py`** (extend) — make sure every agent turn writes a structured row with: `timestamp, session_id, phase (planner/teacher/examiner), model, prompt_tokens, completion_tokens, tools_called[], tools_results[], latency_ms`
6. **`evals/trace_query.py`** (optional) — a small CLI that queries the JSONL traces (e.g. `python evals/trace_query.py --session abc --phase teacher`)
7. **`Makefile`** — `make eval`, `make eval-retrieval`, `make eval-lessons` targets

---

## The judge prompt

Read this carefully — judges live or die by their prompt.

```
You are evaluating a lesson written by an AI tutor.

CONCEPT: {concept}
SOURCE MATERIAL (the only ground truth):
{source_chunks}

LESSON TO EVALUATE:
{lesson_output}

Score the lesson on three dimensions, 1 (poor) to 5 (excellent):

ACCURACY: Does the lesson make claims consistent with the source material?
A "5" means every factual claim is supported by the source. A "1" means
multiple unsupported or contradictory claims.

CLARITY: Could a curious learner with no prior exposure follow this?
A "5" means flows naturally, defines terms before using them, no jargon
without explanation. A "1" means confusing, references undefined ideas.

STRUCTURE: Does it follow good pedagogical structure?
A "5" means: hook/motivation → core idea → intuition or example →
brief check or next-step. A "1" means a flat info dump with no structure.

Use the `submit_score` tool to return your evaluation.
```

The judge then "calls" `submit_score` with `{accuracy, clarity, structure, rationale}`.

**Why a rationale field?** Forces the judge to articulate its reasoning, which both improves the scores' reliability (the model can't just guess "3 across the board") and gives you something to inspect when scores look weird.

---

## Trace log shape

One JSONL file per session (or one big append-only file with `session_id`). Each row:

```json
{
  "ts": "2026-05-22T20:13:44Z",
  "session_id": "20260522-201337-abc",
  "phase": "teacher",
  "iteration": 3,
  "model": "claude-sonnet-4-6",
  "input_tokens": 1832,
  "output_tokens": 412,
  "tools_called": [{"name": "search_corpus", "input": {"query": "entropy"}}],
  "tool_results": [{"name": "search_corpus", "num_results": 5}],
  "latency_ms": 2340,
  "text_excerpt": "Entropy can be understood..."
}
```

You don't need to log full text of every message (storage gets big and you don't need it for most debugging). Log enough to reconstruct the *shape* of the session.

---

## Leading questions

1. **Why is recall@5 not enough?** You also report recall@1 and recall@20. What does it mean if recall@5 is 0.85 but recall@1 is 0.40? (Hint: the right chunk is being retrieved but not at the top. Your reranker has room to improve.)

2. **Judge biases.** Your judge is Sonnet 4.6. Your teacher is also Sonnet 4.6. Is this a problem? (Yes — there's a known bias where models prefer their own outputs. Mitigate by using a different model — try Haiku 4.5 as judge — and by including a strong rubric.)

3. **What's a "good" lesson eval score?** You don't know yet. The first run *establishes* a baseline. The point of subsequent runs is to detect changes. Resist the urge to interpret one absolute number.

4. **Run-to-run noise.** Run the same eval twice (with `temperature=0`). Do you get the same scores? If not, why? (Hint: even with `temp=0`, sampling can be non-deterministic across providers / batches. Average over 3 runs for stable numbers.)

5. **Regression detection.** Intentionally make your chunking worse (chunk size 100 tokens, no overlap). Re-run both evals. Both should drop. If only one drops, what does that tell you about which eval is sensitive to which change?

6. **The eval set will grow stale.** As you fix the cases in the set, "easy" questions stop differentiating. Plan to add hard cases as you fix old ones.

7. **What's *not* in your evals?** End-to-end teaching session quality (multi-concept across-session continuity, Phase 5 memory behavior) is much harder to eval automatically. What manual checks would you do?

---

## Success criteria

- [ ] `make eval-retrieval` prints recall@1, recall@5, recall@20, MRR — single command, single output
- [ ] `make eval-lessons` prints per-concept scores and aggregate means
- [ ] Both evals run in < 2 minutes (otherwise you won't run them)
- [ ] You've **intentionally regressed** something (chunk size, removed reranker, etc.) and seen the eval numbers drop. You can name *which* eval moved and by how much.
- [ ] Your trace logs let you reconstruct a full session's tool calls and roughly what was said
- [ ] You can answer [[LEARNING_GUIDE#After Phase 6|Roadmap → After Phase 6]] out loud

---

## Stretch (optional)

- **Pipe traces to Langfuse** for a real observability UI (free tier covers this)
- **Token cost tracking** — sum input/output tokens per session, report dollars per session
- **A/B harness** — `make eval --variant baseline` vs `--variant experimental` runs both and prints a diff
- **Persistent eval history** — log every eval run's scores to a CSV/SQLite so you can plot performance over time
- **Judge ensemble** — average scores from Sonnet judge and Haiku judge; disagreement above some threshold flags a case for human review
- **Failure mode taxonomy** — for each query that fails the retrieval eval, classify the failure (chunk too short, no exact match, semantic gap). Aggregate to identify systemic issues.

---

## Hints

<details>
<summary>Hint 1 — Judge with forced tool</summary>

Use the same forced-tool-call pattern from Phase 4:

```python
judge_tool = {
    "name": "submit_score",
    "description": "Submit your evaluation of the lesson.",
    "input_schema": JudgeScore.model_json_schema(),
}
response = client.messages.create(
    model="claude-haiku-4-5-20251001",  # different from teacher
    tools=[judge_tool],
    tool_choice={"type": "tool", "name": "submit_score"},
    messages=[{"role": "user", "content": judge_prompt}],
)
```

</details>

<details>
<summary>Hint 2 — Why average over runs?</summary>

If you run with `temperature=0`, you'll get *almost* deterministic outputs — but provider-side batching, GPU non-determinism, and slight context variations can shift scores by ±0.1 to ±0.3 per metric. Three runs averaged gives you a more stable estimate. Be transparent about this in your reports.

</details>

<details>
<summary>Hint 3 — Don't log full text in traces by default</summary>

A 100K-token session can produce a 1MB+ JSONL row. Default to text excerpts (first 200 chars) and a `--verbose` flag that includes full messages. Storage gets out of hand fast.

</details>

<details>
<summary>Hint 4 — Cookbook reference</summary>

`cookbook/10_jsonl_traces.py` has a minimal trace writer pattern. The judge pattern is conceptually identical to the structured-output examples in `cookbook/07_anthropic_tool_use.py` and `cookbook/08_pydantic_tools.py`.

</details>

---

When Phase 6 is done you have a working adaptive tutor, evals you trust, and traces you can debug from. That's a real product. Pick a [[PROJECT_PLAN#Stretch Goals (after Phase 6)|stretch goal from the plan]] — or, equally valuable, *use* Curio for a few weeks to actually learn something with it, and notice where it falls short. Real usage uncovers real problems.

Either way: you've built every major modern RAG + agentic pattern from scratch. Congratulations.
