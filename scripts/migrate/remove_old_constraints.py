#!/usr/bin/env python3
"""
Скрипт для удаления старых constraints с конфликтующими именами из PostgreSQL.

Использование:
    python scripts/migrate/remove_old_constraints.py

Или через Docker:
    docker compose exec app python scripts/migrate/remove_old_constraints.py
"""

import os
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

# Получаем DATABASE_URL из окружения или используем дефолт для Docker Compose
database_url = os.getenv(
    "DATABASE_URL",
    "postgresql://kotaemon:kotaemon@postgres:5432/kotaemon",
)

# Убеждаемся, что используется правильный драйвер
if database_url.startswith("postgresql://") and "+psycopg" not in database_url:
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(database_url)


def remove_old_constraints():
    """Удаляет все старые constraints с именем '_name_user_uc' из базы данных."""
    print("Поиск старых constraints с именем '_name_user_uc'...")

    with engine.connect() as conn:
        # Находим все constraints с именем _name_user_uc
        query = text("""
            SELECT conname, conrelid::regclass::text as table_name
            FROM pg_constraint
            WHERE conname = '_name_user_uc'
            ORDER BY conrelid::regclass::text;
        """)

        result = conn.execute(query)
        constraints = result.fetchall()

        if not constraints:
            print("Старые constraints не найдены. Всё в порядке!")
            return

        print(f"Найдено {len(constraints)} старых constraint(s):")
        for constraint_name, table_name in constraints:
            print(f"  - {constraint_name} в таблице {table_name}")

        # Удаляем все найденные constraints
        print("\nУдаление старых constraints...")
        for constraint_name, table_name in constraints:
            try:
                drop_query = text(
                    f'ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS "{constraint_name}";'
                )
                conn.execute(drop_query)
                conn.commit()
                print(
                    f"  ✓ Удалён constraint {constraint_name} из таблицы {table_name}"
                )
            except ProgrammingError as e:
                print(f"  ✗ Ошибка при удалении {constraint_name} из {table_name}: {e}")
                conn.rollback()

        print("\nГотово! Старые constraints удалены.")


if __name__ == "__main__":
    try:
        remove_old_constraints()
    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)
