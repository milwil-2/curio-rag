"""
SPOILER — only read this AFTER attempting Phase 1.

Minimal BGE-small embeddings via sentence-transformers.
First call downloads the model (~130MB).

Run:  python cookbook/02_bge_embeddings.py
"""

from sentence_transformers import SentenceTransformer


def main() -> None:
    # On M3, this picks up the MPS backend automatically.
    # If you want to be explicit: SentenceTransformer(..., device="mps")
    model = SentenceTransformer("BAAI/bge-small-en-v1.5")

    docs = [
        "Photosynthesis converts light energy into chemical energy.",
        "Entropy is a measure of disorder in a thermodynamic system.",
        "The Roomba uses LIDAR sensors to map its environment.",
    ]

    # normalize_embeddings=True is what you almost always want with cosine /
    # inner-product vector DBs. Skip it and your retrieval will silently be bad.
    doc_vecs = model.encode(docs, normalize_embeddings=True, show_progress_bar=False)
    print(f"doc_vecs shape: {doc_vecs.shape}  dtype: {doc_vecs.dtype}")
    # → (3, 384), float32

    query = "how do plants make food?"
    query_vec = model.encode(query, normalize_embeddings=True)

    # Cosine similarity between unit vectors == dot product.
    sims = doc_vecs @ query_vec
    for doc, sim in sorted(zip(docs, sims), key=lambda x: -x[1]):
        print(f"  sim={sim:.3f}  {doc}")

    # Expected: photosynthesis sentence on top, even with zero shared keywords.
    # That's the magic of dense embeddings.


if __name__ == "__main__":
    main()
