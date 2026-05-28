def construct_prompt(query: str, chunks: list[dict]) -> str:
    context = ""
    for i, chunk in enumerate(chunks):
        source = chunk["source"]
        text = chunk["text"]
        context += f"[{i}] (source: Wikipedia/{source}) {text}\n"

    return f"""You are answering a question using ONLY the provided context passages.
If the answer isn't in the context, say so honestly.

Context:
{context}

Question: {query}

For every claim in your answer, add an inline citation [source: Wikipedia/ArticleName].
Cite all sources you draw from, not just one."""
