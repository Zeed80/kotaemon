"""Ollama reranking via embedding API.

Reranker models in Ollama (e.g. qwen3-reranker, bge-reranker-v2-m3) are used through
the /api/embed endpoint: for each (query, document) pair we send a single string
(query + separator + document) and use the first dimension of the returned embedding
as the relevance score.
"""

from __future__ import annotations

import logging

import requests

from flowsettings_config import config
from kotaemon.base import Document, Param

from .base import BaseReranking

logger = logging.getLogger(__name__)

# Размер батча для запросов к /api/embed (ограничение Ollama/модели)
DEFAULT_BATCH_SIZE = 16


class OllamaReranking(BaseReranking):
    """Reranking через Ollama (модели qwen3-reranker, bge-reranker-v2-m3 и др.).

    Использует endpoint /api/embed: для каждой пары (query, document) передаётся
    одна строка (query + separator + document), первый элемент embedding трактуется
    как relevance score.

    Модели: qwen3-reranker, bge-reranker-v2-m3, bge-reranker-large и др.
    См. https://ollama.com/search?q=rerank
    """

    base_url: str = Param(
        default="",
        help="Base URL Ollama (например http://localhost:11434). По умолчанию — KH_OLLAMA_URL из настроек.",
    )
    model_name: str = Param(
        "qwen3-reranker",
        help="Имя модели в Ollama (например qwen3-reranker, bge-reranker-v2-m3).",
        required=True,
    )
    query_doc_separator: str = Param(
        " [SEP] ",
        help="Разделитель между запросом и документом в строке для embed.",
    )
    batch_size: int = Param(
        DEFAULT_BATCH_SIZE,
        help="Сколько пар (query, doc) отправлять в одном запросе к /api/embed.",
    )

    def run(self, documents: list[Document], query: str) -> list[Document]:
        """Переранжировать документы по релевантности к query через Ollama embed."""
        if not documents:
            return []

        raw = self.base_url or config("KH_OLLAMA_URL", default="http://localhost:11434")
        base = raw.rstrip("/").replace("/v1", "")
        if not base:
            logger.warning("Ollama base URL не задан. Пропуск reranking.")
            return documents

        embed_url = f"{base}/api/embed"
        compressed_docs: list[Document] = []
        sep = self.query_doc_separator

        for start in range(0, len(documents), self.batch_size):
            batch = documents[start : start + self.batch_size]
            inputs = [query + sep + (d.content or "") for d in batch]

            try:
                resp = requests.post(
                    embed_url,
                    json={"model": self.model_name, "input": inputs},
                    timeout=120,
                )
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as e:
                logger.exception("Ollama embed запрос не удался: %s", e)
                return documents

            embeddings = data.get("embeddings") or []
            if len(embeddings) != len(batch):
                logger.warning(
                    "Ollama вернул %d embeddings, ожидалось %d",
                    len(embeddings),
                    len(batch),
                )
                embeddings = embeddings[: len(batch)]

            for doc, emb in zip(batch, embeddings, strict=False):
                if isinstance(emb, list) and len(emb) > 0:
                    score = float(emb[0])
                else:
                    score = 0.0
                doc.metadata["reranking_score"] = score
                compressed_docs.append(doc)

        compressed_docs.sort(
            key=lambda x: x.metadata.get("reranking_score", 0.0),
            reverse=True,
        )
        return compressed_docs
