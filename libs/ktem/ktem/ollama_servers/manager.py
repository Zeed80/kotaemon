"""Менеджер списка серверов Ollama: загрузка из БД, add/update/delete/get/list."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ktem.utils.env_file import persist_ollama_url
from ktem.utils.ollama import check_ollama_available

from .db import OllamaServerTable, engine


def _persist_primary_ollama_url(manager: "OllamaServerManager", url: str) -> None:
    """Записать URL основного сервера Ollama в .env, application_settings и spec реранкера."""
    try:
        persist_ollama_url(url)
        _sync_ollama_reranker_base_url(url)
    except Exception:
        pass


def _sync_ollama_reranker_base_url(url: str) -> None:
    """Обновить base_url реранкера Ollama в БД."""
    try:
        from sqlmodel import Session, select

        from ktem.db.engine import engine
        from ktem.rerankings.db import RerankingTable
        from ktem.rerankings.manager import reranking_models_manager

        with Session(engine) as session:
            result = session.exec(
                select(RerankingTable).where(RerankingTable.name == "ollama")
            )
            row = result.first()
            if row:
                item = row[0] if isinstance(row, (tuple, list)) else row
                spec = dict(item.spec or {})
                spec["base_url"] = url
                item.spec = spec
                session.add(item)
                session.commit()
        reranking_models_manager.load()
    except Exception:
        pass


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
        # При добавлении первого сервера — записать URL в .env
        if len(self._servers) == 1 or name in ("local", "default"):
            _persist_primary_ollama_url(self, base_url)

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
        # При обновлении — сохранить в .env, если единственный или "local"
        servers = list(self._servers.values())
        if len(servers) == 1 or name in ("local", "default"):
            _persist_primary_ollama_url(self, base_url.strip())

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
