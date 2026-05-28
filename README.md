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

**A hands-on project for learning Retrieval-Augmented Generation (RAG) and agentic LLM patterns from scratch.**

🔭 **Live demo:** https://mdubs28-curio.hf.space/

Curio is being built incrementally as a way to *actually understand* modern RAG — not by reading about it, but by building each piece by hand: chunking, embeddings, vector search, hybrid retrieval, reranking, evals, and (soon) agentic retrieval and a full tutoring loop. The long-term goal is an **adaptive tutor**: pick a topic, and Curio builds a syllabus from a corpus, teaches it, quizzes you, and adapts to what you struggle with.

It's deliberately built **without** LangChain or LlamaIndex. Those frameworks hide the exact primitives this project exists to learn.

---

## What the live demo shows

The current demo is a **side-by-side comparison of three retrieval strategies**, answering the same question over the same Wikipedia corpus (quantum mechanics + thermodynamics articles):

| Strategy | How it retrieves |
|---|---|
| **Naive dense** | Pure dense-vector cosine similarity (BGE-small embeddings) |
| **Hybrid (RRF)** | Dense + BM25 keyword search, fused with Reciprocal Rank Fusion |
| **Hybrid + rerank** | Hybrid candidates re-scored by a cross-encoder reranker |

Each column retrieves its own chunks, then asks the **same** LLM (Gemini 2.5 Flash) to answer using *only* those chunks, citing sources inline. Because the model and corpus are identical across columns, any difference in the answers comes purely from retrieval quality — which is the whole point.

A banner at the top reports **recall@k** from the project's evaluation suite, so the improvement isn't just a vibe — it's measured.

---

## Why retrieval strategy matters (measured)

From `evals/retrieval_eval.py` — 15 hand-written (question → expected-chunk) fixtures, measured against the live Qdrant index:

| Recall | Naive dense | Hybrid (RRF) | Hybrid + rerank |
|---|---|---|---|
| **@1** | 6.7% | 6.7% | **33.3%** (≈5× naive) |
| **@3** | 13.3% | 46.7% | **66.7%** (≈5× naive) |
| **@5** | 46.7% | 73.3% | **73.3%** |

Reranking delivers the biggest win at the top of the list (recall@1), which matters most because the LLM weights the first chunk most heavily.

---

## The learning path

Curio is structured as six phases, each a working end-to-end system that adds one concept:

1. **Naive RAG** ✅ — ingest Wikipedia, chunk, embed, store, retrieve, answer with citations
2. **Hybrid search + reranking** ✅ — BM25 + dense + RRF, then a cross-encoder reranker, with a recall@k eval
3. **Agentic retrieval** — let the model decide what to search, issue multiple queries, read full articles (multi-hop)
4. **Syllabus + lesson loop** — turn it into a tutor: plan a syllabus, teach concepts, quiz the learner
5. **Persistent memory + adaptation** — remember a learner across sessions, revisit weak spots (spaced repetition)
6. **Evals + observability** — LLM-as-judge scoring, request tracing, regression detection

**Current status:** Phases 1–2 are done, plus a hosted web demo. Phases 3–6 are the "Where Curio is headed" roadmap shown on the site.

---

## Tech stack (and why)

| Concern | Choice | Why |
|---|---|---|
| Language | Python 3.11+, `uv` | Richest LLM ecosystem |
| Vector DB | **Qdrant Cloud** | Native dense + sparse (BM25) hybrid search with RRF fusion |
| Embeddings | **BAAI/bge-small-en-v1.5** | Strong at small size, runs locally |
| Reranker | **BAAI/bge-reranker-v2-m3** | Cross-encoder — the cheapest big accuracy win in RAG |
| LLM (web) | **Gemini 2.5 Flash** | Fast, free tier, native streaming |
| LLM (local CLI) | **Qwen 2.5 3B** via Ollama | Runs offline on modest hardware |
| API | **FastAPI** + Server-Sent Events | Streams answers token-by-token |
| Frontend | Vanilla HTML/CSS/JS | No build step, no framework |
| Deploy | **Hugging Face Spaces** (Docker) | Free, ML-friendly hosting |

The `LLMClient` interface (`generate` / `generate_stream`) is implemented by both `OllamaClient` and `GeminiClient` — swapping models is a one-line change. That swappable-provider pattern is itself one of the things this project is meant to teach.

---

## Running it locally

```bash
# 1. Install dependencies
uv sync

# 2. Configure environment
cp .env.example .env
#    then fill in QDRANT_URL, QDRANT_API_KEY, GEMINI_API_KEY
#    (Qdrant Cloud + Google AI Studio both have free tiers)

# 3. Ingest a corpus (writes chunks to Qdrant)
uv run curio ingest "quantum mechanics"

# 4a. Ask a question from the CLI (uses local Ollama — needs `ollama serve`)
uv run curio ask "What is wavefunction collapse?"

# 4b. ...or run the web demo (uses Gemini)
uv run curio-web        # serves on http://localhost:7860

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
│   ├── store_qdrant.py # Qdrant-backed hybrid search (dense + BM25 + RRF)
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

---

## Status

This is an active learning project, not a finished product. Expect rough edges, and expect the corpus to be small (a couple dozen physics articles). The point is the journey through the RAG/agentic stack — the roadmap on the live site shows what's coming next.
