from typing import Protocol, Iterator

class LLMClient(Protocol):
    def generate(self, messages: list[dict]) -> str:
        ...

    def generate_stream(self, messages: list[dict]) -> Iterator[str]:
        ...
