"""
SPOILER — only read this AFTER attempting Phase 1.

Minimal LanceDB usage: connect, create table, add rows, search.
LanceDB is an embedded vector DB — no server, just a folder.

Run:  python cookbook/01_lancedb_basics.py
"""

import numpy as np
import lancedb


def main() -> None:
    # 1. Connect: this just opens (or creates) a folder.
    db = lancedb.connect("./_cookbook_data/lance_demo")

    # 2. Build some toy rows. The 'vector' column is what gets indexed.
    #    Vectors must be the same dimension within a table.
    rows = [
        {
            "id": f"chunk-{i}",
            "text": f"Sample passage {i} about a fake topic.",
            "source": "demo",
            "vector": np.random.rand(384).astype("float32"),
        }
        for i in range(10)
    ]

    # 3. Create the table from these rows (schema is inferred).
    #    `mode="overwrite"` makes this script idempotent for demos.
    table = db.create_table("chunks", data=rows, mode="overwrite")

    # 4. Search: pass a query vector, get top-k nearest neighbors.
    query_vec = np.random.rand(384).astype("float32")
    results = table.search(query_vec).limit(3).to_list()

    for r in results:
        # `_distance` is added by LanceDB; lower = closer (for L2/cosine)
        print(f"{r['id']:10s} dist={r['_distance']:.4f}  text={r['text'][:60]}")

    # 5. Add an FTS index over the 'text' column for BM25 / hybrid search later.
    table.create_fts_index("text", replace=True)

    # 6. With FTS in place, you can do keyword search too:
    keyword_results = table.search("fake topic", query_type="fts").limit(3).to_list()
    print("\nKeyword (BM25) results:")
    for r in keyword_results:
        print(f"  {r['id']:10s} text={r['text'][:60]}")


if __name__ == "__main__":
    main()
