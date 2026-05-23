# Phase 1 — Naive RAG

> **Working software at the end of this phase:** A CLI command `curio ask "what is wavefunction collapse?"` that retrieves relevant chunks from your ingested Wikipedia articles and produces a cited answer using a local LLM. Total cost: $0.

---

## Why this phase

Before you can build *clever* RAG, you need to build the *dumbest possible RAG that works*. Every pipeline stage you'll later improve (chunking, retrieval, prompting, citation) starts here in its simplest form. Resist the urge to make Phase 1 "good" — make it *complete*. You will improve every part of it in later phases, and you'll only know what's worth improving once you've felt the pain of the baseline.

---

## Concepts to learn first

Skim [[LEARNING_GUIDE#Embeddings and vector spaces|LEARNING_GUIDE → Embeddings and vector spaces]] and [[LEARNING_GUIDE#Chunking|Chunking]]. If those concepts still feel hand-wavy, run `/concept embeddings` for a deeper walkthrough.

Then read the tool primers for [[LEARNING_GUIDE#Ollama|Ollama]], [[LEARNING_GUIDE#sentence-transformers|sentence-transformers]], and [[LEARNING_GUIDE#LanceDB|LanceDB]]. You don't need to read the official docs in full — the primers give you the 3-5 calls per tool that you actually need.

---

## Setup checklist

- [ ] `brew install ollama` and `ollama serve` (leave it running in a terminal)
- [ ] `ollama pull qwen2.5:3b-instruct-q4_K_M` (or `llama3.2:3b-instruct-q4_K_M`)
- [ ] `uv init` in the project root, then `uv add sentence-transformers lancedb wikipedia-api httpx rich pydantic python-dotenv`
- [ ] Pick a topic you find interesting (you'll be reading the chunks — make it something you want to read about)
- [ ] Verify the LLM works from the command line: `curl http://localhost:11434/api/chat -d '{"model":"qwen2.5:3b-instruct-q4_K_M","messages":[{"role":"user","content":"hi"}],"stream":false}'`

---

## The data flow you're building

```
   topic           Wikipedia API        chunker         BGE-small       LanceDB
"thermodynamics" → [articles, raw] → [chunks, ~500t] → [vectors, 384d] → stored
                                                                            ↓
   question     →    BGE-small     →   top-5 search   →   Ollama       →  answer
"what is X?"        [query, 384d]      [chunks]           (chunks+q)       w/ cites
```

Two scripts to write:
1. **`scripts/ingest.py`** — runs once. Fetches Wikipedia articles for a topic, chunks them, embeds them, stores in LanceDB.
2. **`curio/cli.py ask`** — runs every time you ask a question. Embeds query, retrieves top-5 chunks, builds a prompt, calls the local LLM, prints the answer.

---

## Modules to write (build in this order)

1. **`curio/llm/base.py`** — define a `Protocol` (or ABC) called `LLMClient` with one method: `generate(messages: list[dict]) -> str`. Two `dict` keys: `role` and `content`.
2. **`curio/llm/ollama_client.py`** — implement `LLMClient` by POSTing to `http://localhost:11434/api/chat`. Use `httpx`. Model name from env var.
3. **`curio/retrieval/embed.py`** — wrap `sentence_transformers.SentenceTransformer`. Two methods: `embed_documents(texts: list[str]) -> np.ndarray` and `embed_query(text: str) -> np.ndarray`. Use `normalize_embeddings=True`.
4. **`curio/ingest/chunker.py`** — given a long string, split into ~500-token chunks with ~50-token overlap. Use the BGE tokenizer (it's a Hugging Face tokenizer) or `tiktoken` if simpler. Each chunk should carry metadata: `{text, source, chunk_index}`.
5. **`curio/ingest/wikipedia.py`** — given a topic, fetch ~20 related articles. The `wikipedia-api` package has `wiki.page(title)` and `page.links`. Chain: search for topic → take top result → also fetch its `links` (filter to actual article links) → pull full text from each.
6. **`curio/retrieval/store.py`** — wrap LanceDB. Methods: `add(chunks_with_vectors)` and `search(query_vector, k=5) -> list[Chunk]`.
7. **`scripts/ingest.py`** — glue: pick topic → fetch articles → chunk → embed → store.
8. **`curio/cli.py`** — glue: take question → embed → search → format prompt → call LLM → print.

---

## The prompt

Keep this dead simple for Phase 1. Something like:

```
You are answering a question using ONLY the provided context passages.
If the answer isn't in the context, say so honestly. Cite passages by their [source].

Context:
[1] (source: Wikipedia/Thermodynamics) ...chunk text...
[2] (source: Wikipedia/Entropy) ...chunk text...
...

Question: {user_question}

Answer (with citations like [source: Wikipedia/Thermodynamics]):
```

The 3B local model will sometimes botch the citation format — that's fine for now, you'll see *why* in Phase 2.

---

## Leading questions (think before coding)

1. **What goes in the LanceDB row?** You need `text`, `vector`, and at minimum a `source` field. Do you also want `chunk_index`? `created_at`? What will you wish you had stored when you start debugging in Phase 2?

2. **What's a "chunk"?** If a Wikipedia paragraph is 200 tokens and your target chunk size is 500, do you combine paragraphs? What about headings — do they belong with the following paragraph? Don't over-engineer this, but be deliberate.

3. **How will you know your chunking worked?** Before you write the code that calls the LLM, you should be able to print 10 random chunks and confirm they look reasonable. What does "reasonable" mean? (Hint: a chunk should be self-contained enough that you, a human, could answer a related question from just that chunk.)

4. **What should your CLI return when nothing relevant is in the corpus?** "No idea" is honest. But the LLM might hallucinate. How will you encourage it to admit ignorance? (You won't fully solve this in Phase 1 — but think about it.)

5. **Where does the prompt template live?** A Python string? A file in `prompts/`? You'll iterate on this a lot. (Suggestion: file-based templates beat inline strings the moment you have more than one.)

6. **What's your CLI's UX?** `curio ask "..."` is simple. Do you want `curio ingest <topic>` too? `curio status` (to see how many chunks are stored)? Don't gold-plate — but spend 5 minutes thinking about it.

---

## Success criteria

You're done with Phase 1 when:

- [ ] `scripts/ingest.py thermodynamics` (or your topic) completes in <2 minutes and reports `N chunks stored`
- [ ] `curio ask "what is entropy?"` returns a coherent answer in <30 seconds
- [ ] The answer cites at least one source
- [ ] You can describe — out loud — what happens to your query between the moment you type it and the moment the answer appears, naming every component it passes through
- [ ] You've intentionally tried 5 questions and noted which ones failed and *why* you think they failed (chunking? retrieval? generation?)
- [ ] You've answered all the questions in [[LEARNING_GUIDE#After Phase 1|Roadmap → After Phase 1]] out loud without notes

---

## Stretch (optional)

- Add `curio ingest <topic>` as a CLI subcommand so you can build up multiple topics in one DB
- Add a `--show-context` flag that prints the retrieved chunks before the answer (you'll want this for debugging in Phase 2)
- Try different chunk sizes (200, 500, 1000) and see which makes the answers feel best — eyeball only, formal eval comes in Phase 2

---

## Hints

> **Stop here if you haven't tried implementing yet.** The whole point is to design the architecture yourself. Open these only when truly stuck.

<details>
<summary>Hint 1 — I don't know where to start (gentlest nudge)</summary>

Start with `llm/base.py` and `llm/ollama_client.py` and write a 10-line script that just talks to the local LLM. No RAG, just `client.generate([{"role": "user", "content": "hello"}])`. Get a response on your screen. *Then* move on.

</details>

<details>
<summary>Hint 2 — How do I get text out of a Wikipedia article?</summary>

```python
import wikipediaapi
wiki = wikipediaapi.Wikipedia(user_agent="curio-learning", language="en")
page = wiki.page("Thermodynamics")
text = page.text  # the full article body
links = page.links  # dict of {title: WikipediaPage}
```
Filter `links` to ones whose title doesn't start with `Wikipedia:`, `Help:`, `Category:`, etc. Then pull each linked page's `.text`.

</details>

<details>
<summary>Hint 3 — Token-aware chunking, the easiest way</summary>

Use the BGE tokenizer directly (it's what the embedder will use):
```python
from transformers import AutoTokenizer
tok = AutoTokenizer.from_pretrained("BAAI/bge-small-en-v1.5")
tokens = tok.encode(text, add_special_tokens=False)
# now split `tokens` into windows of 500 with 50 overlap
# then tok.decode(window) to get the chunk text back
```
Note: BGE has a max sequence length of 512 tokens — chunks bigger than that get truncated by the embedder, so 500 is your real ceiling.

</details>

<details>
<summary>Hint 4 — LanceDB schema</summary>

The simplest path: pass `data=[{...}]` to `create_table` and LanceDB infers the schema. Better long-term: define a Pydantic model with a `lancedb.pydantic.Vector(384)` field. Either works for Phase 1.

</details>

<details>
<summary>Hint 5 — Full reference (last resort)</summary>

If you're truly stuck after trying for an hour-plus, the spoiler files in `cookbook/` show working minimal versions of each piece. Study them, then close them and write your own. Do not copy-paste.

Relevant ones for Phase 1: `01_lancedb_basics.py`, `02_bge_embeddings.py`, `03_chunking.py`, `04_ollama_chat.py`.

</details>

---

When this phase feels real, ping me with `/quiz-me` and we'll check your understanding before moving to Phase 2.
