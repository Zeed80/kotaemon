import os
from importlib.metadata import version
from inspect import currentframe, getframeinfo
from pathlib import Path

from theflow.settings.default import *  # noqa

from flowsettings_config import config
from ktem.utils.lang import SUPPORTED_LANGUAGE_MAP

cur_frame = currentframe()
if cur_frame is None:
    raise ValueError("Cannot get the current frame.")
this_file = getframeinfo(cur_frame).filename
this_dir = Path(this_file).parent

# change this if your app use a different name
KH_PACKAGE_NAME = "kotaemon_app"

KH_APP_VERSION = config("KH_APP_VERSION", None)
if not KH_APP_VERSION:
    try:
        # Caution: This might produce the wrong version
        # https://stackoverflow.com/a/59533071
        KH_APP_VERSION = version(KH_PACKAGE_NAME)
    except Exception:
        KH_APP_VERSION = "local"

KH_GRADIO_SHARE = config("KH_GRADIO_SHARE", default=False, cast=bool)
KH_ENABLE_FIRST_SETUP = config("KH_ENABLE_FIRST_SETUP", default=True, cast=bool)
KH_DEMO_MODE = config("KH_DEMO_MODE", default=False, cast=bool)
KH_OLLAMA_URL = config("KH_OLLAMA_URL", default="http://localhost:11434/v1/")

# App can be ran from anywhere and it's not trivial to decide where to store app data.
# So let's use the same directory as the flowsetting.py file.
KH_APP_DATA_DIR = this_dir / "ktem_app_data"
KH_APP_DATA_EXISTS = KH_APP_DATA_DIR.exists()
KH_APP_DATA_DIR.mkdir(parents=True, exist_ok=True)

# User data directory
KH_USER_DATA_DIR = KH_APP_DATA_DIR / "user_data"
KH_USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

# markdown output directory
KH_MARKDOWN_OUTPUT_DIR = KH_APP_DATA_DIR / "markdown_cache_dir"
KH_MARKDOWN_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# chunks output directory
KH_CHUNKS_OUTPUT_DIR = KH_APP_DATA_DIR / "chunks_cache_dir"
KH_CHUNKS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# zip output directory
KH_ZIP_OUTPUT_DIR = KH_APP_DATA_DIR / "zip_cache_dir"
KH_ZIP_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# zip input directory
KH_ZIP_INPUT_DIR = KH_APP_DATA_DIR / "zip_cache_dir_in"
KH_ZIP_INPUT_DIR.mkdir(parents=True, exist_ok=True)

# HF models can be big, let's store them in the app data directory so that it's easier
# for users to manage their storage.
# ref: https://huggingface.co/docs/huggingface_hub/en/guides/manage-cache
os.environ["HF_HOME"] = str(KH_APP_DATA_DIR / "huggingface")
os.environ["HF_HUB_CACHE"] = str(KH_APP_DATA_DIR / "huggingface")

# doc directory
KH_DOC_DIR = this_dir / "docs"


def get_application_setting(key: str, default: str | int | float | bool | None = None):  # noqa: ANN201
    """Взять значение настройки приложения: сначала из application_settings.json, иначе default.
    Используется в рантайме (чаты, пайплайны), при построении векторного хранилища и т.д.
    Чувствительные значения (api_key и т.п.) расшифровываются при чтении.
    """
    path = KH_APP_DATA_DIR / "application_settings.json"
    if not path.exists():
        return default
    try:
        import json

        from ktem.utils.secret_storage import decrypt_value

        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if key in data:
            val = data[key]
            if isinstance(val, str) and (
                "api_key" in key or "secret" in key or "password" in key
            ):
                val = decrypt_value(val)
            return val
    except Exception:  # noqa: S110
        pass
    return default


KH_MODE = "dev"
KH_SSO_ENABLED = config("KH_SSO_ENABLED", default=False, cast=bool)

KH_FEATURE_CHAT_SUGGESTION = config(
    "KH_FEATURE_CHAT_SUGGESTION", default=False, cast=bool
)
KH_FEATURE_USER_MANAGEMENT = config(
    "KH_FEATURE_USER_MANAGEMENT", default=True, cast=bool
)
KH_USER_CAN_SEE_PUBLIC = None
KH_FEATURE_USER_MANAGEMENT_ADMIN = str(
    config("KH_FEATURE_USER_MANAGEMENT_ADMIN", default="admin")
)
KH_FEATURE_USER_MANAGEMENT_PASSWORD = str(
    config("KH_FEATURE_USER_MANAGEMENT_PASSWORD", default="admin")
)
KH_ENABLE_ALEMBIC = False
# PostgreSQL: обязательный DATABASE_URL в .env (postgresql:// или postgresql+psycopg://).
# Для Docker Compose используется дефолтное значение postgresql://kotaemon:password@postgres:5432/kotaemon
_database_url = config("DATABASE_URL", default="").strip()
if not _database_url:
    # Дефолтное значение для Docker Compose (если не задано в .env)
    _database_url = "postgresql://kotaemon:kotaemon@postgres:5432/kotaemon"
if _database_url.startswith("postgresql://") and "+" not in _database_url.split(":")[0]:
    # Явный драйвер psycopg (v3) для SQLAlchemy 2
    _database_url = _database_url.replace("postgresql://", "postgresql+psycopg://", 1)
KH_DATABASE = _database_url
KH_FILESTORAGE_PATH = str(KH_USER_DATA_DIR / "files")
# Web search: Tavily (if key) -> SearXNG (self-hosted, no key) for locality/privacy
KH_WEB_SEARCH_BACKEND = (
    "kotaemon.indices.retrievers.tavily_web_search.WebSearch"
    if config("TAVILY_API_KEY", default="")
    else "kotaemon.indices.retrievers.searxng_web_search.WebSearch"
)

KH_DOCSTORE = {
    # "__type__": "kotaemon.storages.ElasticsearchDocumentStore",
    # "__type__": "kotaemon.storages.SimpleFileDocumentStore",
    "__type__": "kotaemon.storages.LanceDBDocumentStore",
    "path": str(KH_USER_DATA_DIR / "docstore"),
}
_qdrant_path = config("QDRANT_PATH", default="")
_kh_vectorstore_type = (
    (config("KH_VECTORSTORE_TYPE", default="qdrant") or "qdrant").strip().lower()
)
_pg_vector_embed_dim = int(config("PG_VECTOR_EMBED_DIM", default="1536") or "1536")
_pg_vector_hnsw_m = int(config("PG_VECTOR_HNSW_M", default="16") or "16")
_pg_vector_hnsw_ef_construction = int(
    config("PG_VECTOR_HNSW_EF_CONSTRUCTION", default="64") or "64"
)
_pg_vector_hnsw_ef_search = int(
    config("PG_VECTOR_HNSW_EF_SEARCH", default="40") or "40"
)

# Кэш для автоматически определённой размерности эмбеддингов
_auto_embed_dim_cache: int | None = None


def _get_default_embedding_dimension() -> int | None:
    """Автоматически определить размерность модели эмбеддингов по умолчанию.

    Returns:
        Размерность эмбеддингов или None, если не удалось определить.
    """
    global _auto_embed_dim_cache
    if _auto_embed_dim_cache is not None:
        return _auto_embed_dim_cache

    try:
        # Пытаемся получить менеджер эмбеддингов (может быть не инициализирован на момент загрузки модуля)
        from ktem.embeddings.manager import embedding_models_manager

        if not hasattr(embedding_models_manager, "get_default"):
            return None

        default_embedding = embedding_models_manager.get_default()
        if default_embedding is None:
            return None

        # Определяем размерность через тестовый запрос
        result = default_embedding(["test"])
        if result and len(result) > 0 and hasattr(result[0], "embedding"):
            _auto_embed_dim_cache = len(result[0].embedding)
            import logging

            logger = logging.getLogger(__name__)
            logger.info(
                "Автоматически определена размерность эмбеддингов: %d (из модели по умолчанию)",
                _auto_embed_dim_cache,
            )
            return _auto_embed_dim_cache
    except Exception as e:
        # Если менеджер ещё не инициализирован или произошла ошибка, возвращаем None
        import logging

        logger = logging.getLogger(__name__)
        logger.debug(
            "Не удалось автоматически определить размерность эмбеддингов: %s", e
        )

    return None


def _parse_bool(val: str | bool) -> bool:
    if isinstance(val, bool):
        return val
    return str(val).lower() in ("true", "1", "yes")


_qdrant_enable_hybrid = _parse_bool(config("QDRANT_ENABLE_HYBRID", default="false"))
_qdrant_sparse_model = config("QDRANT_FASTEMBED_SPARSE_MODEL", default="") or None


def _qdrant_url() -> str:
    """Qdrant URL: config + os.getenv fallback for Docker."""
    val = config("QDRANT_URL", default="http://localhost:6333")
    if not val or not str(val).strip():
        val = os.getenv("QDRANT_URL", "http://localhost:6333")
    return str(val).strip()


def _qdrant_api_key() -> str | None:
    """Qdrant API key; use empty string for local (LlamaIndex rejects None)."""
    val = config("QDRANT_API_KEY", default="") or ""
    return str(val).strip() or None


def _build_qdrant_config() -> dict:
    """Собрать конфиг только Qdrant (application_settings → .env)."""
    path_val = get_application_setting("qdrant_path") or _qdrant_path
    enable_hybrid = get_application_setting("qdrant_enable_hybrid")
    if enable_hybrid is None:
        enable_hybrid = _qdrant_enable_hybrid
    elif isinstance(enable_hybrid, str):
        enable_hybrid = _parse_bool(enable_hybrid)
    sparse_model = (
        get_application_setting("qdrant_sparse_model") or _qdrant_sparse_model or ""
    )
    sparse_model = (sparse_model or "") or None
    url_val = get_application_setting("qdrant_url") or _qdrant_url()
    url_val = str(url_val or "").strip() or _qdrant_url()
    api_key_val = get_application_setting("qdrant_api_key")
    if api_key_val is None:
        api_key_val = _qdrant_api_key() or ""
    else:
        api_key_val = str(api_key_val or "").strip() or ""
    if not path_val and url_val.strip().lower().startswith("http:"):
        api_key_val = ""
    return {
        "__type__": "kotaemon.storages.QdrantVectorStore",
        "collection_name": "default",
        "enable_hybrid": bool(enable_hybrid),
        "fastembed_sparse_model": sparse_model,
        **(
            {"path": str(path_val)}
            if path_val
            else {"url": url_val, "api_key": api_key_val or ""}
        ),
    }


def _build_pgvector_config() -> dict:
    """Собрать конфиг только Pgvector (требуется _database_url) с оптимальными HNSW параметрами."""
    embed_dim = get_application_setting("pg_vector_embed_dim")
    if embed_dim is None or embed_dim == 0:
        # Если размерность не задана явно (None или 0), пытаемся определить автоматически из модели эмбеддингов
        auto_dim = _get_default_embedding_dimension()
        if auto_dim is not None:
            embed_dim = auto_dim
        else:
            # Если автоматическое определение не удалось, используем дефолт из .env
            embed_dim = _pg_vector_embed_dim
    else:
        # Используем явно заданное значение
        embed_dim = int(embed_dim) if embed_dim else _pg_vector_embed_dim
    # HNSW параметры из настроек или дефолты (оптимизированы для качества и скорости)
    hnsw_m = get_application_setting("pg_vector_hnsw_m")
    if hnsw_m is None:
        hnsw_m = _pg_vector_hnsw_m
    else:
        hnsw_m = int(hnsw_m) if hnsw_m else _pg_vector_hnsw_m
    hnsw_ef_construction = get_application_setting("pg_vector_hnsw_ef_construction")
    if hnsw_ef_construction is None:
        hnsw_ef_construction = _pg_vector_hnsw_ef_construction
    else:
        hnsw_ef_construction = (
            int(hnsw_ef_construction)
            if hnsw_ef_construction
            else _pg_vector_hnsw_ef_construction
        )
    hnsw_ef_search = get_application_setting("pg_vector_hnsw_ef_search")
    if hnsw_ef_search is None:
        hnsw_ef_search = _pg_vector_hnsw_ef_search
    else:
        hnsw_ef_search = (
            int(hnsw_ef_search) if hnsw_ef_search else _pg_vector_hnsw_ef_search
        )
    return {
        "__type__": "kotaemon.storages.PgvectorVectorStore",
        "collection_name": "default",
        "connection_string": _database_url,
        "embed_dim": embed_dim,
        "schema_name": "public",
        "perform_setup": True,
        "hnsw_kwargs": {
            "hnsw_m": hnsw_m,
            "hnsw_ef_construction": hnsw_ef_construction,
            "hnsw_ef_search": hnsw_ef_search,
            "hnsw_dist_method": "vector_cosine_ops",  # косинусное расстояние (оптимально для эмбеддингов)
        },
    }


def _build_vectorstore_config() -> dict:
    """Собрать конфиг векторного хранилища: Qdrant, Pgvector или оба (application_settings → .env)."""
    vs_type = get_application_setting("vectorstore_type") or _kh_vectorstore_type
    if vs_type == "pgvector" and _database_url:
        return _build_pgvector_config()
    if vs_type == "qdrant_and_pgvector":
        store_configs = [_build_qdrant_config()]
        if _database_url:
            store_configs.append(_build_pgvector_config())
        return {
            "__type__": "kotaemon.storages.CompositeVectorStore",
            "collection_name": "default",
            "store_configs": store_configs,
        }
    return _build_qdrant_config()


KH_VECTORSTORE = _build_vectorstore_config()
KH_LLMS = {}
KH_EMBEDDINGS = {}
KH_RERANKINGS = {}

# populate options from config
if config("AZURE_OPENAI_API_KEY", default="") and config(
    "AZURE_OPENAI_ENDPOINT", default=""
):
    if config("AZURE_OPENAI_CHAT_DEPLOYMENT", default=""):
        KH_LLMS["azure"] = {
            "spec": {
                "__type__": "kotaemon.llms.AzureChatOpenAI",
                "temperature": 0,
                "azure_endpoint": config("AZURE_OPENAI_ENDPOINT", default=""),
                "api_key": config("AZURE_OPENAI_API_KEY", default=""),
                "api_version": config("OPENAI_API_VERSION", default="")
                or "2024-02-15-preview",
                "azure_deployment": config("AZURE_OPENAI_CHAT_DEPLOYMENT", default=""),
                "timeout": 20,
            },
            "default": False,
        }
    if config("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT", default=""):
        KH_EMBEDDINGS["azure"] = {
            "spec": {
                "__type__": "kotaemon.embeddings.AzureOpenAIEmbeddings",
                "azure_endpoint": config("AZURE_OPENAI_ENDPOINT", default=""),
                "api_key": config("AZURE_OPENAI_API_KEY", default=""),
                "api_version": config("OPENAI_API_VERSION", default="")
                or "2024-02-15-preview",
                "azure_deployment": config(
                    "AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT", default=""
                ),
                "timeout": 10,
            },
            "default": False,
        }

OPENAI_DEFAULT = "<YOUR_OPENAI_KEY>"
OPENAI_API_KEY = config("OPENAI_API_KEY", default=OPENAI_DEFAULT)
GOOGLE_API_KEY = config("GOOGLE_API_KEY", default="your-key")
VOYAGE_API_KEY = config("VOYAGE_API_KEY", default="")
IS_OPENAI_DEFAULT = len(OPENAI_API_KEY) > 0 and OPENAI_API_KEY != OPENAI_DEFAULT

if OPENAI_API_KEY:
    _openai_default = IS_OPENAI_DEFAULT and not VOYAGE_API_KEY
    KH_LLMS["openai"] = {
        "spec": {
            "__type__": "kotaemon.llms.ChatOpenAI",
            "temperature": 0,
            "base_url": config("OPENAI_API_BASE", default="")
            or "https://api.openai.com/v1",
            "api_key": OPENAI_API_KEY,
            "model": config("OPENAI_CHAT_MODEL", default="gpt-4o-mini"),
            "timeout": 20,
        },
        "default": IS_OPENAI_DEFAULT,
    }
    KH_EMBEDDINGS["openai"] = {
        "spec": {
            "__type__": "kotaemon.embeddings.OpenAIEmbeddings",
            "base_url": config("OPENAI_API_BASE", default="https://api.openai.com/v1"),
            "api_key": OPENAI_API_KEY,
            "model": config(
                "OPENAI_EMBEDDINGS_MODEL", default="text-embedding-3-large"
            ),
            "timeout": 10,
            "context_length": 8191,
        },
        "default": _openai_default,
    }

if VOYAGE_API_KEY:
    KH_EMBEDDINGS["voyageai"] = {
        "spec": {
            "__type__": "kotaemon.embeddings.VoyageAIEmbeddings",
            "api_key": VOYAGE_API_KEY,
            "model": config("VOYAGE_EMBEDDINGS_MODEL", default="voyage-3-large"),
        },
        "default": True,
    }
    KH_RERANKINGS["voyageai"] = {
        "spec": {
            "__type__": "kotaemon.rerankings.VoyageAIReranking",
            "model_name": "rerank-2",
            "api_key": VOYAGE_API_KEY,
        },
        "default": True,
    }

if config("LOCAL_MODEL", default=""):
    KH_LLMS["ollama"] = {
        "spec": {
            "__type__": "kotaemon.llms.ChatOpenAI",
            "base_url": KH_OLLAMA_URL,
            "model": config("LOCAL_MODEL", default="qwen2.5:7b"),
            "api_key": "ollama",
        },
        "default": False,
    }
    KH_LLMS["ollama-long-context"] = {
        "spec": {
            "__type__": "kotaemon.llms.LCOllamaChat",
            "base_url": KH_OLLAMA_URL.replace("v1/", ""),
            "model": config("LOCAL_MODEL", default="qwen2.5:7b"),
            "num_ctx": 8192,
        },
        "default": False,
    }

    KH_EMBEDDINGS["ollama"] = {
        "spec": {
            "__type__": "kotaemon.embeddings.OpenAIEmbeddings",
            "base_url": KH_OLLAMA_URL,
            "model": config("LOCAL_MODEL_EMBEDDINGS", default="nomic-embed-text"),
            "api_key": "ollama",
        },
        "default": False,
    }
    KH_EMBEDDINGS["fast_embed"] = {
        "spec": {
            "__type__": "kotaemon.embeddings.FastEmbedEmbeddings",
            "model_name": "BAAI/bge-base-en-v1.5",
        },
        "default": False,
    }

# additional LLM configurations
KH_LLMS["claude"] = {
    "spec": {
        "__type__": "kotaemon.llms.chats.LCAnthropicChat",
        "model_name": "claude-3-5-sonnet-20240620",
        "api_key": "your-key",
    },
    "default": False,
}
KH_LLMS["google"] = {
    "spec": {
        "__type__": "kotaemon.llms.chats.LCGeminiChat",
        "model_name": "gemini-1.5-flash",
        "api_key": GOOGLE_API_KEY,
    },
    "default": not IS_OPENAI_DEFAULT,
}
KH_LLMS["groq"] = {
    "spec": {
        "__type__": "kotaemon.llms.ChatOpenAI",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.1-8b-instant",
        "api_key": "your-key",
    },
    "default": False,
}
KH_LLMS["cohere"] = {
    "spec": {
        "__type__": "kotaemon.llms.chats.LCCohereChat",
        "model_name": "command-r-plus-08-2024",
        "api_key": config("COHERE_API_KEY", default="your-key"),
    },
    "default": False,
}
KH_LLMS["mistral"] = {
    "spec": {
        "__type__": "kotaemon.llms.ChatOpenAI",
        "base_url": "https://api.mistral.ai/v1",
        "model": "ministral-8b-latest",
        "api_key": config("MISTRAL_API_KEY", default="your-key"),
    },
    "default": False,
}

# additional embeddings configurations
KH_EMBEDDINGS["cohere"] = {
    "spec": {
        "__type__": "kotaemon.embeddings.LCCohereEmbeddings",
        "model": "embed-multilingual-v3.0",
        "cohere_api_key": config("COHERE_API_KEY", default="your-key"),
        "user_agent": "default",
    },
    "default": False,
}
KH_EMBEDDINGS["google"] = {
    "spec": {
        "__type__": "kotaemon.embeddings.LCGoogleEmbeddings",
        "model": "models/text-embedding-004",
        "google_api_key": GOOGLE_API_KEY,
    },
    "default": not IS_OPENAI_DEFAULT,
}
KH_EMBEDDINGS["mistral"] = {
    "spec": {
        "__type__": "kotaemon.embeddings.LCMistralEmbeddings",
        "model": "mistral-embed",
        "api_key": config("MISTRAL_API_KEY", default="your-key"),
    },
    "default": False,
}
# KH_EMBEDDINGS["huggingface"] = {
#     "spec": {
#         "__type__": "kotaemon.embeddings.LCHuggingFaceEmbeddings",
#         "model_name": "sentence-transformers/all-mpnet-base-v2",
#     },
#     "default": False,
# }

# Offline default: FastEmbed when no OpenAI/Voyage API keys
if not IS_OPENAI_DEFAULT and not VOYAGE_API_KEY:
    KH_EMBEDDINGS["fast_embed"] = {
        "spec": {
            "__type__": "kotaemon.embeddings.FastEmbedEmbeddings",
            "model_name": config(
                "LOCAL_MODEL_EMBEDDINGS", default="BAAI/bge-base-en-v1.5"
            ),
        },
        "default": True,
    }

# default reranking models
KH_RERANKINGS["cohere"] = {
    "spec": {
        "__type__": "kotaemon.rerankings.CohereReranking",
        "model_name": "rerank-multilingual-v2.0",
        "cohere_api_key": config("COHERE_API_KEY", default=""),
    },
    "default": True,
}

# Ollama reranker (qwen3-reranker, bge-reranker-v2-m3 и др.): ollama pull qwen3-reranker
KH_RERANKINGS["ollama"] = {
    "spec": {
        "__type__": "kotaemon.rerankings.OllamaReranking",
        "base_url": KH_OLLAMA_URL,
        "model_name": config("OLLAMA_RERANKER_MODEL", default="qwen3-reranker"),
    },
    "default": False,
}

KH_REASONINGS = [
    "ktem.reasoning.simple.FullQAPipeline",
    "ktem.reasoning.simple.FullDecomposeQAPipeline",
    "ktem.reasoning.react.ReactAgentPipeline",
    "ktem.reasoning.rewoo.RewooAgentPipeline",
]
KH_REASONINGS_USE_MULTIMODAL = config("USE_MULTIMODAL", default=False, cast=bool)
KH_VLM_ENDPOINT = "{0}/openai/deployments/{1}/chat/completions?api-version={2}".format(
    config("AZURE_OPENAI_ENDPOINT", default=""),
    config("OPENAI_VISION_DEPLOYMENT_NAME", default="gpt-4o"),
    config("OPENAI_API_VERSION", default=""),
)

# VLM options for web UI: list of (display_name, value). "default" -> KH_VLM_ENDPOINT
KH_VLM_OPTIONS = [
    ("Default (from OPENAI_VISION_DEPLOYMENT_NAME)", "default"),
]


def get_vlm_endpoint(value: str) -> str:
    """Resolve VLM option value to endpoint URL."""
    if not value or value == "default":
        return KH_VLM_ENDPOINT
    # value can be a full endpoint URL when extended in flowsettings
    if value.startswith("http"):
        return value
    return KH_VLM_ENDPOINT


# Несекретные настройки приложения — редактируются в веб-интерфейсе (Settings → General).
# Значения по умолчанию из .env; после сохранения в UI используются сохранённые (в т.ч. для Ollama reranker).
SETTINGS_APP: dict[str, dict] = {
    "kh_ollama_url": {
        "name": "Ollama API URL",
        "value": config("KH_OLLAMA_URL", default="http://localhost:11434/v1/"),
        "component": "text",
    },
    "ollama_reranker_model": {
        "name": "Ollama reranker model",
        "value": config("OLLAMA_RERANKER_MODEL", default="qwen3-reranker"),
        "component": "dropdown",
        "choices": [],
        "info": "Модель по умолчанию для реранкера Ollama. Список подставляется с сервера Ollama при открытии настроек.",
    },
    "torch_device": {
        "name": "PyTorch device (Unstructured/Docling)",
        "value": config("TORCH_DEVICE", default="cuda"),
        "component": "text",
        "info": "cuda | cpu | cu121 (Docker). По умолчанию GPU.",
    },
    "local_model": {
        "name": "Ollama LLM model (default)",
        "value": config("LOCAL_MODEL", default=""),
        "component": "dropdown",
        "choices": [],
        "info": "Модель по умолчанию для Ollama LLM. Список подставляется с сервера Ollama при открытии настроек.",
    },
    "local_model_embeddings": {
        "name": "Ollama Embedding model (default)",
        "value": config("LOCAL_MODEL_EMBEDDINGS", default="nomic-embed-text"),
        "component": "dropdown",
        "choices": [],
        "info": "Модель эмбеддингов по умолчанию (Ollama). Список подставляется с сервера при открытии настроек.",
    },
    # Векторное хранилище — вступает в силу после перезапуска приложения.
    "vectorstore_type": {
        "name": "Vector store",
        "value": config("KH_VECTORSTORE_TYPE", default="qdrant"),
        "component": "dropdown",
        "choices": [
            ("Qdrant only", "qdrant"),
            ("PostgreSQL (pgvector) only", "pgvector"),
            ("Qdrant + pgvector (parallel, better quality)", "qdrant_and_pgvector"),
        ],
        "info": "Один бэкенд или оба: при «Qdrant + pgvector» индексация пишет в оба, поиск объединяет результаты (качество и скорость).",
    },
    "pg_vector_embed_dim": {
        "name": "pgvector: embedding dimension",
        "value": int(config("PG_VECTOR_EMBED_DIM", default="1536") or "1536"),
        "component": "number",
        "info": "Размерность эмбеддингов для pgvector (должна совпадать с моделью). Если оставить значение по умолчанию (1536) или 0, размерность будет определена автоматически из модели эмбеддингов по умолчанию при создании конфигурации. Рекомендуется задать явно для вашей модели (например, 4096 для qwen3-embedding).",
    },
    "pg_vector_hnsw_m": {
        "name": "pgvector HNSW: m (connections per node)",
        "value": int(config("PG_VECTOR_HNSW_M", default="16") or "16"),
        "component": "number",
        "info": "Количество связей на узел (16-64). Больше = точнее, но медленнее и больше памяти. 16 оптимально для большинства случаев.",
    },
    "pg_vector_hnsw_ef_construction": {
        "name": "pgvector HNSW: ef_construction",
        "value": int(config("PG_VECTOR_HNSW_EF_CONSTRUCTION", default="64") or "64"),
        "component": "number",
        "info": "Параметр построения индекса (64-200). Больше = точнее индекс, но медленнее построение. 64 оптимально.",
    },
    "pg_vector_hnsw_ef_search": {
        "name": "pgvector HNSW: ef_search",
        "value": int(config("PG_VECTOR_HNSW_EF_SEARCH", default="40") or "40"),
        "component": "number",
        "info": "Параметр поиска (40-200). Больше = точнее результаты, но медленнее запросы. 40 оптимально для баланса скорости и качества.",
    },
    # Qdrant (используется при qdrant или qdrant_and_pgvector)
    "qdrant_url": {
        "name": "Qdrant URL",
        "value": config("QDRANT_URL", default="http://localhost:6333"),
        "component": "text",
    },
    "qdrant_api_key": {
        "name": "Qdrant API key",
        "value": config("QDRANT_API_KEY", default=""),
        "component": "password",
    },
    "qdrant_path": {
        "name": "Qdrant local path (overrides URL if set)",
        "value": config("QDRANT_PATH", default=""),
        "component": "text",
    },
    "qdrant_enable_hybrid": {
        "name": "Qdrant hybrid search (dense + sparse)",
        "value": _parse_bool(config("QDRANT_ENABLE_HYBRID", default="false")),
        "component": "checkbox",
    },
    "qdrant_sparse_model": {
        "name": "Qdrant sparse model (e.g. Qdrant/bm25)",
        "value": config("QDRANT_FASTEMBED_SPARSE_MODEL", default="") or "",
        "component": "text",
    },
    "qdrant_embed_dim": {
        "name": "Qdrant: embedding dimension (informational)",
        "value": int(config("QDRANT_EMBED_DIM", default="0") or "0"),
        "component": "number",
        "info": "Размерность эмбеддингов для Qdrant (информационная настройка). Qdrant определяет размерность автоматически при создании коллекции на основе первого добавленного вектора. Эта настройка используется только для информации и предварительного создания коллекций. Если оставить 0, размерность будет определена автоматически из модели эмбеддингов при первом добавлении векторов.",
    },
    # Флаги индексов: отображаются в UI и сохраняются; для применения нужна перезагрузка приложения.
    "use_lightrag": {
        "name": "Enable LightRAG index",
        "value": config("USE_LIGHTRAG", default=True, cast=bool),
        "component": "checkbox",
    },
    "use_nano_graphrag": {
        "name": "Enable Nano GraphRAG index",
        "value": config("USE_NANO_GRAPHRAG", default=True, cast=bool),
        "component": "checkbox",
    },
    "use_ms_graphrag": {
        "name": "Enable MS GraphRAG index",
        "value": config("USE_MS_GRAPHRAG", default=True, cast=bool),
        "component": "checkbox",
    },
    "use_global_graphrag": {
        "name": "Enable Global GraphRAG index",
        "value": config("USE_GLOBAL_GRAPHRAG", default=True, cast=bool),
        "component": "checkbox",
    },
    "enable_document_classification": {
        "name": "Document classification (по типу при индексации)",
        "value": config("ENABLE_DOCUMENT_CLASSIFICATION", default=True, cast=bool),
        "component": "checkbox",
        "info": "Определять тип документа (счёт, письмо, чертёж и т.д.) по имени/пути при индексации.",
    },
    "enable_vlm_document_classification": {
        "name": "VLM document classification",
        "value": config("ENABLE_VLM_DOCUMENT_CLASSIFICATION", default=False, cast=bool),
        "component": "checkbox",
        "info": "Использовать VLM для классификации (точнее, но нужен KH_VLM_ENDPOINT).",
    },
    "enable_structured_extraction": {
        "name": "Structured extraction (VLM)",
        "value": config("ENABLE_STRUCTURED_EXTRACTION", default=False, cast=bool),
        "component": "checkbox",
        "info": "Извлекать структурированные данные (реквизиты, элементы чертежа) через VLM в Source.note.",
    },
    "kh_chat_msg_placeholder": {
        "name": "Chat thinking placeholder",
        "value": config("KH_CHAT_MSG_PLACEHOLDER", default="Thinking ..."),
        "component": "text",
    },
    "kh_chat_empty_msg_placeholder": {
        "name": "Chat empty answer placeholder",
        "value": config(
            "KH_CHAT_EMPTY_MSG_PLACEHOLDER", default="(Sorry, I don't know)"
        ),
        "component": "text",
    },
    "n_prompt_opt_examples": {
        "name": "Few-shot rewrite: number of examples (k)",
        "value": config("N_PROMPT_OPT_EXAMPLES", default=3, cast=int),
        "component": "number",
    },
    # API Keys и сервисы — записываются в .env при сохранении.
    "openai_api_key": {
        "name": "OpenAI API Key",
        "value": config("OPENAI_API_KEY", default=""),
        "component": "password",
    },
    "openai_api_base": {
        "name": "OpenAI API Base URL",
        "value": config("OPENAI_API_BASE", default="https://api.openai.com/v1"),
        "component": "text",
    },
    "openai_chat_model": {
        "name": "OpenAI Chat Model",
        "value": config("OPENAI_CHAT_MODEL", default="gpt-4o-mini"),
        "component": "text",
    },
    "openai_embeddings_model": {
        "name": "OpenAI Embeddings Model",
        "value": config("OPENAI_EMBEDDINGS_MODEL", default="text-embedding-3-large"),
        "component": "text",
    },
    "google_api_key": {
        "name": "Google API Key (Gemini)",
        "value": config("GOOGLE_API_KEY", default=""),
        "component": "password",
    },
    "cohere_api_key": {
        "name": "Cohere API Key",
        "value": config("COHERE_API_KEY", default=""),
        "component": "password",
    },
    "voyage_api_key": {
        "name": "VoyageAI API Key",
        "value": config("VOYAGE_API_KEY", default=""),
        "component": "password",
    },
    "mistral_api_key": {
        "name": "Mistral API Key",
        "value": config("MISTRAL_API_KEY", default=""),
        "component": "password",
    },
    "tavily_api_key": {
        "name": "Tavily API Key (web search)",
        "value": config("TAVILY_API_KEY", default=""),
        "component": "password",
    },
    "azure_openai_endpoint": {
        "name": "Azure OpenAI Endpoint",
        "value": config("AZURE_OPENAI_ENDPOINT", default=""),
        "component": "text",
    },
    "azure_openai_api_key": {
        "name": "Azure OpenAI API Key",
        "value": config("AZURE_OPENAI_API_KEY", default=""),
        "component": "password",
    },
    "azure_openai_chat_deployment": {
        "name": "Azure OpenAI Chat Deployment",
        "value": config("AZURE_OPENAI_CHAT_DEPLOYMENT", default=""),
        "component": "text",
    },
    "azure_openai_embeddings_deployment": {
        "name": "Azure OpenAI Embeddings Deployment",
        "value": config("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT", default=""),
        "component": "text",
    },
    "openai_api_version": {
        "name": "OpenAI API Version (Azure)",
        "value": config("OPENAI_API_VERSION", default="2024-02-15-preview"),
        "component": "text",
    },
    "searxng_url": {
        "name": "SearXNG URL (web search, self-hosted)",
        "value": config("SEARXNG_URL", default="http://localhost:8080"),
        "component": "text",
    },
}


SETTINGS_REASONING = {
    "use": {
        "name": "Reasoning options",
        "value": None,
        "choices": [],
        "component": "radio",
    },
    "lang": {
        "name": "Language",
        "value": "en",
        "choices": [(lang, code) for code, lang in SUPPORTED_LANGUAGE_MAP.items()],
        "component": "dropdown",
    },
    "max_context_length": {
        "name": "Max context length (LLM)",
        "value": config("MAX_CONTEXT_LENGTH", default=64000, cast=int),
        "component": "number",
        "info": "Макс. токенов контекста для LLM (32k–128k в зависимости от модели).",
    },
    "max_table_count": {
        "name": "Max tables in context",
        "value": config("MAX_TABLE_COUNT", default=15, cast=int),
        "component": "number",
        "info": "Макс. число таблиц в контексте LLM. Увеличьте для документов с множеством таблиц.",
    },
}

USE_GLOBAL_GRAPHRAG = config("USE_GLOBAL_GRAPHRAG", default=True, cast=bool)
USE_NANO_GRAPHRAG = config("USE_NANO_GRAPHRAG", default=True, cast=bool)
USE_LIGHTRAG = config("USE_LIGHTRAG", default=True, cast=bool)
USE_MS_GRAPHRAG = config("USE_MS_GRAPHRAG", default=True, cast=bool)

# Переопределение из сохранённых настроек веб-интерфейса (Settings → General → Save).
# Файл создаётся при сохранении настроек; при следующем запуске приложения список индексов строится по нему.
_APPLICATION_SETTINGS_PATH = KH_APP_DATA_DIR / "application_settings.json"
if _APPLICATION_SETTINGS_PATH.exists():
    try:
        import json

        with open(_APPLICATION_SETTINGS_PATH, encoding="utf-8") as f:
            _saved = json.load(f)
        _bool_keys = (
            "use_lightrag",
            "use_nano_graphrag",
            "use_ms_graphrag",
            "use_global_graphrag",
        )
        for _k in _bool_keys:
            if _k in _saved:
                _v = _saved[_k]
                if isinstance(_v, bool):
                    pass
                elif isinstance(_v, str):
                    _v = _v.strip().lower() in ("1", "true", "yes", "on")
                else:
                    _v = bool(_v)
                if _k == "use_lightrag":
                    USE_LIGHTRAG = _v
                elif _k == "use_nano_graphrag":
                    USE_NANO_GRAPHRAG = _v
                elif _k == "use_ms_graphrag":
                    USE_MS_GRAPHRAG = _v
                elif _k == "use_global_graphrag":
                    USE_GLOBAL_GRAPHRAG = _v
    except Exception:  # noqa: S110
        pass  # оставляем значения из config()

GRAPHRAG_INDEX_TYPES = []

if USE_MS_GRAPHRAG:
    GRAPHRAG_INDEX_TYPES.append("ktem.index.file.graph.GraphRAGIndex")
if USE_NANO_GRAPHRAG:
    GRAPHRAG_INDEX_TYPES.append("ktem.index.file.graph.NanoGraphRAGIndex")
if USE_LIGHTRAG:
    GRAPHRAG_INDEX_TYPES.append("ktem.index.file.graph.LightRAGIndex")

KH_INDEX_TYPES = [
    "ktem.index.file.FileIndex",
    *GRAPHRAG_INDEX_TYPES,
]

GRAPHRAG_INDICES = [
    {
        "name": graph_type.split(".")[-1].replace("Index", "")
        + " Collection",  # get last name
        "config": {
            "supported_file_types": (
                ".png, .jpeg, .jpg, .tiff, .tif, .pdf, .xls, .xlsx, .doc, .docx, "
                ".pptx, .csv, .html, .mhtml, .txt, .md, .zip"
            ),
            "private": True,
        },
        "index_type": graph_type,
    }
    for graph_type in GRAPHRAG_INDEX_TYPES
]

KH_INDICES = [
    {
        "name": "File Collection",
        "config": {
            "supported_file_types": (
                ".png, .jpeg, .jpg, .tiff, .tif, .pdf, .xls, .xlsx, .doc, .docx, "
                ".pptx, .csv, .html, .mhtml, .txt, .md, .zip"
            ),
            "private": True,
        },
        "index_type": "ktem.index.file.FileIndex",
    },
    *GRAPHRAG_INDICES,
]
