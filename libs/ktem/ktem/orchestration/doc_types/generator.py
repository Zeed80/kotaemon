"""Генерация Pydantic-схем и промптов для пользовательских типов документов."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field, create_model

# Маппинг строковых типов из schema_def в Python-типы
_TYPE_MAP: dict[str, type] = {
    "str": str,
    "string": str,
    "int": int,
    "integer": int,
    "float": float,
    "number": float,
    "bool": bool,
    "boolean": bool,
    "list": list,
    "array": list,
    "dict": dict,
    "object": dict,
}


def create_schema_from_def(
    model_name: str, schema_def: list[dict[str, Any]]
) -> type[BaseModel]:
    """Создать Pydantic-модель из schema_def.

    schema_def: список полей [{"name": "...", "type": "str", "description": "..."}]
    """
    if not schema_def:
        return create_model(model_name)

    fields: dict[str, Any] = {}
    for item in schema_def:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("field")
        if not name or not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", str(name)):
            continue
        name = str(name)
        type_str = str(item.get("type", "str")).strip().lower()
        desc = str(item.get("description", ""))
        py_type = _TYPE_MAP.get(type_str, str)
        if py_type in (list, dict):
            factory: Any = list if py_type is list else dict
            fields[name] = (
                py_type,
                Field(default_factory=factory, description=desc)
                if desc
                else Field(default_factory=factory),
            )
        else:
            fields[name] = (py_type | None, Field(None, description=desc or ""))

    return create_model(model_name, **fields)


def generate_prompt_from_fields(
    schema_def: list[dict[str, Any]], template: str | None = None
) -> str:
    """Сгенерировать шаблон промпта экстракции по полям schema_def.

    Если template задан — подставляет {schema}. Иначе — дефолтный.
    """
    if not schema_def:
        default = (
            "Extract structured data from this document. "
            "Output valid JSON. Use null for missing fields. Output ONLY valid JSON.\n\n{schema}"
        )
        return template or default

    lines = []
    for item in schema_def:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("field", "")
        type_str = item.get("type", "str")
        desc = item.get("description", "")
        if name:
            line = f"- {name} ({type_str})"
            if desc:
                line += f": {desc}"
            lines.append(line)

    schema_text = "\n".join(lines) if lines else "{}"
    if template and "{schema}" in template:
        return template.format(schema=schema_text)
    default = (
        "Extract structured data from this document. "
        "Output valid JSON with these fields:\n{schema}\n\n"
        "Use null for missing fields. Output ONLY valid JSON."
    )
    return default.format(schema=schema_text)


def generate_prompt_with_llm(
    schema_def: list[dict[str, Any]], doc_type_name: str = ""
) -> str:
    """Сгенерировать шаблон промпта экстракции через LLM по полям schema_def."""
    if not schema_def:
        return generate_prompt_from_fields([], None)
    try:
        from ktem.llms.manager import llms

        llm = llms.get_default()
        if not llm:
            return generate_prompt_from_fields(schema_def, None)
        fields_desc = "\n".join(
            f"- {item.get('name', '')} ({item.get('type', 'str')}): {item.get('description', '')}"
            for item in schema_def
            if isinstance(item, dict) and item.get("name")
        )
        prompt = f"""Сгенерируй шаблон промпта для экстракции структурированных данных из документа типа «{doc_type_name or 'документ'}».
Поля для извлечения:
{fields_desc}

Шаблон должен:
1. Инструктировать VLM/LLM извлечь JSON с этими полями
2. Содержать placeholder {{schema}} для подстановки JSON-схемы
3. Требовать null для отсутствующих полей
4. Быть на английском (для совместимости с моделями)
5. Выводить ТОЛЬКО валидный JSON

Верни только текст шаблона, без пояснений."""
        resp = llm(prompt)
        text = resp.text if hasattr(resp, "text") else str(resp)
        if text and "{schema}" in text:
            return text.strip()
    except Exception:
        pass
    return generate_prompt_from_fields(schema_def, None)
