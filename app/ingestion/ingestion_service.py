"""
Servicio de ingesta de feedback desde CSVs.

Coordina la lectura, validación, normalización, generación de embeddings y persistencia de feedback.
"""

import logging
from pathlib import Path
from typing import List
from datetime import datetime
from pydantic import BaseModel, Field

from app.ingestion.csv_reader import CSVReader
from app.ingestion.normalizer import FeedbackNormalizer
from app.databases.repositories import FeedbackRepository
from app.databases.elasticsearch_client import ElasticsearchClient, ElasticsearchClientError
from app.embeddings.ollama_embeddings import OllamaEmbeddingService, OllamaEmbeddingError
from app.schemas import FeedbackInDB

logger = logging.getLogger(__name__)


class IngestionResult(BaseModel):
    """
    Resultado de un proceso de ingesta.
    
    Contiene métricas y detalles de la operación.
    """
    success: bool = Field(..., description="Indica si la ingesta fue exitosa")
    total_rows: int = Field(..., ge=0, description="Total de filas procesadas")
    valid_rows: int = Field(..., ge=0, description="Filas válidas")
    invalid_rows: int = Field(..., ge=0, description="Filas inválidas")
    inserted_rows: int = Field(..., ge=0, description="Filas insertadas en BD")
    indexed_rows: int = Field(default=0, ge=0, description="Filas indexadas en Elasticsearch")
    errors: List[str] = Field(default_factory=list, description="Lista de errores por fila")
    source_file: str = Field(..., description="Nombre del archivo procesado")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "total_rows": 100,
                "valid_rows": 98,
                "invalid_rows": 2,
                "inserted_rows": 98,
                "indexed_rows": 98,
                "errors": [
                    "Fila 5: Error en 'date': Fecha debe tener formato YYYY-MM-DD",
                    "Fila 23: Campo 'text' está vacío"
                ],
                "source_file": "feedback_2026_05.csv"
            }
        }
    }


class IngestionService:
    """
    Servicio principal de ingesta de feedback.
    
    Coordina todo el proceso desde la lectura del CSV hasta
    la persistencia en MongoDB e indexación en Elasticsearch.
    """
    
    def __init__(self, enable_embeddings: bool = True):
        """
        Inicializa el servicio de ingesta.
        
        Args:
            enable_embeddings: Si True, genera embeddings e indexa en Elasticsearch
        """
        self.csv_reader = CSVReader()
        self.normalizer = FeedbackNormalizer()
        self.enable_embeddings = enable_embeddings
        
        if self.enable_embeddings:
            self.embedding_service = OllamaEmbeddingService()
            logger.info("Servicio de embeddings habilitado")
        else:
            self.embedding_service = None
            logger.info("Servicio de embeddings deshabilitado")
    
    async def _index_feedbacks_in_elasticsearch(
        self,
        feedbacks: List[FeedbackInDB],
        errors: List[str]
    ) -> int:
        """
        Indexa feedbacks en Elasticsearch con sus embeddings.
        
        Args:
            feedbacks: Lista de feedbacks a indexar
            errors: Lista donde se agregan errores si ocurren
            
        Returns:
            Número de documentos indexados exitosamente
        """
        indexed_count = 0
        
        for feedback in feedbacks:
            try:
                # Generar embedding del texto
                embedding = self.embedding_service.embed_text(feedback.text)
                
                # Indexar en Elasticsearch
                await ElasticsearchClient.index_document(
                    feedback_id=feedback.feedback_id,
                    text=feedback.text,
                    platform=feedback.platform,
                    date=datetime.fromisoformat(feedback.date),
                    embedding=embedding
                )
                
                indexed_count += 1
                logger.debug(f"Indexado feedback {feedback.feedback_id} en Elasticsearch")
                
            except OllamaEmbeddingError as e:
                error_msg = f"Error generando embedding para {feedback.feedback_id}: {str(e)}"
                logger.warning(error_msg)
                errors.append(error_msg)
                
            except ElasticsearchClientError as e:
                error_msg = f"Error indexando {feedback.feedback_id} en Elasticsearch: {str(e)}"
                logger.warning(error_msg)
                errors.append(error_msg)
                
            except Exception as e:
                error_msg = f"Error inesperado indexando {feedback.feedback_id}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        logger.info(f"Indexados {indexed_count}/{len(feedbacks)} documentos en Elasticsearch")
        return indexed_count
    
    @staticmethod
    def _detect_encoding(file_path: Path, preferred: str = "utf-8") -> str:
        """Devuelve el primer encoding que consigue leer el archivo sin errores."""
        candidates = [preferred, "utf-8-sig", "latin-1", "cp1252"]
        # Eliminar duplicados manteniendo el orden
        seen = set()
        ordered = [c for c in candidates if not (c in seen or seen.add(c))]
        for enc in ordered:
            try:
                with open(file_path, encoding=enc) as f:
                    f.read()
                return enc
            except (UnicodeDecodeError, LookupError):
                continue
        return "latin-1"  # fallback seguro para texto occidental

    async def ingest_csv(
        self,
        file_path: str | Path,
        encoding: str = "utf-8",
        persist: bool = True
    ) -> IngestionResult:
        """
        Ingesta un archivo CSV completo.

        Proceso:
        1. Lee el CSV
        2. Valida y normaliza cada fila
        3. Persiste feedback válido en MongoDB (si persist=True)
        4. Genera embeddings e indexa en Elasticsearch (si está habilitado)
        5. Devuelve resultado con métricas y errores

        Args:
            file_path: Ruta al archivo CSV
            encoding: Codificación preferida (se autodetecta si falla)
            persist: Si True, guarda en BD. Si False, solo valida.

        Returns:
            IngestionResult con métricas y errores

        Raises:
            FileNotFoundError: Si el archivo no existe
            ValueError: Si el CSV no tiene la estructura correcta
        """
        file_path = Path(file_path)

        # Autodetectar encoding si el preferido no funciona
        encoding = self._detect_encoding(file_path, preferred=encoding)
        logger.info(f"Encoding detectado para {file_path.name}: {encoding}")

        # Validar estructura del CSV primero
        CSVReader.validate_csv_structure(file_path, encoding)

        # Inicializar contadores y listas
        total_rows = 0
        valid_feedbacks: List[FeedbackInDB] = []
        errors: List[str] = []

        # Procesar cada fila
        for row in CSVReader.read_csv(file_path, encoding):
            total_rows += 1
            
            # Normalizar y preparar para BD
            feedback_in_db, error = FeedbackNormalizer.normalize_and_prepare(row)
            
            if error:
                errors.append(error)
            else:
                valid_feedbacks.append(feedback_in_db)
        
        # Métricas
        valid_rows = len(valid_feedbacks)
        invalid_rows = len(errors)
        inserted_rows = 0
        indexed_rows = 0
        
        # Persistir en BD si se solicita
        if persist and valid_feedbacks:
            try:
                # 1. Insertar en MongoDB
                inserted_rows = await FeedbackRepository.insert_many(valid_feedbacks)
                logger.info(f"Insertados {inserted_rows} documentos en MongoDB")
                
                # 2. Generar embeddings e indexar en Elasticsearch (si está habilitado)
                if self.enable_embeddings and self.embedding_service:
                    indexed_rows = await self._index_feedbacks_in_elasticsearch(
                        valid_feedbacks,
                        errors
                    )
                
            except Exception as e:
                error_msg = f"Error al insertar en BD: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                return IngestionResult(
                    success=False,
                    total_rows=total_rows,
                    valid_rows=valid_rows,
                    invalid_rows=invalid_rows,
                    inserted_rows=0,
                    indexed_rows=0,
                    errors=errors,
                    source_file=file_path.name
                )
        
        # Determinar si la ingesta fue exitosa
        # Consideramos exitosa si se procesaron filas y al menos el 80% son válidas
        success = total_rows > 0 and (valid_rows / total_rows >= 0.8 if total_rows > 0 else False)
        
        if persist:
            # Si se pidió persistir, el éxito también depende de que se hayan insertado
            success = success and (inserted_rows == valid_rows)
            
            # Si embeddings están habilitados, informar si hubo problemas (pero no fallar)
            if self.enable_embeddings and indexed_rows < inserted_rows:
                logger.warning(
                    f"Solo se indexaron {indexed_rows}/{inserted_rows} documentos en Elasticsearch"
                )
        
        return IngestionResult(
            success=success,
            total_rows=total_rows,
            valid_rows=valid_rows,
            invalid_rows=invalid_rows,
            inserted_rows=inserted_rows,
            indexed_rows=indexed_rows,
            errors=errors,
            source_file=file_path.name
        )
    
    async def ingest_from_dicts(
        self,
        records: List[dict],
        source_name: str = "gmail"
    ) -> IngestionResult:
        """
        Ingesta una lista de dicts directamente (sin pasar por CSV).

        Útil para el poller de Gmail, que ya tiene los emails en memoria.
        Cada dict debe tener: nombre, fecha, reseña, plataforma.

        Args:
            records: Lista de dicts con los campos de feedback
            source_name: Nombre de la fuente (para source_file en MongoDB)

        Returns:
            IngestionResult con métricas
        """
        total_rows = len(records)
        valid_feedbacks: List[FeedbackInDB] = []
        errors: List[str] = []

        for i, record in enumerate(records, start=1):
            row = {**record, "_source_file": f"{source_name}.csv", "_row_number": i}
            feedback_in_db, error = FeedbackNormalizer.normalize_and_prepare(row)
            if error:
                errors.append(error)
            else:
                valid_feedbacks.append(feedback_in_db)

        valid_rows = len(valid_feedbacks)
        inserted_rows = 0
        indexed_rows = 0

        if valid_feedbacks:
            try:
                inserted_rows = await FeedbackRepository.insert_many(valid_feedbacks)
                logger.info(f"[{source_name}] Insertados {inserted_rows} docs en MongoDB")

                if self.enable_embeddings and self.embedding_service:
                    indexed_rows = await self._index_feedbacks_in_elasticsearch(
                        valid_feedbacks, errors
                    )
            except Exception as e:
                error_msg = f"Error al insertar en BD: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                return IngestionResult(
                    success=False,
                    total_rows=total_rows,
                    valid_rows=valid_rows,
                    invalid_rows=len(errors),
                    inserted_rows=0,
                    indexed_rows=0,
                    errors=errors,
                    source_file=f"{source_name}.csv"
                )

        success = total_rows > 0 and inserted_rows == valid_rows
        return IngestionResult(
            success=success,
            total_rows=total_rows,
            valid_rows=valid_rows,
            invalid_rows=total_rows - valid_rows,
            inserted_rows=inserted_rows,
            indexed_rows=indexed_rows,
            errors=errors,
            source_file=f"{source_name}.csv"
        )

    def validate_csv_only(self, file_path: str | Path, encoding: str = "utf-8") -> IngestionResult:
        """
        Valida un CSV sin persistir en BD (modo dry-run).
        
        Útil para verificar la calidad de los datos antes de ingestarlos.
        
        Args:
            file_path: Ruta al archivo CSV
            encoding: Codificación del archivo
            
        Returns:
            IngestionResult con métricas de validación
        """
        # Usar el método principal con persist=False
        import asyncio
        return asyncio.run(self.ingest_csv(file_path, encoding, persist=False))
    
    async def ingest_multiple_csvs(
        self,
        file_paths: List[str | Path],
        encoding: str = "utf-8",
        persist: bool = True
    ) -> List[IngestionResult]:
        """
        Ingesta múltiples archivos CSV.
        
        Args:
            file_paths: Lista de rutas a archivos CSV
            encoding: Codificación de los archivos
            persist: Si True, guarda en BD
            
        Returns:
            Lista de IngestionResult, uno por cada archivo
        """
        results = []
        
        for file_path in file_paths:
            try:
                result = await self.ingest_csv(file_path, encoding, persist)
                results.append(result)
            except Exception as e:
                # Si falla un archivo, registrar error y continuar con el siguiente
                file_path = Path(file_path)
                results.append(
                    IngestionResult(
                        success=False,
                        total_rows=0,
                        valid_rows=0,
                        invalid_rows=0,
                        inserted_rows=0,
                        indexed_rows=0,
                        errors=[f"Error al procesar archivo: {str(e)}"],
                        source_file=file_path.name
                    )
                )
        
        return results