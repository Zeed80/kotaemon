"""Модель пользовательских типов документов."""

from __future__ import annotations

import datetime
import uuid

from sqlalchemy import JSON, Boolean, Column, DateTime, String, Text
from sqlalchemy.orm import DeclarativeBase
from theflow.settings import settings as flowsettings

from ktem.db.engine import engine


class _Base(DeclarativeBase):
    pass


class DocumentTypeTable(_Base):
    """Таблица пользовательских типов документов.

    Поля:
        id: UUID
        name: код (invoice, letter, my_custom)
        display_name: отображаемое имя
        schema_def: JSON — список полей для Pydantic [{name, type, description}]
        extraction_prompt_template: текст шаблона с {schema}
        classifier_keywords: JSON — {"ru": [...], "en": [...]}
        enable_pre_aggregation: bool
        created_at: datetime
        user: владелец (для приватных)
    """

    __tablename__ = "document_type"

    id = Column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    name = Column(String(128), unique=True, nullable=False, index=True)
    display_name = Column(String(256), nullable=False)
    schema_def = Column(JSON, default=list)
    extraction_prompt_template = Column(Text, default="")
    classifier_keywords = Column(JSON, default=dict)
    enable_pre_aggregation = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    user = Column(String(256), default="")


def _create_table_if_needed() -> None:
    """Создать таблицу при первом импорте (если не используется Alembic)."""
    if not getattr(flowsettings, "KH_ENABLE_ALEMBIC", False):
        DocumentTypeTable.metadata.create_all(bind=engine)


_create_table_if_needed()
