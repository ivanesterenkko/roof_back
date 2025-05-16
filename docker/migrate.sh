#!/bin/bash
set -e

echo "Ждём, пока БД не будет готова..."
while ! nc -z db 5432; do
  echo "Ещё не готово, ждём 1с..."
  sleep 1
done
echo "БД готова."

# 1) Доводим БД до последней ревизии
echo "Применяем существующие миграции…"
alembic upgrade head

# 2) Генерируем новую ревизию (она всегда создаст файл)
echo "Пытаемся автогенерировать ревизию…"
revision_output=$(alembic revision --autogenerate -m "Auto migration" 2>&1 || true)
echo "$revision_output"

# 3) Парсим путь к файлу из строки "Generating …"
migration_file=$(echo "$revision_output" \
  | grep -Eo "/auto_app/alembic/versions/[0-9a-f]+_auto_migration\.py")

if [ -z "$migration_file" ]; then
  echo "Файл ревизии не найден — выходим."
  exit 0
fi

echo "Найден файл: $migration_file"

# 4) Проверяем содержимое: если внутри только pass — удаляем
if grep -qE "pass" "$migration_file" && ! grep -qE "op\." "$migration_file"; then
  echo "Пустая миграция (только pass) — удаляем $migration_file"
  rm "$migration_file"
else
  echo "Найдены реальные изменения в схеме — применяем миграцию"
  alembic upgrade head
fi

echo "Миграционный процесс завершён."