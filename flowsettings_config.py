"""Configuration layer using pydantic-settings (replaces python-decouple)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, TypeVar

from pydantic_settings import BaseSettings, SettingsConfigDict

T = TypeVar("T")

# Resolve .env path relative to this file (project root)
_THIS_DIR = Path(__file__).resolve().parent
_ENV_FILE = _THIS_DIR / ".env"


class EnvSettings(BaseSettings):
    """Environment settings loaded from .env and os.environ."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # App
    KH_APP_VERSION: str | None = None
    KH_GRADIO_SHARE: bool = False
    KH_ENABLE_FIRST_SETUP: bool = True
    KH_DEMO_MODE: bool = False
    KH_OLLAMA_URL: str = "http://localhost:11434/v1/"
    KH_SSO_ENABLED: bool = False
    KH_FEATURE_CHAT_SUGGESTION: bool = False
    KH_FEATURE_USER_MANAGEMENT: bool = True
    KH_FEATURE_USER_MANAGEMENT_ADMIN: str = "admin"
    KH_FEATURE_USER_MANAGEMENT_PASSWORD: str = "admin"
    KH_FIRST_SETUP: bool = False
    KH_CHAT_MSG_PLACEHOLDER: str = "Thinking ..."
    KH_CHAT_EMPTY_MSG_PLACEHOLDER: str = "(Sorry, I don't know)"

    # Azure OpenAI
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_CHAT_DEPLOYMENT: str = ""
    AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT: str = ""
    AZURE_DI_ENDPOINT: str = ""
    AZURE_DI_CREDENTIAL: str = ""
    OPENAI_VISION_DEPLOYMENT_NAME: str = "gpt-4o"

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    OPENAI_API_VERSION: str = "2024-02-15-preview"
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDINGS_MODEL: str = "text-embedding-3-large"

    # Other APIs
    GOOGLE_API_KEY: str = "your-key"
    VOYAGE_API_KEY: str = ""
    VOYAGE_EMBEDDINGS_MODEL: str = "voyage-3-large"
    COHERE_API_KEY: str = ""
    MISTRAL_API_KEY: str = "your-key"
    JINA_API_KEY: str = ""
    JINA_URL: str = "https://r.jina.ai/"
    TAVILY_API_KEY: str = ""

    # SearXNG (self-hosted web search, no API key)
    SEARXNG_URL: str = "http://localhost:8080"

    # Database (PostgreSQL обязателен)
    DATABASE_URL: str = ""  # postgresql://user:password@host:5432/dbname; для Docker Compose дефолт: postgresql://kotaemon:kotaemon@postgres:5432/kotaemon

    # Vector store: qdrant | pgvector (pgvector использует DATABASE_URL)
    KH_VECTORSTORE_TYPE: str = "qdrant"
    PG_VECTOR_EMBED_DIM: int = 1536  # размерность эмбеддингов для pgvector
    # HNSW параметры для pgvector (оптимизированы для качества и скорости)
    PG_VECTOR_HNSW_M: int = (
        16  # количество связей на узел (16-64, больше = точнее но медленнее)
    )
    PG_VECTOR_HNSW_EF_CONSTRUCTION: int = 64  # параметр построения индекса (64-200, больше = точнее но медленнее построение)
    PG_VECTOR_HNSW_EF_SEARCH: int = (
        40  # параметр поиска (40-200, больше = точнее но медленнее запросы)
    )

    # Qdrant
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    QDRANT_PATH: str = ""  # local path for file mode (dev without server)
    QDRANT_ENABLE_HYBRID: bool = False  # hybrid search (dense + sparse vectors)
    QDRANT_FASTEMBED_SPARSE_MODEL: str = ""  # e.g. "Qdrant/bm25"

    # Local / Ollama
    LOCAL_MODEL: str = ""
    LOCAL_MODEL_EMBEDDINGS: str = "nomic-embed-text"
    OLLAMA_RERANKER_MODEL: str = "qwen3-reranker"
    TORCH_DEVICE: str = "cuda"  # cuda | cpu | cu121 (Docling/Unstructured)

    # GraphRAG
    USE_LIGHTRAG: bool = True
    USE_NANO_GRAPHRAG: bool = True
    USE_MS_GRAPHRAG: bool = True
    USE_GLOBAL_GRAPHRAG: bool = True
    USE_CUSTOMIZED_GRAPHRAG_SETTING: str = "value"
    USE_MULTIMODAL: bool = False
    USE_LOW_LLM_REQUESTS: bool = (
        True  # Выкл LLM relevant scoring по умолчанию — скорость без потери качества
    )

    # RAG quality defaults (оптимизация точности и скорости чата)
    MAX_CONTEXT_LENGTH: int = 64000
    MAX_TABLE_COUNT: int = 15
    NUM_RETRIEVAL_DEFAULT: int = 20
    PRIORITIZE_TABLE_DEFAULT: bool = True
    ENABLE_PRE_AGGREGATION: bool = True  # Извлечение агрегатов из таблиц при индексации

    # Unified upload and background indexing
    ENABLE_UNIFIED_UPLOAD: bool = True
    ENABLE_BACKGROUND_INDEXING: bool = True

    # API for external agents (OpenClaw, etc.)
    API_SECRET_KEY: str = ""

    # Document classification and routing
    ENABLE_DOCUMENT_CLASSIFICATION: bool = True
    ENABLE_VLM_DOCUMENT_CLASSIFICATION: bool = (
        False  # VLM-based (when True) vs path heuristic
    )
    ENABLE_STRUCTURED_EXTRACTION: bool = (
        False  # Type-specific VLM extraction into structured_data
    )

    # Secret storage (optional): ключ для шифрования API-ключей в БД и application_settings.json
    KH_ENCRYPTION_KEY: str = ""

    # Other
    N_PROMPT_OPT_EXAMPLES: int = 3
    HF_SPACE_URL: str = ""
    PDF_SERVICES_CLIENT_ID: str = ""
    PDF_SERVICES_CLIENT_SECRET: str = ""
    PDF_LOADER_DPI: int = 40
    PDFJS_VERSION_DIST: str = "pdfjs-4.0.379-dist"
    PDFJS_PREBUILT_DIR: str = ""
    CONTEXT_RELEVANT_WARNING_SCORE: float = 0.5


_settings_instance: EnvSettings | None = None


def _get_settings() -> EnvSettings:
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = EnvSettings()
    return _settings_instance


def config(
    key: str,
    default: Any = None,
    cast: type[T] | None = None,
) -> Any:
    """Compatibility layer for python-decouple config().

    Reads from pydantic-settings (env) with fallback to os.environ.
    """
    s = _get_settings()
    key_normalized = key.upper().replace("-", "_")
    try:
        val = getattr(s, key_normalized, None)
    except AttributeError:
        val = None
    if val is None or (isinstance(val, str) and val == "" and default is not None):
        env_val = os.getenv(key, default)
        if env_val is not None:
            val = env_val
        elif val is None:
            val = default
    if cast is not None and val is not None:
        if cast is bool:
            if isinstance(val, bool):
                return val
            return str(val).strip().lower() in ("1", "true", "yes", "on")
        return cast(val)  # type: ignore[call-arg]
    return val
