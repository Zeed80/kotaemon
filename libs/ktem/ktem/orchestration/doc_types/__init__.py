"""Реестр типов документов (базовые + пользовательские)."""

from .generator import (
    create_schema_from_def,
    generate_prompt_from_fields,
)
from .registry import (
    DOC_TYPE_DISPLAY_NAMES,
    DOC_TYPES,
    get_display_name,
    get_doc_type_choices,
)

__all__ = [
    "DOC_TYPES",
    "DOC_TYPE_DISPLAY_NAMES",
    "create_schema_from_def",
    "generate_prompt_from_fields",
    "get_display_name",
    "get_doc_type_choices",
]
