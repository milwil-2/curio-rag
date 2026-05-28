import argparse
from curio.ingest import pipeline
from curio.retrieval import store, rerank
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
        top_chunks = store.hybrid_search(question)
        reranked = rerank.rerank(query=question, candidates=top_chunks)
        prompt = construct_prompt(question, reranked)
        messages = [{"role": "user", "content": prompt}]
        response = client.generate(messages)
        print(response)

    elif args.command == "ingest":
    # call ingest_topic
        pipeline.ingest_topic(args.topic)
    else:
        parser.print_help()
