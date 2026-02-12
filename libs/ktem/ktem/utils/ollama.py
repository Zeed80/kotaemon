"""Утилиты для работы с Ollama API."""

import json
import logging
from typing import Iterator

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
    base_url = url.replace("/v1/", "").replace("/v1", "").replace("/api", "").rstrip("/")
    # Убеждаемся, что URL заканчивается на порт или имеет слеш в конце
    if not base_url.endswith("/") and not base_url.endswith(":11434"):
        base_url = f"{base_url}/"
    elif base_url.endswith(":11434"):
        base_url = f"{base_url}/"
    return base_url


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
