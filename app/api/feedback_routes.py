"""
app/api/feedback_routes.py

Endpoints para la gestión de feedback.
"""

import logging
from typing import List
from pathlib import Path
import tempfile
import os

from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pydantic import BaseModel, Field

from app.ingestion.ingestion_service import IngestionService, IngestionResult

logger = logging.getLogger(__name__)

router = APIRouter()


class UploadResponse(BaseModel):
    """Respuesta del endpoint de upload de feedback."""
    
    success: bool = Field(..., description="Indica si la operación fue exitosa")
    files_processed: int = Field(..., ge=0, description="Número de archivos procesados")
    total_rows: int = Field(..., ge=0, description="Total de filas procesadas")
    valid_rows: int = Field(..., ge=0, description="Filas válidas")
    invalid_rows: int = Field(..., ge=0, description="Filas inválidas")
    inserted_rows: int = Field(..., ge=0, description="Filas insertadas en BD")
    indexed_rows: int = Field(default=0, ge=0, description="Filas indexadas en Elasticsearch")
    errors: List[str] = Field(default_factory=list, description="Errores encontrados")
    results: List[IngestionResult] = Field(default_factory=list, description="Resultados por archivo")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "files_processed": 2,
                "total_rows": 150,
                "valid_rows": 148,
                "invalid_rows": 2,
                "inserted_rows": 148,
                "indexed_rows": 148,
                "errors": [
                    "archivo1.csv - Fila 5: Fecha inválida",
                    "archivo2.csv - Fila 23: Campo 'text' vacío"
                ],
                "results": []
            }
        }
    }


def validate_csv_file(file: UploadFile) -> None:
    """
    Valida que el archivo sea un CSV válido.
    
    Args:
        file: Archivo subido
        
    Raises:
        HTTPException: Si el archivo no es válido
    """
    # Validar extensión
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo no tiene nombre"
        )
    
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El archivo '{file.filename}' no es un CSV. Solo se aceptan archivos .csv"
        )
    
    # Validar content type (opcional, algunos navegadores no lo envían correctamente)
    if file.content_type and not file.content_type in ['text/csv', 'application/csv', 'text/plain']:
        logger.warning(
            f"Content-Type inesperado para {file.filename}: {file.content_type}. "
            f"Se procederá igualmente."
        )


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Subir archivos CSV de feedback",
    description="Permite subir uno o varios archivos CSV con feedback de usuarios para su procesamiento e ingesta."
)
async def upload_feedback(
    files: List[UploadFile] = File(..., description="Uno o más archivos CSV"),
    enable_embeddings: bool = True
) -> UploadResponse:
    """
    Endpoint para subir y procesar archivos CSV de feedback.
    
    Proceso:
    1. Valida que los archivos sean CSV
    2. Guarda temporalmente los archivos
    3. Procesa cada archivo con IngestionService
    4. Retorna resultados agregados
    
    Args:
        files: Lista de archivos CSV a procesar
        enable_embeddings: Si True, genera embeddings e indexa en Elasticsearch
        
    Returns:
        UploadResponse con estadísticas agregadas de todos los archivos
        
    Raises:
        HTTPException: Si hay errores en la validación o procesamiento
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se han proporcionado archivos"
        )
    
    logger.info(f"Recibidos {len(files)} archivos para procesar")
    
    # Validar todos los archivos primero
    for file in files:
        validate_csv_file(file)
    
    # Inicializar servicio de ingesta
    ingestion_service = IngestionService(enable_embeddings=enable_embeddings)
    
    # Procesar cada archivo
    results: List[IngestionResult] = []
    temp_files: List[Path] = []
    
    try:
        for file in files:
            logger.info(f"Procesando archivo: {file.filename}")
            
            # Guardar temporalmente el archivo
            with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.csv') as temp_file:
                content = await file.read()
                temp_file.write(content)
                temp_path = Path(temp_file.name)
                temp_files.append(temp_path)
            
            try:
                # Procesar el archivo
                result = await ingestion_service.ingest_csv(
                    file_path=temp_path,
                    encoding='utf-8',
                    persist=True
                )
                
                # Actualizar nombre del archivo en el resultado
                result.source_file = file.filename or "unknown.csv"
                results.append(result)
                
                logger.info(
                    f"Archivo {file.filename} procesado: "
                    f"{result.valid_rows}/{result.total_rows} filas válidas"
                )
                
            except Exception as e:
                error_msg = f"Error procesando {file.filename}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                
                # Crear resultado de error para este archivo
                results.append(
                    IngestionResult(
                        success=False,
                        total_rows=0,
                        valid_rows=0,
                        invalid_rows=0,
                        inserted_rows=0,
                        indexed_rows=0,
                        errors=[error_msg],
                        source_file=file.filename or "unknown.csv"
                    )
                )
    
    finally:
        # Limpiar archivos temporales
        for temp_path in temp_files:
            try:
                if temp_path.exists():
                    os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"No se pudo eliminar archivo temporal {temp_path}: {e}")
    
    # Agregar resultados
    total_rows = sum(r.total_rows for r in results)
    valid_rows = sum(r.valid_rows for r in results)
    invalid_rows = sum(r.invalid_rows for r in results)
    inserted_rows = sum(r.inserted_rows for r in results)
    indexed_rows = sum(r.indexed_rows for r in results)
    
    # Recopilar todos los errores con prefijo del archivo
    all_errors = []
    for result in results:
        for error in result.errors:
            all_errors.append(f"{result.source_file} - {error}")
    
    # Determinar éxito general
    success = all(r.success for r in results) and len(results) > 0
    
    response = UploadResponse(
        success=success,
        files_processed=len(results),
        total_rows=total_rows,
        valid_rows=valid_rows,
        invalid_rows=invalid_rows,
        inserted_rows=inserted_rows,
        indexed_rows=indexed_rows,
        errors=all_errors,
        results=results
    )
    
    logger.info(
        f"Procesamiento completado: {len(results)} archivos, "
        f"{inserted_rows} filas insertadas, {indexed_rows} indexadas"
    )
    
    return response


@router.get(
    "/stats",
    summary="Obtener estadísticas de feedback",
    description="Retorna estadísticas básicas del feedback almacenado"
)
async def get_feedback_stats():
    """
    Obtiene estadísticas básicas del feedback almacenado.
    
    Returns:
        Estadísticas del feedback
    """
    # TODO: Implementar cuando tengamos repositorios con métodos de estadísticas
    return {
        "message": "Endpoint de estadísticas - Pendiente de implementación",
        "total_feedback": 0,
        "by_platform": {}
    }