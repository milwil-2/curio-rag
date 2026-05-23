from transformers import AutoTokenizer
from pydantic import BaseModel, ConfigDict, Field
from curio.config import EMBED_MODEL
from datetime import datetime, timezone


TOKENIZER = AutoTokenizer.from_pretrained(EMBED_MODEL)

class Chunk(BaseModel):
    id: str
    text: str
    vector: list[float] | None = None
    url: str
    source: str
    chunk_index: int  # position of this chunk within the source document
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    model_config = ConfigDict(frozen=False)


def chunk_text(
    text: str, 
    source: str, url: str,
    chunk_size: int = 500,
    overlap: int = 50,) -> list[Chunk]:
    """Split text into overlapping windows of ~chunk_tokens tokens."""

    assert overlap < chunk_size, "overlap must be smaller than chunk"

    chunks: list[Chunk] = []
    token_ids = TOKENIZER.encode(text, add_special_tokens=False)
    step = chunk_size - overlap
    for i, start in enumerate(range(0, len(token_ids), step)):
        window = token_ids[start : start + chunk_size]
        if not window:
            break
        chunk_text_str = TOKENIZER.decode(window, skip_special_tokens=True)
        chunks.append(Chunk(id=f"{source}::{i}", text=chunk_text_str, source=source, url=url ,chunk_index=i))
        if start + chunk_size >= len(token_ids):
            break
    return chunks


def main():

    sample = (
        "Thermodynamics is the branch of physics that deals with heat, work, "
        "and temperature, and their relation to energy, entropy, and the physical "
        "properties of matter and radiation. The behavior of these quantities is "
        "governed by the four laws of thermodynamics, which convey a quantitative "
        "description using measurable macroscopic physical quantities, but may be "
        "explained in terms of microscopic constituents by statistical mechanics. "
    ) * 30  # repeat to force multiple chunks

    chunks = chunk_text(sample, source="wiki/Thermodynamics", url="ex.com", chunk_size=200, overlap=30)
    print(f"Produced {len(chunks)} chunks from {len(sample)} chars")
    for c in chunks[:3]:
        print(f"\n--- chunk {c.chunk_index} ---")
        print(c.text[:150], "...")




if __name__ == '__main__':
    main()