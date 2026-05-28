"""Qdrant Cloud-backed storage for Curio.

Public API mirrors the original LanceDB-based store so callers
(pipeline.py, cli.py, evals) don't need to change.

Hybrid search uses Qdrant's native RRF fusion over named vectors:
  - "dense": 384-d cosine vectors from BAAI/bge-small-en-v1.5
  - "bm25":  sparse vectors from fastembed's Qdrant/bm25 model
"""

import uuid

from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient, models

from curio.config import QDRANT_API_KEY, QDRANT_COLLECTION, QDRANT_URL
from curio.ingest.chunker import Chunk
from curio.retrieval.embed import embed_query


# Module-level singletons. Reading config only — never accept URLs from callers.
client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
bm25 = SparseTextEmbedding("Qdrant/bm25")

DENSE_VECTOR_SIZE = 384
DENSE_NAME = "dense"
SPARSE_NAME = "bm25"


def _chunk_uuid(chunk_id: str) -> str:
    """Deterministically map a chunk.id string to a Qdrant-compatible UUID."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))


def _point_to_dict(point) -> dict:
    """Convert a Qdrant ScoredPoint (or Record) to the dict shape callers expect."""
    payload = point.payload or {}
    out = {
        "id": payload.get("id"),
        "text": payload.get("text"),
        "source": payload.get("source"),
        "url": payload.get("url"),
        "chunk_index": payload.get("chunk_index"),
        "created_at": payload.get("created_at"),
    }
    # ScoredPoint has .score; Record does not.
    score = getattr(point, "score", None)
    if score is not None:
        out["score"] = score
    return out


def get_or_create_collection(name: str = QDRANT_COLLECTION):
    """Create the collection on Qdrant if it doesn't already exist.

    Uses named vectors so we can co-locate a dense vector and a BM25 sparse
    vector per point. bge-bm25 requires IDF-style normalization, hence Modifier.IDF.
    """
    if client.collection_exists(name):
        return client

    client.create_collection(
        collection_name=name,
        vectors_config={
            DENSE_NAME: models.VectorParams(
                size=DENSE_VECTOR_SIZE,
                distance=models.Distance.COSINE,
            ),
        },
        sparse_vectors_config={
            SPARSE_NAME: models.SparseVectorParams(
                modifier=models.Modifier.IDF,
            ),
        },
    )
    return client


def add_chunks(
    chunks: list[Chunk],
    name: str = QDRANT_COLLECTION,
    overwrite: bool = False,
) -> None:
    """Upsert chunks to Qdrant.

    Each point carries a dense vector and a BM25 sparse vector, plus the
    original chunk metadata in payload. The original string id is preserved
    in payload["id"]; the Qdrant point id is a UUIDv5 derived from it.
    """
    assert all(c.vector is not None for c in chunks), (
        "chunks must be embedded before storing"
    )

    if overwrite and client.collection_exists(name):
        client.delete_collection(collection_name=name)

    get_or_create_collection(name)

    if not chunks:
        return

    # Batch the sparse embeddings in a single fastembed pass.
    sparse_embeddings = list(bm25.embed([c.text for c in chunks]))

    points = []
    for c, sparse in zip(chunks, sparse_embeddings):
        points.append(
            models.PointStruct(
                id=_chunk_uuid(c.id),
                vector={
                    DENSE_NAME: c.vector,
                    SPARSE_NAME: models.SparseVector(
                        indices=sparse.indices.tolist(),
                        values=sparse.values.tolist(),
                    ),
                },
                payload={
                    "id": c.id,
                    "text": c.text,
                    "source": c.source,
                    "url": c.url,
                    "chunk_index": c.chunk_index,
                    "created_at": c.created_at,
                },
            )
        )

    client.upsert(collection_name=name, points=points)


def create_fts_index(column: str, name: str = QDRANT_COLLECTION) -> None:
    """No-op for Qdrant — sparse vectors are indexed at insert time.

    Kept for API compatibility with the LanceDB store, which required an
    explicit FTS index call after ingestion.
    """
    return None


def search_table(
    query_vector: list[float],
    k: int = 5,
    name: str = QDRANT_COLLECTION,
) -> list[dict]:
    """Dense-only similarity search."""
    response = client.query_points(
        collection_name=name,
        query=query_vector,
        using=DENSE_NAME,
        limit=k,
        with_payload=True,
    )
    return [_point_to_dict(p) for p in response.points]


def sparse_search(
    query_text: str,
    k: int = 5,
    fts_columns: str = "text",
    name: str = QDRANT_COLLECTION,
) -> list[dict]:
    """BM25-only sparse search. `fts_columns` is ignored (API compatibility)."""
    sparse = next(bm25.query_embed([query_text]))
    sparse_query = models.SparseVector(
        indices=sparse.indices.tolist(),
        values=sparse.values.tolist(),
    )
    response = client.query_points(
        collection_name=name,
        query=sparse_query,
        using=SPARSE_NAME,
        limit=k,
        with_payload=True,
    )
    return [_point_to_dict(p) for p in response.points]


def hybrid_search(
    query_text: str,
    k: int = 5,
    K: int = 60,
    name: str = QDRANT_COLLECTION,
    fts_columns: str = "text",
) -> list[dict]:
    """Hybrid dense + BM25 search fused server-side via RRF.

    `K` and `fts_columns` are accepted for API compatibility but unused —
    Qdrant performs the RRF fusion natively.
    """
    dense_vec = embed_query(query_text)
    sparse = next(bm25.query_embed([query_text]))
    sparse_query = models.SparseVector(
        indices=sparse.indices.tolist(),
        values=sparse.values.tolist(),
    )

    response = client.query_points(
        collection_name=name,
        prefetch=[
            models.Prefetch(query=dense_vec, using=DENSE_NAME, limit=k * 4),
            models.Prefetch(query=sparse_query, using=SPARSE_NAME, limit=k * 4),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=k,
        with_payload=True,
    )
    return [_point_to_dict(p) for p in response.points]


def main():
    print(hybrid_search("What is thermodynamics?"))


if __name__ == "__main__":
    main()
