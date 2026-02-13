"""Таблица и модель для хранения настроенных VLM (vision models)."""

from ktem.db.engine import engine
from sqlalchemy import JSON, Column, String
from sqlalchemy.orm import DeclarativeBase

from theflow.settings import settings as flowsettings


class Base(DeclarativeBase):
    pass


class VLMTable(Base):
    """Таблица VLM: имя, spec (JSON: provider, endpoint_url, model, api_key, ollama_server и т.д.)."""

    __tablename__ = "vlm_table"

    name = Column(String, primary_key=True, unique=True)
    spec = Column(JSON, default=dict, nullable=False)


if not getattr(flowsettings, "KH_ENABLE_ALEMBIC", False):
    VLMTable.metadata.create_all(engine)
