# Curio — An Adaptive Tutor That Teaches You Anything

## Context

You want a project that teaches both **RAG** (retrieval-augmented generation) and **agentic workflows** in a hands-on way, starting from zero LLM-app experience. The challenge with most RAG tutorials is they stop at "chat with your docs" — which barely scratches modern patterns (agentic retrieval, multi-step reasoning, memory, evals, multi-agent orchestration).

**Curio** is a personalized tutor: you say *"teach me quantum field theory"* or *"teach me how the Fed sets interest rates"*, and it builds you a custom syllabus from Wikipedia + research papers + your own notes, runs interactive lessons, quizzes you, tracks what you know across sessions, and adapts. It's an excellent learning project because:

- It exercises **every core RAG primitive** (ingestion, chunking, embeddings, hybrid search, reranking, citation)
- It demands a real **agentic loop** (the agent must plan, retrieve, teach, grade, reflect, remember)
- It's genuinely **useful** — when you finish you have a tool you'll actually use to learn things
- It's **incremental** — each phase ships a working system and adds one concept

Built on a **hybrid stack**: local embeddings + local vector DB (your M3 handles this easily), local LLM for early phases, Claude API for later agentic phases. You keep your data private and your API bill small.

---

## How We'll Work Together

**You write the code. I'm your guide.**

For each phase I'll point you to:
- The 1-3 concepts you need to understand before starting (with the *right* docs/links to read, not a firehose)
- The interface/shape of what you're building (function signatures, data flow), not the implementation
- The common gotchas I've seen others hit

You drive the keyboard. When you're stuck, share:
- The error or unexpected behavior
- What you've already tried
- The relevant code

I'll diagnose, suggest the next experiment, or explain the underlying concept — but I won't reach for the keyboard unless you explicitly ask me to write a specific chunk (e.g. "the Claude tool-use loop is fiddly, can you draft this one?"). Some pieces are genuinely worth me writing so you can read them as a reference (the agent loop is a good candidate).

For each phase you should be able to:
1. Explain what you're building and why, in your own words
2. Write the code with light reference to docs
3. Run it and debug failures yourself
4. Verify it works using the criteria at the end of the phase

If any of those four feels shaky after a phase, we slow down and dig in before moving on. The goal isn't to finish — it's to understand.

---

## Tech Stack (and why)

| Concern | Choice | Why |
|---|---|---|
| Language | **Python 3.11+** | Richest LLM ecosystem, gentlest on-ramp |
| Reasoning model (local, Phases 1-2) | **Ollama** running **Qwen 2.5 3B Instruct** or **Llama 3.2 3B Instruct** (Q4_K_M, ~2GB) | Fits comfortably in 8GB unified RAM alongside the embedding model. Good enough for "given chunks, write cited answer." Free. |
| Reasoning model (cloud, Phase 3+) | **Claude Sonnet 4.6** (agent loop, teaching), **Haiku 4.5** (cheap subtasks: query rewrites, grading) | Reliable tool-use, large context. Switch in when local models start failing on multi-step tool calls. |
| LLM abstraction | Custom `LLMClient` interface (`generate`, `generate_with_tools`) with `OllamaClient` and `AnthropicClient` implementations | Swap models by changing one line. Teaches a pattern you'll use in every real LLM app. |
| Embeddings | **sentence-transformers** with `BAAI/bge-small-en-v1.5` (384-dim, ~130MB) | Runs in <50ms per query on M3 via PyTorch MPS. Top of MTEB at small sizes. No API cost. |
| Vector DB | **LanceDB** | Embedded (no server), file-based, hybrid search out of the box, great on Apple Silicon. Simpler than Qdrant, more mature than sqlite-vss. |
| Reranker | **bge-reranker-v2-m3** (cross-encoder) via sentence-transformers | Dramatically improves retrieval quality. Local, fast on M3. |
| Wikipedia | **wikipedia-api** + raw HTTP for full-article HTML | Free, no key |
| PDF/markdown ingestion | **pypdf**, **markdown-it-py** | Simple, no AI needed for parsing |
| Learner state | **SQLite** (stdlib) | Zero-config, perfect for single-user app |
| CLI UI | **rich** (later: **textual** if you want TUI) | Pretty output, progress bars, makes the loop feel alive |
| Tracing | JSONL trace file → optionally **Langfuse** (free tier) | See every agent turn, every retrieval, every tool call |
| Schemas | **Pydantic v2** | Tool-call argument validation |

**Deliberately avoided**: LangChain / LlamaIndex. They abstract away the exact concepts you want to learn. Build from scratch with the `anthropic` SDK — once you understand the primitives, you can choose whether you want a framework.

---

## Project Structure

```
rag-learning/
├── README.md
├── pyproject.toml          # uv-managed deps
├── .env.example            # ANTHROPIC_API_KEY=...
├── curio/
│   ├── __init__.py
│   ├── cli.py              # entry point: `curio teach "quantum mechanics"`
│   ├── config.py           # paths, model names, constants
│   ├── ingest/             # document → chunks → embeddings → LanceDB
│   │   ├── wikipedia.py
│   │   ├── pdf.py
│   │   ├── markdown.py
│   │   └── chunker.py      # semantic / token-aware chunking
│   ├── retrieval/
│   │   ├── store.py        # LanceDB wrapper (add, hybrid_search)
│   │   ├── embed.py        # sentence-transformers wrapper
│   │   └── rerank.py       # cross-encoder reranker
│   ├── llm/
│   │   ├── base.py         # LLMClient protocol: generate(), generate_with_tools()
│   │   ├── ollama_client.py # local: hits http://localhost:11434
│   │   └── anthropic_client.py # cloud: anthropic SDK
│   ├── agent/
│   │   ├── loop.py         # the core agent loop (tool-use rounds)
│   │   ├── tools.py        # @tool definitions: search_corpus, web_search, ...
│   │   ├── planner.py      # builds syllabus from retrieved corpus
│   │   ├── teacher.py      # runs a single lesson
│   │   └── examiner.py     # generates + grades quizzes
│   ├── memory/
│   │   ├── learner.py      # SQLite-backed: what you know, last session, weak spots
│   │   └── schema.sql
│   └── obs/
│       └── trace.py        # JSONL trace writer
├── data/
│   ├── lance/              # vector DB (gitignored)
│   ├── learner.db          # SQLite (gitignored)
│   └── notes/              # your own markdown notes to ingest (gitignored)
├── evals/
│   ├── retrieval_eval.py   # measure recall@k on a hand-built test set
│   ├── lesson_eval.py      # LLM-as-judge on lesson quality
│   └── fixtures/           # 20-30 q/a pairs for testing
└── traces/                 # JSONL agent traces (gitignored)
```

---

## The Learning Path: 6 Phases

Each phase is a **working end-to-end system** that adds one concept. Don't move on until the current phase actually works and you understand why.

### Phase 1 — Naive RAG (weekend 1) — **Local, $0**
**Goal:** "Ask a question about quantum mechanics, get a cited answer."

Build:
- `llm/base.py` + `llm/ollama_client.py`: `LLMClient.generate(messages) -> str`. Just hit `POST localhost:11434/api/chat`. Pick model via env var.
- `ingest/wikipedia.py`: fetch ~20 Wikipedia articles on a chosen topic, parse, chunk (~500 tokens with 50 token overlap)
- `retrieval/embed.py`: load BGE-small, embed chunks
- `retrieval/store.py`: write chunks + embeddings to LanceDB
- Simple script: embed user question → top-5 nearest chunks → stuff into local LLM prompt → answer with `[source: <article>]` citations

**Setup:** `brew install ollama && ollama pull qwen2.5:3b-instruct-q4_K_M`

**You will learn:** embeddings as semantic coordinates, chunking trade-offs, why naive RAG hallucinates citations, the cosine-similarity / vector-DB mental model, the LLM-as-pluggable-component pattern.

**Verify:** Ask 5 questions you know the answer to. Are citations correct? Where does it fail?

### Phase 2 — Hybrid Search + Reranking (weekend 2)
**Goal:** Fix the cases where Phase 1 retrieved the wrong chunks.

Build:
- Add BM25 sparse search alongside dense (LanceDB supports both)
- Combine with Reciprocal Rank Fusion
- Add cross-encoder reranker over top-20 → keep top-5
- Re-run your Phase 1 questions

**You will learn:** why dense embeddings miss keyword-specific queries, what a reranker actually does, why re-ranking is the cheapest accuracy win in RAG.

**Verify:** Build `evals/retrieval_eval.py` — 20 hand-written (question, expected-chunk-id) pairs. Measure recall@5 for naive vs hybrid vs hybrid+rerank. You should see a clear improvement.

### Phase 3 — Agentic Retrieval (weekend 3)
**Goal:** Stop stuffing 5 chunks into one prompt. Let Claude *decide* what to search for.

Build:
- `agent/loop.py`: implement Claude tool-use loop (request → tool_use → tool_result → repeat until `stop_reason=end_turn`)
- `agent/tools.py`: define `search_corpus(query, k)`, `read_full_article(title)`, `web_search(query)` (use Brave Search API or DuckDuckGo)
- System prompt: "You're researching to answer a question. Use tools as many times as you need. Cite sources."

Now ask hard, multi-hop questions ("How does the uncertainty principle relate to the stability of atoms?"). Watch in your trace log as the agent issues 3-5 searches, reads full articles, then answers.

**You will learn:** the agent loop, tool-use protocol, query decomposition, why agentic retrieval beats naive single-shot RAG on complex questions.

**Verify:** Run the same hard question through Phase 1 vs Phase 3. Inspect the JSONL trace — count tool calls, see the reasoning.

### Phase 4 — Syllabus + Lesson Loop (weekend 4)
**Goal:** Stop just answering questions. Become a tutor.

Build:
- `agent/planner.py`: given a topic, agent does scouting retrieval → outputs a structured syllabus (ordered list of `{subtopic, prerequisites, key_concepts}`) as JSON
- `agent/teacher.py`: for each lesson, retrieve relevant chunks, present concept in 2-3 paragraphs, ask one open-ended question
- `agent/examiner.py`: grade user's response (3-point rubric: correct, partial, miss), give feedback
- `cli.py`: `curio teach "topic"` → interactive REPL loop

**You will learn:** structured outputs (JSON mode / tool calls for non-conversational tasks), multi-agent orchestration (planner → teacher → examiner are distinct roles), interactive agent loops.

**Verify:** Run a full session on a topic you know cold. Is the syllabus reasonable? Does the teacher explain well? Does the examiner grade fairly?

### Phase 5 — Persistent Memory + Adaptation (weekend 5)
**Goal:** Curio remembers you between sessions and adapts.

Build:
- `memory/schema.sql`: tables for `topics`, `concepts`, `attempts` (which concepts you've seen, how you scored, when), `notes` (free-text agent observations like "user struggles with calculus")
- `memory/learner.py`: read/write API
- Add tools: `get_learner_state(topic)`, `update_concept_mastery(concept, score)`, `log_observation(text)`
- Modify teacher to read learner state when planning what to teach next (spaced repetition: prioritize weak / stale concepts)

**You will learn:** the agentic memory pattern, why durable state changes everything, how to give an agent "intuition" about a user it's seen before.

**Verify:** Do 3 sessions across 3 days on the same topic. Does session 3 correctly recall what you struggled with on day 1 and revisit it?

### Phase 6 — Evals + Observability (weekend 6)
**Goal:** Treat this like a real product. Measure quality, catch regressions.

Build:
- `evals/lesson_eval.py`: LLM-as-judge — given (concept, lesson_output), score on accuracy / clarity / pedagogy (1-5). Run on 20 fixed concepts.
- `obs/trace.py`: structured JSONL — one row per agent turn with `{timestamp, phase, model, tokens_in, tokens_out, tools_called, latency_ms}`
- Optional: pipe traces to Langfuse for nicer UI
- A `make eval` target that runs retrieval + lesson evals and prints scores

**You will learn:** the eval mindset (vibes don't scale), LLM-as-judge patterns and their limits, how observability changes how you debug agents.

**Verify:** Change your chunking strategy (e.g. 800 → 300 tokens). Re-run evals. Did retrieval get better or worse? Did lesson quality follow?

---

## Stretch Goals (after Phase 6)

Pick whichever excites you — each is a meaningful extension:

- **Knowledge graph layer**: extract entities + relationships from chunks (use Claude with structured output), store in Kuzu or NetworkX, let the agent query the graph for "what concepts depend on X". Teaches graph-RAG.
- **Sub-agent specialization**: split the monolithic agent into Curator (finds materials), Teacher (explains), Examiner (quizzes), each its own Claude call with its own tools and system prompt. Teaches multi-agent orchestration patterns.
- **Source diversity**: ingest research papers from arXiv, your own Obsidian vault, even YouTube transcripts (via `youtube-transcript-api`). Teaches multi-source ingestion + dedup.
- **MCP server wrapper**: expose Curio's tools as an MCP server so you can use it from Claude Desktop / Claude Code itself. Teaches the modern tool-protocol standard.
- **Confidence + uncertainty**: when retrieval scores are low, have the teacher say "I'm not sure, want me to web search?" instead of hallucinating. Teaches calibration.
- **TUI**: rebuild the CLI in `textual` for a real interactive teaching interface with side panels showing sources, learner stats, etc.

---

## Memory Budget on 8GB M3

You'll be running, simultaneously: macOS + browser + Python process + BGE-small embedder (~150MB resident) + LanceDB (small) + Ollama with a 3B Q4 model (~2.5GB). Total ~5-6GB. Comfortable, but:

- **Close memory hogs while developing** (heavy Chrome tabs, Slack, etc.)
- For ingestion runs, the embedder loads once and embeds in batches — close other things during long ingests
- The reranker model (Phase 2) adds ~250MB — fine
- Avoid loading multiple Ollama models at once — only one at a time fits
- If you start swapping, switch the LLM to Claude API for that phase rather than fight memory

---

## How to Start (today, before any code)

1. Install Ollama and pull a small model:
   ```
   brew install ollama
   ollama serve     # in one terminal
   ollama pull qwen2.5:3b-instruct-q4_K_M
   ```
2. Install `uv` if you don't have it, then create the project:
   ```
   uv init && uv add anthropic sentence-transformers lancedb wikipedia-api pypdf httpx rich pydantic python-dotenv
   ```
3. Pick a topic you find genuinely interesting (this matters — you'll be QA-ing the output by reading lessons)
4. **Before writing code**, read these (~30 min total):
   - [Ollama API docs](https://github.com/ollama/ollama/blob/main/docs/api.md) — just the `/api/chat` endpoint
   - [LanceDB quickstart](https://lancedb.github.io/lancedb/) — the "Create a table" + "Vector search" sections
   - [BGE-small model card](https://huggingface.co/BAAI/bge-small-en-v1.5) — just the "Usage" section
5. Ask me to walk through Phase 1 in detail — I'll outline the data flow, the functions you need, and the order to build them, then you take over.

Each phase is ~1 weekend of focused work. After 6 weekends you'll have a tool you use + a deep working understanding of every major modern RAG / agentic pattern.

---

## Deliverables (what I'll create immediately after plan approval)

### Top-level docs
- `PROJECT_PLAN.md` — Obsidian-readable copy of this plan
- `LEARNING_GUIDE.md` — concepts (embeddings, chunking, hybrid retrieval, reranking, agent loops, memory, evals) + tool primers (Ollama, sentence-transformers, LanceDB, Anthropic SDK, Pydantic, SQLite) + roadmap of what you should be able to *explain* at the end of each phase + curated reading (BGE paper, original RAG paper, Anthropic tool-use docs, Lilian Weng's agent post)

### Per-phase challenge docs (`phases/`)
Six markdown files, each structured as a guided assignment:
- **Goal** — what working software looks like at the end
- **Concepts to learn first** — 1-3 things to understand before coding (with links)
- **Leading questions** — "What would happen if your chunk size is 50 tokens? 5000? Why?"
- **Success criteria** — observable behaviors that prove the phase works
- **Collapsible hints** — `<details>` sections for when you're truly stuck, ordered from gentle nudge to specific
- **Stretch challenges** — for after you finish

Files: `phases/01_naive_rag.md`, `02_hybrid_rerank.md`, `03_agentic_retrieval.md`, `04_syllabus_lessons.md`, `05_memory.md`, `06_evals_obs.md`

### Cookbook reference snippets (`cookbook/`)
**Spoiler-tagged** — each file starts with a comment header indicating which phase to study it from. Don't peek before attempting.

- `01_lancedb_basics.py` — create table, add vectors, search (Phase 1)
- `02_bge_embeddings.py` — load BGE-small, embed batch, embed query (Phase 1)
- `03_chunking.py` — token-aware chunking with overlap (Phase 1)
- `04_ollama_chat.py` — minimal Ollama `/api/chat` call with httpx (Phase 1)
- `05_hybrid_search.py` — BM25 + dense + Reciprocal Rank Fusion (Phase 2)
- `06_reranker.py` — cross-encoder reranking pattern (Phase 2)
- `07_anthropic_tool_use.py` — minimal Claude tool-use loop, annotated (Phase 3)
- `08_pydantic_tools.py` — defining tool schemas with Pydantic (Phase 3)
- `09_sqlite_learner.py` — minimal SQLite schema + repo functions (Phase 5)
- `10_jsonl_traces.py` — minimal trace writer (Phase 6)

### Claude Code slash commands (`.claude/commands/`)
- `concept.md` — `/concept <topic>` → focused explanation of a RAG/agent concept with worked mini-examples
- `quiz-me.md` — `/quiz-me` → 3 conceptual questions on the phase you're currently working on, ungraded but with feedback
- `stuck.md` — `/stuck` → you describe your stuck point + what you tried; I diagnose and suggest the next experiment WITHOUT writing code
- `socratic-review.md` — `/socratic-review` → I review your latest code by asking leading questions about decisions instead of listing fixes

### Persistent memories (in `~/.claude/projects/.../memory/`)
Three memory files capturing: who you are (new to LLM apps, base M3 / 8GB), how we work together (you write code, I guide), and what we're building (Curio + swappable LLM stack).

---

## Verification Plan

End-to-end check, run after each phase:

| Phase | Smoke test |
|---|---|
| 1 | `curio ask "what is wavefunction collapse"` returns cited paragraph |
| 2 | `make eval-retrieval` prints recall@5 ≥ 0.85 on test set |
| 3 | Trace log shows ≥3 `search_corpus` calls for a multi-hop question |
| 4 | `curio teach "thermodynamics"` runs a full 5-concept session interactively |
| 5 | After 2 sessions, learner.db has populated `attempts` rows; session 3 references prior weak spots in trace |
| 6 | `make eval` produces a numeric score; intentional chunking regression shows up in the score |
