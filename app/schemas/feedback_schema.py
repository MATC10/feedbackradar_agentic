"""
Schemas para Feedback - Comentarios y reseñas de usuarios.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from dateutil import parser as dateutil_parser


class FeedbackBase(BaseModel):
    """Campos base compartidos de Feedback"""
    author_name: str = Field(..., min_length=1, max_length=200, description="Nombre del autor")
    date: str = Field(..., description="Fecha del comentario (formato: YYYY-MM-DD)")
    text: str = Field(..., min_length=1, description="Texto del feedback")
    platform: str = Field(..., description="Origen: Email, Encuestas, Reviews, etc.")
    
    @field_validator('date')
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Parsea cualquier formato de fecha reconocible y normaliza a YYYY-MM-DD."""
        try:
            parsed = dateutil_parser.parse(v, dayfirst=True)
            return parsed.strftime('%Y-%m-%d')
        except (ValueError, OverflowError):
            raise ValueError(
                f"No se pudo interpretar la fecha '{v}'. "
                "Usa formatos como DD/MM/YYYY, YYYY-MM-DD, DD-MM-YYYY, etc."
            )
    
    @field_validator('platform')
    @classmethod
    def validate_platform(cls, v: str) -> str:
        """Normaliza y valida la plataforma"""
        valid_platforms = {'email', 'encuestas', 'reviews', 'formularios', 'otros'}
        v_lower = v.lower()
        if v_lower not in valid_platforms:
            # Permite valores no estándar pero los registra
            pass
        return v


class FeedbackCreate(FeedbackBase):
    """Schema para crear Feedback (sin ID ni timestamps)"""
    source_file: Optional[str] = Field(None, description="Archivo CSV de origen")


class FeedbackInDB(FeedbackBase):
    """Schema para Feedback almacenado en BD"""
    feedback_id: str = Field(..., description="ID único del feedback")
    source_file: Optional[str] = Field(None, description="Archivo CSV de origen")
    ingested_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp de ingesta")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "feedback_id": "fb_001",
                "author_name": "Laura Gómez",
                "date": "2026-05-10",
                "text": "No consigo completar el pago desde el móvil",
                "platform": "Reviews",
                "source_file": "reviews.csv",
                "ingested_at": "2026-05-12T10:30:00"
            }
        }
    }


class FeedbackResponse(FeedbackInDB):
    """Schema para respuesta de API con Feedback"""
    pass


class FeedbackUploadResponse(BaseModel):
    """Respuesta al subir feedback"""
    success: bool = Field(..., description="Indica si la operación fue exitosa")
    total_processed: int = Field(..., ge=0, description="Total de registros procesados")
    total_inserted: int = Field(..., ge=0, description="Total de registros insertados")
    errors: list[str] = Field(default_factory=list, description="Lista de errores si los hubo")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "total_processed": 150,
                "total_inserted": 148,
                "errors": ["Fila 23: fecha inválida", "Fila 89: texto vacío"]
            }
        }
    }