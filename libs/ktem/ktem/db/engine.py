from sqlmodel import create_engine
from theflow.settings import settings

# Оптимизированные параметры для PostgreSQL (connection pooling, timeout)
_db_url = settings.KH_DATABASE
if not _db_url.startswith("postgresql"):
    raise ValueError(
        f"KH_DATABASE должен быть PostgreSQL URL (postgresql://...), получено: {_db_url}. "
        "Задайте DATABASE_URL в .env или используйте дефолтное значение для Docker Compose."
    )
# Connection pooling для PostgreSQL: оптимальные значения для производительности
# pool_size и max_overflow настроены для баланса между производительностью и ресурсами
engine = create_engine(
    _db_url,
    pool_size=10,  # базовое количество соединений в пуле
    max_overflow=20,  # дополнительные соединения при пиковой нагрузке (всего до 30)
    pool_pre_ping=True,  # проверка соединений перед использованием (восстановление после разрыва)
    pool_recycle=3600,  # пересоздание соединений каждые 3600 сек (1 час) — избегаем таймаутов
    connect_args={
        "connect_timeout": 10,  # таймаут подключения (сек)
        "application_name": "kotaemon",  # имя приложения в pg_stat_activity (для мониторинга)
        "options": "-c statement_timeout=30000",  # таймаут выполнения запроса 30 сек (для долгих векторных запросов)
    },
)
