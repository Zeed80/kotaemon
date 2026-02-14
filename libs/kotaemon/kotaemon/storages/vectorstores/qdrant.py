from typing import Any, cast

from .base import LlamaIndexVectorStore


def _ensure_li_qdrant_private_attrs(
    li_store: Any,
    collection_name: str,
    qdrant_client: Any = None,
) -> None:
    """Ensure LI QdrantVectorStore has all PrivateAttr (workaround: parent init clears them)."""
    private = getattr(li_store, "__pydantic_private__", None)
    if private is None:
        return
    if qdrant_client is not None:
        if "_client" not in private:
            private["_client"] = qdrant_client
        if "_aclient" not in private:
            private["_aclient"] = None
    attrs_defaults: list[tuple[str, Any]] = [
        ("_collection_initialized", None),
        ("_dense_config", None),
        ("_sparse_config", None),
        ("_quantization_config", None),
        ("_legacy_vector_format", None),
        ("_shard_key_selector_fn", None),
        ("_shard_keys", None),
        ("_shard_number", None),
        ("_sharding_method", None),
        ("_replication_factor", None),
        ("_write_consistency_factor", None),
    ]
    for attr, default in attrs_defaults:
        if attr not in private:
            private[attr] = default
    if private.get("_collection_initialized") is None:
        try:
            exists = li_store._collection_exists(collection_name)
        except Exception:
            exists = False
        private["_collection_initialized"] = exists


class QdrantVectorStore(LlamaIndexVectorStore):
    _li_class = None

    def _get_li_class(self):
        try:
            from llama_index.vector_stores.qdrant import (
                QdrantVectorStore as LIQdrantVectorStore,
            )
        except ImportError:
            raise ImportError(
                "Please install missing package: "
                "'pip install llama-index-vector-stores-qdrant'"
            )

        return LIQdrantVectorStore

    def __init__(
        self,
        collection_name,
        url: str | None = None,
        api_key: str | None = None,
        path: str | None = None,
        client_kwargs: dict | None = None,
        enable_hybrid: bool = False,
        fastembed_sparse_model: str | None = None,
        **kwargs: Any,
    ):
        self._collection_name = collection_name
        self._url = url
        self._api_key = api_key
        self._path = path
        self._client_kwargs = client_kwargs
        self._enable_hybrid = enable_hybrid
        self._fastembed_sparse_model = fastembed_sparse_model
        self._kwargs = kwargs

        qdrant_client_for_workaround: Any = None
        li_kwargs = {
            "enable_hybrid": enable_hybrid,
            "fastembed_sparse_model": fastembed_sparse_model,
            **kwargs,
        }
        if path:
            from qdrant_client import QdrantClient

            qdrant_client_for_workaround = QdrantClient(path=path)
            super().__init__(
                collection_name=collection_name,
                client=qdrant_client_for_workaround,
                **li_kwargs,
            )
        else:
            qdrant_client_for_workaround = kwargs.get("client")
            super().__init__(
                collection_name=collection_name,
                url=url,
                api_key=api_key,
                client_kwargs=client_kwargs,
                **li_kwargs,
            )
        from llama_index.vector_stores.qdrant import (
            QdrantVectorStore as LIQdrantVectorStore,
        )

        self._client = cast(LIQdrantVectorStore, self._client)

        # Workaround: parent init clears PrivateAttr when client= is passed (LlamaIndex/Pydantic v2)
        _ensure_li_qdrant_private_attrs(
            self._client, collection_name, qdrant_client=qdrant_client_for_workaround
        )

    def delete(self, ids: list[str], **kwargs):
        """Delete vector embeddings from vector stores

        Args:
            ids: List of ids of the embeddings to be deleted
            kwargs: meant for vectorstore-specific parameters
        """
        from qdrant_client import models

        self._client.client.delete(
            collection_name=self._collection_name,
            points_selector=models.PointIdsList(
                points=ids,
            ),
            **kwargs,
        )

    def drop(self):
        """Delete entire collection from vector stores"""
        self._client.client.delete_collection(self._collection_name)

    def count(self) -> int:
        return self._client.client.count(
            collection_name=self._collection_name, exact=True
        ).count

    def __persist_flow__(self):
        return {
            "collection_name": self._collection_name,
            "url": self._url,
            "api_key": self._api_key,
            "path": self._path,
            "client_kwargs": self._client_kwargs,
            "enable_hybrid": self._enable_hybrid,
            "fastembed_sparse_model": self._fastembed_sparse_model,
            **self._kwargs,
        }
