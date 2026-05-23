"""
SPOILER — only read this AFTER attempting Phase 1.

Minimal Ollama /api/chat call via httpx. No SDK needed — Ollama's HTTP API
is genuinely simple. Set OLLAMA_MODEL in env or change the constant below.

Prereqs:
  brew install ollama && ollama serve
  ollama pull qwen2.5:3b-instruct-q4_K_M

Run:  python cookbook/04_ollama_chat.py
"""

import os
import httpx

MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b-instruct-q4_K_M")
URL = "http://localhost:11434/api/chat"


def chat(messages: list[dict], temperature: float = 0.2) -> str:
    """Send messages to Ollama, return the assistant's text."""
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }
    resp = httpx.post(URL, json=payload, timeout=120.0)
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def main() -> None:
    answer = chat([
        {"role": "system", "content": "You answer in exactly one sentence."},
        {"role": "user", "content": "What is entropy?"},
    ])
    print(answer)


if __name__ == "__main__":
    main()
