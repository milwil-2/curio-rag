---
description: Focused explanation of a RAG/agent concept with worked mini-examples
argument-hint: <concept name>
---

The user is working on the Curio rag-learning project (see PROJECT_PLAN.md and LEARNING_GUIDE.md in this repo) and wants a focused, interactive explanation of the concept:

**Concept:** $ARGUMENTS

Your job:

1. Give a 2-3 sentence **plain-English definition** — like you'd explain to a smart friend who doesn't know the jargon.
2. Walk through **one concrete worked example** end-to-end. Use realistic data (not "foo" / "bar"). Show inputs, intermediate steps, and outputs.
3. Name the **one most common misconception** about this concept and clear it up.
4. Tie it back to **where it shows up in Curio** — which phase of the project uses this, and what it's protecting against.
5. End with **one short question** for the user that checks whether they got the core idea. Don't grade their answer unless they reply.

Constraints:
- Avoid restating LEARNING_GUIDE.md verbatim. Reference it if it'd be useful, but bring your own framing.
- No code blocks longer than ~15 lines. This is a conceptual explainer, not a tutorial.
- If the concept is ambiguous (e.g. "memory" could be 4 different things), pick the most likely interpretation given the current phase context, but call out the disambiguation in one sentence.
- If the concept isn't actually in the project's scope (e.g. "graph neural networks"), say so and suggest a related in-scope concept instead.

Remember: Milan writes the code; you're his guide. Don't drift into "here's how to implement it" — that's what the phase docs are for.
