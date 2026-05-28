from lancedb.pydantic import LanceModel, Vector
import lancedb
from curio.config import LANCE_PATH
from curio.ingest.chunker import Chunk
from curio.retrieval.embed import embed_query

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
    table.optimize()
    
def create_fts_index(column:str, name: str = "chunks"):
    table = get_or_create_table(name)
    table.create_fts_index(column, replace=True)

def search_table(query_vector: list[float], k=5, name="chunks") -> list[dict]:
     """ Search table using query_vector and return top k results."""
     table = get_or_create_table(name)
     results = table.search(query=query_vector).limit(k).to_list()
     return results

def sparse_search(query_text: str, k: int = 5, fts_columns:str = "text", name: str = "chunks"):
    table = get_or_create_table(name)
    results = table.search(query=query_text, fts_columns=[fts_columns]).limit(k).to_list()
    return results

def hybrid_search(query_text: str, k: int=5, K: int = 60, name: str="chunks", fts_columns:str = "text"):
    """ Search table using query_vector and using dense + BM25 to return top k results."""
    query_vector = embed_query(query_text)
    sparse_results = sparse_search(query_text=query_text, k=k, fts_columns=fts_columns, name=name)
    dense_results = search_table(query_vector=query_vector, k=k, name=name)
    
    scores = {}  # chunk id → combined score
    for i, r in enumerate(dense_results):
        scores[r["id"]] = scores.get(r["id"], 0) + 1 / (i + 1 + K)
    for i, r in enumerate(sparse_results):
        scores[r["id"]] = scores.get(r["id"], 0) + 1 / (i + 1 + K)
    
    all_results = {r["id"]: r for r in dense_results + sparse_results}

    sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:k]
    results = []
    for id, _ in sorted_scores:
        if id in all_results:
            r = {key: v for key, v in all_results[id].items() if key != "vector"}            
            results.append(r)
    return results



def main():
    print(hybrid_search("What is thermodynamics?"))

if __name__ == "__main__":
    main()