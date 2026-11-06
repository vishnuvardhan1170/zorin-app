# ---------- builder ----------
FROM python:3.11-slim-bookworm AS builder

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

RUN python -m pip install --no-cache-dir \
        pip==25.0.1 \
        wheel==0.45.1 \
    && python -m pip wheel \
        --no-cache-dir \
        --wheel-dir=/wheels \
        -r requirements.txt

# ---------- runtime ----------
FROM python:3.11-slim-bookworm AS runtime

WORKDIR /app

ENV FLASK_ENV=production \
    FLASK_APP=app.py

COPY --from=builder /wheels /wheels
COPY requirements.txt ./

RUN python -m pip install \
        --no-cache-dir \
        --no-index \
        --find-links=/wheels \
        -r requirements.txt \
    && rm -rf /wheels \
    && useradd --create-home --shell /usr/sbin/nologin appuser

COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "app:app"]