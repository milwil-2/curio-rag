# Phase 3 — Agentic Retrieval

> **Working software at the end of this phase:** The LLM, not your code, decides what to search for. Multi-hop questions that Phase 1-2 couldn't answer now work, because the agent issues 3-5 searches, reads a full article if needed, and reasons across the results. JSONL trace logs let you watch the agent think.

> **This is also the phase where you switch from local Ollama to Claude.** Local 3B models are unreliable for multi-step tool use; Sonnet 4.6 is the standard. You'll see the difference immediately.

---

## Why this phase

Phases 1-2 had one structural limitation: your code controlled retrieval. Query in → fixed pipeline → answer out. The LLM was a passive consumer.

For hard questions, this fails. "How does the uncertainty principle relate to the stability of atoms?" requires:
1. Searching for "uncertainty principle"
2. Searching for "atomic stability" / "electron orbit"
3. Possibly reading both articles in full to find the connection

A single fixed retrieval cannot do this. You need a system where the LLM:
1. Reads the question
2. Decides what to search for
3. Looks at the results
4. Decides whether it has enough, or needs another search
5. Possibly fetches a full document
6. Synthesizes

This is the **agent loop**. It's the central pattern of modern AI systems.

---

## Concepts to learn first

Read [[LEARNING_GUIDE#The agent loop|LEARNING_GUIDE → The agent loop]] and [[LEARNING_GUIDE#Agentic vs naive RAG|Agentic vs naive RAG]] carefully. Then read the Anthropic tool-use docs (linked in the [[LEARNING_GUIDE#Phase 3|Phase 3 reading list]]) — this is your reference for the protocol.

Also read [[LEARNING_GUIDE#Anthropic SDK|Anthropic SDK primer]] in the learning guide.

Bonus (optional but valuable): skim Lilian Weng's "LLM Powered Autonomous Agents" post for the mental model.

If anything's unclear, `/concept agent loop` or `/concept tool use`.

---

## Setup

- [ ] Get an Anthropic API key from console.anthropic.com (you'll spend a few dollars at most over all phases)
- [ ] Put it in `.env` as `ANTHROPIC_API_KEY=sk-ant-...`
- [ ] `uv add anthropic`
- [ ] Test it works: a 5-line script that calls Sonnet with a "hello" prompt and prints the response

---

## The shape of the loop

Read this carefully — it's the heart of Phase 3.

```python
# pseudocode, not real
messages = [{"role": "user", "content": user_question}]

while True:
    response = anthropic.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        tools=TOOLS,
        messages=messages,
    )

    # Append assistant's response (it may contain tool_use blocks)
    messages.append({"role": "assistant", "content": response.content})

    if response.stop_reason == "end_turn":
        # model produced a final text answer; we're done
        return response

    if response.stop_reason == "tool_use":
        # find each tool_use block, execute, append tool_result
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = run_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result),
                })
        messages.append({"role": "user", "content": tool_results})
        # loop continues
```

A few key things to internalize:
- The loop is the agent. There is nothing else.
- The model is stateless between turns — your `messages` list IS the agent's memory.
- One assistant response can have *multiple* `tool_use` blocks. You execute all of them and return all the results before looping.
- `stop_reason` is your loop condition.
- Always set a `max_iterations` cap. Buggy loops cost money.

---

## Modules to write / change

1. **`curio/llm/anthropic_client.py`** — implement `LLMClient` with the Anthropic SDK. The interface is similar to your Ollama client, but you'll need an extra method `generate_with_tools(messages, tools)` that returns the full response (not just text).
2. **`curio/agent/tools.py`** — define your tool schemas. Start with three:
   - `search_corpus(query: str, k: int = 5)` — your Phase 2 retrieval pipeline
   - `read_full_article(title: str)` — return full Wikipedia article text (you have this in LanceDB or can re-fetch)
   - `web_search(query: str)` — use Brave Search API (free tier) or DuckDuckGo's HTML endpoint. Optional but adds a lot of capability.
3. **`curio/agent/loop.py`** — the loop itself. Function signature: `run_agent(question: str, max_iterations: int = 10) -> AgentResult`. Implement the loop in ~50 lines.
4. **`curio/obs/trace.py`** — JSONL trace writer. After each iteration, append one row: `{ts, iteration, model_response_summary, tool_calls, tool_results_summary}`. You'll want this for debugging immediately.
5. **`curio/cli.py`** — add `curio ask --agentic "..."` flag that uses the agent loop instead of naive RAG.

Optional but recommended:
- **`curio/agent/system_prompt.py`** — keep your system prompt separate. You'll iterate on it a lot.

---

## Defining tools (Anthropic format)

Tools are dicts with `name`, `description`, and `input_schema` (JSON Schema). Example:

```python
{
    "name": "search_corpus",
    "description": "Search the knowledge corpus (Wikipedia articles about <your topic>) for chunks relevant to a query. Returns up to k chunks with their text and source.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query"},
            "k": {"type": "integer", "description": "Number of chunks to return", "default": 5}
        },
        "required": ["query"]
    }
}
```

The `description` matters enormously — it's how Claude decides *when* to use the tool. Write clear, specific descriptions. Note when *not* to use it (e.g. "Do not use this for general world knowledge — use it only for questions about <topic>").

You can generate these schemas from Pydantic models via `Model.model_json_schema()` — that's a clean pattern.

---

## Leading questions

1. **What does your system prompt say?** "You're a helpful AI" is useless. Try: "You are a research assistant. To answer questions, you have access to tools. Search the corpus first; if the corpus doesn't have what you need, try web search. Cite sources. If you can't find an answer, say so." Iterate on this. Watch how it changes the agent's behavior.

2. **What happens on the *second* tool call after the first one returned nothing useful?** Does your agent give up? Try a different query? Web search? Read your trace logs.

3. **How many iterations is "too many"?** Set a max. What should happen when you hit it? Return the best answer so far? Error out?

4. **What if the agent calls the same tool with the same args twice?** Should you cache? Should you nudge it ("you already searched for that")? Should you just let it?

5. **Token cost.** A multi-turn agent run with full context each turn can use 50K+ tokens easily. Do the math on Sonnet 4.6 ($3/M input). Are you OK with that per question? (Yes — but be aware.)

6. **Prompt caching.** Claude supports caching the system prompt + tools across calls. For a multi-turn agent loop, this can cut input costs by ~90%. Worth implementing — see Anthropic docs on prompt caching. (Or leave for stretch.)

7. **What does success look like in the trace?** For a hard question, you should see the agent: search → look at results → search differently → maybe read full → answer. For an easy question, it might just search once and answer. Both are good — bad is searching 10 times for one question.

---

## Success criteria

- [ ] `curio ask --agentic "<a hard, multi-hop question about your topic>"` produces a coherent cited answer
- [ ] The JSONL trace shows ≥3 tool calls for the multi-hop question
- [ ] The same question with `--no-agentic` (Phase 2 pipeline) produces a measurably worse answer
- [ ] You've inspected at least 3 traces and can describe, step by step, what the agent did and why
- [ ] You've intentionally tried a question where the corpus has no answer — does the agent admit it? Does it try web search?
- [ ] You can answer [[LEARNING_GUIDE#After Phase 3|Roadmap → After Phase 3]] out loud
- [ ] Your `max_iterations` cap actually triggers somewhere — you've forced a runaway loop to test it

---

## Stretch (optional)

- **Prompt caching** for the system prompt + tools (`cache_control` in the SDK)
- **Streaming** — show the agent's progress as it happens (rich library has spinners + live text)
- **Parallel tool calls** — Claude can request multiple tools in one turn; execute them in parallel
- **Self-reflection turn** — before the final answer, the agent reviews its own retrievals and decides if it has enough evidence
- **A `summarize_article` tool** that takes a long article and returns a focused summary — saves context

---

## Hints

<details>
<summary>Hint 1 — The minimum-viable loop in 30 lines</summary>

If you've never written one before, here's the skeleton (still you need to flesh out `run_tool` etc):

```python
def run_agent(question: str, tools: list[dict], max_iter: int = 10) -> str:
    messages = [{"role": "user", "content": question}]
    for _ in range(max_iter):
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": resp.content})
        if resp.stop_reason == "end_turn":
            return "".join(b.text for b in resp.content if b.type == "text")
        tool_results = []
        for block in resp.content:
            if block.type == "tool_use":
                result = run_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })
        messages.append({"role": "user", "content": tool_results})
    raise RuntimeError("max iterations exceeded")
```
This is intentionally a reference shape — don't paste, retype it as you understand each piece. See `cookbook/07_anthropic_tool_use.py` for a fuller annotated version when you're ready.

</details>

<details>
<summary>Hint 2 — Tool execution dispatcher</summary>

Keep a registry: `TOOLS = {"search_corpus": search_corpus_fn, "web_search": web_search_fn, ...}`. `run_tool(name, input)` becomes `TOOLS[name](**input)`. Validate input with Pydantic before calling, return a clean error string on failure.

</details>

<details>
<summary>Hint 3 — Web search without paying</summary>

Brave Search API has a free tier (2000 queries/month). Sign up, get an API key. Or use `duckduckgo-search` Python package — no key, sometimes flaky. For learning, either is fine.

</details>

<details>
<summary>Hint 4 — Debugging the loop</summary>

If the agent seems "stuck" or behaves unexpectedly, the first thing to do is print the full `messages` list at every iteration. You'll quickly see what the agent is "seeing" each turn. The model is not magic — it does what the context tells it to do.

</details>

<details>
<summary>Hint 5 — Cookbook references</summary>

`cookbook/07_anthropic_tool_use.py` has the canonical annotated loop. `cookbook/08_pydantic_tools.py` shows the Pydantic → schema pattern. Study after attempting.

</details>

---

Once Phase 3 works, the rest of the project layers more agentic patterns on top of this same loop. Master the loop here.
