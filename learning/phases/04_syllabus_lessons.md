# Phase 4 — Syllabus + Lesson Loop

> **Working software at the end of this phase:** `curio teach "thermodynamics"` runs a full interactive teaching session. The agent generates a structured syllabus, walks you through it concept-by-concept, asks you to demonstrate understanding, and grades your responses with feedback.

---

## Why this phase

So far Curio answers questions. Useful, but Q&A is not the goal — *teaching* is. Teaching demands different patterns:

- **Structured output** — the syllabus isn't prose, it's a list of `{subtopic, prerequisites, key_concepts}`. Your code needs to consume it programmatically.
- **Distinct agent roles** — the planner, teacher, and examiner each need different prompts and tools. They're not the same agent wearing hats.
- **Interactive loops** — unlike Phase 3's "ask once, answer once," teaching is multi-turn dialog over many minutes.

You'll touch the most important agentic pattern beyond the basic loop: **structured outputs via tool use** (the technique that lets you get reliable JSON back from an LLM).

---

## Concepts to learn first

There's no big new "concept" page in the learning guide for this phase — the foundations were laid in Phase 3. What's new is *structuring*: how to get a reliable JSON output, and how to break one big agent into specialized ones.

Read Anthropic's [docs on tool use for structured output](https://docs.anthropic.com/en/docs/build-with-claude/tool-use) (especially the part about using tools to return JSON, even when there's nothing to "execute").

Optional but excellent: [Anthropic's "Building effective agents"](https://www.anthropic.com/research/building-effective-agents) — has a great section on when to split agents vs. one prompt with chain of thought.

`/concept structured outputs` for an interactive walkthrough.

---

## The three roles

```
       Planner            →    Teacher    →    Examiner    ↑
   (one-shot per topic)        (per concept)   (per concept)
                                                 (back to Teacher with feedback)
```

- **Planner.** Input: topic. Output: a syllabus — JSON object with a list of concepts in pedagogical order, each with `prerequisites` and `key_ideas`. Uses retrieval to ground the syllabus in your corpus.
- **Teacher.** Input: one concept + retrieved chunks. Output: a 2-3 paragraph explanation followed by one open-ended question. Conversational.
- **Examiner.** Input: the concept, the teacher's question, the user's answer. Output: a score (correct / partial / miss) plus a sentence of feedback. Decides whether to move on or revisit.

These are **three different Claude calls** with three different system prompts. Sharing them in one giant prompt is tempting but worse — you'll get muddled outputs.

---

## Modules to write

1. **`curio/agent/planner.py`** — `plan_syllabus(topic: str) -> Syllabus`. Internally: scouting retrieval to gather context, then a Claude call that returns structured JSON via tool use.
2. **`curio/agent/teacher.py`** — `teach_concept(concept: Concept) -> str`. Retrieves relevant chunks, returns lesson text + a question.
3. **`curio/agent/examiner.py`** — `grade(concept, question, answer) -> Grade`. Returns structured grade via tool use.
4. **`curio/cli.py`** — `curio teach <topic>` runs the full REPL: plan → for each concept: teach → ask → grade → maybe move on.
5. **Pydantic models** — `Syllabus`, `Concept`, `Grade`. These define the structured-output shapes.

---

## Structured outputs — the canonical trick

You want Claude to return JSON, not prose. The reliable way is to define a *tool* that the LLM "calls" with the data. You never actually execute it — you just take the tool's input as the structured output.

```python
syllabus_tool = {
    "name": "submit_syllabus",
    "description": "Submit the final syllabus for the topic. Use this once you've thought through prerequisites and ordering.",
    "input_schema": Syllabus.model_json_schema(),
}

response = client.messages.create(
    model="claude-sonnet-4-6",
    tools=[syllabus_tool],
    tool_choice={"type": "tool", "name": "submit_syllabus"},  # force the tool
    messages=[{"role": "user", "content": planner_prompt}],
)

tool_use = next(b for b in response.content if b.type == "tool_use")
syllabus = Syllabus.model_validate(tool_use.input)
```

The `tool_choice` parameter *forces* Claude to call this specific tool, which guarantees you get structured output matching your schema. (Without it, Claude might give you prose.)

---

## The REPL loop

The full `curio teach` flow, in pseudocode:

```
syllabus = planner.plan_syllabus(topic)
print_outline(syllabus)
for concept in syllabus.concepts:
    while not concept.mastered:
        lesson, question = teacher.teach_concept(concept)
        print(lesson)
        user_answer = input(question + "\n> ")
        grade = examiner.grade(concept, question, user_answer)
        print(grade.feedback)
        if grade.score == "correct":
            concept.mastered = True
        elif grade.score == "partial":
            # let teacher re-explain the weak part
            ...
        # miss → revisit with simpler framing
```

For Phase 4, keep "mastered" purely in-memory (no DB yet — that's Phase 5).

---

## Leading questions

1. **What does a "good" syllabus look like?** Pick a topic you know well, write your own syllabus on paper. Then let the agent generate one. Compare. What's the agent missing? Adjust the prompt.

2. **How many concepts in a syllabus?** Too few (3) and the lessons are too coarse. Too many (50) and the session never ends. Aim for 5-10 for Phase 4. Make it a parameter.

3. **What's the teacher's "voice"?** Try the same lesson with different system prompts: formal textbook, friendly mentor, Socratic. Which feels best? Why?

4. **The examiner's rubric.** Three buckets (correct / partial / miss) is intentionally coarse — finer rubrics often confuse small-scale LLM judges. Why might 1-5 stars be worse than 3 buckets?

5. **What if the user gives a smarter answer than expected?** The agent's expectation is in the question; the user might exceed it. Does your examiner handle "more right than asked for" gracefully? (Usually yes if the prompt is good.)

6. **What if the user types nonsense or "i don't know"?** Should the examiner treat this as a miss? Should the teacher offer a simpler version?

7. **Latency.** Each concept = at least one teach call + one grade call (sometimes more). At 3-5s per Sonnet call, a 7-concept session is 1-2 minutes of LLM time. Is that OK? Should you stream? Use Haiku for grading?

---

## Success criteria

- [ ] `curio teach <topic>` runs end-to-end without crashing on a topic you know
- [ ] The syllabus has plausible ordering and reasonable prerequisites
- [ ] The teacher's explanations are coherent and grounded in retrieved chunks (you can verify by looking at the trace)
- [ ] The examiner's grading feels fair on at least 5 deliberate test answers (1 perfect, 1 partial, 1 wrong, 1 nonsense, 1 "I don't know")
- [ ] You've used **forced tool_choice** for both syllabus generation and grading
- [ ] You've split planner/teacher/examiner into distinct Claude calls with distinct system prompts
- [ ] You can answer [[LEARNING_GUIDE#After Phase 4|Roadmap → After Phase 4]] out loud

---

## Stretch (optional)

- **"Ask me what I know first"** — before the first lesson, the teacher asks 2-3 probing questions to gauge prior knowledge and skip concepts the user already knows
- **Lesson variants** — if a user fails twice on a concept, teacher tries a *different angle* (analogy, worked example, simpler vocabulary). Store last 2 explanations to avoid repetition.
- **Branching syllabus** — instead of linear, model concepts as a DAG (prerequisites). Use NetworkX. Teach by topological order, skipping branches the user already knows.
- **Save the session transcript** — write the full conversation to a markdown file in `data/sessions/` for later review. (This is *not* the same as the learner memory in Phase 5 — that's structured, this is raw.)

---

## Hints

<details>
<summary>Hint 1 — Pydantic models for the structured outputs</summary>

```python
from pydantic import BaseModel, Field
from typing import Literal

class Concept(BaseModel):
    name: str
    summary: str = Field(description="One sentence summary")
    prerequisites: list[str] = Field(default_factory=list, description="Names of prior concepts")
    key_ideas: list[str]

class Syllabus(BaseModel):
    topic: str
    concepts: list[Concept]

class Grade(BaseModel):
    score: Literal["correct", "partial", "miss"]
    feedback: str
    suggestion: str = Field(description="What the teacher should do next")
```
The Pydantic `Field(description=...)` ends up in the JSON schema, which the LLM sees. So write good descriptions.

</details>

<details>
<summary>Hint 2 — Forcing the tool</summary>

```python
response = client.messages.create(
    ...,
    tools=[my_tool],
    tool_choice={"type": "tool", "name": "submit_syllabus"},
)
```
This guarantees Claude will call exactly this tool (no text-only response). Use it whenever you want structured output.

</details>

<details>
<summary>Hint 3 — Keep system prompts in files</summary>

`prompts/planner.md`, `prompts/teacher.md`, `prompts/examiner.md`. Load them at startup. You'll iterate on these constantly — strings in code get ugly fast.

</details>

<details>
<summary>Hint 4 — Cookbook references</summary>

No new spoiler files for Phase 4 — the techniques are extensions of Phase 3's tool use. Refer back to `cookbook/07_anthropic_tool_use.py` and `cookbook/08_pydantic_tools.py`.

</details>

---

When Phase 4 works, you have a real tutor — but one with amnesia. Phase 5 fixes that.
