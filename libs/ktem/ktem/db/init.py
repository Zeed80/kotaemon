"""Автоматическая инициализация базы данных с оптимальными настройками.

Выполняется при первом запуске приложения для применения оптимальных параметров
PostgreSQL и создания необходимых расширений (pgvector).
"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from ktem.db.engine import engine

logger = logging.getLogger(__name__)

# Флаг для отслеживания, была ли выполнена инициализация
_initialization_done = False


def ensure_pgvector_extension(session: Session) -> None:
    """Создать расширение pgvector, если его еще нет."""
    try:
        # Проверяем, существует ли расширение
        result = session.execute(
            text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        ).scalar()
        if result:
            logger.debug("Расширение pgvector уже установлено")
            return

        # Создаем расширение
        session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        session.commit()
        logger.info("Расширение pgvector успешно создано")
    except Exception as e:
        # Если это не PostgreSQL или другая ошибка, просто логируем
        logger.debug(
            "Не удалось создать расширение pgvector (возможно, не PostgreSQL): %s", e
        )
        session.rollback()


def apply_optimal_postgresql_settings(session: Session) -> None:
    """Применить оптимальные настройки PostgreSQL (если они еще не применены).

    Эти настройки уже заданы в docker-compose.yml через command,
    но для локальной установки можно применить их здесь.
    """
    try:
        # Проверяем текущие значения (только для информации, не меняем через SQL)
        # Основные настройки применяются через docker-compose command или postgresql.conf
        # Здесь мы только логируем текущие значения для диагностики
        settings_to_check = [
            "shared_buffers",
            "effective_cache_size",
            "maintenance_work_mem",
            "work_mem",
            "random_page_cost",
            "effective_io_concurrency",
        ]
        for setting_name in settings_to_check:
            try:
                result = session.execute(text(f"SHOW {setting_name}")).scalar()
                logger.debug("PostgreSQL %s = %s", setting_name, result)
            except Exception:
                pass  # Игнорируем ошибки для отдельных настроек
    except Exception as e:
        logger.debug("Не удалось проверить настройки PostgreSQL: %s", e)


def initialize_database() -> None:
    """Инициализировать базу данных с оптимальными настройками.

    Вызывается автоматически при первом запуске приложения.
    """
    global _initialization_done
    if _initialization_done:
        return

    db_url = str(engine.url)
    if not db_url.startswith("postgresql"):
        raise ValueError(
            f"База данных должна быть PostgreSQL, получено: {db_url}. "
            "Задайте DATABASE_URL в .env или используйте дефолтное значение для Docker Compose."
        )

    try:
        with Session(engine) as session:
            # Создаем расширение pgvector (если используется pgvector)
            ensure_pgvector_extension(session)

            # Логируем текущие настройки PostgreSQL (для диагностики)
            apply_optimal_postgresql_settings(session)

        _initialization_done = True
        logger.info("Инициализация базы данных завершена")
    except Exception as e:
        logger.warning("Ошибка при инициализации базы данных: %s", e)
        # Не прерываем запуск приложения, если инициализация не удалась
        _initialization_done = True
