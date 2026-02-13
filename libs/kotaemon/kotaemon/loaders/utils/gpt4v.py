import json
import logging
from typing import Any, List

import requests
from decouple import config

logger = logging.getLogger(__name__)


def generate_gpt4v(
    endpoint: str,
    images: str | List[str],
    prompt: str,
    max_tokens: int = 512,
    max_images: int = 10,
    model: str | None = None,
) -> str:
    """Генерировать ответ от VLM для изображений.

    Args:
        endpoint: URL endpoint для VLM (OpenAI-compatible или Ollama).
        images: Изображение(я) в формате data URL или список data URLs.
        prompt: Текст промпта для VLM.
        max_tokens: Максимальное количество токенов в ответе.
        max_images: Максимальное количество изображений для обработки.
        model: Имя модели (обязательно для Ollama, опционально для других провайдеров).

    Returns:
        str: Текст ответа от VLM.
    """
    # Определяем тип провайдера по endpoint
    # Ollama использует OpenAI-compatible API на порту 11434
    # Проверяем по порту 11434 или по отсутствию известных доменов OpenAI/Azure
    known_providers = ["openai.com", "azure.com", "api.openai.com", "api.groq.com"]
    has_known_provider = any(provider in endpoint for provider in known_providers)
    is_ollama = (
        "/v1/chat/completions" in endpoint 
        and ":11434" in endpoint
        and not has_known_provider
    )
    
    # Для Ollama не нужен api-key в заголовках
    if is_ollama:
        headers = {"Content-Type": "application/json"}
    else:
        # OpenAI API Key для Azure OpenAI / OpenAI
        api_key = config("AZURE_OPENAI_API_KEY", default="")
        headers = {"Content-Type": "application/json", "api-key": api_key}

    if isinstance(images, str):
        images = [images]

    payload = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                ]
                + [
                    {
                        "type": "image_url",
                        "image_url": {"url": image},
                    }
                    for image in images[:max_images]
                ],
            }
        ],
        "max_tokens": max_tokens,
        "temperature": 0,
    }

    # Для Ollama обязательно нужен параметр model
    if is_ollama and model:
        payload["model"] = model
    elif is_ollama and not model:
        logger.warning(
            f"Ollama endpoint detected but no model provided: {endpoint}. "
            "Model parameter is required for Ollama."
        )

    if len(images) > max_images:
        logger.warning(
            f"Truncated to {max_images} images (original {len(images)} images)"
        )

    response = requests.post(endpoint, headers=headers, json=payload)

    try:
        response.raise_for_status()
    except Exception as e:
        logger.exception(f"Error generating gpt4v: {response.text}; error {e}")
        return ""

    output = response.json()
    output = output["choices"][0]["message"]["content"]
    return output


def stream_gpt4v(
    endpoint: str,
    images: str | List[str],
    prompt: str,
    max_tokens: int = 512,
    max_images: int = 10,
    model: str | None = None,
) -> Any:
    """Потоковая генерация ответа от VLM для изображений.

    Args:
        endpoint: URL endpoint для VLM (OpenAI-compatible или Ollama).
        images: Изображение(я) в формате data URL или список data URLs.
        prompt: Текст промпта для VLM.
        max_tokens: Максимальное количество токенов в ответе.
        max_images: Максимальное количество изображений для обработки.
        model: Имя модели (обязательно для Ollama, опционально для других провайдеров).

    Yields:
        tuple[str, List[float]]: (chunk текста, logprobs).
    """
    # Определяем тип провайдера по endpoint
    # Ollama использует OpenAI-compatible API на порту 11434
    # Проверяем по порту 11434 или по отсутствию известных доменов OpenAI/Azure
    known_providers = ["openai.com", "azure.com", "api.openai.com", "api.groq.com"]
    has_known_provider = any(provider in endpoint for provider in known_providers)
    is_ollama = (
        "/v1/chat/completions" in endpoint 
        and ":11434" in endpoint
        and not has_known_provider
    )
    
    # Для Ollama не нужен api-key в заголовках
    if is_ollama:
        headers = {"Content-Type": "application/json"}
    else:
        # OpenAI API Key для Azure OpenAI / OpenAI
        api_key = config("AZURE_OPENAI_API_KEY", default="")
        headers = {"Content-Type": "application/json", "api-key": api_key}

    if isinstance(images, str):
        images = [images]

    payload = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                ]
                + [
                    {
                        "type": "image_url",
                        "image_url": {"url": image},
                    }
                    for image in images[:max_images]
                ],
            }
        ],
        "max_tokens": max_tokens,
        "stream": True,
        "logprobs": True,
        "temperature": 0,
    }

    # Для Ollama обязательно нужен параметр model
    if is_ollama and model:
        payload["model"] = model
    elif is_ollama and not model:
        logger.warning(
            f"Ollama endpoint detected but no model provided: {endpoint}. "
            "Model parameter is required for Ollama."
        )

    if len(images) > max_images:
        logger.warning(
            f"Truncated to {max_images} images (original {len(images)} images)"
        )
    try:
        response = requests.post(endpoint, headers=headers, json=payload, stream=True)
        assert response.status_code == 200, str(response.content)
        output = ""
        logprobs = []
        for line in response.iter_lines():
            if line:
                if line.startswith(b"\xef\xbb\xbf"):
                    line = line[9:]
                else:
                    line = line[6:]
                try:
                    if line == "[DONE]":
                        break
                    line = json.loads(line.decode("utf-8"))
                except Exception:
                    break
                if len(line["choices"]):
                    if line["choices"][0].get("logprobs") is None:
                        _logprobs = []
                    else:
                        _logprobs = [
                            logprob["logprob"]
                            for logprob in line["choices"][0]["logprobs"].get(
                                "content", []
                            )
                        ]

                    output += line["choices"][0]["delta"].get("content", "")
                    logprobs += _logprobs
                    yield line["choices"][0]["delta"].get("content", ""), _logprobs

    except Exception as e:
        logger.error(f"Error streaming gpt4v {e}")
        logprobs = []
        output = ""

    return output, logprobs
