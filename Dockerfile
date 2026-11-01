FROM python:3.12-slim

WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 PYTHONUNBUFFERED=1

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir . && pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu \
    "torch>=2.2" "transformers>=4.44"

# Model weights are pulled from HuggingFace on first start (or mount a cache):
#   docker run -v $PWD/hf-cache:/root/.cache/huggingface -p 8819:8819 spanguard
ENV SPANGUARD_HOST=0.0.0.0 SPANGUARD_PORT=8819
EXPOSE 8819

HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import httpx;httpx.get('http://127.0.0.1:8819/healthz').raise_for_status()"

CMD ["spanguard", "up"]
