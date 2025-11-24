#!/bin/sh

# This script is the entrypoint for the backend container.
# It waits for the database to be ready, runs migrations, and then starts the app.

echo "Waiting for MySQL to be ready..."

# Use netcat to check if the database host and port are available
# 'db' is the service name from docker-compose.yml
while ! nc -z db 3306; do
  sleep 1
done

echo "MySQL is ready."

# Run Alembic migrations
echo "Running database migrations..."
alembic upgrade head

# Start the FastAPI application
echo "Starting FastAPI server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000