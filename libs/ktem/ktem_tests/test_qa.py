import os
import sys
from pathlib import Path

# ktem modules rely on theflow settings from root-level flowsettings.py.
# Ensure tests can resolve it when running from libs/ktem.
repo_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repo_root))
os.environ.setdefault("THEFLOW_SETTINGS_MODULE", "flowsettings")

from ktem.index.file import FileIndex  # noqa: E402
from ktem.index.file.pipelines import IndexDocumentPipeline  # noqa: E402


def test_file_index_importable_from_public_api():
    """Regression test for legacy import paths in ktem tests."""
    assert FileIndex is not None


def test_index_document_pipeline_settings_have_expected_keys():
    settings = IndexDocumentPipeline.get_user_settings()
    assert "document_recognition_mode" in settings
    assert "vlm_model" in settings
    assert "llm_model" in settings
