"""Утилиты для согласования размерности эмбеддингов и векторного хранилища."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def get_embedding_dimension(embedding: Any) -> int | None:
    """Получить размерность эмбеддингов модели.

    Args:
        embedding: Модель эмбеддингов (BaseEmbeddings).

    Returns:
        Размерность вектора или None при ошибке.
    """
    try:
        result = embedding(["test"])
        if result and len(result) > 0 and hasattr(result[0], "embedding"):
            return len(result[0].embedding)
    except Exception as e:
        logger.debug("Failed to get embedding dimension: %s", e)
    return None


def get_pgvector_collection_dimension(vector_store: Any) -> int | None:
    """Получить размерность векторов в PgvectorVectorStore (из конфига)."""
    if getattr(vector_store, "_embed_dim", None) is not None and getattr(
        vector_store, "_connection_string", None
    ):
        return int(vector_store._embed_dim)
    return None


def get_composite_collection_dimension(vector_store: Any) -> int | None:
    """Получить размерность из первого вложенного хранилища (CompositeVectorStore)."""
    stores = getattr(vector_store, "_stores", None)
    if not stores:
        return None
    for s in stores:
        dim = get_pgvector_collection_dimension(s) or get_qdrant_collection_dimension(s)
        if dim is not None:
            return dim
    return None


def get_qdrant_collection_dimension(vector_store: Any) -> int | None:
    """Получить размерность плотных (dense) векторов в коллекции Qdrant.

    Args:
        vector_store: QdrantVectorStore (kotaemon) или LlamaIndex QdrantVectorStore.

    Returns:
        Размерность или None, если не Qdrant или коллекция не существует.
    """
    try:
        li_store = getattr(vector_store, "_client", vector_store)
        if li_store is None:
            return None
        qdrant_client = getattr(li_store, "client", li_store)
        if qdrant_client is None:
            return None
        collection_name = getattr(vector_store, "_collection_name", None) or getattr(
            li_store, "collection_name", None
        )
        if not collection_name:
            return None
        if not qdrant_client.collection_exists(collection_name):
            return None
        info = qdrant_client.get_collection(collection_name)
        config = getattr(info, "config", None)
        if config is None:
            return None
        params = getattr(config, "params", None)
        if params is None:
            return None
        vectors = getattr(params, "vectors", None)
        if vectors is None:
            return None
        if isinstance(vectors, dict):
            for _name, vec_config in vectors.items():
                if vec_config is not None and hasattr(vec_config, "size"):
                    return vec_config.size
            return None
        if hasattr(vectors, "size"):
            return vectors.size
    except Exception as e:
        logger.debug("Failed to get Qdrant collection dimension: %s", e)
    return None


def resolve_embedding_for_collection(
    embedding,
    embedding_name: str,
    vector_store: Any,
    embedding_models_manager: Any,
) -> tuple[Any, str]:
    """Подобрать модель эмбеддингов под размерность коллекции.

    Если выбранная модель не совпадает по размерности с коллекцией,
    автоматически выбирается модель с подходящей размерностью.

    Args:
        embedding: Текущая модель эмбеддингов.
        embedding_name: Имя текущей модели.
        vector_store: Векторное хранилище (Qdrant).
        embedding_models_manager: Менеджер моделей эмбеддингов.

    Returns:
        (embedding, used_model_name): модель и имя используемой модели.
    """
    col_dim = (
        get_pgvector_collection_dimension(vector_store)
        or get_qdrant_collection_dimension(vector_store)
        or get_composite_collection_dimension(vector_store)
    )
    if col_dim is None:
        return embedding, embedding_name

    emb_dim = get_embedding_dimension(embedding)
    if emb_dim is None:
        return embedding, embedding_name

    if emb_dim == col_dim:
        return embedding, embedding_name

    logger.info(
        "Embedding dimension mismatch: collection=%d, model %s=%d. "
        "Searching for matching embedding model.",
        col_dim,
        embedding_name,
        emb_dim,
    )

    for name, model in embedding_models_manager.options().items():
        if name == embedding_name:
            continue
        dim = get_embedding_dimension(model)
        if dim == col_dim:
            logger.info("Using embedding model %s (dim=%d) for retrieval.", name, dim)
            return model, name

    logger.warning(
        "No embedding model with dimension %d found. "
        "Retrieval may fail. Consider re-indexing with current embedding model.",
        col_dim,
    )
    return embedding, embedding_name
