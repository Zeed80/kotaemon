"""Извлечение связей между документами (счета, чертежи, техкарты)."""

from __future__ import annotations

import re
from typing import Any


def extract_drawing_refs(text: str) -> list[str]:
    """Извлечь ссылки на чертежи из текста (обозначения, номера)."""
    # Паттерны: Деталь 123-456, черт. 789, 01.234.567, АБ 123-456
    patterns = [
        (r"\b(?:черт\.?|чертеж|drawing)\s*[:\s№#]*\s*([A-Za-z0-9.\-]+)", 1),
        (r"\b(?:деталь|изделие)\s+([A-Za-z0-9.\-]+)", 1),
        (r"\b(\d{2}\.\d{3}\.\d{3}(?:\.\d+)?)\b", 1),  # 01.234.567
        (r"\b([A-Z]{2,}\s*\d+[.\-]\d+)\b", 1),  # АБ 123-456
    ]
    refs: set[str] = set()
    for pat, grp in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            refs.add(m.group(grp).strip())
    return list(refs)


def extract_invoice_refs(text: str) -> list[str]:
    """Извлечь ссылки на счета (номера)."""
    # Счёт №123, invoice 456, счет 789
    patterns = [
        r"(?:счёт|счет|invoice)\s*[№#:]*\s*(\d+[-\w]*)",
        r"\b№\s*(\d+[-\w]*)",
    ]
    refs: set[str] = set()
    for pat in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            refs.add(m.group(1).strip())
    return list(refs)


def extract_article_refs(text: str) -> list[str]:
    """Извлечь артикулы и коды позиций."""
    # Артикул 123-456, арт. 789, article ABC123
    patterns = [
        (r"(?:артикул|арт\.?|article)\s*[:\s]*([A-Za-z0-9.\-]+)", 1),
        (r"\b([A-Z]{2,}\d{4,})\b", 1),  # AB12345
    ]
    refs: set[str] = set()
    for pat, grp in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            refs.add(m.group(grp).strip())
    return list(refs)


def extract_links_from_structured_data(
    doc_type: str,
    structured_data: dict[str, Any],
) -> list[dict[str, str]]:
    """
    Извлечь связи из структурированных данных документа.

    Returns:
        List of {"target_type": "drawing"|"invoice"|"article", "ref": "..."}
    """
    links: list[dict[str, str]] = []
    if not structured_data:
        return links

    combined_text = str(structured_data)

    for ref in extract_drawing_refs(combined_text):
        links.append({"target_type": "drawing", "ref": ref})
    for ref in extract_invoice_refs(combined_text):
        links.append({"target_type": "invoice", "ref": ref})
    for ref in extract_article_refs(combined_text):
        links.append({"target_type": "article", "ref": ref})

    # Из line_items счёт -> артикулы
    if doc_type == "invoice":
        for item in structured_data.get("line_items") or []:
            name = (item.get("name") or "") + " " + (item.get("article") or "")
            for ref in extract_article_refs(name):
                links.append({"target_type": "article", "ref": ref})

    return links
