"""
SPOILER — only read this AFTER attempting Phase 3.

Minimal Anthropic tool-use loop. This is THE pattern for agentic systems —
internalize the shape and you can build any agent.

Prereqs:
  uv add anthropic
  export ANTHROPIC_API_KEY=sk-ant-...

Run:  python cookbook/07_anthropic_tool_use.py
"""

import json
from anthropic import Anthropic

client = Anthropic()


# ---- Tools the agent can call ----

def get_weather(location: str) -> dict:
    """Pretend weather tool — in real Curio this would be search_corpus, etc."""
    fake = {"San Francisco": {"temp_f": 62, "conditions": "foggy"},
            "Tokyo": {"temp_f": 78, "conditions": "humid"}}
    return fake.get(location, {"error": f"unknown location: {location}"})


TOOL_REGISTRY = {"get_weather": get_weather}

TOOLS = [
    {
        "name": "get_weather",
        "description": "Get current weather for a city. Use this when the user asks about weather.",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "City name, e.g. 'San Francisco'"}
            },
            "required": ["location"],
        },
    }
]


# ---- The loop ----

SYSTEM_PROMPT = (
    "You are a helpful assistant with access to a weather tool. "
    "When asked about weather, use the tool. Otherwise answer normally."
)


def run_agent(user_question: str, max_iterations: int = 10) -> str:
    """The canonical agent loop. Read carefully — every agent is a variation of this."""
    messages = [{"role": "user", "content": user_question}]

    for iteration in range(max_iterations):
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Always append the assistant's response to messages, even if it includes tool_use.
        # Claude expects to see its own prior content on the next turn.
        messages.append({"role": "assistant", "content": response.content})

        # End condition: model produced text and signaled it's done.
        if response.stop_reason == "end_turn":
            text_blocks = [b.text for b in response.content if b.type == "text"]
            return "\n".join(text_blocks)

        # Otherwise the model wants to use tools. Execute each tool_use block.
        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                fn = TOOL_REGISTRY[block.name]
                result = fn(**block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result),
                })
            # The tool_results go back as a user-role message.
            messages.append({"role": "user", "content": tool_results})
            continue

        # Anything else (max_tokens, error) — bail.
        return f"[unexpected stop_reason: {response.stop_reason}]"

    return "[hit max_iterations — agent did not finish]"


def main() -> None:
    print(run_agent("What's the weather in Tokyo and San Francisco?"))


if __name__ == "__main__":
    main()
