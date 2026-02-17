"""Векторное хранилище на PostgreSQL (расширение pgvector).

Используется вместе с той же БД, что и реляционные данные (DATABASE_URL).
Можно комбинировать с Qdrant: например, ретривер по pgvector + кэш в Qdrant.
"""

from __future__ import annotations

from typing import Any, cast

from .base import LlamaIndexVectorStore


def _connection_string_to_params(connection_string: str) -> dict[str, Any]:
    """Извлечь host, port, user, password, database из URL для from_params."""
    from sqlalchemy import make_url

    # Убрать драйвер из схемы для make_url (postgresql+psycopg -> postgresql)
    url_str = connection_string
    for prefix in ("postgresql+psycopg://", "postgresql+asyncpg://"):
        if url_str.startswith(prefix):
            url_str = "postgresql://" + url_str[len(prefix) :]
            break
    url = make_url(url_str)
    return {
        "host": url.host or "localhost",
        "port": url.port or 5432,
        "user": url.username or "kotaemon",
        "password": url.password or "",
        "database": (url.database or "kotaemon"),
    }


class PgvectorVectorStore(LlamaIndexVectorStore):
    """Векторное хранилище на PostgreSQL (pgvector).

    Требует: PostgreSQL с расширением pgvector, connection_string в формате
    postgresql://user:password@host:port/dbname (или postgresql+psycopg://...).
    """

    _li_class = None

    def _get_li_class(self):
        try:
            from llama_index.vector_stores.postgres import (
                PGVectorStore as LIPGVectorStore,
            )
        except ImportError:
            raise ImportError(
                "PgvectorVectorStore requires: "
                "pip install llama-index-vector-stores-postgres pgvector asyncpg"
            )
        return LIPGVectorStore

    def __init__(
        self,
        collection_name: str = "default",
        connection_string: str | None = None,
        table_name: str | None = None,
        schema_name: str = "public",
        embed_dim: int = 1536,
        hybrid_search: bool = False,
        perform_setup: bool = True,
        hnsw_kwargs: dict[str, Any] | None = None,
        **kwargs: Any,
    ):
        self._collection_name = collection_name
        self._connection_string = connection_string
        self._table_name = (table_name or collection_name).lower().replace("-", "_")
        self._schema_name = schema_name.lower()
        self._embed_dim = embed_dim
        self._hybrid_search = hybrid_search
        self._perform_setup = perform_setup
        self._hnsw_kwargs = hnsw_kwargs or {}
        self._kwargs = kwargs

        if not connection_string:
            raise ValueError(
                "PgvectorVectorStore requires connection_string (e.g. from DATABASE_URL)."
            )

        params = _connection_string_to_params(connection_string)
        LIClass = self._get_li_class()
        from_params_kw: dict[str, Any] = {
            "host": params["host"],
            "port": params["port"],
            "user": params["user"],
            "password": params["password"],
            "database": params["database"],
            "table_name": self._table_name,
            "embed_dim": embed_dim,
            **kwargs,
        }
        if self._hnsw_kwargs:
            from_params_kw["hnsw_kwargs"] = self._hnsw_kwargs
        self._client = LIClass.from_params(**from_params_kw)

        from dataclasses import fields

        from llama_index.core.vector_stores.types import VectorStoreQuery

        self._vsq_kwargs = {_.name for _ in fields(VectorStoreQuery)}
        for key in ["query_embedding", "similarity_top_k", "node_ids"]:
            self._vsq_kwargs.discard(key)

        self._client = cast(Any, self._client)

    def delete(self, ids: list[str], **kwargs) -> None:
        """Удалить векторы по id."""
        for node_id in ids:
            self._client.delete(ref_doc_id=node_id, **kwargs)

    def drop(self) -> None:
        """Удалить таблицу векторов (все данные коллекции)."""
        self._client.drop()

    def count(self) -> int:
        """Число векторов в хранилище."""
        if hasattr(self._client, "client") and self._client.client is not None:
            from sqlalchemy import func, select
            from sqlalchemy.orm import Session

            table = getattr(self._client, "_table_class", None)
            if table is None:
                return 0
            engine = getattr(self._client, "_engine", None)
            if engine is None:
                return 0
            with Session(engine) as session:
                r = session.execute(select(func.count()).select_from(table))
                return r.scalar() or 0
        return 0

    def __persist_flow__(self) -> dict[str, Any]:
        return {
            "collection_name": self._collection_name,
            "connection_string": self._connection_string,
            "table_name": self._table_name,
            "schema_name": self._schema_name,
            "embed_dim": self._embed_dim,
            "hybrid_search": self._hybrid_search,
            "perform_setup": self._perform_setup,
            "hnsw_kwargs": self._hnsw_kwargs,
            **self._kwargs,
        }
