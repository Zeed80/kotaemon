from unittest.mock import patch

from kotaemon.loaders.utils.gpt4v import (
    generate_gpt4v,
    is_ollama_endpoint,
    normalize_ollama_chat_endpoint,
)


class _FakeResponse:
    status_code = 200
    content = b"{}"

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_is_ollama_endpoint_variants():
    assert is_ollama_endpoint("http://localhost:11434/v1/chat/completions")
    assert is_ollama_endpoint("http://example.internal:9999/v1/chat/completions")
    assert is_ollama_endpoint("http://127.0.0.1:11434/api/chat")
    assert not is_ollama_endpoint("https://api.openai.com/v1/chat/completions")


def test_normalize_ollama_chat_endpoint():
    assert (
        normalize_ollama_chat_endpoint("http://localhost:11434/v1/chat/completions")
        == "http://localhost:11434/api/chat"
    )
    assert (
        normalize_ollama_chat_endpoint("http://localhost:11434")
        == "http://localhost:11434/api/chat"
    )


def test_generate_gpt4v_uses_native_ollama_payload():
    captured = {}

    def _fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return _FakeResponse({"message": {"content": "ok"}})

    with patch("requests.post", side_effect=_fake_post):
        output = generate_gpt4v(
            endpoint="http://localhost:11434/v1/chat/completions",
            images="data:image/png;base64,AAAA",
            prompt="extract",
            model="qwen3-vl:8b",
        )

    assert output == "ok"
    assert captured["url"] == "http://localhost:11434/api/chat"
    assert captured["json"]["messages"][0]["images"] == ["AAAA"]


def test_generate_gpt4v_ollama_empty_content_returns_empty_string():
    """Пустой или null content от Ollama должен возвращать '' без исключения."""
    with patch("requests.post") as mock_post:
        mock_post.return_value = _FakeResponse({"message": {"content": ""}})
        output = generate_gpt4v(
            endpoint="http://localhost:11434/api/chat",
            images="data:image/png;base64,AAAA",
            prompt="extract",
            model="qwen3-vl:8b",
        )
    assert output == ""

    with patch("requests.post") as mock_post:
        mock_post.return_value = _FakeResponse({"message": {"content": None}})
        output = generate_gpt4v(
            endpoint="http://localhost:11434/api/chat",
            images="data:image/png;base64,AAAA",
            prompt="extract",
            model="qwen3-vl:8b",
        )
    assert output == ""


def test_generate_gpt4v_ollama_uses_thinking_when_content_empty():
    """Если content пустой, но thinking есть — используем thinking (qwen3-vl)."""
    with patch("requests.post") as mock_post:
        mock_post.return_value = _FakeResponse(
            {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "thinking": "Invoice #123\nDate: 2024-01-15\nTotal: $99.99",
                }
            }
        )
        output = generate_gpt4v(
            endpoint="http://localhost:11434/api/chat",
            images="data:image/png;base64,AAAA",
            prompt="extract",
            model="qwen3-vl:8b",
        )
    assert output == "Invoice #123\nDate: 2024-01-15\nTotal: $99.99"
