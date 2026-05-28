"""Storage facade. Currently backed by Qdrant Cloud.

The previous LanceDB implementation is preserved in store_lance.py for reference.
"""
from curio.retrieval.store_qdrant import (
    add_chunks,
    create_fts_index,
    search_table,
    sparse_search,
    hybrid_search,
    get_or_create_collection,
)

__all__ = [
    "add_chunks",
    "create_fts_index",
    "search_table",
    "sparse_search",
    "hybrid_search",
    "get_or_create_collection",
]
