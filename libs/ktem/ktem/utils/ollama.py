"""Утилиты для работы с Ollama API.

Все HTTP-запросы к Ollama (проверка доступности, список моделей, загрузка)
выполняются на бэкенде — на хосте, где запущен Kotaemon. URL localhost
и 127.0.0.1 означают «этот сервер», а не браузер пользователя.
Используется только официальный Ollama API (GET /api/tags, POST /api/pull и т.д.).
"""

import json
import logging
from collections.abc import Iterator

import requests
from theflow.settings import settings as flowsettings

from flowsettings import get_application_setting

logger = logging.getLogger(__name__)


def get_ollama_base_url() -> str:
    """Получить базовый URL Ollama из настроек.

    Returns:
        str: Базовый URL для Ollama API (без /v1/, с /api)
    """
    url = get_application_setting("kh_ollama_url")
    if not url:
        url = getattr(flowsettings, "KH_OLLAMA_URL", "http://localhost:11434/v1/")
    # Конвертируем /v1/ в /api для native API
    api_url = url.replace("/v1/", "/api").replace("/v1", "/api").rstrip("/")
    if not api_url.endswith("/api"):
        # Если URL не содержит /api, добавляем его
        if api_url.endswith(":11434"):
            api_url = f"{api_url}/api"
        elif not api_url.endswith("/api"):
            api_url = f"{api_url}/api"
    return api_url


def server_url_to_langchain_base(url: str) -> str:
    """Привести URL сервера (из OllamaServerTable) к формату для langchain_ollama.

    Например: http://localhost:11434/v1/ -> http://localhost:11434/
    """
    url = (url or "").strip().rstrip("/")
    url = url.replace("/v1/", "").replace("/v1", "").replace("/api", "")
    if url and not url.endswith("/"):
        url = f"{url}/"
    return url or "http://localhost:11434/"


def get_ollama_base_url_for_langchain() -> str:
    """Получить базовый URL Ollama для использования с langchain_ollama.

    langchain_ollama.ChatOllama ожидает базовый URL без /api и без /v1/,
    например: http://localhost:11434/

    Returns:
        str: Базовый URL для langchain_ollama (без /v1/ и без /api)
    """
    url = get_application_setting("kh_ollama_url")
    if not url:
        url = getattr(flowsettings, "KH_OLLAMA_URL", "http://localhost:11434/v1/")
    # Убираем /v1/ и /api, оставляем только базовый URL
    base_url = (
        url.replace("/v1/", "").replace("/v1", "").replace("/api", "").rstrip("/")
    )
    # Убеждаемся, что URL заканчивается на порт или имеет слеш в конце
    if not base_url.endswith("/") and not base_url.endswith(":11434"):
        base_url = f"{base_url}/"
    elif base_url.endswith(":11434"):
        base_url = f"{base_url}/"
    return base_url


def _normalize_url_to_api(url: str) -> str:
    """Привести URL к формату с /api для запросов к Ollama API (на бэкенде).

    Поддерживает: http://host:11434, http://host:11434/v1/, http://host:11434/api.
    """
    url = (url or "").strip().rstrip("/")
    if not url:
        return ""
    # Убираем /v1/ и /v1, добавляем /api
    url = url.replace("/v1/", "/").replace("/v1", "/").rstrip("/")
    if "/api" not in url:
        url = f"{url}/api" if url else ""
    # Убеждаемся, что заканчивается на /api (без лишнего слеша перед tags)
    return url.rstrip("/")


def check_ollama_available(base_url: str | None = None) -> tuple[bool, str]:
    """Проверить доступность сервера Ollama по URL.

    Запрос выполняется на бэкенде (на хосте, где запущен Kotaemon).
    localhost и 127.0.0.1 означают «этот сервер», а не браузер пользователя.

    Выполняет GET к {base_url}/api/tags с таймаутом 3 с. При 200 считает
    сервер доступным. Используется только официальный Ollama API.

    Args:
        base_url: URL Ollama (с /v1/ или /api или без). Если None — из настроек.

    Returns:
        (success, message): успех и код для UI: ok, timeout, unreachable,
        error, empty_url, status_XXX.
    """
    if base_url is None or not (base_url or "").strip():
        base_url = get_application_setting("kh_ollama_url")
        if not base_url:
            base_url = getattr(
                flowsettings, "KH_OLLAMA_URL", "http://localhost:11434/v1/"
            )
    api_url = _normalize_url_to_api(base_url)
    if not api_url:
        return False, "empty_url"
    try:
        tags_url = f"{api_url}/tags" if not api_url.endswith("/tags") else api_url
        response = requests.get(tags_url, timeout=5)
        if response.status_code == 200:
            return True, "ok"
        return False, f"status_{response.status_code}"
    except requests.exceptions.Timeout:
        return False, "timeout"
    except requests.exceptions.ConnectionError:
        return False, "unreachable"
    except requests.exceptions.RequestException as e:
        logger.debug("check_ollama_available failed: %s", e)
        return False, "error"
    except Exception as e:
        logger.exception("check_ollama_available: %s", e)
        return False, "error"


def get_ollama_models(base_url: str | None = None) -> list[dict[str, str | int]]:
    """Получить список моделей из Ollama.

    Args:
        base_url: Базовый URL Ollama API. Если None, берется из настроек.

    Returns:
        List[Dict]: Список моделей с полями name и size.
        При ошибке возвращается пустой список.
    """
    if base_url is None:
        base_url = get_ollama_base_url()
    else:
        base_url = _normalize_url_to_api(base_url)

    try:
        response = requests.get(f"{base_url}/tags", timeout=5)
        response.raise_for_status()
        data = response.json()
        models = []
        for model in data.get("models", []):
            models.append(
                {
                    "name": model.get("name", ""),
                    "size": model.get("size", 0),
                    "modified_at": model.get("modified_at", ""),
                }
            )
        return models
    except requests.exceptions.RequestException as e:
        logger.warning(f"Не удалось получить список моделей из Ollama: {e}")
        return []
    except Exception as e:
        logger.error(f"Ошибка при получении списка моделей Ollama: {e}")
        return []


def check_ollama_embed_model(
    base_url: str | None = None,
    model_name: str = "",
    timeout: int = 30,
) -> None:
    """Проверить, что модель в Ollama доступна и поддерживает /api/embed.

    Выполняет GET /api/tags (наличие модели в списке) и POST /api/embed
    (тестовый запрос). При ошибке выбрасывает Exception с понятным текстом.

    Args:
        base_url: Базовый URL Ollama (с /v1/ или /api или без). Если пусто — из настроек.
        model_name: Имя модели (например qwen3-reranker).
        timeout: Таймаут запросов в секундах.

    Raises:
        ValueError: Пустое имя модели или URL.
        requests.HTTPError: Модель не найдена (404) или не поддерживает embed (500).
        Exception: Сеть, таймаут или пустой ответ embeddings.
    """
    if not (model_name or "").strip():
        raise ValueError("Имя модели для проверки не задано")

    if base_url is None or not (base_url or "").strip():
        base_url = get_application_setting("kh_ollama_url")
        if not base_url:
            base_url = getattr(
                flowsettings, "KH_OLLAMA_URL", "http://localhost:11434/v1/"
            )
    api_url = _normalize_url_to_api(base_url)
    if not api_url:
        raise ValueError("URL Ollama не задан и не найден в настройках")

    # 1) Проверить, что модель есть в списке (GET /api/tags)
    try:
        resp = requests.get(f"{api_url}/tags", timeout=min(timeout, 10))
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout as e:
        raise ConnectionError(
            "Таймаут при обращении к Ollama (GET /api/tags). Проверьте доступность сервера."
        ) from e
    except requests.exceptions.ConnectionError as e:
        raise ConnectionError(
            "Не удалось подключиться к Ollama. Проверьте URL и что сервер запущен."
        ) from e
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(
            f"Ollama вернул ошибку при запросе списка моделей: {e}"
        ) from e

    models = data.get("models") or []
    name_stripped = model_name.strip()
    found = any(
        (m.get("name") or "").strip() == name_stripped
        or (m.get("name") or "").strip().startswith(name_stripped + ":")
        for m in models
    )
    if not found:
        available = ", ".join((m.get("name") or "") for m in models[:10])
        if len(models) > 10:
            available += ", ..."
        raise ValueError(
            f"Модель «{model_name}» не найдена в Ollama. "
            f"Доступные модели: {available or 'нет'}. "
            "Загрузите модель: ollama pull " + model_name
        )

    # 2) Проверить поддержку /api/embed тестовым запросом
    embed_url = f"{api_url}/embed"
    payload = {"model": model_name, "input": "check [SEP] connection"}
    try:
        resp = requests.post(
            embed_url,
            json=payload,
            timeout=timeout,
            headers={"Content-Type": "application/json"},
        )
    except requests.exceptions.Timeout as e:
        raise ConnectionError(
            "Таймаут при вызове /api/embed. Модель может быть слишком тяжёлой или сервер перегружен."
        ) from e
    except requests.exceptions.ConnectionError as e:
        raise ConnectionError(
            "Не удалось подключиться к Ollama при проверке /api/embed."
        ) from e

    if resp.status_code == 404:
        raise ValueError(
            f"Модель «{model_name}» не найдена (404). Загрузите: ollama pull {model_name}"
        )
    if resp.status_code == 500:
        try:
            err_msg = (resp.json() or {}).get("error", resp.text or "Internal Server Error")
        except Exception:
            err_msg = resp.text or "Internal Server Error"
        raise RuntimeError(
            f"Модель «{model_name}» не поддерживает /api/embed или произошла ошибка сервера (500): {err_msg}"
        )
    resp.raise_for_status()

    try:
        data = resp.json()
    except Exception as e:
        raise RuntimeError("Ответ Ollama /api/embed не является JSON") from e

    embeddings = data.get("embeddings")
    if not embeddings or not isinstance(embeddings, list):
        raise RuntimeError(
            "Ответ /api/embed не содержит поля embeddings или оно пустое. "
            "Убедитесь, что модель предназначена для embeddings/rerank."
        )
    if len(embeddings) < 1 or not isinstance(embeddings[0], (list, tuple)):
        raise RuntimeError(
            "Ответ /api/embed: неверный формат embeddings (ожидается массив векторов)."
        )


def pull_ollama_model(
    base_url: str | None = None, model_name: str = "", stream: bool = True
) -> Iterator[dict]:
    """Загрузить модель из Ollama.

    Args:
        base_url: Базовый URL Ollama API. Если None, берется из настроек.
        model_name: Имя модели для загрузки.
        stream: Использовать потоковую загрузку.

    Yields:
        Dict: Словарь с информацией о прогрессе загрузки.

    Raises:
        requests.exceptions.RequestException: При ошибке HTTP запроса.
    """
    if base_url is None:
        base_url = get_ollama_base_url()
    else:
        base_url = _normalize_url_to_api(base_url)

    if not model_name:
        raise ValueError("Имя модели не может быть пустым")

    payload = {"name": model_name}
    headers = {"Content-Type": "application/json"}

    response = requests.post(
        f"{base_url}/pull",
        json=payload,
        headers=headers,
        stream=stream,
        timeout=None,
    )
    response.raise_for_status()

    if stream:
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line.decode("utf-8"))
                    yield data
                    if data.get("status") == "success":
                        break
                except json.JSONDecodeError:
                    continue
    else:
        yield response.json()
