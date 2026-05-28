import json
import random
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from curio.retrieval import store
from curio.retrieval.embed import embed_query
from curio.retrieval.rerank import rerank
from curio.llm.gemini_client import GeminiClient
from curio.llm.prompts import construct_prompt

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Curio")
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"error": "rate_limited"})


STATIC_DIR = Path(__file__).parent / "static"
EVAL_RESULTS_PATH = Path(__file__).parent.parent.parent / "evals" / "results.json"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

llm = GeminiClient()  # module-level — initialized once; fail fast if API key missing


class RetrieveRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)


Strategy = Literal["naive", "hybrid", "hybrid_rerank"]
RERANK_CANDIDATES = 10
TOP_K = 5

# Questions known to have answers in the QM + thermodynamics corpus
# (derived from evals/retrieval_eval.py fixtures plus a few variety prompts).
EXAMPLE_QUESTIONS = [
    "Who is considered the father of thermodynamics and what did he publish in 1824?",
    "What does the zeroth law of thermodynamics state?",
    "Why is the zeroth law called 'zeroth' rather than another number?",
    "Who invented matrix mechanics?",
    "What did Louis de Broglie propose about particles in 1923?",
    "What is the many-worlds interpretation of quantum mechanics?",
    "What is a qubit?",
    "What does wave function collapse mean?",
    "What is the Bohr model and what discovery preceded it?",
    "What is the predicted heat death of the universe?",
    "Who is the Born rule named after?",
    "What is the Copenhagen interpretation of quantum mechanics?",
    "What is quantum entanglement?",
    "What is the Schrödinger equation used for?",
    "What did Einstein's 1905 paper on the photoelectric effect demonstrate?",
    "How does the second law of thermodynamics define entropy?",
    "What is the measurement problem in quantum mechanics?",
    "What is a Hamiltonian in quantum mechanics?",
    "How does cooling work from a thermodynamic perspective?",
    "How can a deterministic theory produce a probabilistic measurement outcome?",
]


def _retrieve(strategy: Strategy, question: str) -> list[dict]:
    if strategy == "naive":
        vec = embed_query(question)
        return store.search_table(vec, k=TOP_K)
    if strategy == "hybrid":
        return store.hybrid_search(question, k=TOP_K)
    if strategy == "hybrid_rerank":
        candidates = store.hybrid_search(question, k=RERANK_CANDIDATES)
        return rerank(query=question, candidates=candidates, k=TOP_K)
    raise HTTPException(status_code=400, detail="unknown strategy")


def _strip(chunk: dict) -> dict:
    keep = ("id", "text", "source", "url", "chunk_index", "created_at", "score")
    return {k: chunk.get(k) for k in keep}


@app.get("/", response_class=HTMLResponse)
def index():
    return (STATIC_DIR / "index.html").read_text()


@app.get("/api/eval")
def eval_stats():
    if not EVAL_RESULTS_PATH.exists():
        return {"error": "results.json not generated yet — run evals/retrieval_eval.py"}
    return json.loads(EVAL_RESULTS_PATH.read_text())


@app.get("/api/examples")
def examples(n: int = Query(8, ge=1, le=len(EXAMPLE_QUESTIONS))):
    return {"examples": random.sample(EXAMPLE_QUESTIONS, n)}


@app.post("/api/retrieve")
@limiter.limit("20/minute")
def retrieve(request: Request, body: RetrieveRequest):
    q = body.question
    return {
        "naive": [_strip(c) for c in _retrieve("naive", q)],
        "hybrid": [_strip(c) for c in _retrieve("hybrid", q)],
        "hybrid_rerank": [_strip(c) for c in _retrieve("hybrid_rerank", q)],
    }


@app.get("/api/answer")
@limiter.limit("30/minute")
def answer(
    request: Request,
    question: str = Query(..., min_length=3, max_length=500),
    strategy: Strategy = Query(...),
):
    chunks = _retrieve(strategy, question)
    prompt = construct_prompt(question, chunks)
    messages = [{"role": "user", "content": prompt}]

    def event_stream():
        try:
            for delta in llm.generate_stream(messages):
                yield f"data: {json.dumps({'delta': delta})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception:
            # Don't leak internals to the client
            yield f"data: {json.dumps({'error': 'generation_failed'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def main():
    import uvicorn

    uvicorn.run("curio.web.app:app", host="0.0.0.0", port=7860, reload=False)


if __name__ == "__main__":
    main()
