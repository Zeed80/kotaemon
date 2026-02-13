import base64
import json
import logging
import time
from typing import Any, List

import requests
from decouple import config
from tenacity import (
    after_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_type((requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.ChunkedEncodingError)),
    after=after_log(logger, logging.WARNING),
)
def generate_gpt4v(
    endpoint: str,
    images: str | List[str],
    prompt: str,
    max_tokens: int = 8192,
    max_images: int = 10,
    model: str | None = None,
    timeout: int = 300,
) -> str:
    """Генерировать ответ от VLM для изображений.

    Args:
        endpoint: URL endpoint для VLM (OpenAI-compatible или Ollama).
        images: Изображение(я) в формате data URL или список data URLs.
        prompt: Текст промпта для VLM.
        max_tokens: Максимальное количество токенов в ответе (по умолчанию 8192 для документов).
        max_images: Максимальное количество изображений для обработки.
        model: Имя модели (обязательно для Ollama, опционально для других провайдеров).
        timeout: Таймаут запроса в секундах (по умолчанию 300 для больших изображений).

    Returns:
        str: Текст ответа от VLM.
    """
    # Определяем тип провайдера по endpoint
    # Ollama использует OpenAI-compatible API на порту 11434 для LLM,
    # но для vision моделей лучше использовать нативный API /api/chat
    known_providers = ["openai.com", "azure.com", "api.openai.com", "api.groq.com"]
    has_known_provider = any(provider in endpoint for provider in known_providers)
    # Ollama endpoint обычно содержит :11434
    # Проверяем по порту 11434 или наличию "ollama" в URL
    is_ollama = (
        (":11434" in endpoint or "ollama" in endpoint.lower())
        and not has_known_provider
    )
    
    # Для Ollama vision моделей используем нативный API вместо OpenAI-compatible
    # Преобразуем endpoint из /v1/chat/completions в /api/chat для Ollama
    ollama_endpoint = None
    if is_ollama:
        # Преобразуем OpenAI-compatible endpoint в нативный Ollama API
        if "/v1/chat/completions" in endpoint:
            # Заменяем /v1/chat/completions на /api/chat
            ollama_endpoint = endpoint.replace("/v1/chat/completions", "/api/chat")
        elif "/api/chat" in endpoint:
            # Уже правильный формат
            ollama_endpoint = endpoint
        else:
            # Если endpoint не содержит ни /v1/chat/completions, ни /api/chat
            # Извлекаем базовый URL (до последнего /) и добавляем /api/chat
            if endpoint.endswith("/"):
                ollama_endpoint = f"{endpoint}api/chat"
            else:
                # Находим базовый URL (убираем путь после последнего /)
                parts = endpoint.rsplit("/", 1)
                if len(parts) == 2:
                    base_url = parts[0]
                    ollama_endpoint = f"{base_url}/api/chat"
                else:
                    # Если нет / в URL, добавляем /api/chat
                    ollama_endpoint = f"{endpoint}/api/chat"
    
    # Для Ollama не нужен api-key в заголовках
    if is_ollama:
        headers = {"Content-Type": "application/json"}
        actual_endpoint = ollama_endpoint or endpoint
    else:
        # OpenAI API Key для Azure OpenAI / OpenAI
        api_key = config("AZURE_OPENAI_API_KEY", default="")
        headers = {"Content-Type": "application/json", "api-key": api_key}
        actual_endpoint = endpoint

    if isinstance(images, str):
        images = [images]

    # Для Ollama используем нативный формат с массивом images в сообщении
    if is_ollama:
        # Извлекаем base64 из data URL для Ollama
        base64_images = []
        for image in images[:max_images]:
            if image.startswith("data:"):
                # Извлекаем base64 из data URL: data:image/jpeg;base64,<base64>
                # Разделяем по запятой и берем часть после неё
                base64_data = image.split(",", 1)[1] if "," in image else image
            else:
                # Если уже base64 строка (без data: префикса)
                base64_data = image
            base64_images.append(base64_data)
        
        payload = {
            "model": model if model else "",
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": base64_images,
                }
            ],
            "options": {
                "num_ctx": 16384,  # Увеличенное контекстное окно для обработки больших изображений
                "num_predict": max_tokens,  # Максимальное количество токенов для генерации
                "temperature": 0,
                "keep_alive": "5m",  # Сохранять модель в памяти 5 минут
            },
            "stream": False,
        }
        
        if not model:
            logger.warning(
                f"Ollama endpoint detected but no model provided: {endpoint}. "
                "Model parameter is required for Ollama."
            )
    else:
        # OpenAI-compatible формат для других провайдеров
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

    if len(images) > max_images:
        logger.warning(
            f"Truncated to {max_images} images (original {len(images)} images)"
        )

    # Вычисляем размер изображений для логирования
    images_to_send = images[:max_images]
    total_image_size = sum(len(img) for img in images_to_send)
    
    # Логируем параметры запроса для отладки
    logger.info(
        f"VLM request: endpoint={actual_endpoint}, model={model}, max_tokens={max_tokens}, "
        f"timeout={timeout}s, images_count={len(images_to_send)}, "
        f"total_image_size={total_image_size / 1024:.2f} KB, is_ollama={is_ollama}, "
        f"using_native_api={is_ollama and ollama_endpoint is not None}"
    )

    response = None
    try:
        response = requests.post(actual_endpoint, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
    except requests.exceptions.Timeout as e:
        logger.error(
            f"VLM request timeout after {timeout}s: endpoint={actual_endpoint}, model={model}, "
            f"image_size={total_image_size / 1024:.2f} KB"
        )
        raise
    except (requests.exceptions.ConnectionError, requests.exceptions.ChunkedEncodingError) as e:
        # RemoteDisconnected является подклассом ConnectionError
        error_detail = str(e)
        if "Remote end closed connection" in error_detail or "RemoteDisconnected" in str(type(e)):
            logger.error(
                f"VLM connection closed by server (RemoteDisconnected): endpoint={actual_endpoint}, "
                f"model={model}, image_size={total_image_size / 1024:.2f} KB, "
                f"timeout={timeout}s. This may indicate the image is too large or the request "
                f"takes too long. Try reducing image size or increasing timeout."
            )
        else:
            logger.error(
                f"VLM connection error: endpoint={actual_endpoint}, model={model}, "
                f"error={error_detail}, image_size={total_image_size / 1024:.2f} KB"
            )
        raise
    except requests.exceptions.HTTPError as e:
        # HTTP ошибки (4xx, 5xx)
        error_text = ""
        if response is not None:
            try:
                error_text = response.text[:500]  # Ограничиваем размер лога
            except Exception:
                error_text = f"Status {response.status_code}"
        logger.error(
            f"VLM HTTP error: endpoint={actual_endpoint}, model={model}, "
            f"status={response.status_code if response else 'unknown'}, "
            f"error={error_text}, image_size={total_image_size / 1024:.2f} KB"
        )
        raise
    except Exception as e:
        error_text = ""
        if response is not None:
            try:
                error_text = response.text[:500] if hasattr(response, "text") else ""
            except Exception:
                pass
        logger.exception(
            f"Error generating gpt4v: endpoint={actual_endpoint}, model={model}, "
            f"response={error_text}, error={e}, image_size={total_image_size / 1024:.2f} KB"
        )
        raise

    output = response.json()
    
    # Для Ollama нативного API формат ответа отличается
    if is_ollama:
        # Ollama возвращает {"message": {"content": "..."}}
        if "message" in output and "content" in output["message"]:
            return output["message"]["content"]
        else:
            logger.error(f"Unexpected Ollama response format: {output}")
            raise ValueError(f"Unexpected Ollama response format: {output}")
    else:
        # OpenAI-compatible формат: {"choices": [{"message": {"content": "..."}}]}
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
    # Ollama endpoint обычно содержит :11434 и /v1/chat/completions
    # Также проверяем по отсутствию известных провайдеров и наличию /v1/chat/completions
    is_ollama = (
        "/v1/chat/completions" in endpoint 
        and (":11434" in endpoint or "ollama" in endpoint.lower())
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

    if len(images) > max_images:
        logger.warning(
            f"Truncated to {max_images} images (original {len(images)} images)"
        )
    
    # Для Ollama добавляем дополнительные параметры
    if is_ollama:
        if not model:
            logger.warning(
                f"Ollama endpoint detected but no model provided: {endpoint}. "
                "Model parameter is required for Ollama."
            )
        else:
            payload["model"] = model
        payload["options"] = {
            "num_ctx": 16384,  # Увеличенное контекстное окно для обработки больших изображений
            "num_predict": max_tokens,
            "temperature": 0,
            "keep_alive": "5m",
        }

    try:
        response = requests.post(
            endpoint, headers=headers, json=payload, stream=True, timeout=300
        )
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
