import argparse
from curio.ingest import pipeline
from curio.retrieval import store, rerank
from curio.llm.ollama_client import OllamaClient
from curio.llm.prompts import construct_prompt


parser = argparse.ArgumentParser(description="Curio CLI Interface")
subparsers = parser.add_subparsers(dest='command')

ask_parser = subparsers.add_parser("ask")
ask_parser.add_argument("question")

ingest_parser = subparsers.add_parser("ingest")
ingest_parser.add_argument("topic")


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
