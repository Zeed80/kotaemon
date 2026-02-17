import json
import logging
from typing import Any
from urllib.parse import urlparse

import requests
from tenacity import (
    after_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from flowsettings_config import config

logger = logging.getLogger(__name__)

_KNOWN_OPENAI_PROVIDERS = ("openai.com", "azure.com", "api.openai.com", "api.groq.com")


def is_ollama_endpoint(endpoint: str) -> bool:
    """Определить, относится ли endpoint к Ollama."""
    if not endpoint:
        return False
    lowered = endpoint.lower()
    if any(provider in lowered for provider in _KNOWN_OPENAI_PROVIDERS):
        return False
    if "ollama" in lowered:
        return True
    if "/api/chat" in lowered or "/api/generate" in lowered:
        return True
    if "/v1/chat/completions" in lowered:
        return True
    parsed = urlparse(endpoint)
    if parsed.hostname in {"localhost", "127.0.0.1"} and parsed.port == 11434:
        return True
    if parsed.port == 11434:
        return True
    return False


def normalize_ollama_chat_endpoint(endpoint: str) -> str:
    """Преобразовать URL к Ollama native endpoint `/api/chat`."""
    if not endpoint:
        return endpoint
    endpoint = endpoint.rstrip("/")
    if endpoint.endswith("/api/chat"):
        return endpoint
    if endpoint.endswith("/v1/chat/completions"):
        return endpoint[: -len("/v1/chat/completions")] + "/api/chat"
    parsed = urlparse(endpoint)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}/api/chat"
    return f"{endpoint}/api/chat"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_type(
        (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
            requests.exceptions.ChunkedEncodingError,
        )
    ),
    after=after_log(logger, logging.WARNING),
)
def generate_gpt4v(
    endpoint: str,
    images: str | list[str],
    prompt: str,
    max_tokens: int = 8192,
    max_images: int = 10,
    model: str | None = None,
    timeout: int = 300,
    ingestion_id: str = "",
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
    is_ollama = is_ollama_endpoint(endpoint)

    # Для Ollama vision моделей используем нативный API вместо OpenAI-compatible
    endpoint_type = "ollama_native" if is_ollama else "openai_compatible"

    # Преобразуем endpoint из /v1/chat/completions в /api/chat для Ollama
    ollama_endpoint = None
    if is_ollama:
        ollama_endpoint = normalize_ollama_chat_endpoint(endpoint)

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
            "think": False,  # Отключаем thinking — для OCR нужен прямой ответ в content
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
        f"VLM request: ingestion_id={ingestion_id or 'n/a'}, endpoint={actual_endpoint}, endpoint_type={endpoint_type}, model={model}, max_tokens={max_tokens}, "
        f"timeout={timeout}s, images_count={len(images_to_send)}, "
        f"total_image_size={total_image_size / 1024:.2f} KB, is_ollama={is_ollama}, "
        f"using_native_api={is_ollama and ollama_endpoint is not None}"
    )

    response = None
    try:
        response = requests.post(
            actual_endpoint, headers=headers, json=payload, timeout=timeout
        )
        response.raise_for_status()
    except requests.exceptions.Timeout:
        logger.error(
            f"VLM request timeout after {timeout}s: ingestion_id={ingestion_id or 'n/a'}, endpoint={actual_endpoint}, endpoint_type={endpoint_type}, model={model}, "
            f"image_size={total_image_size / 1024:.2f} KB"
        )
        raise
    except (
        requests.exceptions.ConnectionError,
        requests.exceptions.ChunkedEncodingError,
    ) as e:
        # RemoteDisconnected является подклассом ConnectionError
        error_detail = str(e)
        if (
            "Remote end closed connection" in error_detail
            or "RemoteDisconnected" in str(type(e))
        ):
            logger.error(
                f"VLM connection closed by server (RemoteDisconnected): ingestion_id={ingestion_id or 'n/a'}, endpoint={actual_endpoint}, endpoint_type={endpoint_type}, "
                f"model={model}, image_size={total_image_size / 1024:.2f} KB, "
                f"timeout={timeout}s. This may indicate the image is too large or the request "
                f"takes too long. Try reducing image size or increasing timeout."
            )
        else:
            logger.error(
                f"VLM connection error: ingestion_id={ingestion_id or 'n/a'}, endpoint={actual_endpoint}, endpoint_type={endpoint_type}, model={model}, "
                f"error={error_detail}, image_size={total_image_size / 1024:.2f} KB"
            )
        raise
    except requests.exceptions.HTTPError:
        # HTTP ошибки (4xx, 5xx)
        error_text = ""
        if response is not None:
            try:
                error_text = response.text[:500]  # Ограничиваем размер лога
            except Exception:
                error_text = f"Status {response.status_code}"
        logger.error(
            f"VLM HTTP error: ingestion_id={ingestion_id or 'n/a'}, endpoint={actual_endpoint}, endpoint_type={endpoint_type}, model={model}, "
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
            f"Error generating gpt4v: ingestion_id={ingestion_id or 'n/a'}, endpoint={actual_endpoint}, endpoint_type={endpoint_type}, model={model}, "
            f"response={error_text}, error={e}, image_size={total_image_size / 1024:.2f} KB"
        )
        raise

    output = response.json()

    # Для Ollama нативного API формат ответа отличается
    if is_ollama:
        # Ollama возвращает {"message": {"role": "assistant", "content": "...", "thinking": "..."}}
        if "message" not in output:
            logger.error(
                f"Ollama response missing 'message': keys={list(output.keys())}"
            )
            raise ValueError("Unexpected Ollama response format: missing 'message'")
        msg = output["message"]
        content = msg.get("content") if isinstance(msg, dict) else None
        thinking = msg.get("thinking") if isinstance(msg, dict) else None
        # content может быть None или пустой строкой — нормализуем к ""
        result = (content or "").strip() if content is not None else ""
        # qwen3-vl и др. thinking-модели иногда возвращают OCR-текст в thinking вместо content
        if not result and thinking:
            thinking_text = (thinking or "").strip() if thinking is not None else ""
            if thinking_text:
                result = thinking_text
                logger.info(
                    f"Ollama returned empty content but non-empty thinking, using thinking: "
                    f"ingestion_id={ingestion_id or 'n/a'}, model={model}, thinking_len={len(result)}"
                )
        if not result:
            logger.warning(
                f"Ollama VLM returned empty content and empty thinking: ingestion_id={ingestion_id or 'n/a'}, "
                f"model={model}, message_keys={list(msg.keys()) if isinstance(msg, dict) else 'n/a'}"
            )
            logger.debug(
                f"Ollama raw response (truncated): {json.dumps({k: (str(v)[:200] + '...' if len(str(v)) > 200 else v) for k, v in output.items()})}"
            )
        return result
    else:
        # OpenAI-compatible формат: {"choices": [{"message": {"content": "..."}}]}
        content = output["choices"][0]["message"]["content"]
        return (content or "").strip() if content is not None else ""


def stream_gpt4v(
    endpoint: str,
    images: str | list[str],
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
    is_ollama = is_ollama_endpoint(endpoint)

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

    actual_endpoint = endpoint
    # Для Ollama добавляем дополнительные параметры
    if is_ollama:
        actual_endpoint = normalize_ollama_chat_endpoint(endpoint)
        if not model:
            logger.warning(
                f"Ollama endpoint detected but no model provided: {endpoint}. "
                "Model parameter is required for Ollama."
            )
        else:
            payload["model"] = model
        base64_images = []
        for image in images[:max_images]:
            if image.startswith("data:"):
                base64_data = image.split(",", 1)[1] if "," in image else image
            else:
                base64_data = image
            base64_images.append(base64_data)
        payload = {
            "model": model if model else "",
            "messages": [{"role": "user", "content": prompt, "images": base64_images}],
            "options": {
                "num_ctx": 16384,
                "num_predict": max_tokens,
                "temperature": 0,
                "keep_alive": "5m",
            },
            "stream": False,
        }

    try:
        response = requests.post(
            actual_endpoint, headers=headers, json=payload, stream=True, timeout=300
        )
        assert response.status_code == 200, str(response.content)
        output = ""
        logprobs = []
        if is_ollama:
            content = response.json().get("message", {}).get("content", "")
            yield content, []
            return content, []
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
