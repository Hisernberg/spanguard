# NOTE: this file lives in the Hugging Face Space repo (Docker SDK).
FROM python:3.12-slim

WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 PYTHONUNBUFFERED=1 SPANGUARD_HOST=0.0.0.0 SPANGUARD_PORT=7860 \
    SPANGUARD_MODE=fast-v4

RUN pip install --no-cache-dir "git+https://github.com/Hisernberg/spanguard.git@v5.0.0" \
 && pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu \
      "torch>=2.2" "transformers>=4.44"

# Pre-download every model the v5 stack uses at build time (public repos, no token):
# the 135M span backbone, the three char experts of the router, and SPG-FM-1.
RUN python - <<'EOF'
from huggingface_hub import snapshot_download
from transformers import AutoModelForTokenClassification, AutoTokenizer

m = 'Nabidnur/spanguard-span-mdistil'
AutoTokenizer.from_pretrained(m)
AutoModelForTokenClassification.from_pretrained(m)
for repo in ["Nabidnur/spanguard-char", "Nabidnur/spanguard-char-v3",
             "Nabidnur/spanguard-char-v4", "Nabidnur/spanguard-fm-1"]:
    p = snapshot_download(repo)
    print("cached", repo, "->", p)
EOF

# Resolve the snapshot dirs into the env vars the gateway reads, then start it.
# SPANGUARD_MODE=fm switches the whole Space to SPG-FM-1 with one env change.
CMD ["sh", "-c", "\
export SPANGUARD_MODEL=$(python -c \"from huggingface_hub import snapshot_download; print(snapshot_download('Nabidnur/spanguard-span-mdistil-v2'))\") && \
export SPANGUARD_CHAR_MODEL=$(python -c \"from huggingface_hub import snapshot_download; print(snapshot_download('Nabidnur/spanguard-char'))\") && \
export SPANGUARD_CHAR_MODEL_V3=$(python -c \"from huggingface_hub import snapshot_download; print(snapshot_download('Nabidnur/spanguard-char-v3'))\") && \
export SPANGUARD_CHAR_MODEL_V4=$(python -c \"from huggingface_hub import snapshot_download; print(snapshot_download('Nabidnur/spanguard-char-v4'))\") && \
export SPANGUARD_FM_MODEL=$(python -c \"from huggingface_hub import snapshot_download; print(snapshot_download('Nabidnur/spanguard-fm-1'))\") && \
exec spanguard up"]

EXPOSE 7860
