# NOTE: this file lives in the Hugging Face Space repo (Docker SDK).
FROM python:3.12-slim

WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 PYTHONUNBUFFERED=1 SPANGUARD_HOST=0.0.0.0 SPANGUARD_PORT=7860

RUN pip install --no-cache-dir "git+https://github.com/Hisernberg/spanguard.git" \
 && pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu \
      "torch>=2.2" "transformers>=4.44"

# Pre-download the span model at build time (public repo, no token needed)
RUN python -c "from transformers import AutoModelForTokenClassification, AutoTokenizer; \
m='Nabidnur/spanguard-span-mdistil'; \
AutoTokenizer.from_pretrained(m); AutoModelForTokenClassification.from_pretrained(m)"

EXPOSE 7860
CMD ["spanguard", "up"]
