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
KH_DATABASE = f"sqlite:///{KH_USER_DATA_DIR / 'sql.db'}"
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


KH_VECTORSTORE = {
    "__type__": "kotaemon.storages.QdrantVectorStore",
    "collection_name": "default",
    "enable_hybrid": _qdrant_enable_hybrid,
    "fastembed_sparse_model": _qdrant_sparse_model,
    **(
        {"path": _qdrant_path}
        if _qdrant_path
        else {
            "url": _qdrant_url(),
            "api_key": _qdrant_api_key() or "",
        }
    ),
    # "__type__": "kotaemon.storages.LanceDBVectorStore",
    # "__type__": "kotaemon.storages.ChromaVectorStore",
    # "__type__": "kotaemon.storages.MilvusVectorStore",
    # "path": str(KH_USER_DATA_DIR / "vectorstore"),
}
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


def get_application_setting(key: str, default: str | int | float | bool | None = None):  # noqa: ANN201
    """Взять значение настройки приложения: сначала из application_settings.json, иначе default.
    Используется в рантайме (чаты, пайплайны), когда нет доступа к settings_state.
    """
    path = KH_APP_DATA_DIR / "application_settings.json"
    if not path.exists():
        return default
    try:
        import json

        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if key in data:
            return data[key]
    except Exception:  # noqa: S110
        pass
    return default


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
        "component": "text",
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
        "value": 32000,
        "component": "number",
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
