"""Классификатор документов для маршрутизации при индексации."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from ktem.orchestration.doc_types.registry import DOC_TYPES

if TYPE_CHECKING:
    from kotaemon.base import Document

logger = logging.getLogger(__name__)


@dataclass
class DocClassification:
    """Результат классификации документа."""

    doc_type: str  # invoice | letter | drawing | tech_spec | sketch | contract | specification | price_list | unknown
    confidence: float


# Ключевые слова по типам (в имени файла или пути)
_TYPE_KEYWORDS: dict[str, list[str]] = {
    "invoice": [
        "invoice",
        "счёт",
        "счет",
        "fattura",
        "rechnung",
        "facture",
        "bill",
        "receipt",
        "квітанція",
        "квитанция",
        "oplata",
        "payment",
    ],
    "letter": [
        "letter",
        "письмо",
        "лист",
        "brief",
        "correspondence",
        "email",
        "mail",
        "сообщение",
        "message",
    ],
    "drawing": [
        "drawing",
        "чертёж",
        "чертеж",
        "креслення",
        "схема",
        "diagram",
        "blueprint",
        "cad",
        "dwg",
        "dxf",
        "technical_drawing",
    ],
    "tech_spec": [
        "spec",
        "specification",
        "технич",
        "техн_",
        "ГОСТ",
        "ISO",
        "manual",
        "руководство",
        "instruction",
        "инструкция",
    ],
    "sketch": [
        "sketch",
        "эскиз",
        "ескіз",
        "набросок",
        "черновик",
        "draft",
    ],
    "contract": [
        "contract",
        "договор",
        "контракт",
        "договір",
        "agreement",
    ],
    "specification": [
        "specification",
        "спецификация",
        "специфікація",
        "технічні умови",
    ],
    "price_list": [
        "price",
        "прайс",
        "price_list",
        "прайс-лист",
        "pricelist",
    ],
}

# Порог уверенности для VLM-классификации (ниже — fallback на эвристику)
VLM_CONFIDENCE_THRESHOLD = 0.6

CLASSIFY_BY_IMAGE_PROMPT = """Classify this document image. Choose exactly ONE type from:
- invoice: bill, receipt, счёт, invoice with line items and totals
- letter: correspondence, email, official letter, письмо
- drawing: technical drawing, чертёж, blueprint, CAD output (dwg, dxf)
- tech_spec: technical specification, техкарта, manual, instruction
- sketch: эскиз, draft, rough drawing
- contract: договор, agreement, contract
- specification: specification document, спецификация
- price_list: прайс-лист, price list, catalog with prices
- unknown: if unclear

Respond ONLY with valid JSON: {"doc_type": "<type>", "confidence": <0.0-1.0>}
Example: {"doc_type": "invoice", "confidence": 0.95}"""


def _normalize(s: str) -> str:
    return re.sub(r"[_\s\-.]", " ", s.lower())


def _get_first_page_image_data_url(file_path: Path) -> str | None:
    """Получить первую страницу документа как data URL для VLM."""
    ext = file_path.suffix.lower()
    try:
        if ext in (".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"):
            import base64

            with open(file_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            mime = "image/png" if ext == ".png" else "image/jpeg"
            return f"data:{mime};base64,{b64}"
        if ext == ".pdf":
            import base64
            from io import BytesIO

            try:
                import fitz
            except ImportError:
                return None
            doc = fitz.open(file_path)
            if doc.page_count == 0:
                doc.close()
                return None
            page = doc.load_page(0)
            pm = page.get_pixmap(dpi=100)
            from PIL import Image

            img = Image.frombytes("RGB", [pm.width, pm.height], pm.samples)
            doc.close()
            buf = BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            return f"data:image/png;base64,{b64}"
    except Exception as e:
        logger.warning("Failed to get first page image for classification: %s", e)
    return None


def classify_by_image(
    file_path: str | Path,
    vlm_endpoint: str = "",
    vlm_model: str | None = None,
) -> DocClassification:
    """
    Классифицировать документ по изображению первой страницы через VLM.

    Использует VLM для определения типа. При ошибке или низкой уверенности —
    fallback на classify_by_path.

    Args:
        file_path: путь к файлу (PDF или изображение)
        vlm_endpoint: URL VLM endpoint
        vlm_model: имя модели (опционально для Ollama)

    Returns:
        DocClassification
    """
    path = Path(file_path)
    data_url = _get_first_page_image_data_url(path)
    if not data_url:
        return classify_by_path(file_path)

    if not vlm_endpoint:
        try:
            from theflow.settings import settings as flowsettings

            vlm_endpoint = (
                getattr(
                    flowsettings,
                    "get_vlm_endpoint",
                    lambda _: getattr(flowsettings, "KH_VLM_ENDPOINT", ""),
                )("default")
                or ""
            )
        except Exception:
            pass
    if not vlm_endpoint:
        return classify_by_path(file_path)

    try:
        from kotaemon.loaders.utils.gpt4v import generate_gpt4v

        text = generate_gpt4v(
            endpoint=vlm_endpoint,
            prompt=CLASSIFY_BY_IMAGE_PROMPT,
            images=data_url,
            max_tokens=128,
            model=vlm_model,
        )
        text = (text or "").strip()
        # Извлечь JSON из ответа
        for start in ("{", "```json"):
            idx = text.find(start)
            if idx >= 0:
                if start == "```json":
                    idx += len("```json")
                json_str = text[idx:].split("```")[0].strip()
                try:
                    data = json.loads(json_str)
                    doc_type = (data.get("doc_type") or "unknown").lower().strip()
                    confidence = float(data.get("confidence", 0.5))
                    if doc_type not in DOC_TYPES:
                        doc_type = "unknown"
                    if confidence < VLM_CONFIDENCE_THRESHOLD:
                        return classify_by_path(file_path)
                    return DocClassification(doc_type, min(1.0, max(0.0, confidence)))
                except (json.JSONDecodeError, ValueError, TypeError):
                    continue
        return classify_by_path(file_path)
    except Exception as e:
        logger.warning("VLM document classification failed: %s", e)
        return classify_by_path(file_path)


def classify_by_path(file_path: str | Path, user_id: str = "") -> DocClassification:
    """
    Классифицировать документ по пути к файлу (расширение + ключевые слова).

    Returns:
        DocClassification с doc_type и confidence
    """
    from ktem.orchestration.doc_types.registry import get_all_type_keywords

    path = Path(file_path)
    name = _normalize(path.stem)
    ext = path.suffix.lower()
    type_keywords = get_all_type_keywords(user_id)

    # Эвристика по расширению
    if ext in (".dwg", ".dxf", ".step", ".stp", ".iges", ".igs"):
        return DocClassification("drawing", 0.9)
    invoice_kw = type_keywords.get("invoice", [])
    if ext in (".pdf",) and invoice_kw and any(kw in name for kw in invoice_kw):
        return DocClassification("invoice", 0.85)
    if any(kw in name for kw in type_keywords.get("drawing", [])):
        return DocClassification("drawing", 0.8)
    if invoice_kw and any(kw in name for kw in invoice_kw):
        return DocClassification("invoice", 0.8)
    for doc_type in (
        "tech_spec",
        "letter",
        "sketch",
        "contract",
        "specification",
        "price_list",
    ):
        if any(kw in name for kw in type_keywords.get(doc_type, [])):
            return DocClassification(doc_type, 0.75)
    # Пользовательские типы
    for doc_type, keywords in type_keywords.items():
        if (
            doc_type not in DOC_TYPES
            and keywords
            and any(kw in name for kw in keywords)
        ):
            return DocClassification(doc_type, 0.75)

    return DocClassification("unknown", 0.5)


def classify_by_document(doc: Document, user_id: str = "") -> DocClassification:
    """
    Классифицировать по содержимому документа (первый чанк / метаданные).

    Используется при наличии уже загруженного документа.
    """
    from ktem.orchestration.doc_types.registry import get_all_type_keywords

    text = (doc.text or "")[:2000]
    name = doc.metadata.get("file_name", "") or doc.metadata.get("file_path", "")
    combined = _normalize(f"{name} {text}")
    type_keywords = get_all_type_keywords(user_id)

    for doc_type, keywords in type_keywords.items():
        if keywords and any(kw in combined for kw in keywords):
            return DocClassification(doc_type, 0.7)
    return DocClassification("unknown", 0.5)
