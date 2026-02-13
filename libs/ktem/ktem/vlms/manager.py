"""Менеджер списка VLM: загрузка из БД, add/update/delete/get/list, get_endpoint(name)."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ktem.ollama_servers import ollama_servers_manager
from ktem.utils.ollama import server_url_to_langchain_base

from .db import VLMTable, engine


def _build_ollama_vlm_endpoint(server_name: str, model: str) -> str:
    """По имени сервера Ollama и модели собрать URL для chat completions (OpenAI-совместимый)."""
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

    def get(self, name: str) -> Optional[dict]:
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

    def delete(self, name: str) -> None:
        """Удалить VLM."""
        with Session(engine) as session:
            item = session.get(VLMTable, name)
            if item:
                session.delete(item)
                session.commit()
        self.load()

    def get_endpoint(self, name: str) -> str:
        """Вернуть URL endpoint для вызова VLM по имени.

        Для provider azure_openai/openai — endpoint_url из spec.
        Для provider ollama — собирается из ollama_server + model.
        Если name пустой или 'default', возвращается пустая строка (caller подставит KH_VLM_ENDPOINT).
        """
        if not name or name == "default":
            return ""
        v = self.get(name)
        if not v:
            return ""
        spec = v["spec"] or {}
        provider = (spec.get("provider") or "").strip().lower()
        if provider == "ollama":
            return _build_ollama_vlm_endpoint(
                spec.get("ollama_server") or "",
                spec.get("model") or "llava",
            )
        return (spec.get("endpoint_url") or "").strip()

    def options_for_dropdown(self) -> list[tuple[str, str]]:
        """Список (display_name, value) для выпадающего списка."""
        return [(v["name"], v["name"]) for v in self.list()]


vlms_manager = VLMManager()
