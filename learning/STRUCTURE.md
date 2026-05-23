# Project Structure

The full directory tree you'll build across all 6 phases. You don't create everything now — each phase adds its section.

---

## Full tree

```
rag-learning/
├── .env                        # ANTHROPIC_API_KEY=sk-ant-... (never commit)
├── .env.example                # safe to commit — template only
├── .gitignore
├── pyproject.toml              # uv-managed deps + entry point
├── Makefile                    # make eval, make eval-retrieval, etc. (Phase 6)
│
├── curio/                      # the app package
│   ├── __init__.py
│   ├── cli.py                  # entry point: `curio ask`, `curio teach`
│   ├── config.py               # paths, model names, constants
│   │
│   ├── ingest/                 # raw docs → chunks → embeddings → LanceDB
│   │   ├── __init__.py
│   │   ├── wikipedia.py        # fetch + parse Wikipedia articles
│   │   ├── pdf.py              # parse PDFs (Phase 3+)
│   │   ├── markdown.py         # parse .md notes (Phase 3+)
│   │   └── chunker.py          # token-aware sliding-window chunking
│   │
│   ├── retrieval/              # search + rerank
│   │   ├── __init__.py         # top-level retrieve(query, k) entry point
│   │   ├── store.py            # LanceDB wrapper: add, dense_search, bm25_search
│   │   ├── embed.py            # BGE-small wrapper: embed_batch, embed_query
│   │   └── rerank.py           # cross-encoder reranker (Phase 2)
│   │
│   ├── llm/                    # swappable LLM clients
│   │   ├── __init__.py
│   │   ├── base.py             # LLMClient Protocol: generate(), generate_with_tools()
│   │   ├── ollama_client.py    # local: POST localhost:11434/api/chat
│   │   └── anthropic_client.py # cloud: anthropic SDK (Phase 3+)
│   │
│   ├── agent/                  # agentic layer (Phase 3+)
│   │   ├── __init__.py
│   │   ├── loop.py             # the core tool-use loop
│   │   ├── tools.py            # tool definitions + dispatcher
│   │   ├── planner.py          # builds syllabus (Phase 4+)
│   │   ├── teacher.py          # runs a single lesson (Phase 4+)
│   │   └── examiner.py         # grades answers (Phase 4+)
│   │
│   ├── memory/                 # persistent learner state (Phase 5+)
│   │   ├── __init__.py
│   │   ├── learner.py          # SQLite repo functions
│   │   └── schema.sql          # DDL: topics, concepts, attempts, observations
│   │
│   └── obs/                    # observability (Phase 3+)
│       ├── __init__.py
│       └── trace.py            # JSONL trace writer
│
├── data/                       # runtime data — gitignored
│   ├── lance/                  # LanceDB files
│   ├── learner.db              # SQLite learner state
│   └── notes/                  # your own markdown files to ingest
│
├── evals/                      # evaluation scripts
│   ├── retrieval_eval.py       # recall@k, MRR (Phase 2+)
│   ├── lesson_eval.py          # LLM-as-judge on lesson quality (Phase 6)
│   ├── judge.py                # reusable judge prompt + structured call (Phase 6)
│   └── fixtures/
│       ├── test_queries.json   # 20 (question, expected_chunk_id) pairs (Phase 2)
│       └── test_concepts.json  # 10-20 fixed concepts for lesson eval (Phase 6)
│
├── traces/                     # JSONL agent traces — gitignored
│
├── phases/                     # per-phase challenge docs (already created)
├── cookbook/                   # reference snippets (already created)
└── prompts/                    # system prompt files (Phase 4+)
    ├── planner.md
    ├── teacher.md
    └── examiner.md
```

---

## What to create right now (Phase 1)

Run these commands from the repo root:

```bash
# App package
mkdir -p curio/ingest curio/retrieval curio/llm

# Touch the __init__.py files
touch curio/__init__.py
touch curio/ingest/__init__.py
touch curio/retrieval/__init__.py
touch curio/llm/__init__.py

# Runtime data dir (contents are gitignored)
mkdir -p data/lance data/notes

# Eval scaffolding
mkdir -p evals/fixtures
```

Then create these files (empty or with stubs — you'll fill them in):
- `curio/config.py`
- `curio/cli.py`
- `curio/ingest/wikipedia.py`
- `curio/ingest/chunker.py`
- `curio/retrieval/embed.py`
- `curio/retrieval/store.py`
- `curio/llm/base.py`
- `curio/llm/ollama_client.py`

That's Phase 1's entire surface area.

---

## Gitignore additions

Make sure `data/` and `traces/` are gitignored (they'll get large):

```gitignore
data/
traces/
.env
```

---

## pyproject.toml entry point

Add a `[project.scripts]` section so `curio` becomes a real CLI command:

```toml
[project.scripts]
curio = "curio.cli:main"
```

After adding it, run `uv sync` — then `curio ask "..."` will work from anywhere in the venv.

---

## Phases → files added

| Phase | New files |
|---|---|
| 1 | `curio/config.py`, `curio/cli.py`, `curio/ingest/wikipedia.py`, `curio/ingest/chunker.py`, `curio/retrieval/embed.py`, `curio/retrieval/store.py`, `curio/llm/base.py`, `curio/llm/ollama_client.py` |
| 2 | `curio/retrieval/rerank.py`, `curio/retrieval/__init__.py` (real retrieve fn), `evals/retrieval_eval.py`, `evals/fixtures/test_queries.json`, `curio/ingest/pdf.py` (optional) |
| 3 | `curio/llm/anthropic_client.py`, `curio/agent/loop.py`, `curio/agent/tools.py`, `curio/obs/trace.py` |
| 4 | `curio/agent/planner.py`, `curio/agent/teacher.py`, `curio/agent/examiner.py`, `prompts/` files |
| 5 | `curio/memory/learner.py`, `curio/memory/schema.sql` |
| 6 | `evals/lesson_eval.py`, `evals/judge.py`, `evals/fixtures/test_concepts.json`, `Makefile` |

---

## Module responsibilities (one line each)

| Module | Does exactly one thing |
|---|---|
| `config.py` | Central constants: `LANCE_PATH`, `DB_PATH`, `EMBED_MODEL`, `LLM_MODEL`, etc. |
| `cli.py` | Parses CLI args, wires modules together, prints output. No business logic. |
| `ingest/wikipedia.py` | Fetches raw Wikipedia HTML, returns plain text per article. |
| `ingest/chunker.py` | Splits text into token-bounded chunks with overlap. Returns `list[Chunk]`. |
| `retrieval/embed.py` | Loads BGE-small once, exposes `embed_query(str)` and `embed_batch(list[str])`. |
| `retrieval/store.py` | Wraps LanceDB: `add_chunks(chunks)`, `dense_search(vec, k)`, `bm25_search(query, k)`. |
| `retrieval/__init__.py` | Composes store + reranker into `retrieve(query, k) -> list[Chunk]`. |
| `llm/base.py` | Defines the `LLMClient` Protocol that all backends must satisfy. |
| `llm/ollama_client.py` | Implements `LLMClient` against Ollama's `/api/chat`. |
| `llm/anthropic_client.py` | Implements `LLMClient` against the Anthropic SDK. |
| `agent/loop.py` | The tool-use loop: sends messages, handles tool_use blocks, loops until end_turn. |
| `agent/tools.py` | Tool schemas + dispatcher: `run_tool(name, input) -> str`. |
| `memory/learner.py` | SQLite read/write: masteries, attempts, observations. No business logic. |
| `obs/trace.py` | Appends one JSONL row per agent turn. Nothing else. |
