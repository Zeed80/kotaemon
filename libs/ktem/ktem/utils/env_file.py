"""Утилита для чтения и записи .env файла из Web UI."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def _get_env_path() -> Path | None:
    """Путь к .env (корень проекта, где flowsettings_config)."""
    try:
        import flowsettings_config  # noqa: PLC0415

        return Path(flowsettings_config.__file__).resolve().parent / ".env"
    except ImportError:
        pass
    return Path.cwd() / ".env"


def _parse_env_content(content: str) -> dict[str, str]:
    """Парсинг .env: ключ=значение. Комментарии и пустые строки пропускаются."""
    result: dict[str, str] = {}
    for line in content.splitlines():
        line = line.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line)
        if m:
            key, value = m.group(1), m.group(2)
            if value and value[0] == value[-1] and value[0] in "\"'":
                value = (
                    value[1:-1]
                    .replace("\\n", "\n")
                    .replace("\\'", "'")
                    .replace('\\"', '"')
                )
            result[key] = value
    return result


def _serialize_env_value(val: str | int | float | bool) -> str:
    """Сериализация значения для .env."""
    if isinstance(val, bool):
        return "true" if val else "false"
    s = str(val)
    if not s:
        return ""
    if " " in s or "#" in s or "=" in s or "\n" in s or s[0] in "\"'":
        return f'"{s.replace(chr(34), chr(92) + chr(34))}"'
    return s


def read_env() -> dict[str, str]:
    """Прочитать все KEY=VALUE из .env."""
    path = _get_env_path()
    if not path or not path.exists():
        return {}
    try:
        return _parse_env_content(path.read_text(encoding="utf-8"))
    except OSError:
        return {}


def write_env_updates(updates: dict[str, str | int | float | bool]) -> bool:
    """Обновить или добавить ключи в .env. Возвращает True при успехе."""
    path = _get_env_path()
    if not path:
        return False
    content = ""
    existing = {}
    if path.exists():
        content = path.read_text(encoding="utf-8")
        existing = _parse_env_content(content)
    for k, v in updates.items():
        existing[k] = _serialize_env_value(v)
    lines: list[str] = []
    seen: set[str] = set()
    for line in content.splitlines():
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=.*", line)
        if m:
            key = m.group(1)
            seen.add(key)
            if key in existing:
                lines.append(f"{key}={existing[key]}")
                continue
        lines.append(line)
    for k, v in existing.items():
        if k not in seen:
            lines.append(f"{k}={v}")
    try:
        path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        return True
    except OSError:
        return False


def persist_ollama_url(url: str) -> bool:
    """Записать Ollama URL в .env и application_settings.json.

    Вызывается при добавлении/обнаружении серверов Ollama, чтобы значение
    KH_OLLAMA_URL и application.kh_ollama_url сохранялось для следующего запуска.
    """
    url = (url or "").strip().rstrip("/")
    if not url:
        return False
    # Привести к формату .../v1/
    if "/v1" not in url:
        url = f"{url}/v1/"
    elif not url.endswith("/"):
        url = f"{url}/"
    ok = write_env_updates({"KH_OLLAMA_URL": url})
    if not ok:
        return False
    try:
        from theflow.settings import settings as flowsettings

        app_data_dir = getattr(flowsettings, "KH_APP_DATA_DIR", None)
        if app_data_dir:
            import json

            path = app_data_dir / "application_settings.json"
            data: dict = {}
            if path.exists():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    pass
            data["kh_ollama_url"] = url
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
    except Exception:
        pass
    return True


# Маппинг: ключ в application_settings (без префикса) -> переменная .env
APPLICATION_TO_ENV: dict[str, str] = {
    "kh_ollama_url": "KH_OLLAMA_URL",
    "ollama_reranker_model": "OLLAMA_RERANKER_MODEL",
    "qdrant_url": "QDRANT_URL",
    "qdrant_api_key": "QDRANT_API_KEY",
    "qdrant_path": "QDRANT_PATH",
    "qdrant_enable_hybrid": "QDRANT_ENABLE_HYBRID",
    "qdrant_sparse_model": "QDRANT_FASTEMBED_SPARSE_MODEL",
    "use_lightrag": "USE_LIGHTRAG",
    "use_nano_graphrag": "USE_NANO_GRAPHRAG",
    "use_ms_graphrag": "USE_MS_GRAPHRAG",
    "use_global_graphrag": "USE_GLOBAL_GRAPHRAG",
    "kh_chat_msg_placeholder": "KH_CHAT_MSG_PLACEHOLDER",
    "kh_chat_empty_msg_placeholder": "KH_CHAT_EMPTY_MSG_PLACEHOLDER",
    "n_prompt_opt_examples": "N_PROMPT_OPT_EXAMPLES",
    # API Keys
    "openai_api_key": "OPENAI_API_KEY",
    "openai_api_base": "OPENAI_API_BASE",
    "openai_chat_model": "OPENAI_CHAT_MODEL",
    "openai_embeddings_model": "OPENAI_EMBEDDINGS_MODEL",
    "google_api_key": "GOOGLE_API_KEY",
    "cohere_api_key": "COHERE_API_KEY",
    "voyage_api_key": "VOYAGE_API_KEY",
    "mistral_api_key": "MISTRAL_API_KEY",
    "tavily_api_key": "TAVILY_API_KEY",
    "azure_openai_endpoint": "AZURE_OPENAI_ENDPOINT",
    "azure_openai_api_key": "AZURE_OPENAI_API_KEY",
    "azure_openai_chat_deployment": "AZURE_OPENAI_CHAT_DEPLOYMENT",
    "azure_openai_embeddings_deployment": "AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT",
    "openai_api_version": "OPENAI_API_VERSION",
    "searxng_url": "SEARXNG_URL",
}
