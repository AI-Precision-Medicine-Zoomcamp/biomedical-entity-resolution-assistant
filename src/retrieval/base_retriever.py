from abc import ABC, abstractmethod

class BaseRetrievalService(ABC):
    """
    Abstract interface for Retrieval Service, defining search endpoints.
    Allows easy swapping of retrieval databases and search implementations.
    """
    @abstractmethod
    def lexical_search(self, query: str, limit: int = 10) -> list[dict]:
        """
        Performs lexical match based on query formatting or normalized lookup aliases.
        """
        pass

    @abstractmethod
    def vector_search(self, query: str, limit: int = 10, min_score: float = 0.70) -> list[dict]:
        """
        Performs semantic vector search.
        """
        pass

    @abstractmethod
    def hybrid_search(self, query: str, limit: int = None) -> list[dict]:
        """
        Combines lexical and vector searches.
        """
        pass
