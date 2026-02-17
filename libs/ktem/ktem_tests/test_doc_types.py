"""Тесты для doc_types (реестр, генератор)."""

import pytest

from ktem.orchestration.doc_types import (
    DOC_TYPE_DISPLAY_NAMES,
    DOC_TYPES,
    create_schema_from_def,
    generate_prompt_from_fields,
    get_display_name,
    get_doc_type_choices,
)
from ktem.orchestration.graph_builder import (
    build_document_links,
    extract_links_from_structured_data,
)


def test_doc_types_constants():
    """Проверка констант DOC_TYPES и DOC_TYPE_DISPLAY_NAMES."""
    assert "invoice" in DOC_TYPES
    assert "unknown" in DOC_TYPES
    assert DOC_TYPE_DISPLAY_NAMES["invoice"] == "Счёт"
    assert DOC_TYPE_DISPLAY_NAMES["letter"] == "Письмо"


def test_get_doc_type_choices():
    """Проверка get_doc_type_choices."""
    choices = get_doc_type_choices()
    assert len(choices) >= len(DOC_TYPES)
    codes = [c[1] for c in choices]
    assert "invoice" in codes
    assert "unknown" in codes


def test_get_display_name_builtin():
    """Проверка get_display_name для базовых типов."""
    assert get_display_name("invoice") == "Счёт"
    assert get_display_name("unknown") == "Неизвестный"
    assert get_display_name("nonexistent") == "nonexistent"


def test_create_schema_from_def():
    """Проверка создания Pydantic-модели из schema_def."""
    schema_def = [
        {"name": "title", "type": "str", "description": "Заголовок"},
        {"name": "count", "type": "int", "description": "Количество"},
    ]
    model = create_schema_from_def("TestSchema", schema_def)
    assert model is not None
    inst = model(title="Test", count=10)  # type: ignore[call-arg]
    assert getattr(inst, "title", None) == "Test"
    assert getattr(inst, "count", None) == 10


def test_create_schema_from_def_empty():
    """Проверка create_schema_from_def с пустым schema_def."""
    model = create_schema_from_def("EmptySchema", [])
    assert model is not None
    inst = model()
    assert inst.model_dump() == {}


def test_generate_prompt_from_fields():
    """Проверка генерации промпта по полям."""
    schema_def = [
        {"name": "number", "type": "str", "description": "Номер"},
    ]
    prompt = generate_prompt_from_fields(schema_def)
    assert "number" in prompt
    assert "{schema}" in prompt or "number" in prompt


def test_extract_links_from_structured_data():
    """Проверка извлечения ссылок из structured_data."""
    data = {"invoice_number": "INV-001", "date": "2024-01-01"}
    links = extract_links_from_structured_data(data, "invoice")
    assert len(links) >= 1
    assert any(ln.get("target_ref") == "INV-001" for ln in links)


def test_build_document_links():
    """Проверка build_document_links."""
    links = build_document_links(
        source_doc_id="src-1",
        structured_data={"invoice_number": "INV-002"},
        doc_type="invoice",
    )
    assert len(links) >= 1
    assert links[0]["source_doc_id"] == "src-1"
    assert "target_ref" in links[0]


def test_index_document_pipeline_has_doc_type_override():
    """Проверка, что IndexDocumentPipeline имеет doc_type_override в настройках."""
    pytest.importorskip("psycopg")
    from ktem.index.file.pipelines import IndexDocumentPipeline

    settings = IndexDocumentPipeline.get_user_settings()
    assert "doc_type_override" in settings
