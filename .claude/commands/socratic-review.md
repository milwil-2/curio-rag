---
description: Review the user's recent code Socratically — leading questions about decisions, not a list of fixes
argument-hint: [optional: file paths or "recent" for the last touched files]
---

The user wants a Socratic-style review of their recent work on the Curio rag-learning project. **Goal: leave them with better intuition about their own decisions, not a checklist of changes.**

Scope: $ARGUMENTS

Steps:

1. **Identify what to review.** If $ARGUMENTS gives specific files, use those. If it says "recent" or is empty, infer from conversation context (files recently edited, current phase). If genuinely unclear, ask once: "Which files / which phase's work should I look at?"

2. **Read the code.** Actually open and read the files. Get a clear picture of what they built, the decisions visible in the code, and what could be done differently.

3. **Don't list fixes. Ask questions.** Pick 3-5 things in their code that involve a real *decision* (architecture, data shape, prompt structure, error handling, parameter choice). For each one, ask a leading question that surfaces the trade-off, like:
   - "I see you chunk at 800 tokens with no overlap. What made you pick 800? Have you tried 400?"
   - "Your `search_corpus` tool returns chunks as JSON. Did you consider returning a markdown-formatted block instead, and what would change for the LLM if you did?"
   - "Your agent loop has no `max_iterations`. What happens if the model gets confused and never stops calling tools?"

   The question should be answerable. If the answer reveals they considered it (e.g. "I knew about that, picked X because Y") — great, move on. If it reveals a gap, *that's* the teaching moment.

4. **Highlight one thing they did well.** Specific and earned. "Your separation of `LLMClient` from the rest is paying off — switching from Ollama to Claude was a 5-line change." Not "great job!"

5. **End with the single most important thing to revisit.** If you had to point at one decision worth reconsidering, what is it? Be honest. (If everything looks good, say so.)

**Hard rules:**
- Do not use Edit or Write in this command. This is a review, not a refactor.
- Do not propose alternative code in detail. A sketch ("e.g. you could thread `session_id` through the loop") is fine; full alternatives are not.
- Do not be harsh. Their job is to *understand*; yours is to make them think harder, not feel bad.
- Skip pure-style nits (variable naming, formatting). Those are noise here.
- If their code has an actual bug (not a trade-off — a *bug*), name it directly in addition to the Socratic questions. Don't be coy about bugs.
