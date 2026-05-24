from curio.ingest import chunker, wikipedia
from curio.retrieval import embed, store

def ingest_topic(topic: str, limit: int = 5) -> None:
    # 1. fetch articles
    # 2. for each article: chunk_text(...)
    # 3. embed all chunks in one batch
    # 4. assign vectors back to chunks
    # 5. add_chunks(...) to the store

    articles = wikipedia.search_wikipedia_topic(topic=topic, limit=limit)
    print(f"Found {len(articles)} articles.")
    if not articles:
        print(f"No articles found for {topic}") 
        return None
    for a in articles:
        chunks = chunker.chunk_text(text=a["text"], source=a["title"], url=a["url"], chunk_size=500, overlap=50)
        chunked_text = [chunk.text for chunk in chunks]
        vectors = embed.embed_batch(chunked_text)
        for chunk, vector in zip(chunks, vectors):
            chunk.vector = vector
        store.add_chunks(chunks)
        print("Stored:", len(chunks))
        
def main():
    ingest_topic("quantum mechanics")

if __name__ == "__main__":
    main()