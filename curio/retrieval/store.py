from lancedb.pydantic import LanceModel, Vector
import lancedb
from curio.config import LANCE_PATH
from curio.ingest.chunker import Chunk
import curio.ingest.chunker as ch
import curio.retrieval.embed as em

db = lancedb.connect(LANCE_PATH)

class ChunkRecord(LanceModel):
    id: str
    text: str
    vector: Vector(384) # type: ignore
    source: str
    url: str
    chunk_index: int
    created_at: str


def get_or_create_table(name="chunks", schema=ChunkRecord):
      """ 
      Open the named table if it exists, otherwise create it with ChunkRecord schema. 
        """
      if name in db.list_tables().tables:
          return db.open_table(name)
      return db.create_table(name, schema=schema)

def add_chunks(chunks: list[Chunk], name="chunks", overwrite=False):
    """ Add list of chunks to specified table (default: "chunks") """

    assert all(c.vector is not None for c in chunks), "chunks must be embedded before storing"

    table = get_or_create_table(name)
    data = [c.model_dump() for c in chunks]
    table.add(data, mode="overwrite" if overwrite else "append")

def search_table(query_vector: list[float], k=5, name="chunks") -> list[dict]:
     """ Search table using query_vector and return top k results."""
     table = get_or_create_table(name)
     results = table.search(query_vector).limit(k).to_list()
     return results



def main() -> None:
    # 1. Connect: this just opens (or creates) a folder.
    sample = (
        "Thermodynamics is the branch of physics that deals with heat, work, "
        "and temperature, and their relation to energy, entropy, and the physical "
        "properties of matter and radiation. The behavior of these quantities is "
        "governed by the four laws of thermodynamics, which convey a quantitative "
        "description using measurable macroscopic physical quantities, but may be "
        "explained in terms of microscopic constituents by statistical mechanics. "
    ) * 30

    chunks = ch.chunk_text(sample, source="wiki/Thermodynamics", url="ex.com", chunk_size=200, overlap=30)
    vectors = em.embed_batch([c.text for c in chunks])
    for chunk, vector in zip(chunks, vectors):
      chunk.vector = vector


    # 3. Create the table from these rows (schema is inferred).
    add_chunks(chunks, "chunks", overwrite=True)

    # 4. Search: pass a query vector, get top-k nearest neighbors.
    query_vec = em.embed_query("What is thermodynamics?")
    results = search_table(query_vec, 3)

    for r in results:
        # `_distance` is added by LanceDB; lower = closer (for L2/cosine)
        print(f"{r['id']:10s} dist={r['_distance']:.4f}  text={r['text'][:60]}")

    # 5. Add an FTS index over the 'text' column for BM25 / hybrid search later.
    table = get_or_create_table()
    table.create_fts_index("text", replace=True)

    # 6. With FTS in place, you can do keyword search too:
    keyword_results = table.search("entropy", query_type="fts").limit(3).to_list()
    print("\nKeyword (BM25) results:")
    for r in keyword_results:
        print(f"  {r['id']:10s} text={r['text'][:60]}")


if __name__ == "__main__":
    main()