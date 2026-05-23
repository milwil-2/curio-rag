from sentence_transformers import SentenceTransformer
from curio.config import EMBED_MODEL


model = SentenceTransformer(EMBED_MODEL)

def embed_query(query: str) -> list[float]:
    """ Embeds a search query using BGE's required query prefix. Use this for questions, not documents. """
    constructed_query = "Represent this sentence for searching relevant passages: " + query
    return model.encode(constructed_query, normalize_embeddings=True).tolist()

def embed_batch(text: list[str]) -> list[list[float]]:
    """ Embeds a list of document chunks in a single model pass. Do not use for queries — use embed_query instead. """
    return model.encode(text, normalize_embeddings=True).tolist()
    

def main():
    print(embed_query('What is an LLM?'))
    print(embed_batch(['dsafsadfasf', 'dasdfasdfasdf', 'asdfasdfasdfsdf']))

if __name__ == "__main__":
    main()