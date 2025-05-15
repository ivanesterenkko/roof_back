#!/bin/bash

echo "Waiting for DB to be ready..."
while ! nc -z db 5432; do
  echo "Waiting for the database..."
  sleep 1
done

echo "DB is ready."

# Проверка на изменения в моделях
if alembic revision --autogenerate -m "Auto migration" | grep -q "No changes in schema detected"; then
  echo "No schema changes detected. Skipping migration."
else
  echo "Schema changes detected. Applying migration..."
  alembic upgrade head
fi

echo "Migration process completed!"