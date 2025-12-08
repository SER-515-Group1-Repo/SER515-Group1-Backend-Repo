#!/bin/sh

# This script is the entrypoint for the backend container.
# It waits for the database to be ready, runs migrations, and then starts the app.

# Be strict: exit on first error and print expanded commands for debugging
set -e
set -x


# Wait for DB to be ready (supports DATABASE_URL or DB_HOST)
echo "Waiting for the database to be ready..."

# Try to parse DATABASE_URL to get host and port (very tersely)
DB_HOSTNAME=""
DB_PORT=""
if [ -n "$DATABASE_URL" ]; then
  # Example DATABASE_URL: postgres://user:pass@hostname:port/dbname
  DB_HOSTNAME=$(echo $DATABASE_URL | sed -n 's|.*@\([^:/]*\).*|\1|p')
  DB_PORT=$(echo $DATABASE_URL | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
fi

if [ -z "$DB_HOSTNAME" ]; then
  DB_HOSTNAME=${DB_HOST:-db}
fi
if [ -z "$DB_PORT" ]; then
  # Default MySQL port or fallback to Postgres default
  if [ -n "$DATABASE_URL" ] && echo "$DATABASE_URL" | grep -q "postgres"; then
    DB_PORT=5432
  else
    DB_PORT=${DB_PORT:-3306}
  fi
fi

echo "DB host: $DB_HOSTNAME, port: $DB_PORT"

# Print some debug information that can help while diagnosing deploy issues
echo "Environment (masked):"
echo "  PORT: $PORT"
echo "  DB_HOSTNAME: $DB_HOSTNAME"
echo "  DB_PORT: $DB_PORT"
if [ -n "$DATABASE_URL" ]; then
  # Do not print full DATABASE_URL, mask password
  MASKED=$(echo $DATABASE_URL | sed -E 's/:[^:@]+@/:<PWD>@/')
  echo "  DATABASE_URL: $MASKED"
fi

# Attempt waiting with a loop and a max attempts to avoid infinite hangs
MAX_ATTEMPTS=60
SLEEP=3
ATTEMPTS=0
while ! nc -z $DB_HOSTNAME $DB_PORT; do
  ATTEMPTS=$((ATTEMPTS + 1))
  if [ "$ATTEMPTS" -ge "$MAX_ATTEMPTS" ]; then
    echo "Timeout waiting for DB at $DB_HOSTNAME:$DB_PORT after $((MAX_ATTEMPTS * SLEEP)) seconds"
    # Print a quick DNS check as well
    echo "Debug: DNS lookup for host:" && nslookup $DB_HOSTNAME || true
    # Exit to allow Render to record the failure in logs
    exit 1
  fi
  sleep $SLEEP
done

echo "Database is ready."

# Run Alembic migrations
echo "Running database migrations..."
alembic upgrade head

# Start the FastAPI application
echo "Starting FastAPI server..."
# Use the PORT environment variable provided by Render (default 8000 fallback)
PORT=${PORT:-8000}
exec uvicorn main:app --host 0.0.0.0 --port $PORT