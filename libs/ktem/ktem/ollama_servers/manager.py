"""Менеджер списка серверов Ollama: загрузка из БД, add/update/delete/get/list."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ktem.utils.ollama import check_ollama_available

from .db import OllamaServerTable, engine


class OllamaServerManager:
    """Пул зарегистрированных серверов Ollama."""

    def __init__(self) -> None:
        self._servers: dict[str, dict] = {}
        self.load()

    def load(self) -> None:
        """Загрузить серверы из БД."""
        self._servers = {}
        with Session(engine) as session:
            stmt = select(OllamaServerTable)
            for row in session.execute(stmt).scalars():
                self._servers[row.name] = {
                    "name": row.name,
                    "base_url": row.base_url,
                    "num_ctx": row.num_ctx,
                }

    def list(self) -> list[dict]:
        """Список серверов (name, base_url, num_ctx)."""
        return list(self._servers.values())

    def get(self, name: str) -> dict | None:
        """Получить сервер по имени."""
        return self._servers.get(name)

    def add(self, name: str, base_url: str, num_ctx: int = 8192) -> None:
        """Добавить сервер."""
        from sqlalchemy.exc import IntegrityError

        name = name.strip()
        if not name:
            raise ValueError("Имя сервера не может быть пустым")
        base_url = base_url.strip()
        if not base_url:
            raise ValueError("Ollama API URL не может быть пустым")
        try:
            with Session(engine) as session:
                item = OllamaServerTable(
                    name=name,
                    base_url=base_url,
                    num_ctx=num_ctx,
                )
                session.add(item)
                session.commit()
        except IntegrityError:
            raise ValueError(f"Сервер с именем «{name}» уже существует")
        self.load()

    def update(self, name: str, base_url: str, num_ctx: int) -> None:
        """Обновить сервер."""
        if not name or name not in self._servers:
            raise ValueError(f"Сервер {name!r} не найден")
        with Session(engine) as session:
            item = session.get(OllamaServerTable, name)
            if item:
                item.base_url = base_url.strip()
                item.num_ctx = num_ctx
                session.add(item)
                session.commit()
        self.load()

    def delete(self, name: str) -> None:
        """Удалить сервер."""
        with Session(engine) as session:
            item = session.get(OllamaServerTable, name)
            if item:
                session.delete(item)
                session.commit()
        self.load()

    def check_available(self, name: str) -> tuple[bool, str]:
        """Проверить доступность сервера по имени. Возвращает (ok, message)."""
        s = self.get(name)
        if not s:
            return False, "not_found"
        return check_ollama_available(s["base_url"])

    def options_for_dropdown(self) -> list[tuple[str, str]]:
        """Список (display, value) для выпадающего списка (имя как value)."""
        return [(s["name"], s["name"]) for s in self.list()]


ollama_servers_manager = OllamaServerManager()
