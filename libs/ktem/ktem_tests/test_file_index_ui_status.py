from ktem.index.file.ui import (
    _format_quick_upload_status,
    _format_upload_runtime_info,
    _read_index_runtime_settings,
)


def test_read_index_runtime_settings_uses_prefix():
    settings = {
        "index.options.1.document_recognition_mode": "vlm",
        "index.options.1.vlm_model": "qwen3-vl:8b",
        "index.options.1.llm_model": "",
        "index.options.2.document_recognition_mode": "ocr",
    }
    runtime = _read_index_runtime_settings(settings, 1)
    assert runtime["document_recognition_mode"] == "vlm"
    assert runtime["vlm_model"] == "qwen3-vl:8b"
    assert runtime["llm_model"] == ""


def test_format_quick_upload_status():
    assert "No files were indexed" in _format_quick_upload_status([])
    assert "1 file indexed" in _format_quick_upload_status(["a"])
    assert "2 files indexed" in _format_quick_upload_status(["a", "b"])


def test_format_upload_runtime_info_contains_mode_and_id():
    info = _format_upload_runtime_info(
        {
            "document_recognition_mode": "vlm",
            "vlm_model": "qwen3-vl:8b",
            "llm_model": "",
        },
        "abc123",
    )
    assert "ingestion_id=abc123" in info
    assert "document_recognition_mode=vlm" in info
    assert "vlm_model=qwen3-vl:8b" in info
