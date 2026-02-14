from abc import ABC, abstractmethod

from kotaemon.base import Document


class BaseDocumentStore(ABC):
    """A document store is in charged of storing and managing documents"""

    @abstractmethod
    def __init__(self, *args, **kwargs): ...

    @abstractmethod
    def add(
        self,
        docs: Document | list[Document],
        ids: list[str] | str | None = None,
        **kwargs,
    ):
        """Add document into document store

        Args:
            docs: Document or list of documents
            ids: List of ids of the documents. Optional, if not set will use doc.doc_id
        """
        ...

    @abstractmethod
    def get(self, ids: list[str] | str) -> list[Document]:
        """Get document by id"""
        ...

    @abstractmethod
    def get_all(self) -> list[Document]:
        """Get all documents"""
        ...

    @abstractmethod
    def count(self) -> int:
        """Count number of documents"""
        ...

    @abstractmethod
    def query(
        self, query: str, top_k: int = 10, doc_ids: list | None = None
    ) -> list[Document]:
        """Search document store using search query"""
        ...

    @abstractmethod
    def delete(self, ids: list[str] | str):
        """Delete document by id"""
        ...

    @abstractmethod
    def drop(self):
        """Drop the document store"""
        ...
