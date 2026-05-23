# Curio Learning Guide

This is your **conceptual companion** to the Curio project. `PROJECT_PLAN.md` tells you *what* to build. This document tells you *what to understand* — concepts, tools, and a roadmap of mental models you should own at the end of each phase.

Treat this like a textbook, not a recipe. Skim once before Phase 1, then come back per-phase as the relevant concepts apply.

---

## Table of Contents

1. [[#How to use this guide]]
2. [[#Core Concepts]]
   - [[#Embeddings and vector spaces]]
   - [[#Chunking]]
   - [[#Dense vs sparse retrieval]]
   - [[#Reranking]]
   - [[#The agent loop]]
   - [[#Agentic vs naive RAG]]
   - [[#Memory in agents]]
   - [[#Evals and LLM-as-judge]]
3. [[#Tool primers]]
   - [[#Ollama]]
   - [[#sentence-transformers]]
   - [[#LanceDB]]
   - [[#Anthropic SDK]]
   - [[#Pydantic v2]]
   - [[#SQLite]]
4. [[#Roadmap]]
5. [[#Curated reading list]]
6. [[#Working rhythm]]
7. [[#Common traps]]

---

## How to use this guide

- **Before starting a phase:** re-read the concept sections that map to that phase (Phase 1 → embeddings, chunking. Phase 3 → agent loop. Etc.)
- **Read the tool primer for any new tool you'll touch in that phase** — don't read all of them up front.
- **The roadmap section** is the most important page. After each phase, you should be able to answer those questions out loud. If you can't, you skipped something.
- **Use `/concept <topic>` in this directory** to get a focused, interactive explanation of any concept here.

---

## Core Concepts

### Embeddings and vector spaces

**The mental model.** An embedding model is a function `text → vector` (a list of, say, 384 floats). The crucial property: texts with similar *meaning* end up at similar *positions* in that 384-dimensional space. "King" and "queen" land close together. "King" and "broccoli" land far apart. This holds for sentences and paragraphs too, not just single words.

This works because the embedding model was trained on hundreds of millions of (similar-text, similar-text) and (different-text, different-text) pairs, learning to place semantically related text close in vector space.

**Why it matters for RAG.** You want to find passages relevant to a question. Exact keyword matching is brittle — the user asks "how do plants make food?" but the document says "photosynthesis converts light energy into chemical energy." No shared keywords, but semantically identical. Embed both, compute cosine similarity, they're close. That's how RAG escapes keyword search.

**Cosine similarity** — the standard way to measure "closeness" between two embedding vectors. Equals 1.0 if vectors point the same direction, 0 if perpendicular, -1 if opposite. Most vector DBs use cosine (or its cousin, inner product on normalized vectors) under the hood. You don't compute this yourself — the vector DB does.

**Why dimensions matter.** Higher-dim embeddings (e.g. 1024d) capture more nuance but cost more memory + compute. Lower-dim (e.g. 384d) are faster and cheaper. For most RAG, 384d is plenty. You're using BGE-small (384d, 130MB) — a sweet spot.

**Question to internalize:** if a user asks a question that requires a *very specific keyword* (e.g. an error code "E_404_X"), will dense embeddings find it? (Often not — this is why we need hybrid retrieval, see below.)

### Chunking

**The problem.** You have a 10,000-word Wikipedia article. You can't embed the whole thing as one vector — too much information gets averaged away. You also can't pass all 10,000 words to the LLM (context limits, cost, distraction). So you **chunk** the document into smaller pieces, embed each chunk, and retrieve relevant chunks at query time.

**The trade-offs:**
- **Too small** (e.g. 50 tokens) → chunks lack context. "He stated this was incorrect" is useless without the surrounding paragraph.
- **Too large** (e.g. 5000 tokens) → embeddings get mushy (averaging too many ideas), and you can't fit many chunks in the LLM context.
- **Sweet spot for most prose** is 300-800 tokens with 10-20% overlap.

**Overlap** = repeat ~50 tokens from the end of chunk N at the start of chunk N+1. Why? An idea that spans the chunk boundary would otherwise be split and findable in neither. Overlap is cheap insurance.

**Token-aware vs character-aware vs semantic.**
- *Character-aware* (split every 2000 characters): naive, can split mid-word, terrible.
- *Token-aware* (use the LLM's tokenizer): respects word boundaries, predictable for context-limit math. **Default to this.**
- *Semantic* (split at paragraph / heading boundaries): preserves logical units but variable size. Best for structured docs (markdown, papers). More work to implement.

**Question to internalize:** if the user's question requires synthesizing two facts from far-apart parts of a document, does chunking hurt you? (Yes — and this is one motivation for *agentic* retrieval where the LLM can fetch multiple chunks and reason across them.)

### Dense vs sparse retrieval

- **Dense retrieval** = embeddings + cosine similarity. Strong on *semantic* matches. Weak on *exact keyword* matches (acronyms, IDs, rare terms, named entities the model hasn't seen).
- **Sparse retrieval** = BM25 (Best Match 25), an improvement on TF-IDF. Strong on keyword/lexical matches. Weak on semantic matches (synonyms, paraphrases).
- **Hybrid** = run both, combine the result lists. The most common combiner is **Reciprocal Rank Fusion (RRF)**: each chunk gets a score of `Σ 1/(k + rank_i)` summed across the result lists it appears in. Simple, parameter-light, works well.

**Why both are needed.** If a user asks "what is BFGS-Q?", dense embeddings might miss it (model doesn't know the acronym). BM25 will find documents containing "BFGS-Q" verbatim. If they ask "how does a Roomba see?", BM25 might miss the answer phrased as "uses LIDAR sensors." Dense will find it.

**Question to internalize:** why don't you always just use BM25 (it's free, no embedding model needed)? (Because synonyms, paraphrases, and natural-language queries crush it.)

### Reranking

**The setup.** After hybrid retrieval, you have 20 candidate chunks. You can only afford to pass 5 to the LLM (context costs). Which 5?

**Cross-encoder rerankers** — a different kind of model from your embedding model. An embedder embeds *one piece of text at a time* and you compare with cosine. A cross-encoder takes (query, chunk) *together* as input and outputs a relevance score. It's much more accurate because it can directly model the interaction between query and chunk — but ~100x slower per pair. So the pipeline is:

1. Hybrid retrieval over your corpus → top 20 (fast)
2. Cross-encoder reranker scores all 20 (slower, but only 20 calls) → top 5

**The result:** dramatically better top-5 precision. This is widely considered the cheapest single accuracy win in RAG. The model you'll use is `bge-reranker-v2-m3`, ~570MB, runs fine on M3.

**Question to internalize:** could you just use a cross-encoder as your *only* retrieval method (skip the embedding step)? (No — you'd need to score the query against every chunk in your corpus, which doesn't scale past a few hundred chunks.)

### The agent loop

This is the central pattern of agentic systems. Read carefully.

**Simple LLM call:** you send `messages` → model returns `text`. Done. One round-trip.

**Tool-use LLM call (agent loop):**
1. You send `messages` + `tools` (a list of tool schemas, e.g. `search_corpus(query: str, k: int)`)
2. Model returns either: (a) text + `stop_reason="end_turn"` (it's done), OR (b) one or more `tool_use` blocks + `stop_reason="tool_use"` (it wants to call a tool)
3. If (b): you execute the tool(s), append the `tool_use` block(s) AND the `tool_result` block(s) to messages, send back to model
4. Loop: model now has the tool results in context, decides what to do next — might call more tools, might answer
5. Continue until `stop_reason="end_turn"`

That's it. The "agent" is just an LLM in a loop where the LLM decides each turn whether to call a tool or finish.

**Crucially, the LLM is stateless between turns.** Your code keeps the message history; the model just sees the full conversation each turn. The "memory" is your message list.

**Why this is powerful.** The LLM can:
- Decide *when* to search (vs. when it already knows the answer)
- Decide *what* to search for (rewrite the user's question into a better query)
- Iterate (search → didn't find it → try a different query → search again)
- Combine tools (search corpus → if nothing useful → web search → if found a paper → read it in full)

**Question to internalize:** what's the difference between an LLM with tool use and an LLM with no tools that's just told "to answer, write '<SEARCH: query>' and we'll show you results"? (Functionally similar, but tool-use is a *structured protocol* the model is trained on — it's far more reliable than parsing strings out of prose.)

### Agentic vs naive RAG

**Naive RAG** (Phase 1):
```
question → embed → search → top-k chunks → stuff into prompt → answer
```
Single round-trip. No reasoning about retrieval. Works for simple "find a fact" questions. Fails on multi-hop ("how does X relate to Y?"), questions where the user's wording is imprecise, or questions that require iterating until enough evidence is found.

**Agentic RAG** (Phase 3+):
```
question → agent decides what to search → search → maybe more searches → maybe read in full → answer
```
The LLM is in control. Slower (multiple round-trips), more expensive (more tokens), but qualitatively better on hard questions.

**The headline trade-off:** agentic systems are slower and more expensive in exchange for quality and flexibility. They're the right call when retrieval is hard; overkill when it's easy.

### Memory in agents

There are several distinct kinds of "memory" in an agent — don't confuse them:

1. **Context window** — the literal tokens the model sees this turn. Ephemeral, capped by model limits (200K for Claude).
2. **Working memory** — the message history within a single conversation. You manage this. Often you compress / truncate it as it grows.
3. **Episodic memory** — what happened in past sessions. You persist this to a database (SQLite in Curio). The agent queries it with tools like `get_learner_state(topic)`.
4. **Semantic memory** — extracted facts/knowledge about the user. "Milan struggles with eigenvalues." Stored in the same DB. Updated by the agent over time.

Phases 1-4 only use working memory (within-session). Phase 5 introduces episodic and semantic memory.

**Question to internalize:** why not just dump all past sessions into the context window? (Cost, context limits, signal-to-noise — most past content is irrelevant to the current turn.)

### Evals and LLM-as-judge

**The vibes problem.** Early on you'll change something ("I added a reranker!") and feel like the answers got better. They might have. Or you might be confirmation-biased. Or they got better on some questions and worse on others.

**The fix:** a frozen test set + automated scoring.

**Retrieval evals** are easy: hand-write 20 (question, expected-chunk-id) pairs. After any change, recompute recall@5 (was the right chunk in the top 5?). Numeric, deterministic, fast.

**Generation evals are hard:** "is this lesson good?" has no ground truth. Options:
- **Reference-based** (need a gold answer): BLEU, ROUGE. Mostly useless for free-form generation.
- **LLM-as-judge** (no gold answer needed): another LLM (often Claude with a rubric prompt) scores the output. e.g. "Rate this lesson 1-5 on accuracy, clarity, pedagogical structure."
- **Human eval** (you read it). Most accurate, slowest.

**LLM-as-judge caveats:**
- The judge has biases (favors verbose answers, its own writing style, certain structures).
- Calibration drifts across model versions.
- Best used to detect *regressions* (relative changes) more than to claim absolute quality.

**Question to internalize:** what's a good test set size? (For learning: 20-30 hand-curated examples is plenty. For production: hundreds, refreshed regularly.)

---

## Tool primers

For each: what it is, the mental model, and the 3-5 API calls you actually need.

### Ollama

**What it is.** A local server that runs open-source LLMs on your Mac. You download a model with `ollama pull`, then call its HTTP API. Models run on Apple Silicon GPU via Metal — fast.

**Mental model.** It's a tiny replacement for the Anthropic/OpenAI API surface, but running on localhost. You give it `messages`, it gives you back text.

**Calls you need:**
```
POST http://localhost:11434/api/chat
{
  "model": "qwen2.5:3b-instruct-q4_K_M",
  "messages": [{"role": "user", "content": "..."}],
  "stream": false
}
```
Returns `{"message": {"role": "assistant", "content": "..."}, ...}`.

You can use the `ollama` Python package or just hit the HTTP API with `httpx`. Doing the HTTP yourself is more educational — it's literally one POST request.

### sentence-transformers

**What it is.** A Python library for loading embedding models (and cross-encoder rerankers) and embedding text. Wraps HuggingFace under the hood. Apple Silicon GPU support via PyTorch's MPS backend.

**Mental model.** A function `texts: list[str] → vectors: np.ndarray` for embedders. For rerankers, `(query, chunks) → scores`.

**Calls you need (embedder):**
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("BAAI/bge-small-en-v1.5")
vectors = model.encode(["text 1", "text 2"], normalize_embeddings=True)
# vectors.shape == (2, 384)
```

**Calls you need (reranker):**
```python
from sentence_transformers import CrossEncoder
reranker = CrossEncoder("BAAI/bge-reranker-v2-m3")
scores = reranker.predict([("query", "chunk 1"), ("query", "chunk 2")])
```

**Gotcha:** `normalize_embeddings=True` is required for cosine similarity to behave correctly with most vector DBs that default to inner product on normalized vectors.

### LanceDB

**What it is.** An embedded (no-server) vector database. Stores tables of records, where one column is a vector. Supports dense + sparse + hybrid search. File-based — your data lives in a folder.

**Mental model.** Think SQLite but for vectors. You `connect()` to a folder, `create_table()` with a schema, `add()` records, then `search()`.

**Calls you need:**
```python
import lancedb
db = lancedb.connect("./data/lance")
table = db.create_table("chunks", data=[
    {"text": "...", "vector": [0.1, 0.2, ...], "source": "wiki/foo"}
])
results = table.search(query_vector).limit(5).to_list()
```

For hybrid search you'll set up an FTS index for the text column, then use `.search(query="...", query_type="hybrid")`. See `cookbook/05_hybrid_search.py` when you get to Phase 2.

### Anthropic SDK

**What it is.** The official Python client for the Claude API. Handles auth, request shape, response parsing, streaming, tool use.

**Mental model.** A thin wrapper around the REST API. The interesting complexity is in the *protocol* (especially tool use), not the SDK itself.

**Calls you need (basic):**
```python
from anthropic import Anthropic
client = Anthropic()  # reads ANTHROPIC_API_KEY from env
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": "..."}],
)
print(response.content[0].text)
```

**Calls you need (tool use):**
```python
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    tools=[{
        "name": "search_corpus",
        "description": "Search the knowledge corpus...",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}, "k": {"type": "integer"}}},
    }],
    messages=[...],
)
# response.stop_reason might be "tool_use"
# response.content is a list of blocks; some may be {"type": "tool_use", "id": ..., "name": ..., "input": ...}
```

You then execute the tool, send back a `tool_result` block referencing the `id`, and loop until `stop_reason == "end_turn"`. See `cookbook/07_anthropic_tool_use.py`.

**Two models you'll use:**
- `claude-sonnet-4-6` — the workhorse. Strong reasoning, reliable tool use. Best for the agent loop.
- `claude-haiku-4-5-20251001` — faster, cheaper. Best for subtasks like query rewriting or grading where you don't need full Sonnet horsepower.

### Pydantic v2

**What it is.** A Python library for typed data validation. Define a class with type hints, get free JSON validation and serialization.

**Mental model.** Like a `@dataclass` but with runtime validation against the types. If you say `query: str`, Pydantic will refuse a dict.

**Calls you need:**
```python
from pydantic import BaseModel

class SearchCorpusInput(BaseModel):
    query: str
    k: int = 5

# Validate from dict (e.g. tool call args from Claude):
parsed = SearchCorpusInput.model_validate({"query": "...", "k": 10})
# Get JSON schema (for tool definitions):
schema = SearchCorpusInput.model_json_schema()
```

The reason this matters for agents: the LLM sometimes sends tool inputs with wrong shapes. Pydantic catches that and lets you return an error to the LLM instead of crashing.

### SQLite

**What it is.** A file-based relational database built into Python. Zero config, zero server, perfect for single-user apps.

**Mental model.** A real SQL database (queries, indexes, transactions) that lives in one file.

**Calls you need:**
```python
import sqlite3
conn = sqlite3.connect("data/learner.db")
conn.execute("CREATE TABLE IF NOT EXISTS attempts (concept TEXT, score INTEGER, ts INTEGER)")
conn.execute("INSERT INTO attempts VALUES (?, ?, ?)", ("eigenvalues", 2, 1700000000))
conn.commit()
rows = conn.execute("SELECT * FROM attempts WHERE concept = ?", ("eigenvalues",)).fetchall()
```

**Pro tip:** put your schema in a `.sql` file and run it on startup with `conn.executescript(open("schema.sql").read())`. Keeps schema readable and version-controllable.

---

## Roadmap

After each phase, you should be able to answer these *out loud* without checking notes. If you can't, you skipped something — go back.

### After Phase 1
- What is an embedding? How would you explain it to a friend who knows Python but not ML?
- What's in your LanceDB table — describe the schema, what each row represents, what the vector column means.
- Why did you choose your chunk size? What would happen if you doubled it? Halved it?
- When the LLM hallucinates a citation, what part of the pipeline is to blame?
- What's the rough latency of: (a) embedding a query, (b) vector search over 1000 chunks, (c) generating an answer with the local LLM?

### After Phase 2
- What kind of query does BM25 win on that dense embeddings lose? Give a real example from your corpus.
- What's Reciprocal Rank Fusion in one sentence? Why do you add `1/(k+rank)` instead of just averaging scores?
- What's the difference between an embedder and a cross-encoder reranker? Why not use the reranker for the initial search?
- Looking at your recall@5 numbers: which questions still fail? What's the pattern?

### After Phase 3
- Walk through one full tool-use loop for a hard question. What did the agent do at each step?
- Why is the LLM "stateless between turns" but the conversation has memory?
- What would happen if your `search_corpus` tool sometimes returned no results — how does the agent recover?
- Compare a Phase 1 answer vs a Phase 3 answer on the same hard question. What's different about the *process*, not just the output?

### After Phase 4
- What's a "structured output" and why is it useful for the syllabus step? How does Claude's tool use enable it?
- Why split planner/teacher/examiner into separate roles instead of one mega-prompt?
- What's in the lesson context window? Trace it: system prompt + retrieved chunks + recent history.
- What happens when the examiner grades the user wrong? How would you debug that?

### After Phase 5
- Name three distinct kinds of memory in your system. Where does each live?
- How does the teacher use learner state when deciding what to teach next?
- What's spaced repetition and how (loosely) is it modeled in your scoring?
- If the user goes silent for a month and comes back, what does session N+1 look like?

### After Phase 6
- What does your retrieval eval measure? Why recall@5 and not recall@1 or recall@20?
- What's an LLM-as-judge prompt and what are three biases to watch for?
- Walk through a trace for one session. What questions would you ask of the trace if quality regressed tomorrow?
- What's the cheapest change you could make right now that would most likely improve quality? How would you know?

---

## Curated reading list

Read these *as the relevant phase comes up*, not all at once.

### Phase 1
- [BGE: BAAI General Embedding (model card)](https://huggingface.co/BAAI/bge-small-en-v1.5) — read the "Usage" and "Evaluation" sections
- [LanceDB Quickstart](https://lancedb.github.io/lancedb/) — the first ~5 pages
- [Ollama API Reference](https://github.com/ollama/ollama/blob/main/docs/api.md) — just `/api/chat`

### Phase 2
- [BM25 explained intuitively](https://www.elastic.co/blog/practical-bm25-part-2-the-bm25-algorithm-and-its-variables) — Elastic's blog, very clear
- [Reciprocal Rank Fusion paper (skim)](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf) — 2 pages, just the algorithm
- [The case for cross-encoders (Pinecone)](https://www.pinecone.io/learn/series/rag/rerankers/) — short, well-illustrated

### Phase 3
- [Anthropic: Tool use overview](https://docs.anthropic.com/en/docs/build-with-claude/tool-use) — official, your bible for the protocol
- [Lilian Weng: LLM Powered Autonomous Agents](https://lilianweng.github.io/posts/2023-06-23-agent/) — the foundational mental model post; some details are dated, the concepts aren't
- [Anthropic: Building effective agents](https://www.anthropic.com/research/building-effective-agents) — opinionated, very practical

### Phase 4
- [Anthropic: Structured outputs with tool use](https://docs.anthropic.com/en/docs/build-with-claude/tool-use#chain-of-thought-tool-use) — the section on using tools for non-conversational structured output
- Optionally: [Patterns for building multi-agent systems](https://www.anthropic.com/research/multi-agent-research-system) — Anthropic's writeup, accessible

### Phase 5
- [Generative Agents: Interactive Simulacra of Human Behavior](https://arxiv.org/abs/2304.03442) — skim section 4 (Memory and Retrieval). Origin of the modern "agent with memory" pattern.
- [MemGPT (skim the architecture diagram)](https://arxiv.org/abs/2310.08560) — overkill for Curio but the conceptual layering is worth seeing

### Phase 6
- [Eugene Yan: How to evaluate RAG](https://eugeneyan.com/writing/llm-patterns/#evals-to-measure-performance) — the section on evals is excellent
- [Anthropic: Reducing latency](https://docs.anthropic.com/en/docs/about-claude/agent-and-tools/latency) — observability mindset
- [LLM-as-Judge: a survey (just the intro)](https://arxiv.org/abs/2411.15594)

### Foundational (read anytime)
- [The original RAG paper (Lewis et al., 2020)](https://arxiv.org/abs/2005.11401) — the term "RAG" was born here. Skim section 2.
- [Anthropic prompt engineering docs](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview) — the whole section is excellent and short

---

## Working rhythm

LLM apps fail differently than normal apps. The bug is rarely an exception — it's "the output is bad." Some habits:

1. **Read the inputs.** When the output is wrong, 80% of the time the inputs were wrong (bad retrieval, missing context, garbled chunk). Look at what the LLM actually saw before blaming the LLM.

2. **Log everything, structured.** Every retrieval (query, top-k with scores), every LLM call (full messages + response), every tool call (name + input + output). JSONL files in `traces/`. You'll inspect these constantly.

3. **Lower the temperature when debugging.** `temperature=0` makes outputs ~deterministic. Two runs should be near-identical. If they aren't, your *inputs* changed (maybe retrieval is non-deterministic — investigate).

4. **Bisect, don't speculate.** "I think the reranker is hurting" — test it. Disable the reranker, re-run your eval set, compare numbers. Vibes lie.

5. **Trust prints over docs.** When integrating a new library, `print(result)` and look at the actual shape. Docs lie or omit; the runtime doesn't.

6. **Save a test session.** Pick 5-10 questions / scenarios you know well. Re-run them after any change. This is your smoke test.

7. **Don't try to "fix" the LLM.** If the model is consistently bad at something, the fix is usually upstream (better retrieval, clearer prompt, structured output, smaller subtask). Asking the same model "but really do better this time" rarely works.

---

## Common traps

- **Stuffing too many chunks into the context** — more isn't better. Past ~10 chunks the model gets distracted. Quality of top 3-5 matters more than quantity of top 20.
- **Mocking the LLM in tests** — your "tests pass" but production fails. Either don't test LLM behavior in unit tests, or use a real (cheap) model in integration tests.
- **Over-engineering the agent loop early** — write the simplest 30-line loop first. Add complexity (parallel tool calls, retries, repair) only when you have a concrete reason.
- **Hand-waving evals** — "looks better" is not a metric. Numbers or it didn't happen.
- **Embedding the wrong text** — sometimes you want to embed the *question* a chunk answers, not the chunk itself. Or embed a summary, not the raw passage. Be deliberate.
- **Forgetting to normalize embeddings** when your vector DB expects unit vectors. Causes silently bad search.
- **Building the framework, not the product** — easy to spend a week on a perfect `LLMClient` abstraction. Use a simple version, evolve it when you actually need to swap.
- **Letting the agent loop run forever** — always set a max turn count. Buggy loops cost real money.
- **Trusting LLM-as-judge absolutely** — it's a *signal*, not a *truth*. Spot-check with your own eyes regularly.

---

That's the guide. Reference it, don't memorize it. The goal is that by Phase 6, every concept here feels obvious because you've built systems that use them.
