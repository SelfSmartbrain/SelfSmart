"""
RAG (Retrieval-Augmented Generation) pipeline for the Autonomous Agent Platform.

Provides embedding generation, vector storage, text chunking, document ingestion,
and semantic retrieval with reranking capabilities.
"""

from src.rag.chunking import Chunk, ChunkingStrategy, TextChunker
from src.rag.embeddings import EmbeddingService
from src.rag.ingestion import IngestionPipeline, KnowledgeDocument
from src.rag.retriever import RetrievalResult, Retriever
from src.rag.vector_store import VectorStoreManager

__all__ = [
    "Chunk",
    "ChunkingStrategy",
    "EmbeddingService",
    "IngestionPipeline",
    "KnowledgeDocument",
    "RetrievalResult",
    "Retriever",
    "TextChunker",
    "VectorStoreManager",
]
