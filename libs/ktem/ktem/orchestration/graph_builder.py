"""Построение графов связей между документами.

Извлекает ссылки из structured_data, создаёт chunks-связи для векторного поиска.
Используется при индексации или по кнопке «Построить граф».
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def extract_links_from_structured_data(
    structured_data: dict[str, Any] | None, doc_type: str
) -> list[dict[str, str]]:
    """Извлечь ссылки на другие документы из structured_data.

    Args:
        structured_data: структурированные данные документа
        doc_type: тип документа (invoice, letter, contract, ...)

    Returns:
        Список ссылок [{"target_ref": "...", "link_type": "..."}, ...]
    """
    if not structured_data:
        return []
    links: list[dict[str, str]] = []
    # Базовые поля, которые могут содержать ссылки
    ref_fields = ("invoice_number", "document_number", "contract_number", "reference")
    for key, val in structured_data.items():
        if key.lower() in ref_fields and val and isinstance(val, str):
            links.append({"target_ref": str(val).strip(), "link_type": key})
    return links


def build_document_links(
    source_doc_id: str,
    structured_data: dict[str, Any] | None,
    doc_type: str,
) -> list[dict[str, Any]]:
    """Построить связи документа для добавления в векторное хранилище.

    Args:
        source_doc_id: ID исходного документа (Source)
        structured_data: структурированные данные
        doc_type: тип документа

    Returns:
        Список метаданных для chunks-связей
    """
    links = extract_links_from_structured_data(structured_data, doc_type)
    return [
        {
            "link_type": ln.get("link_type", "reference"),
            "source_doc_id": source_doc_id,
            "target_ref": ln.get("target_ref", ""),
        }
        for ln in links
    ]
