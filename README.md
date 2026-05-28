---
title: Curio
emoji: 🔭
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
short_description: Side-by-side RAG retrieval strategy comparison
---

# Curio

**An educational platform for understanding modern Retrieval-Augmented Generation — built from primitives, not frameworks.**

🔭 **Live demo:** [https://mdubs28-curio.hf.space/](https://mdubs28-curio.hf.space/)

Most RAG tutorials stop at "chat with your docs," which hides the decisions that actually determine quality. Curio takes the opposite approach: every layer — chunking, embeddings, hybrid search, reranking, evaluation — is built and measured in the open, so you can *see* how each one moves the needle. It's designed to teach the retrieval and agentic patterns behind production LLM systems by making them visible and interactive.

Curio is built deliberately **without** LangChain or LlamaIndex. The goal is to understand the primitives those frameworks abstract away — and to keep the system small enough to reason about end to end.

---

## What the demo teaches

The live app answers the **same question, three ways**, over the same Wikipedia corpus (quantum mechanics + thermodynamics), so the only variable is *how chunks are retrieved*:

| Strategy | Retrieval method |
|---|---|
| **Naive dense** | Dense-vector cosine similarity (BGE-small embeddings) |
| **Hybrid (RRF)** | Dense + BM25 keyword search, fused with Reciprocal Rank Fusion |
| **Hybrid + rerank** | Hybrid candidates re-scored by a cross-encoder reranker |

Each column retrieves its own chunks, then the **same** model (Gemini 2.5 Flash) answers using only those chunks, with inline citations streamed token-by-token. Identical model, identical corpus — so every difference in the answers traces directly back to retrieval quality. That's the lesson, made tangible.

A live banner reports **recall@k** from the evaluation suite, so the comparison is grounded in numbers, not intuition.

---

## Retrieval quality, measured

From `evals/retrieval_eval.py` — 15 hand-written (question → expected-chunk) fixtures, run against the production Qdrant index:

| Recall | Naive dense | Hybrid (RRF) | Hybrid + rerank |
|---|---|---|---|
| **@1** | 6.7% | 6.7% | **33.3%** (≈5× naive) |
| **@3** | 13.3% | 46.7% | **66.7%** (≈5× naive) |
| **@5** | 46.7% | 73.3% | **73.3%** |

Reranking delivers its biggest gain at rank 1 — exactly where it matters, since the LLM weights the top chunk most heavily.

---

## Engineering decisions

A few choices worth calling out, because they're the interesting part:

- **Swappable `LLMClient` interface.** A single protocol (`generate` / `generate_stream`) is implemented by both `OllamaClient` (local, offline) and `GeminiClient` (hosted, streaming). Switching providers — or adding Claude for the agentic phase — is a one-line change, with no call sites touched.
- **Hybrid search done properly.** Dense and sparse (BM25) retrieval are fused with Reciprocal Rank Fusion in Qdrant, defending against the scale mismatch between cosine scores and keyword scores rather than naively concatenating results.
- **Reranking as the cheap accuracy win.** A cross-encoder re-scores the top hybrid candidates jointly against the query — the highest-leverage quality improvement in the whole pipeline, and the data above proves it.
- **Evals before vibes.** Retrieval quality is tracked with a real recall@k harness, so changes are verified, not guessed — and the results are surfaced directly in the UI.
- **Streaming-first API.** FastAPI + Server-Sent Events stream three independent answers in parallel, so the comparison feels live.

---

## Roadmap

Curio ships in deliberate stages. The retrieval layer is live; here's what's in active development:

- ✅ **Naive RAG** — ingest, chunk, embed, retrieve, cite
- ✅ **Hybrid search + reranking** — BM25 + dense + RRF + cross-encoder, with a recall@k eval
- 🔜 **Agentic retrieval** — the model decides what to search, issues multiple queries, and reads full articles to answer multi-hop questions
- 🔜 **Tutor mode** — pick a topic; Curio builds a syllabus, teaches concept by concept, and quizzes you
- ⏳ **Persistent memory + adaptation** — remembers a learner across sessions and revisits weak spots with spaced repetition
- ⏳ **Evals + observability** — LLM-as-judge scoring and full request tracing to catch regressions

---

## Tech stack

| Concern | Choice | Why |
|---|---|---|
| Language | Python 3.11+, `uv` | Richest LLM ecosystem, fast tooling |
| Vector DB | **Qdrant Cloud** | Native dense + sparse (BM25) hybrid with RRF fusion |
| Embeddings | **BAAI/bge-small-en-v1.5** | Strong quality at small size, runs locally |
| Reranker | **BAAI/bge-reranker-v2-m3** | Cross-encoder — the cheapest big accuracy win in RAG |
| LLM (web) | **Gemini 2.5 Flash** | Fast, native streaming |
| LLM (local) | **Qwen 2.5 3B** via Ollama | Runs fully offline |
| API | **FastAPI** + Server-Sent Events | Token-by-token streaming |
| Frontend | Vanilla HTML/CSS/JS | No build step, no framework |
| Deploy | **Hugging Face Spaces** (Docker) | Reproducible, containerized hosting |

---

## Run it locally

```bash
# 1. Install dependencies
uv sync

# 2. Configure environment (Qdrant Cloud + Google AI Studio both have free tiers)
cp .env.example .env
#    fill in QDRANT_URL, QDRANT_API_KEY, GEMINI_API_KEY

# 3. Ingest a corpus into Qdrant
uv run curio ingest "quantum mechanics"

# 4a. Ask from the CLI (uses local Ollama — needs `ollama serve`)
uv run curio ask "What is wavefunction collapse?"

# 4b. ...or launch the web demo (uses Gemini)
uv run curio-web        # http://localhost:7860

# 5. Run the retrieval eval
uv run python evals/retrieval_eval.py
```

---

## Project layout

```
curio/
├── cli.py              # `curio ask` / `curio ingest`
├── config.py           # env-driven settings
├── ingest/             # Wikipedia fetch + token-aware chunking
├── retrieval/
│   ├── embed.py        # BGE-small embeddings
│   ├── store_qdrant.py # Qdrant hybrid search (dense + BM25 + RRF)
│   └── rerank.py       # cross-encoder reranker
├── llm/
│   ├── base.py         # LLMClient protocol
│   ├── ollama_client.py
│   ├── gemini_client.py
│   └── prompts.py
└── web/                # FastAPI app + vanilla JS frontend
evals/
└── retrieval_eval.py   # recall@k over hand-written fixtures
```
