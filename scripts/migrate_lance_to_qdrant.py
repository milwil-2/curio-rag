"""One-shot migration: copy existing chunks from LanceDB into Qdrant Cloud.

Reads the local LanceDB store at LANCE_PATH, reconstructs Chunk objects
(reusing the dense vectors already stored there), then re-uploads them via
the Qdrant store. The Qdrant store will recompute BM25 sparse vectors at
upsert time.

Safe to rerun: passes overwrite=True so the Qdrant collection is wiped and
recreated from scratch each time.

Usage:
    uv run python scripts/migrate_lance_to_qdrant.py
"""

from collections import Counter

import lancedb

from curio.config import LANCE_PATH
from curio.ingest.chunker import Chunk
from curio.retrieval import store_qdrant


LANCE_TABLE = "chunks"


def main() -> None:
    db = lancedb.connect(LANCE_PATH)
    if LANCE_TABLE not in db.list_tables().tables:
        print(f"No '{LANCE_TABLE}' table at {LANCE_PATH} — nothing to migrate.")
        return

    table = db.open_table(LANCE_TABLE)
    rows = table.search().limit(1_000_000).to_list()
    print(f"Loaded {len(rows)} rows from LanceDB at {LANCE_PATH}.")

    if not rows:
        print("Source table is empty — nothing to do.")
        return

    chunks: list[Chunk] = []
    for row in rows:
        vector = row.get("vector")
        if hasattr(vector, "tolist"):
            vector = vector.tolist()
        chunks.append(
            Chunk(
                id=row["id"],
                text=row["text"],
                vector=list(vector) if vector is not None else None,
                source=row["source"],
                url=row["url"],
                chunk_index=row["chunk_index"],
                created_at=row["created_at"],
            )
        )

    # overwrite=True deletes + recreates the collection, making reruns idempotent.
    store_qdrant.add_chunks(chunks, overwrite=True)

    source_counts = Counter(c.source for c in chunks)
    print("\nMigration summary:")
    for source, count in sorted(source_counts.items(), key=lambda kv: -kv[1]):
        print(f"  {source}: {count}")
    print(f"\nTotal uploaded: {len(chunks)}")


if __name__ == "__main__":
    main()
