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

# Curio — RAG strategy comparison

A learning project visualizing how retrieval strategy affects RAG answer quality.

Three columns show the same question answered using different retrieval pipelines over the same Wikipedia corpus (quantum mechanics + thermodynamics):

- **Naive dense** — pure dense-vector cosine similarity (BGE-small embeddings)
- **Hybrid RRF** — dense + BM25 fused via Reciprocal Rank Fusion
- **Hybrid + rerank** — hybrid retrieval + cross-encoder reranking (bge-reranker-v2-m3)

Each column then asks Gemini 2.5 Flash to answer using only its retrieved chunks, citing sources inline. The eval banner at the top reports recall@k measured against 15 hand-written question/expected-chunk fixtures.

## Stack

- **Vector DB**: Qdrant Cloud (dense + sparse hybrid)
- **Embeddings**: BAAI/bge-small-en-v1.5
- **Reranker**: BAAI/bge-reranker-v2-m3
- **LLM**: Gemini 2.5 Flash (streaming)
- **API**: FastAPI + Server-Sent Events
- **Frontend**: Vanilla HTML/CSS/JS, no build step

Source: https://github.com/milwil-2/curio-rag
