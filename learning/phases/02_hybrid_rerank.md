# Phase 2 — Hybrid Search + Reranking

> **Working software at the end of this phase:** Same `curio ask` interface as Phase 1, but with dramatically better retrieval. Plus a `make eval-retrieval` (or `python evals/retrieval_eval.py`) that produces a real recall@5 number, allowing you to *measure* the improvement instead of guessing.

---

## Why this phase

In Phase 1 you almost certainly had a question where the retrieval pulled the wrong chunks. Dense embeddings are great at semantic matches but blind to exact-keyword matches (acronyms, IDs, named entities). And even when retrieval finds the right chunks somewhere in the top 20, you might be passing the wrong 5 to the LLM.

Two techniques fix this:
1. **Hybrid search** — run dense + BM25 sparse in parallel, fuse the result lists.
2. **Reranking** — a cross-encoder re-scores the top 20 to give you a better top 5.

You'll also build a **retrieval eval** — a tiny dataset of `(question, expected_chunk)` pairs. Without it, you can't tell whether your changes help or hurt.

---

## Concepts to learn first

Read [[LEARNING_GUIDE#Dense vs sparse retrieval|LEARNING_GUIDE → Dense vs sparse retrieval]] and [[LEARNING_GUIDE#Reranking|Reranking]] carefully. Also skim [[LEARNING_GUIDE#Evals and LLM-as-judge|Evals and LLM-as-judge]] — you'll write your first eval.

For deeper reading: the Elastic blog post on BM25 (in the Phase 2 reading list) is genuinely the clearest explanation I know. The Pinecone reranker post is also short and well-illustrated.

If you want me to walk through any concept interactively: `/concept BM25` or `/concept reranking`.

---

## The data flow you're adding

Phase 1 was:
```
query → BGE-small → search dense → top-5
```

Phase 2 becomes:
```
query → BGE-small → search dense → top-20 ┐
                                          ├→ RRF fuse → top-20 → cross-encoder → top-5
query →           search BM25  → top-20 ┘
```

The Phase 1 components don't change. You're adding:
- A BM25 index over the same chunks
- A fusion step (Reciprocal Rank Fusion)
- A cross-encoder reranking step

LanceDB supports BM25 (called "full-text search" / FTS) and hybrid search natively. You'll use that.

---

## Modules to write / change

1. **`curio/retrieval/store.py`** — add an FTS index when you create the table; add a `hybrid_search(query, k)` method that does both dense + BM25 and returns top-K with both scores.
2. **`curio/retrieval/rerank.py`** — wrap `sentence_transformers.CrossEncoder("BAAI/bge-reranker-v2-m3")`. One method: `rerank(query, candidates, k=5) -> list[Chunk]`.
3. **`curio/retrieval/__init__.py`** — a top-level `retrieve(query, k=5) -> list[Chunk]` that does the full pipeline: hybrid search → top-20 → rerank → top-5. This is the new single entry point your CLI calls.
4. **`evals/retrieval_eval.py`** — a script that reads a JSON or YAML test set and prints recall@k for naive / hybrid / hybrid+rerank. Make it possible to toggle each component on/off via flags or constants.
5. **`evals/fixtures/test_queries.json`** — hand-curate 20 (question, expected_chunk_id) pairs from your corpus. You'll write these yourself; only you know your corpus.

---

## The eval

This is the part most tutorials skip and where the real learning lives.

### Building the test set

1. Pick 20 questions whose answer is *clearly* in your corpus.
2. For each, find the chunk(s) that contain the answer. Note their IDs. (You'll need stable chunk IDs — add an `id` column if you didn't already.)
3. Store as JSON:
   ```json
   [
     {"id": "q1", "question": "What is the second law of thermodynamics?", "expected_chunk_ids": ["wiki/Second_law_of_thermodynamics::3"]},
     ...
   ]
   ```

### Scoring

For each question, run retrieval, get the top-K chunk IDs. **Recall@K** = (1 if any expected ID is in the top K, else 0), averaged across questions. Simple.

You'll compute recall@5 for:
- Dense-only (Phase 1 baseline)
- Hybrid (no rerank)
- Hybrid + rerank
- Optional: also report recall@10, recall@20 to see how often the right chunk is "in there somewhere"

---

## Leading questions

1. **Why recall@5 and not recall@1?** Why not recall@20? What's the right metric for the *downstream task* (passing chunks to the LLM)?

2. **Will every query benefit from BM25?** Try to predict before you measure. Then look at the per-query results. Which queries did dense win? Which did BM25 win? Is there a pattern?

3. **The reranker is slow.** How slow on your M3? Is it slow enough that you need to be selective about when to use it? (You'll find: not for 20 candidates, but it scales linearly — 200 would hurt.)

4. **RRF has one parameter, `k` (usually 60).** What does it do? What happens if you set `k=1`? `k=1000`? Read the paper section if curious.

5. **Your test set is 20 questions.** What's the noise level on a recall@5 measurement with 20 questions? (Hint: a single question flipping from miss to hit changes the score by 5 percentage points. Real evals use 100+ questions.)

6. **Could the eval be lying?** Is there a way your code could "cheat" — e.g. by including chunk IDs as part of the query embedding? (Probably not in your setup, but worth thinking about. Eval contamination is a real production hazard.)

---

## Success criteria

- [ ] `python evals/retrieval_eval.py` prints recall@5 for all three modes (dense / hybrid / hybrid+rerank)
- [ ] You see a measurable improvement: hybrid+rerank > hybrid > dense. Expected uplift: at least 5-10 percentage points from dense to hybrid+rerank, often more.
- [ ] You can name at least one query where BM25 specifically helped, and one where the reranker reordered things in a way you'd recognize as correct
- [ ] You can answer the [[LEARNING_GUIDE#After Phase 2|Roadmap → After Phase 2 questions]] out loud
- [ ] You re-ran the 5 questions from Phase 1 that failed — at least one or two now work

---

## Stretch (optional)

- Try BGE's larger sibling (`bge-base-en-v1.5`) — does recall improve enough to justify the extra memory?
- Add per-source weighting in fusion (e.g. trust certain articles more) and see if you can hand-tune for your test set (and yes, this is "overfitting" — that's the point of trying it)
- Plot a recall-vs-K curve (1, 3, 5, 10, 20) for the three modes. Are they parallel or do they cross?
- Try `query_type="hybrid"` in LanceDB's built-in hybrid call instead of computing RRF yourself, compare results

---

## Hints

<details>
<summary>Hint 1 — LanceDB FTS / hybrid search</summary>

```python
# When creating the table, add an FTS index:
table.create_fts_index("text", replace=True)

# Then you can do hybrid search:
results = table.search(query="entropy", query_type="hybrid").limit(20).to_list()
```
But hand-rolling RRF over separate dense + sparse calls is more educational for Phase 2 — do that first, then try the built-in hybrid as a comparison.

</details>

<details>
<summary>Hint 2 — Reciprocal Rank Fusion in 5 lines</summary>

```python
def rrf(rankings: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    scores = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: -x[1])
```
Each ranking is just a list of doc IDs in order. RRF doesn't care about the raw scores.

</details>

<details>
<summary>Hint 3 — Reranker usage</summary>

```python
from sentence_transformers import CrossEncoder
reranker = CrossEncoder("BAAI/bge-reranker-v2-m3", max_length=512)
pairs = [(query, chunk.text) for chunk in candidates]
scores = reranker.predict(pairs)  # ndarray of floats
ranked = sorted(zip(candidates, scores), key=lambda x: -x[1])[:k]
```
First call downloads ~570MB. Be patient.

</details>

<details>
<summary>Hint 4 — Building a test set without going insane</summary>

Don't try to write 20 questions from scratch in one sitting. As you ingested articles in Phase 1, you saw chunks. Open your LanceDB table, sample 5-10 chunks at random, and for each one ask yourself: "what's a question this chunk answers?" Write that pair. Done in 20 minutes.

For harder/multi-hop questions (good for stretch), pick two chunks that relate and write a question that requires both.

</details>

<details>
<summary>Hint 5 — Cookbook references</summary>

Last resort: `cookbook/05_hybrid_search.py` and `cookbook/06_reranker.py` show minimal working versions. Try yours first.

</details>

---

When you've finished Phase 2 and your numbers tell a clear story, you're ready for the qualitative leap of Phase 3 — letting the LLM run retrieval itself.
