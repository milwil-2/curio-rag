# Curio — RAG strategy comparison
# Target: Hugging Face Spaces (Docker SDK)
# Docs: https://huggingface.co/docs/hub/spaces-sdks-docker
#
# Secrets (GEMINI_API_KEY, QDRANT_URL, QDRANT_API_KEY) are injected at runtime
# via Space Secrets — they are NEVER baked into this image.

FROM python:3.11-slim

# System deps. git/curl needed for uv installer + some HF model pulls.
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        curl \
        build-essential \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# HF Spaces runs containers as a non-root user with UID 1000.
# Create that user up front so all subsequent file ownership is correct.
RUN useradd --create-home --uid 1000 user

USER user

# Paths the `user` account can actually write to. /home/user is owned by user,
# /root is not — so all caches/config must live under /home/user or /app.
ENV HOME=/home/user \
    PATH="/home/user/.local/bin:$PATH" \
    HF_HOME=/home/user/.cache/huggingface \
    TRANSFORMERS_CACHE=/home/user/.cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/home/user/.cache/huggingface \
    XDG_CACHE_HOME=/home/user/.cache \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install uv as the non-root user.
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# --- Dependency layer ---------------------------------------------------
# Copy only the lockfile + project metadata first so this layer caches
# until dependencies actually change.
COPY --chown=user:user pyproject.toml uv.lock ./

# Create the venv with locked deps. --no-dev skips dev-only deps if any.
# --frozen ensures the lockfile is the source of truth (fail if drift).
RUN uv sync --frozen --no-dev --no-install-project

# --- Source layer -------------------------------------------------------
# Copy application code. We deliberately do NOT copy .env or data/ —
# secrets come from Space Secrets, and the corpus lives in Qdrant Cloud.
COPY --chown=user:user curio/ ./curio/
COPY --chown=user:user evals/ ./evals/
COPY --chown=user:user prompts/ ./prompts/
COPY --chown=user:user README.md ./

# Install the project itself now that source is present.
RUN uv sync --frozen --no-dev

# --- Pre-warm model cache ----------------------------------------------
# Pull embedding + reranker weights at build time so cold starts on HF
# Spaces don't spend their first minute downloading ~1GB of models.
# Models land in $HF_HOME, which the runtime user owns.
RUN uv run python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; SentenceTransformer('BAAI/bge-small-en-v1.5'); CrossEncoder('BAAI/bge-reranker-v2-m3', max_length=512)"

# HF Spaces convention: expose 7860 and bind uvicorn there.
EXPOSE 7860

CMD ["uv", "run", "uvicorn", "curio.web.app:app", "--host", "0.0.0.0", "--port", "7860"]
