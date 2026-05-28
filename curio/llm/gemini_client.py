from google import genai
from google.genai import types
from typing import Iterator
from curio.config import GEMINI_API_KEY, GEMINI_MODEL


class GeminiClient:
    def __init__(self):
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY not set in .env")
        self._client = genai.Client(api_key=GEMINI_API_KEY)
        self._model = GEMINI_MODEL

    def _to_gemini_contents(self, messages: list[dict]) -> list:
        """Convert OpenAI-style [{role, content}] messages to Gemini Content list.
        Role mapping: 'user' -> 'user', 'assistant' -> 'model'. 'system' is folded into
        the first user message (Gemini doesn't have a separate system role in this API).
        """
        contents = []
        system_text = ""
        for m in messages:
            role = m.get("role")
            content = m.get("content", "")
            if role == "system":
                system_text += content + "\n\n"
                continue
            target_role = "model" if role == "assistant" else "user"
            text = (system_text + content) if (role == "user" and system_text) else content
            if role == "user":
                system_text = ""
            contents.append(types.Content(role=target_role, parts=[types.Part.from_text(text=text)]))
        return contents

    def generate(self, messages: list[dict]) -> str:
        contents = self._to_gemini_contents(messages)
        response = self._client.models.generate_content(model=self._model, contents=contents)
        return response.text

    def generate_stream(self, messages: list[dict]) -> Iterator[str]:
        contents = self._to_gemini_contents(messages)
        stream = self._client.models.generate_content_stream(model=self._model, contents=contents)
        for chunk in stream:
            if chunk.text:
                yield chunk.text


def main():
    client = GeminiClient()
    for delta in client.generate_stream([{"role": "user", "content": "In one sentence, why is the sky blue?"}]):
        print(delta, end="", flush=True)
    print()


if __name__ == "__main__":
    main()
