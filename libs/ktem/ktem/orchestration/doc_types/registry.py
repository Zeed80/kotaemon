"""Реестр типов документов.

Базовые типы + пользовательские из БД.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pydantic import BaseModel

# Базовые типы документов (источник истины для UI и классификатора)
DOC_TYPES = (
    "invoice",
    "letter",
    "drawing",
    "tech_spec",
    "sketch",
    "contract",
    "specification",
    "price_list",
    "unknown",
)

# Маппинг код -> отображаемое имя для UI (базовые)
DOC_TYPE_DISPLAY_NAMES: dict[str, str] = {
    "invoice": "Счёт",
    "letter": "Письмо",
    "drawing": "Чертёж",
    "tech_spec": "Техкарта",
    "sketch": "Эскиз",
    "contract": "Договор",
    "specification": "Спецификация",
    "price_list": "Прайс-лист",
    "unknown": "Неизвестный",
}


def _load_custom_types_from_db(user_id: str = "") -> list[tuple[str, str]]:
    """Загрузить пользовательские типы из БД. Возвращает [(display_name, name), ...]."""
    try:
        from sqlalchemy import select
        from sqlalchemy.orm import Session

        from ktem.db.document_type import DocumentTypeTable
        from ktem.db.engine import engine

        with Session(engine) as session:
            stmt = select(DocumentTypeTable).order_by(DocumentTypeTable.name)
            if user_id:
                stmt = stmt.where(
                    (DocumentTypeTable.user == user_id) | (DocumentTypeTable.user == "")
                )
            rows = session.execute(stmt).scalars().all()
            return [(str(r.display_name), str(r.name)) for r in rows]
    except Exception:
        return []


def get_doc_type_choices(user_id: str = "") -> list[tuple[str, str]]:
    """Список (display_name, code) для выпадающего списка в UI.

    Базовые типы + пользовательские из БД.
    """
    base_choices = [(DOC_TYPE_DISPLAY_NAMES.get(t, t), t) for t in DOC_TYPES]
    custom = _load_custom_types_from_db(user_id)
    # Исключить дубликаты по name (пользовательский перезаписывает базовый)
    seen = {t[1] for t in base_choices}
    for dname, name in custom:
        if name not in seen:
            base_choices.append((dname, name))
            seen.add(name)
    return base_choices


def get_all_doc_types(user_id: str = "") -> list[dict]:
    """Все типы: базовые (readonly) + пользовательские из БД."""
    result = []
    for t in DOC_TYPES:
        result.append(
            {
                "name": t,
                "display_name": DOC_TYPE_DISPLAY_NAMES.get(t, t),
                "is_builtin": True,
            }
        )
    try:
        from sqlalchemy import select
        from sqlalchemy.orm import Session

        from ktem.db.document_type import DocumentTypeTable
        from ktem.db.engine import engine

        with Session(engine) as session:
            stmt = select(DocumentTypeTable).order_by(DocumentTypeTable.name)
            if user_id:
                stmt = stmt.where(
                    (DocumentTypeTable.user == user_id) | (DocumentTypeTable.user == "")
                )
            for r in session.execute(stmt).scalars().all():
                result.append(
                    {
                        "id": r.id,
                        "name": r.name,
                        "display_name": r.display_name,
                        "schema_def": r.schema_def or [],
                        "extraction_prompt_template": r.extraction_prompt_template
                        or "",
                        "classifier_keywords": r.classifier_keywords or {},
                        "enable_pre_aggregation": r.enable_pre_aggregation,
                        "created_at": r.created_at.isoformat()
                        if r.created_at
                        else None,
                        "user": r.user,
                        "is_builtin": False,
                    }
                )
    except Exception:
        pass
    return result


def get_schema_for_type(doc_type: str) -> type[BaseModel] | None:
    """Получить Pydantic-схему для типа. Базовые — из SCHEMAS, кастомные — из schema_def."""
    from ktem.orchestration.doc_types.generator import create_schema_from_def
    from ktem.orchestration.extractors.schemas import SCHEMAS

    if doc_type in SCHEMAS:
        return SCHEMAS[doc_type]
    try:
        from sqlalchemy import select
        from sqlalchemy.orm import Session

        from ktem.db.document_type import DocumentTypeTable
        from ktem.db.engine import engine

        with Session(engine) as session:
            row = (
                session.execute(
                    select(DocumentTypeTable).where(DocumentTypeTable.name == doc_type)
                )
                .scalars()
                .first()
            )
            if row and row.schema_def:
                schema_def: list = (
                    row.schema_def if isinstance(row.schema_def, list) else []
                )
                return create_schema_from_def(
                    f"{doc_type.title().replace('_', '')}Schema",
                    schema_def,
                )
    except Exception:
        pass
    return None


def get_prompt_for_type(doc_type: str) -> str | None:
    """Получить шаблон промпта экстракции для типа. None — использовать дефолт из файла."""
    try:
        from sqlalchemy import select
        from sqlalchemy.orm import Session

        from ktem.db.document_type import DocumentTypeTable
        from ktem.db.engine import engine

        with Session(engine) as session:
            row = (
                session.execute(
                    select(DocumentTypeTable).where(DocumentTypeTable.name == doc_type)
                )
                .scalars()
                .first()
            )
            if row and row.extraction_prompt_template:
                return str(row.extraction_prompt_template)
    except Exception:
        pass
    return None


def get_display_name(doc_type: str) -> str:
    """Получить отображаемое имя для типа (базовый или из БД)."""
    if doc_type in DOC_TYPE_DISPLAY_NAMES:
        return DOC_TYPE_DISPLAY_NAMES[doc_type]
    try:
        from sqlalchemy import select
        from sqlalchemy.orm import Session

        from ktem.db.document_type import DocumentTypeTable
        from ktem.db.engine import engine

        with Session(engine) as session:
            row = (
                session.execute(
                    select(DocumentTypeTable).where(DocumentTypeTable.name == doc_type)
                )
                .scalars()
                .first()
            )
            if row:
                return str(row.display_name)
    except Exception:
        pass
    return doc_type or "—"


def get_all_type_keywords(user_id: str = "") -> dict[str, list[str]]:
    """Все типы и их ключевые слова для классификации (базовые + пользовательские)."""
    from ktem.orchestration.classifier import _TYPE_KEYWORDS

    result = dict(_TYPE_KEYWORDS)
    try:
        from sqlalchemy import select
        from sqlalchemy.orm import Session

        from ktem.db.document_type import DocumentTypeTable
        from ktem.db.engine import engine

        with Session(engine) as session:
            stmt = select(DocumentTypeTable)
            if user_id:
                stmt = stmt.where(
                    (DocumentTypeTable.user == user_id) | (DocumentTypeTable.user == "")
                )
            for r in session.execute(stmt).scalars().all():
                kw: Any = r.classifier_keywords or {}
                if isinstance(kw, dict) and "ru" in kw:
                    result[str(r.name)] = (
                        list(kw["ru"]) if isinstance(kw["ru"], list) else []
                    )
                elif isinstance(kw, list):
                    result[str(r.name)] = list(kw)
    except Exception:
        pass
    return result


def get_keywords_for_type(doc_type: str, user_id: str = "") -> dict[str, list[str]]:
    """Ключевые слова для классификатора. Базовые + из БД."""
    from ktem.orchestration.classifier import _TYPE_KEYWORDS

    base_list = _TYPE_KEYWORDS.get(doc_type, [])
    result: dict[str, list[str]] = {"ru": list(base_list), "en": []}
    try:
        from sqlalchemy import select
        from sqlalchemy.orm import Session

        from ktem.db.document_type import DocumentTypeTable
        from ktem.db.engine import engine

        with Session(engine) as session:
            row = (
                session.execute(
                    select(DocumentTypeTable).where(DocumentTypeTable.name == doc_type)
                )
                .scalars()
                .first()
            )
            if row and row.classifier_keywords:
                kw = row.classifier_keywords
                if isinstance(kw, dict):
                    for lang, words in kw.items():
                        result[lang] = list(words) if isinstance(words, list) else []
                elif isinstance(kw, list):
                    result["ru"] = list(kw)
    except Exception:
        pass
    return result


def register_custom_type(
    name: str,
    display_name: str,
    schema_def: list | None = None,
    extraction_prompt_template: str = "",
    classifier_keywords: dict | None = None,
    enable_pre_aggregation: bool = True,
    user_id: str = "",
) -> str:
    """Добавить или обновить пользовательский тип. Возвращает id."""
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from ktem.db.document_type import DocumentTypeTable
    from ktem.db.engine import engine

    with Session(engine) as session:
        existing = session.execute(
            select(DocumentTypeTable).where(DocumentTypeTable.name == name)
        ).scalar_one_or_none()
        if existing:
            existing.display_name = display_name  # type: ignore[assignment]
            existing.schema_def = schema_def or []  # type: ignore[assignment]
            existing.extraction_prompt_template = extraction_prompt_template  # type: ignore[assignment]
            existing.classifier_keywords = classifier_keywords or {}  # type: ignore[assignment]
            existing.enable_pre_aggregation = enable_pre_aggregation  # type: ignore[assignment]
            existing.user = user_id  # type: ignore[assignment]
            session.commit()
            return str(existing.id)
        new_row = DocumentTypeTable(
            name=name,
            display_name=display_name,
            schema_def=schema_def or [],
            extraction_prompt_template=extraction_prompt_template,
            classifier_keywords=classifier_keywords or {},
            enable_pre_aggregation=enable_pre_aggregation,
            user=user_id,
        )
        session.add(new_row)
        session.commit()
        session.refresh(new_row)
        return str(new_row.id)


def delete_custom_type(name: str, user_id: str = "") -> bool:
    """Удалить пользовательский тип. Возвращает True при успехе."""
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from ktem.db.document_type import DocumentTypeTable
    from ktem.db.engine import engine

    if name in DOC_TYPES:
        return False
    with Session(engine) as session:
        stmt = select(DocumentTypeTable).where(DocumentTypeTable.name == name)
        if user_id:
            stmt = stmt.where(
                (DocumentTypeTable.user == user_id) | (DocumentTypeTable.user == "")
            )
        row = session.execute(stmt).scalars().first()
        if row:
            session.delete(row)
            session.commit()
            return True
    return False


def get_custom_type_by_id(type_id: str) -> dict | None:
    """Получить пользовательский тип по id."""
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from ktem.db.document_type import DocumentTypeTable
    from ktem.db.engine import engine

    with Session(engine) as session:
        row = (
            session.execute(
                select(DocumentTypeTable).where(DocumentTypeTable.id == type_id)
            )
            .scalars()
            .first()
        )
        if row:
            return {
                "id": row.id,
                "name": row.name,
                "display_name": row.display_name,
                "schema_def": row.schema_def or [],
                "extraction_prompt_template": row.extraction_prompt_template or "",
                "classifier_keywords": row.classifier_keywords or {},
                "enable_pre_aggregation": row.enable_pre_aggregation,
                "user": row.user,
            }
    return None


def get_sources_by_doc_type(
    Source, doc_type: str, user_id: str | None = None
) -> list[tuple[str, str]]:
    """Найти Source по doc_type в note. Возвращает [(source_id, path_hash), ...]."""
    from sqlalchemy import text
    from sqlalchemy.orm import Session

    from ktem.db.engine import engine

    tbl = Source.__table__.name
    sql = f"SELECT id, path FROM {tbl} " "WHERE note->>'doc_type' = :doc_type"
    params: dict[str, str] = {"doc_type": doc_type}
    if user_id:
        sql += ' AND ("user" = :user_id OR "user" = \'\')'
        params["user_id"] = user_id
    with Session(engine) as session:
        result = session.execute(text(sql), params).fetchall()
        return [(r[0], r[1]) for r in result]
