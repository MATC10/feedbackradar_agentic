"""
Módulo de embeddings.

Proporciona servicios para generar embeddings de texto usando diferentes modelos.
"""

from app.embeddings.ollama_embeddings import OllamaEmbeddingService

__all__ = [
    "OllamaEmbeddingService",
]