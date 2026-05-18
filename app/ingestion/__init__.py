"""
Módulo de ingesta de datos.

Proporciona funcionalidades para leer, validar y normalizar datos
desde diferentes fuentes (principalmente CSVs).
"""

from app.ingestion.csv_reader import CSVReader
from app.ingestion.normalizer import FeedbackNormalizer
from app.ingestion.ingestion_service import IngestionService, IngestionResult

__all__ = [
    "CSVReader",
    "FeedbackNormalizer",
    "IngestionService",
    "IngestionResult",
]