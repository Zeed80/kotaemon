"""Менеджер списка VLM: загрузка из БД, add/update/delete/get/list, get_endpoint(name)."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import requests
from sqlalchemy import select
from sqlalchemy.orm import Session

from ktem.ollama_servers import ollama_servers_manager
from ktem.utils.ollama import server_url_to_langchain_base

from .db import VLMTable, engine

logger = logging.getLogger(__name__)


def _build_ollama_vlm_endpoint(server_name: str, model: str) -> str:
    """По имени сервера Ollama и модели собрать URL для chat completions (OpenAI-совместимый)."""
    return _build_ollama_vlm_endpoint_cached(server_name, model)


@lru_cache(maxsize=32)
def _build_ollama_vlm_endpoint_cached(server_name: str, model: str) -> str:
    """Кэшированная версия для построения Ollama VLM endpoint."""
    s = ollama_servers_manager.get(server_name)
    if not s:
        return ""
    base = server_url_to_langchain_base(s["base_url"])
    # Ollama OpenAI-compatible endpoint: http://host:11434/v1/chat/completions
    if base.endswith("/"):
        base = base.rstrip("/")
    return f"{base}/v1/chat/completions"


class VLMManager:
    """Пул зарегистрированных VLM."""

    def __init__(self) -> None:
        self._vlms: dict[str, dict] = {}
        self.load()

    def load(self) -> None:
        """Загрузить VLM из БД."""
        self._vlms = {}
        with Session(engine) as session:
            stmt = select(VLMTable)
            for row in session.execute(stmt).scalars():
                self._vlms[row.name] = {
                    "name": row.name,
                    "spec": row.spec or {},
                }

    def list(self) -> list[dict]:
        """Список VLM (name, spec)."""
        return list(self._vlms.values())

    def get(self, name: str) -> dict | None:
        """Получить VLM по имени."""
        return self._vlms.get(name)

    def add(self, name: str, spec: dict[str, Any]) -> None:
        """Добавить VLM."""
        name = name.strip()
        if not name:
            raise ValueError("Имя VLM не может быть пустым")
        with Session(engine) as session:
            item = VLMTable(name=name, spec=spec)
            session.add(item)
            session.commit()
        self.load()
        self._clear_cache()

    def update(self, name: str, spec: dict[str, Any]) -> None:
        """Обновить VLM."""
        if not name or name not in self._vlms:
            raise ValueError(f"VLM {name!r} не найден")
        with Session(engine) as session:
            item = session.get(VLMTable, name)
            if item:
                item.spec = spec
                session.add(item)
                session.commit()
        self.load()
        self._clear_cache()

    def delete(self, name: str) -> None:
        """Удалить VLM."""
        with Session(engine) as session:
            item = session.get(VLMTable, name)
            if item:
                session.delete(item)
                session.commit()
        self.load()
        self._clear_cache()

    def _clear_cache(self) -> None:
        """Очистить кэш при изменении VLM."""
        self._get_endpoint_and_model_cached.cache_clear()
        _build_ollama_vlm_endpoint_cached.cache_clear()
        logger.debug("VLMManager cache cleared")

    def get_endpoint(self, name: str) -> str:
        """Вернуть URL endpoint для вызова VLM по имени.

        Для provider azure_openai/openai — endpoint_url из spec.
        Для provider ollama — собирается из ollama_server + model.
        Если name пустой или 'default', возвращается пустая строка (caller подставит KH_VLM_ENDPOINT).
        """
        endpoint, _ = self.get_endpoint_and_model(name)
        return endpoint

    def get_model(self, name: str) -> str:
        """Вернуть имя модели для VLM по имени.

        Для provider ollama — model из spec.
        Для provider azure_openai/openai — пустая строка (модель в endpoint URL).
        """
        _, model = self.get_endpoint_and_model(name)
        return model

    def get_endpoint_and_model(self, name: str) -> tuple[str, str]:
        """Вернуть URL endpoint и имя модели для вызова VLM по имени.

        Returns:
            tuple[str, str]: (endpoint_url, model_name)
            Для provider azure_openai/openai — (endpoint_url, "").
            Для provider ollama — (endpoint_url, model_name).
        """
        return self._get_endpoint_and_model_cached(name)

    @lru_cache(maxsize=64)
    def _get_endpoint_and_model_cached(self, name: str) -> tuple[str, str]:
        """Кэшированная версия get_endpoint_and_model."""
        if not name or name == "default":
            return "", ""
        v = self.get(name)
        if not v:
            return "", ""
        spec = v["spec"] or {}
        provider = (spec.get("provider") or "").strip().lower()
        if provider == "ollama":
            model = (spec.get("model") or "llava").strip()
            endpoint = _build_ollama_vlm_endpoint(
                spec.get("ollama_server") or "",
                model,
            )
            return endpoint, model
        endpoint = (spec.get("endpoint_url") or "").strip()
        return endpoint, ""

    def options_for_dropdown(self) -> list[tuple[str, str]]:
        """Список (display_name, value) для выпадающего списка."""
        return [(v["name"], v["name"]) for v in self.list()]

    def health_check(self, name: str = "default", timeout: float = 5.0) -> dict:
        """Проверить доступность VLM endpoint.

        Args:
            name: имя VLM для проверки (по умолчанию "default")
            timeout: таймаут запроса в секундах

        Returns:
            dict с ключами:
                - available: bool - доступен ли endpoint
                - status: str - статус (ok, unreachable, error, no_endpoint)
                - message: str - сообщение с деталями
                - latency_ms: float - время отклика в миллисекундах (если доступен)
        """
        import time

        result = {
            "available": False,
            "status": "no_endpoint",
            "message": "",
            "latency_ms": None,
        }

        endpoint, model = self.get_endpoint_and_model(name)
        if not endpoint:
            result["message"] = f"VLM '{name}' has no endpoint configured"
            return result

        # Check if it's Ollama endpoint
        from .utils.gpt4v import is_ollama_endpoint

        is_ollama = is_ollama_endpoint(endpoint)
        start_time = time.time()

        try:
            if is_ollama:
                # For Ollama, check /api/tags endpoint

                # Convert /v1/chat/completions to base URL
                base_url = endpoint.replace("/v1/chat/completions", "").rstrip("/")
                tags_url = f"{base_url}/api/tags"
                response = requests.get(tags_url, timeout=timeout)
                if response.status_code == 200:
                    result["available"] = True
                    result["status"] = "ok"
                    result["message"] = "Ollama server is healthy"
                else:
                    result["status"] = "error"
                    result["message"] = f"Ollama returned status {response.status_code}"
            else:
                # For OpenAI-compatible endpoints, try a minimal request
                # Just check if the endpoint responds
                response = requests.get(endpoint.rsplit("/", 1)[0], timeout=timeout)
                result["available"] = True
                result["status"] = "ok"
                result["message"] = "Endpoint is reachable"

        except requests.exceptions.ConnectionError:
            result["status"] = "unreachable"
            result["message"] = f"Cannot connect to {endpoint}"
        except requests.exceptions.Timeout:
            result["status"] = "unreachable"
            result["message"] = f"Connection to {endpoint} timed out"
        except Exception as e:
            result["status"] = "error"
            result["message"] = str(e)
        finally:
            if result["latency_ms"] is None:
                elapsed = time.time() - start_time
                result["latency_ms"] = round(elapsed * 1000, 2)

        return result

    def health_check_all(self, timeout: float = 5.0) -> dict:
        """Проверить доступность всех зарегистрированных VLM.

        Returns:
            dict: {vlm_name: health_check_result}
        """
        results = {}
        for vlm in self.list():
            results[vlm["name"]] = self.health_check(vlm["name"], timeout)
        return results


vlms_manager = VLMManager()
