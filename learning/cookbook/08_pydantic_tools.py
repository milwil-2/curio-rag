"""
SPOILER — only read this AFTER attempting Phase 3.

Defining tool schemas with Pydantic, plus validating Claude's tool inputs
before execution. Catches "model sent wrong arg shape" bugs cleanly.

Bonus: shows the FORCED tool_choice pattern for structured outputs
(used in Phases 4 and 6).

Prereqs: uv add anthropic pydantic

Run:  python cookbook/08_pydantic_tools.py
"""

from pydantic import BaseModel, Field, ValidationError
from anthropic import Anthropic

client = Anthropic()


# ---- Define your tool inputs as Pydantic models ----

class SearchCorpusInput(BaseModel):
    """Args for the search_corpus tool."""
    query: str = Field(description="What to search for, in natural language")
    k: int = Field(default=5, ge=1, le=20, description="Number of chunks to return")


# Pydantic generates the JSON Schema that Claude needs.
search_tool = {
    "name": "search_corpus",
    "description": "Search the knowledge corpus for chunks relevant to a query.",
    "input_schema": SearchCorpusInput.model_json_schema(),
}


def run_tool_safely(name: str, raw_input: dict) -> str:
    """Validate Claude's tool input, then dispatch. Return a string for the model."""
    if name == "search_corpus":
        try:
            args = SearchCorpusInput.model_validate(raw_input)
        except ValidationError as e:
            return f"ERROR: invalid arguments: {e}"
        # ... actually run the tool with args.query, args.k
        return f"[mock] Searched for {args.query!r} (k={args.k})"
    return f"ERROR: unknown tool {name}"


# ---- Structured outputs via forced tool_choice ----

class SyllabusOutput(BaseModel):
    """The structured output we want for a syllabus."""
    topic: str
    concepts: list[str] = Field(description="Ordered list of concept names")
    estimated_minutes: int


def generate_syllabus(topic: str) -> SyllabusOutput:
    """
    Trick: define a 'tool' the model will 'call' with the structured data.
    We never actually execute it — we just take the tool input as our output.
    `tool_choice={"type": "tool", "name": ...}` forces Claude to call THIS tool.
    """
    submit_tool = {
        "name": "submit_syllabus",
        "description": "Submit the final syllabus for the topic.",
        "input_schema": SyllabusOutput.model_json_schema(),
    }

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        tools=[submit_tool],
        tool_choice={"type": "tool", "name": "submit_syllabus"},
        messages=[{"role": "user", "content": f"Build a syllabus for: {topic}"}],
    )

    tool_use = next(b for b in response.content if b.type == "tool_use")
    return SyllabusOutput.model_validate(tool_use.input)


def main() -> None:
    syllabus = generate_syllabus("photosynthesis")
    print(syllabus.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
