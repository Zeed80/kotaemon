"""Составное векторное хранилище: запись в несколько бэкендов, поиск с объединением результатов.

Используется для режима «Qdrant + pgvector»: приоритет качество и скорость ответа —
параллельный запрос к обоим хранилищам и слияние по RRF (Reciprocal Rank Fusion).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from theflow.utils.modules import deserialize

from kotaemon.base import DocumentWithEmbedding

from .base import BaseVectorStore

logger = logging.getLogger(__name__)


def _reciprocal_rank_fusion(
    results_per_store: list[tuple[list[list[float]], list[float], list[str]]],
    top_k: int,
    k: int = 60,
) -> tuple[list[list[float]], list[float], list[str]]:
    """Объединить результаты нескольких хранилищ по RRF.

    RRF score(id) = sum over stores of 1 / (k + rank). k=60 по умолчанию (сглаживание).
    Возвращает top_k уникальных id, отсортированных по убыванию RRF score.
    """
    rrf_scores: dict[str, float] = defaultdict(float)
    # (embedding, score, id) по id для финальной сборки
    id_to_embedding: dict[str, list[float]] = {}
    id_to_original_score: dict[str, float] = {}

    for embeddings, scores, ids in results_per_store:
        for rank, (emb, score, id_) in enumerate(zip(embeddings, scores, ids, strict=False)):
            rrf_scores[id_] += 1.0 / (k + rank + 1)
            if id_ not in id_to_embedding:
                id_to_embedding[id_] = emb
                id_to_original_score[id_] = score

    sorted_ids = sorted(rrf_scores.keys(), key=lambda x: -rrf_scores[x])[:top_k]
    out_embeddings = [id_to_embedding[id_] for id_ in sorted_ids]
    out_scores = [rrf_scores[id_] for id_ in sorted_ids]
    return out_embeddings, out_scores, sorted_ids


class CompositeVectorStore(BaseVectorStore):
    """Векторное хранилище, объединяющее несколько бэкендов.

    - add/delete: выполняются для всех хранилищ.
    - query: запрос ко всем параллельно, результаты объединяются по RRF (качество и скорость).
    """

    def __init__(
        self,
        store_configs: list[dict[str, Any]],
        collection_name: str = "default",
        **kwargs: Any,
    ):
        if not store_configs:
            raise ValueError("CompositeVectorStore requires at least one store_configs entry.")
        self._collection_name = collection_name
        self._store_configs = store_configs
        self._stores: list[BaseVectorStore] = []
        for conf in store_configs:
            c = dict(conf)
            c["collection_name"] = collection_name
            try:
                store = deserialize(c, safe=False)
                self._stores.append(store)
            except Exception as e:
                logger.warning("CompositeVectorStore: skip store %s: %s", c.get("__type__"), e)

        if not self._stores:
            raise ValueError("CompositeVectorStore: no store could be initialized.")

    def add(
        self,
        embeddings: list[list[float]] | list[DocumentWithEmbedding],
        metadatas: list[dict] | None = None,
        ids: list[str] | None = None,
    ) -> list[str]:
        result_ids: list[str] | None = None
        for store in self._stores:
            try:
                out = store.add(embeddings, metadatas=metadatas, ids=ids)
                if result_ids is None:
                    result_ids = out
            except Exception as e:
                logger.warning("CompositeVectorStore add to %s: %s", type(store).__name__, e)
        return result_ids or []

    def delete(self, ids: list[str], **kwargs) -> None:
        for store in self._stores:
            try:
                store.delete(ids, **kwargs)
            except Exception as e:
                logger.warning("CompositeVectorStore delete from %s: %s", type(store).__name__, e)

    def query(
        self,
        embedding: list[float],
        top_k: int = 1,
        ids: list[str] | None = None,
        **kwargs,
    ) -> tuple[list[list[float]], list[float], list[str]]:
        # Запрашиваем у каждого хранилища больше кандидатов для RRF (Reciprocal Rank Fusion)
        # Больше кандидатов = лучше качество объединения, но медленнее
        # Для качества: top_k * 4-5; для скорости: top_k * 2-3
        fetch_k = min(top_k * 4, 100)  # оптимизировано для качества: больше кандидатов для лучшего RRF
        results_per_store: list[tuple[list[list[float]], list[float], list[str]]] = []

        def query_one(s: BaseVectorStore) -> tuple[list[list[float]], list[float], list[str]]:
            return s.query(embedding, top_k=fetch_k, ids=ids, **kwargs)

        with ThreadPoolExecutor(max_workers=len(self._stores)) as executor:
            futures = {executor.submit(query_one, s): s for s in self._stores}
            for future in as_completed(futures):
                try:
                    results_per_store.append(future.result())
                except Exception as e:
                    logger.warning("CompositeVectorStore query: %s", e)

        if not results_per_store:
            return [], [], []
        if len(results_per_store) == 1:
            emb, scores, id_list = results_per_store[0]
            return emb[:top_k], scores[:top_k], id_list[:top_k]
        return _reciprocal_rank_fusion(results_per_store, top_k=top_k)

    def drop(self) -> None:
        for store in self._stores:
            try:
                store.drop()
            except Exception as e:
                logger.warning("CompositeVectorStore drop %s: %s", type(store).__name__, e)

    def __persist_flow__(self) -> dict[str, Any]:
        return {
            "store_configs": self._store_configs,
            "collection_name": self._collection_name,
        }
