#!/bin/bash

echo "Waiting for DB to be ready..."
while ! nc -z db 5432; do
  echo "Waiting for the database..."
  sleep 1
done

echo "DB is ready. Applying migrations..."
alembic upgrade head

echo "Migrations applied successfully!"