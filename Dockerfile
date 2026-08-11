# syntax=docker/dockerfile:1

##############################################################################
# Stage 1 — builder
#
# All heavy, slow, cache-friendly work happens here: creating a virtualenv and
# installing Python dependencies (including a CPU-only PyTorch) and baking the
# sentence-transformers model into an on-disk cache. None of the build tooling
# or pip caches from this stage reach the final image.
##############################################################################
FROM python:3.12-slim AS builder

# - PYTHONDONTWRITEBYTECODE: no .pyc files (smaller, deterministic layers).
# - PYTHONUNBUFFERED: flush logs immediately (useful even during build).
# - PIP_* : never cache wheels, never phone home for version checks.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Self-contained virtualenv. Copying a single directory to the runtime stage is
# simpler and more reproducible than replaying pip installs there.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Install from the LOCK file (exact reproduction of the dev venv), not the
# curated requirements.txt. This guarantees development == Docker == production:
# every transitive dependency (torch, numpy, transformers, ...) is the exact
# version the app was developed and tested against. Installed BEFORE the app
# code is copied so this expensive layer is cached across code-only changes.
COPY requirements-lock.txt ./

# 1) Install the pinned torch FIRST, from PyTorch's CPU wheel index.
#    torch is pinned to 2.2.2 to MATCH DEV (no silent upgrade). On Linux the
#    default PyPI wheel for this version is the CUDA build (multiple GB, useless
#    on a CPU host like Koyeb); the CPU index gives the CPU-only build of the
#    SAME version -- the Linux equivalent of the CPU wheel dev runs on macOS.
#    Doing it first means the lock install below sees torch already satisfied
#    and never pulls the CUDA wheel.
# 2) Install everything else at the exact locked versions.
RUN pip install --upgrade pip && \
    pip install \
        --extra-index-url https://download.pytorch.org/whl/cpu \
        -r requirements-lock.txt
# Bake the embedding model into the image (Option A — see explanation below).
# HF_HOME points the huggingface/sentence-transformers cache at a fixed path we
# will copy into the runtime image, so no download happens at container start.
ENV HF_HOME=/opt/models
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"


##############################################################################
# Stage 2 — runtime
#
# Minimal image: the Python runtime, the prebuilt virtualenv, the cached model,
# the application code, and a non-root user. No compilers, no pip caches.
##############################################################################
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    HF_HOME=/opt/models \
    UPLOAD_DIR=/app/uploads \
    PORT=8000

# libgomp1 is the one genuinely required OS package: PyTorch's CPU kernels link
# against libgomp.so.1 (OpenMP) and fail to import without it. Everything else
# our dependencies need ships inside their manylinux wheels.
# We clean apt lists in the same layer so they never inflate the image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Non-root user created up front so we can chown files as we copy them.
# A fixed UID/GID keeps ownership stable across rebuilds and volume mounts.
RUN groupadd --gid 10001 appuser \
    && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin appuser

WORKDIR /app

# Virtualenv and the pre-downloaded model, owned by the runtime user.
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv
COPY --from=builder --chown=appuser:appuser /opt/models /opt/models

# Application code and migration assets. Only what the service needs at runtime;
# .dockerignore keeps tests, docs, local DBs, .env, and caches out entirely.
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser alembic ./alembic
COPY --chown=appuser:appuser alembic.ini ./alembic.ini
COPY --chown=appuser:appuser docker/entrypoint.sh ./docker/entrypoint.sh

# Make the entrypoint executable regardless of the checkout's file mode
# (Windows/CRLF checkouts often lose the +x bit) and create the uploads mount
# point owned by the runtime user so writes succeed under a volume mount.
RUN chmod +x ./docker/entrypoint.sh \
    && mkdir -p /app/uploads \
    && chown appuser:appuser /app/uploads

USER appuser

# Documented port. Koyeb injects $PORT; the entrypoint honours it and defaults
# to 8000 so local `docker run`/compose behave predictably.
EXPOSE 8000

# Container-level liveness probe using only the stdlib (no curl to install).
# Koyeb runs its own health checks and ignores this, but it makes plain
# `docker run` and `docker compose` report health correctly.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import os,urllib.request,sys; \
url='http://127.0.0.1:%s/health' % os.environ.get('PORT','8000'); \
sys.exit(0 if urllib.request.urlopen(url, timeout=4).status == 200 else 1)"

# Default command: start the server only. Migrations are a SEPARATE, run-once
# step (see docker-compose.yml's `migrate` service and the Koyeb notes), so app
# instances never race to migrate on every start. The entrypoint honours $PORT
# and can be overridden (e.g. `alembic upgrade head`) to run the migration step.
ENTRYPOINT ["./docker/entrypoint.sh"]
