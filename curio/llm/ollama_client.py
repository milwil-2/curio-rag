from curio.llm.base import LLMClient
import httpx
from curio.config import MODEL_NAME, OLLAMA_URL



class OllamaClient():
    def generate(self, messages: list[dict]) -> str:
        data = {'model': MODEL_NAME, "messages": messages, "stream": False}
        r = httpx.post(OLLAMA_URL, json=data, timeout=120.0)
        return r.json()["message"]["content"]


def main():
    client = OllamaClient()
    print(client.generate([
                {
                "role": "user",
                "content": "why is the sky blue?"
                }
            ]
        ))
    
if __name__ == "__main__":
    main()