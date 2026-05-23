"""
SPOILER — only read this AFTER attempting Phase 2.

Cross-encoder reranking. The model takes (query, chunk) PAIRS as input —
unlike an embedder which encodes one text at a time. This means it can
directly model interaction between query and chunk, which is dramatically
more accurate. The trade-off: ~100x slower per pair, so you use it only
on the top-K from a fast first-stage retriever.

First call downloads ~570MB.

Run:  python cookbook/06_reranker.py
"""

from sentence_transformers import CrossEncoder


def rerank(query: str, candidates: list[str], k: int = 5) -> list[tuple[int, float]]:
    """
    Score (query, candidate) pairs. Returns [(original_index, score), ...]
    sorted by score desc, truncated to k.
    """
    reranker = CrossEncoder("BAAI/bge-reranker-v2-m3", max_length=512)
    pairs = [(query, c) for c in candidates]
    scores = reranker.predict(pairs)
    ranked = sorted(enumerate(scores), key=lambda x: -x[1])
    return ranked[:k]


def main() -> None:
    query = "What is the second law of thermodynamics?"
    candidates = [
        # Plausible but irrelevant
        "Thermodynamics has four laws governing energy and entropy.",
        # Direct hit
        "The second law states that the total entropy of an isolated system can never decrease over time.",
        # Adjacent but not the answer
        "The first law of thermodynamics is a statement of conservation of energy.",
        # Completely off-topic
        "The Roomba uses LIDAR sensors to navigate.",
        # Indirect hit
        "Entropy always increases in spontaneous processes, a principle that defines the arrow of time.",
    ]
    top = rerank(query, candidates, k=3)
    print("Reranked top-3:")
    for orig_idx, score in top:
        print(f"  score={score:+.3f}  {candidates[orig_idx]}")


if __name__ == "__main__":
    main()
