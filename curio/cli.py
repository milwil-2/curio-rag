import argparse
import curio.retrieval.embed as em
import curio.ingest.pipeline as pp
import curio.retrieval.store as st
from curio.llm.ollama_client import OllamaClient

parser = argparse.ArgumentParser(description="Curio CLI Interface")
subparsers = parser.add_subparsers(dest='command')

ask_parser = subparsers.add_parser("ask")
ask_parser.add_argument("question")

ingest_parser = subparsers.add_parser("ingest")
ingest_parser.add_argument("topic")


def construct_prompt(query: str, chunks: list[dict]):
    context = """"""
    for i, chunk in enumerate(chunks):
        source = chunk["source"]
        text = chunk["text"]
        chunk_str = f"[{i}] (source: Wikipedia/{source}) {text}"
        context += chunk_str + "\n"

    prompt = f"""You are answering a question using ONLY the provided context passages.
        If the answer isn't in the context, say so honestly. 

        Context:
        {context}
        

        Question: {query}

        For every claim in your answer, add an inline citation [source: Wikipedia/ArticleName].
        Cite all sources you draw from, not just one."""
    return prompt

def main():
    args = parser.parse_args()


    if args.command == "ask":
    # run the RAG pipeline
        client = OllamaClient()
        question = args.question
        query = em.embed_query(question)
        top_chunks = st.search_table(query, k=5)
        prompt = construct_prompt(question, top_chunks)
        messages = [{"role": "user", "content": prompt}]
        # Check sources
        for c in top_chunks:
            print(c["source"], c["_distance"])
        response = client.generate(messages)
        print(response)

    elif args.command == "ingest":
    # call ingest_topic
        pp.ingest_topic(args.topic)
    else:
        parser.print_help()
