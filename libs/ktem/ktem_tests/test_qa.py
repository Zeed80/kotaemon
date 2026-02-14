from ktem.index.file import FileIndex
from ktem.index.file.pipelines import IndexDocumentPipeline


def test_file_index_importable_from_public_api():
    """Regression test for legacy import paths in ktem tests."""
    assert FileIndex is not None


def test_index_document_pipeline_settings_have_expected_keys():
    settings = IndexDocumentPipeline.get_user_settings()
    assert "document_recognition_mode" in settings
    assert "vlm_model" in settings
    assert "llm_model" in settings
