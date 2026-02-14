"""Таблица и модель для хранения настроенных серверов Ollama."""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import DeclarativeBase
from theflow.settings import settings as flowsettings

from ktem.db.engine import engine


class Base(DeclarativeBase):
    pass


class OllamaServerTable(Base):
    """Таблица серверов Ollama: имя, URL, макс. контекст."""

    __tablename__ = "ollama_server_table"

    name = Column(String, primary_key=True, unique=True)
    base_url = Column(String, nullable=False)
    num_ctx = Column(Integer, default=8192, nullable=False)


if not getattr(flowsettings, "KH_ENABLE_ALEMBIC", False):
    OllamaServerTable.metadata.create_all(engine)
