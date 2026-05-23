---
description: 3 conceptual questions on the current phase, ungraded but with feedback
argument-hint: [optional: phase number, e.g. "3"]
---

The user is working through the Curio rag-learning project and wants a quick conceptual quiz to check their understanding.

**Optional phase override:** $ARGUMENTS

Steps:

1. **Identify the current phase.** If $ARGUMENTS specifies a phase number, use that. Otherwise: check recent conversation context, look at any files they've been editing under `curio/`, or check git log if applicable. If still ambiguous, ask one sharp question to disambiguate (e.g. "Quiz on Phase 2 (hybrid retrieval) or Phase 3 (agent loop)?") rather than guessing.

2. **Draft 3 questions** drawn from the "Roadmap → After Phase N" section of `LEARNING_GUIDE.md` plus any leading questions in `phases/0N_*.md`. Mix:
   - 1 "explain it in your own words" question (concept)
   - 1 "what would happen if..." question (intuition / trade-off)
   - 1 "trace through this specific scenario" question (applied)

3. **Ask them one at a time.** After each answer:
   - If correct: confirm briefly, surface one nuance they may not have mentioned, move on.
   - If partially correct: name what's right, name what's missing, give them a chance to add — don't immediately reveal the answer.
   - If wrong: don't say "wrong" bluntly. Re-ask with a sharper hint or a re-framing. If they still miss after the second try, explain it cleanly and move on.

4. **At the end:** a one-paragraph summary of which concepts feel solid vs. which are worth revisiting. Suggest 1-2 specific sections of `LEARNING_GUIDE.md` if there are gaps.

Constraints:
- Don't ask all 3 questions at once. One at a time. Let them think.
- Don't grade harshly — this is for *their* learning, not evaluation.
- Push back gently if their answer is shallow ("can you say a bit more about WHY?"). Real understanding shows in the why.
- Don't write code in this command. It's a conceptual check.
