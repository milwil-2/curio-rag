from sentence_transformers import CrossEncoder

model = CrossEncoder("BAAI/bge-reranker-v2-m3", max_length=512)

def rerank(query: str, candidates: list[dict], k: int = 5) -> list[dict]:
    # build (query, text) pairs
    # score with model.predict()
    # sort by score, return top k
    pairs = [(query, c["text"]) for c in candidates]
    scores = model.predict(pairs)
    ranked = sorted(enumerate(scores), key=lambda x: -x[1])
    return [candidates[i] for i, _ in ranked[:k]]
