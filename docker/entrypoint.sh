#!/bin/sh
# Container entrypoint: start the API server.
#
# Migrations are intentionally NOT run here. They are a separate, run-once step
# (the compose `migrate` service, or a Koyeb pre-deploy command), so the flow is
#   deploy -> migrate once -> start app
# rather than every replica racing to run `alembic upgrade head` on boot.
#
# `set -e` aborts on error. `exec` replaces this shell with uvicorn so the
# server becomes PID 1 and receives SIGTERM/SIGINT directly (clean, fast
# shutdowns and correct restart behaviour under Docker/Koyeb).
set -e

# Bind to all interfaces so the container is reachable, and honour $PORT
# (Koyeb injects it; defaults to 8000 locally). One worker by default: each
# worker loads its own copy of the embedding model, so scale with instances
# rather than workers unless you have measured the memory headroom.
echo "Starting uvicorn on 0.0.0.0:${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
