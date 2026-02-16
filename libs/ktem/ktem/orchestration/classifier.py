"""Классификатор документов для маршрутизации при индексации."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kotaemon.base import Document


@dataclass
class DocClassification:
    """Результат классификации документа."""

    doc_type: str  # invoice | letter | drawing | tech_spec | unknown
    confidence: float


# Ключевые слова по типам (в имени файла или пути)
_TYPE_KEYWORDS: dict[str, list[str]] = {
    "invoice": [
        "invoice", "счёт", "счет", "fattura", "rechnung", "facture",
        "bill", "receipt", "квітанція", "квитанция", "oplata", "payment",
    ],
    "letter": [
        "letter", "письмо", "лист", "brief", "correspondence",
        "email", "mail", "сообщение", "message",
    ],
    "drawing": [
        "drawing", "чертёж", "чертеж", "креслення", "схема", "diagram",
        "blueprint", "cad", "dwg", "dxf", "technical_drawing",
    ],
    "tech_spec": [
        "spec", "specification", "технич", "техн_", "ГОСТ", "ISO",
        "manual", "руководство", "instruction", "инструкция",
    ],
}


def _normalize(s: str) -> str:
    return re.sub(r"[_\s\-.]", " ", s.lower())


def classify_by_path(file_path: str | Path) -> DocClassification:
    """
    Классифицировать документ по пути к файлу (расширение + ключевые слова).

    Returns:
        DocClassification с doc_type и confidence
    """
    path = Path(file_path)
    name = _normalize(path.stem)
    ext = path.suffix.lower()

    # Эвристика по расширению
    if ext in (".dwg", ".dxf", ".step", ".stp", ".iges", ".igs"):
        return DocClassification("drawing", 0.9)
    if ext in (".pdf",) and any(kw in name for kw in _TYPE_KEYWORDS["invoice"]):
        return DocClassification("invoice", 0.85)
    if any(kw in name for kw in _TYPE_KEYWORDS["drawing"]):
        return DocClassification("drawing", 0.8)
    if any(kw in name for kw in _TYPE_KEYWORDS["invoice"]):
        return DocClassification("invoice", 0.8)
    if any(kw in name for kw in _TYPE_KEYWORDS["tech_spec"]):
        return DocClassification("tech_spec", 0.75)
    if any(kw in name for kw in _TYPE_KEYWORDS["letter"]):
        return DocClassification("letter", 0.75)

    return DocClassification("unknown", 0.5)


def classify_by_document(doc: Document) -> DocClassification:
    """
    Классифицировать по содержимому документа (первый чанк / метаданные).

    Используется при наличии уже загруженного документа.
    """
    text = (doc.text or "")[:2000]
    name = doc.metadata.get("file_name", "") or doc.metadata.get("file_path", "")
    combined = _normalize(f"{name} {text}")

    for doc_type, keywords in _TYPE_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            return DocClassification(doc_type, 0.7)
    return DocClassification("unknown", 0.5)
