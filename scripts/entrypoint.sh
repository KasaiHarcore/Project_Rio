#!/usr/bin/env bash
set -euo pipefail

# ── Wait for PostgreSQL ─────────────────────────────────────────────────
echo "Waiting for PostgreSQL..."
MAX_RETRIES=30
RETRY_COUNT=0
until pg_isready -h db -p 5432 -q 2>/dev/null; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ "$RETRY_COUNT" -ge "$MAX_RETRIES" ]; then
        echo "ERROR: PostgreSQL not ready after $MAX_RETRIES attempts. Exiting."
        exit 1
    fi
    echo "  PostgreSQL not ready (attempt $RETRY_COUNT/$MAX_RETRIES)..."
    sleep 2
done
echo "PostgreSQL is ready."

# ── Wait for Redis ──────────────────────────────────────────────────────
echo "Waiting for Redis..."
RETRY_COUNT=0
until redis-cli -h redis -p 6379 ping 2>/dev/null | grep -q PONG; do
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ "$RETRY_COUNT" -ge "$MAX_RETRIES" ]; then
        echo "WARNING: Redis not ready after $MAX_RETRIES attempts. Continuing anyway."
        break
    fi
    echo "  Redis not ready (attempt $RETRY_COUNT/$MAX_RETRIES)..."
    sleep 2
done
echo "Redis is ready."

# ── Run database migrations ─────────────────────────────────────────────
echo "Running Alembic migrations..."
alembic upgrade head
echo "Migrations complete."

# ── Start the application ───────────────────────────────────────────────
echo "Starting application..."
exec "$@"
