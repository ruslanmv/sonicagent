# Hugging Face Docker Space and local voice image.
# Build context is the SonicAgent repository root:
#   docker build -f hf/Dockerfile .
# The Space listens on 7860. Local Compose publishes that port as 8000.

FROM python:3.11-slim

ARG BUNDLE_STT_MODEL=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 user

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY model_registry ./model_registry
COPY deploy/docker/healthcheck.py ./deploy/docker/healthcheck.py
COPY hf/app.py ./app.py
COPY hf/requirements.txt ./requirements.txt
COPY hf/scripts/setup-models.py ./setup-models.py
COPY hf/ui ./ui

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir . \
    && pip install --no-cache-dir -r requirements.txt \
    && mkdir -p /home/user/.cache/sonicagent-rt \
    && if [ "$BUNDLE_STT_MODEL" = "1" ]; then python setup-models.py --model tiny --cache-dir /home/user/.cache/sonicagent-rt; fi \
    && chown -R user:user /app /home/user

USER user

ENV HOME=/home/user \
    PATH="/home/user/.local/bin:$PATH" \
    PORT=7860 \
    SONIC_MODEL_CACHE_DIR=/home/user/.cache/sonicagent-rt \
    SONIC_STT_PROVIDER=faster-whisper \
    SONIC_STT_MODEL=tiny \
    SONIC_STT_DEVICE=cpu \
    SONIC_STT_COMPUTE_TYPE=int8 \
    SONIC_STT_LANGUAGE=auto \
    SONIC_STT_LANGUAGES=en,it \
    SONIC_STT_WARMUP=true \
    SONIC_STT_ALLOW_DOWNLOAD=false \
    SONIC_STT_CPU_THREADS=2 \
    SONIC_STT_MAX_CONCURRENCY=1 \
    SONIC_MAX_AUDIO_SECONDS=15 \
    SONIC_MAX_UPLOAD_BYTES=2097152 \
    SONIC_ENVIRONMENT=production \
    SONIC_AUTH_MODE=token \
    SONIC_VOICE_ENABLED=true \
    SONIC_TTS_ENABLED=false \
    SONIC_STORE_AUDIO=false \
    SONIC_STORE_TRANSCRIPTS=false \
    SONIC_LOG_TRANSCRIPT_CONTENT=false \
    SONIC_PUBLIC_DEMO_ENABLED=false \
    SONIC_PUBLIC_DEMO_TTS_ENABLED=false

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=5 \
    CMD python deploy/docker/healthcheck.py || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
