"""
SPOILER — only read this AFTER attempting Phase 1.

Token-aware chunking with overlap, using the BGE tokenizer (so chunk lengths
match what the embedder will actually accept — 512 token max).

Run:  python cookbook/03_chunking.py
"""

from dataclasses import dataclass
from transformers import AutoTokenizer

TOKENIZER = AutoTokenizer.from_pretrained("BAAI/bge-small-en-v1.5")


@dataclass
class Chunk:
    text: str
    source: str
    chunk_index: int  # position of this chunk within the source document


def chunk_text(
    text: str,
    source: str,
    chunk_tokens: int = 500,
    overlap_tokens: int = 50,
) -> list[Chunk]:
    """Split text into overlapping windows of ~chunk_tokens tokens."""
    assert overlap_tokens < chunk_tokens, "overlap must be smaller than chunk"

    # Encode without special tokens; we'll let the embedder add them later.
    token_ids = TOKENIZER.encode(text, add_special_tokens=False)

    chunks: list[Chunk] = []
    step = chunk_tokens - overlap_tokens
    for i, start in enumerate(range(0, len(token_ids), step)):
        window = token_ids[start : start + chunk_tokens]
        if not window:
            break
        chunk_text_str = TOKENIZER.decode(window, skip_special_tokens=True)
        chunks.append(Chunk(text=chunk_text_str, source=source, chunk_index=i))
        if start + chunk_tokens >= len(token_ids):
            break
    return chunks


def main() -> None:
    sample = (
        "Thermodynamics is the branch of physics that deals with heat, work, "
        "and temperature, and their relation to energy, entropy, and the physical "
        "properties of matter and radiation. The behavior of these quantities is "
        "governed by the four laws of thermodynamics, which convey a quantitative "
        "description using measurable macroscopic physical quantities, but may be "
        "explained in terms of microscopic constituents by statistical mechanics. "
    ) * 30  # repeat to force multiple chunks

    chunks = chunk_text(sample, source="wiki/Thermodynamics", chunk_tokens=200, overlap_tokens=30)
    print(f"Produced {len(chunks)} chunks from {len(sample)} chars")
    for c in chunks[:3]:
        print(f"\n--- chunk {c.chunk_index} ---")
        print(c.text[:150], "...")


if __name__ == "__main__":
    main()
