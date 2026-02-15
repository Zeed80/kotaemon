"""Автообнаружение Ollama на хосте."""

from __future__ import annotations

import logging
from typing import Any

from theflow.settings import settings as flowsettings

from ktem.ollama_servers import ollama_servers_manager
from ktem.utils.ollama import check_ollama_available

logger = logging.getLogger(__name__)

# Кандидаты URL для поиска Ollama (хост:порт или полный URL)
_OLLAMA_CANDIDATES = [
    "http://localhost:11434",
    "http://127.0.0.1:11434",
    "http://host.docker.internal:11434",
    "http://172.17.0.1:11434",
    "http://192.168.1.1:11434",
    "http://192.168.0.1:11434",
]


def _get_ollama_candidates() -> list[str]:
    """Собрать список кандидатов для сканирования, включая KH_OLLAMA_URL из .env."""
    candidates = list(_OLLAMA_CANDIDATES)
    env_url = getattr(flowsettings, "KH_OLLAMA_URL", None)
    if env_url and isinstance(env_url, str):
        url = env_url.strip().rstrip("/")
        if url:
            url = url.replace("/v1/", "").replace("/v1", "").rstrip("/")
            if url and "11434" in url and url not in candidates:
                candidates.insert(0, url)
    return candidates


def _normalize_base_url(url: str) -> str:
    """Нормализовать URL до формата с /v1/ для единообразия."""
    u = url.strip().rstrip("/")
    if not u:
        return ""
    if u.endswith("/api"):
        u = u[:-4]
    if u.endswith("/v1"):
        u = u[:-3]
    if not u.endswith("/v1"):
        u = f"{u}/v1"
    return f"{u}/"


def discover_ollama_servers() -> list[dict[str, Any]]:
    """Сканировать типичные адреса и вернуть список найденных Ollama.

    Учитывает KH_OLLAMA_URL из .env (важно для Docker).

    Returns:
        Список {"url": str, "base_url": str} для каждого найденного сервера.
    """
    found: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    candidates = _get_ollama_candidates()

    for candidate in candidates:
        base = candidate.replace("/v1", "").rstrip("/")
        if base in seen_urls:
            continue
        ok, _ = check_ollama_available(f"{base}/v1/")
        if ok:
            seen_urls.add(base)
            found.append(
                {
                    "url": candidate,
                    "base_url": _normalize_base_url(candidate),
                }
            )

    return found


def _normalize_for_compare(url: str) -> str:
    """Нормализовать URL для сравнения (без /v1/, без trailing /)."""
    u = url.strip().rstrip("/").replace("/v1", "").replace("/api", "")
    return u.rstrip("/")


def auto_add_discovered_ollama() -> tuple[int, list[str]]:
    """Добавить обнаруженные Ollama в список серверов, если их ещё нет.

    Returns:
        (количество добавленных, список имён добавленных серверов).
    """
    discovered = discover_ollama_servers()
    existing_norm = {
        _normalize_for_compare(s["base_url"]): s["name"]
        for s in ollama_servers_manager.list()
    }
    added: list[str] = []
    existing_names = {s["name"] for s in ollama_servers_manager.list()}
    for item in discovered:
        norm = _normalize_for_compare(item["base_url"])
        if norm in existing_norm:
            continue
        base_name = _url_to_server_name(item["base_url"])
        if not base_name:
            continue
        name = base_name
        idx = 1
        while name in existing_names:
            name = f"{base_name}-{idx}"
            idx += 1
        existing_names.add(name)
        try:
            ollama_servers_manager.add(
                name=name,
                base_url=item["base_url"],
                num_ctx=8192,
            )
            added.append(name)
        except ValueError as e:
            logger.debug("Ollama auto-add skip %s: %s", name, e)

    return len(added), added


def _url_to_server_name(url: str) -> str:
    """Сгенерировать короткое имя сервера из URL."""
    u = url.replace("http://", "").replace("https://", "").rstrip("/")
    u = u.split("/")[0]
    if ":" in u:
        host, port = u.rsplit(":", 1)
        if port == "11434":
            return (
                host.replace(".", "-")
                if host not in ("localhost", "127.0.0.1")
                else "local"
            )
        return u.replace(".", "-").replace(":", "-")
    return u.replace(".", "-") if u not in ("localhost", "127.0.0.1") else "local"
