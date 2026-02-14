"""Pytest configuration for kotaemon tests.

kotaemon modules rely on theflow settings from root-level flowsettings.py.
This conftest ensures theflow can resolve flowsettings when tests are run
from libs/kotaemon (e.g. `pytest libs/kotaemon`).
"""

import os
import sys
from pathlib import Path

import pytest

_repo_root = Path(__file__).resolve().parents[3]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))
os.environ.setdefault("THEFLOW_SETTINGS_MODULE", "flowsettings")


@pytest.fixture(scope="function")
def mock_google_search(monkeypatch):
    import googlesearch

    def result(*args, **kwargs):
        yield googlesearch.SearchResult(
            url="https://www.cinnamon.is/en/",
            title="Cinnamon AI",
            description="Cinnamon AI is an enterprise AI company.",
        )

    monkeypatch.setattr(googlesearch, "search", result)


def if_haystack_not_installed():
    try:
        import haystack  # noqa: F401
    except ImportError:
        return True
    else:
        return False


def if_sentence_bert_not_installed():
    try:
        import sentence_transformers  # noqa: F401
    except ImportError:
        return True
    else:
        return False


def if_sentence_fastembed_not_installed():
    try:
        import fastembed  # noqa: F401
    except ImportError:
        return True
    else:
        return False


def if_unstructured_pdf_not_installed():
    try:
        import unstructured  # noqa: F401
        from unstructured.partition.pdf import partition_pdf  # noqa: F401
    except ImportError:
        return True
    else:
        return False


def if_cohere_not_installed():
    try:
        import cohere  # noqa: F401
    except ImportError:
        return True
    else:
        return False


def if_llama_cpp_not_installed():
    try:
        import llama_cpp  # noqa: F401
    except ImportError:
        return True
    else:
        return False


def if_voyageai_not_installed():
    try:
        import voyageai  # noqa: F401
    except ImportError:
        return True
    else:
        return False


def if_milvus_not_installed():
    try:
        import milvus_lite  # noqa: F401
        import pymilvus  # noqa: F401
    except ImportError:
        return True
    else:
        return False


def if_qdrant_not_installed():
    try:
        import qdrant_client  # noqa: F401
    except ImportError:
        return True
    else:
        return False


def if_ddgs_not_installed():
    try:
        import ddgs  # noqa: F401
    except ImportError:
        return True
    else:
        return False


skip_when_haystack_not_installed = pytest.mark.skipif(
    if_haystack_not_installed(), reason="Haystack is not installed"
)

skip_when_sentence_bert_not_installed = pytest.mark.skipif(
    if_sentence_bert_not_installed(), reason="SBert is not installed"
)

skip_when_fastembed_not_installed = pytest.mark.skipif(
    if_sentence_fastembed_not_installed(), reason="fastembed is not installed"
)

skip_when_unstructured_pdf_not_installed = pytest.mark.skipif(
    if_unstructured_pdf_not_installed(), reason="unstructured is not installed"
)

skip_when_cohere_not_installed = pytest.mark.skipif(
    if_cohere_not_installed(), reason="cohere is not installed"
)

skip_openai_lc_wrapper_test = pytest.mark.skipif(
    True,
    reason="LangChain/LangGraph tests require API mocks compatible with openai>=2",
)

skip_llama_cpp_not_installed = pytest.mark.skipif(
    if_llama_cpp_not_installed(), reason="llama_cpp is not installed"
)

skip_when_ddgs_not_installed = pytest.mark.skipif(
    if_ddgs_not_installed(), reason="ddgs (duckduckgo-search) is not installed"
)

skip_when_voyageai_not_installed = pytest.mark.skipif(
    if_voyageai_not_installed(), reason="voyageai is not installed"
)

skip_when_milvus_not_installed = pytest.mark.skipif(
    if_milvus_not_installed(),
    reason="Milvus (pymilvus/llama-index-vector-stores-milvus) is not installed",
)

skip_when_qdrant_not_installed = pytest.mark.skipif(
    if_qdrant_not_installed(),
    reason="Qdrant (qdrant-client/llama-index-vector-stores-qdrant) is not installed",
)
