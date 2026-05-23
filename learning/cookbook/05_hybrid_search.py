"""
SPOILER — only read this AFTER attempting Phase 2.

Hybrid search = dense (cosine) + sparse (BM25), combined with
Reciprocal Rank Fusion (RRF). LanceDB supports both modes natively;
we run them separately here so you can SEE the fusion happen.

Prereqs: a LanceDB table already populated with embeddings and a `text`
column with an FTS index. See cookbook/01_lancedb_basics.py.

Run:  python cookbook/05_hybrid_search.py
"""

from typing import Iterable
import numpy as np
import lancedb
from sentence_transformers import SentenceTransformer


def rrf_fuse(rankings: Iterable[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """
    Reciprocal Rank Fusion. Each ranking is a list of doc IDs in order.
    Returns (doc_id, fused_score) sorted by score desc.

    Why 1/(k+rank+1)? It compresses absolute scores (which differ in scale
    between BM25 and cosine) into a rank-only signal. The +k softens the top.
    """
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: -x[1])


def hybrid_search(
    table: "lancedb.table.Table",
    embedder: SentenceTransformer,
    query: str,
    k: int = 20,
) -> list[dict]:
    """Run dense + BM25 in parallel, fuse, return top-k full rows."""
    query_vec = embedder.encode(query, normalize_embeddings=True)

    dense = table.search(query_vec).limit(k).to_list()
    sparse = table.search(query, query_type="fts").limit(k).to_list()

    dense_ids = [r["id"] for r in dense]
    sparse_ids = [r["id"] for r in sparse]

    fused = rrf_fuse([dense_ids, sparse_ids])
    top_ids = [doc_id for doc_id, _ in fused[:k]]

    # Map ids back to full rows (preserve fused order)
    by_id = {r["id"]: r for r in dense + sparse}
    return [by_id[doc_id] for doc_id in top_ids if doc_id in by_id]


def main() -> None:
    db = lancedb.connect("./_cookbook_data/lance_demo")
    table = db.open_table("chunks")
    embedder = SentenceTransformer("BAAI/bge-small-en-v1.5")

    results = hybrid_search(table, embedder, "fake topic", k=5)
    for r in results:
        print(f"  {r['id']:10s} text={r['text'][:60]}")


if __name__ == "__main__":
    main()
