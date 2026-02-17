"""Базовый экстрактор структурированных данных из документов."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import BaseModel

logger = logging.getLogger(__name__)

_EXTRACTION_PROMPTS_DIR = (
    Path(__file__).resolve().parent.parent / "prompts" / "extraction"
)


def _load_prompt(doc_type: str) -> str:
    """Загрузить шаблон промпта для типа документа. Реестр → файл → generic."""
    from ktem.orchestration.doc_types.registry import get_prompt_for_type

    custom = get_prompt_for_type(doc_type)
    if custom:
        return custom
    path = _EXTRACTION_PROMPTS_DIR / f"{doc_type}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")
    # fallback generic
    return (
        "Extract structured data from this document. "
        "Output valid JSON conforming to the schema. Use null for missing fields. "
        "Output ONLY valid JSON.\n\nSchema:\n{schema}"
    )


def generate_extraction_prompt(doc_type: str, schema: str | dict) -> str:
    """Сгенерировать промпт экстракции с подставленной схемой."""
    if isinstance(schema, dict):
        schema_str = json.dumps(schema, indent=2, ensure_ascii=False)
    else:
        schema_str = str(schema)
    template = _load_prompt(doc_type)
    return template.format(schema=schema_str)


def extract_json_from_response(text: str) -> dict | None:
    """Извлечь JSON из ответа VLM (может быть обёрнут в markdown)."""
    text = (text or "").strip()
    for start in ("{", "```json"):
        idx = text.find(start)
        if idx >= 0:
            if start == "```json":
                idx += len("```json")
            json_str = text[idx:].split("```")[0].strip()
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                continue
    return None


class BaseDocumentExtractor:
    """Базовый класс экстрактора: загружает документ и вызывает VLM для извлечения."""

    def __init__(
        self,
        vlm_endpoint: str = "",
        vlm_model: str | None = None,
        reader=None,
    ):
        self.vlm_endpoint = vlm_endpoint
        self.vlm_model = vlm_model
        self.reader = reader

    def _get_schema_class(self, doc_type: str) -> type[BaseModel] | None:
        from ktem.orchestration.doc_types.registry import get_schema_for_type

        return get_schema_for_type(doc_type)

    def extract(
        self,
        file_path: str | Path,
        doc_type: str,
        raw_text: str | None = None,
        image_data_url: str | None = None,
    ) -> dict | None:
        """
        Извлечь структурированные данные.

        Args:
            file_path: путь к файлу
            doc_type: тип документа (invoice, letter, drawing, tech_spec, sketch)
            raw_text: уже извлечённый текст (если есть)
            image_data_url: data URL изображения для VLM (если есть)

        Returns:
            dict с данными или None при ошибке
        """
        schema_cls = self._get_schema_class(doc_type)
        if not schema_cls:
            logger.debug("No schema for doc_type=%s, skipping extraction", doc_type)
            return None

        schema = schema_cls.model_json_schema()
        prompt = generate_extraction_prompt(doc_type, schema)

        # Нужно изображение для VLM
        if not image_data_url and not raw_text:
            image_data_url = self._get_first_page_image(Path(file_path))
        if not image_data_url and not raw_text:
            logger.warning("No image or text for extraction: %s", file_path)
            return None

        try:
            from kotaemon.loaders.utils.gpt4v import generate_gpt4v

            if image_data_url:
                text = generate_gpt4v(
                    endpoint=self.vlm_endpoint,
                    prompt=prompt,
                    images=image_data_url,
                    max_tokens=4096,
                    model=self.vlm_model,
                )
            else:
                # Только текст — используем LLM (если доступен) или пропускаем
                from ktem.llms.manager import llms

                llm = llms.get_default()
                if llm:
                    full_prompt = f"{prompt}\n\nDocument text:\n{(raw_text or '')[:8000]}"
                    resp = llm(full_prompt)
                    text = resp.text if hasattr(resp, "text") else str(resp)
                else:
                    return None

            data = extract_json_from_response(text)
            if data:
                # Валидация через Pydantic
                schema_cls.model_validate(data)
                return data
        except Exception as e:
            logger.warning("Extraction failed for %s: %s", file_path, e)
        return None

    def _get_first_page_image(self, file_path: Path) -> str | None:
        """Получить первую страницу как data URL."""
        from ktem.orchestration.classifier import _get_first_page_image_data_url

        return _get_first_page_image_data_url(Path(file_path))
