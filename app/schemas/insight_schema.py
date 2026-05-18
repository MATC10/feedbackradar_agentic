"""
Schemas para Insights - Hallazgos principales del análisis.
"""

from typing import Literal
from pydantic import BaseModel, Field


# Tipo literal para prioridades
PriorityLevel = Literal["Crítica", "Alta", "Media", "Baja"]


class InsightBase(BaseModel):
    """Campos base de un Insight"""
    theme: str = Field(..., min_length=1, max_length=200, description="Tema principal detectado")
    summary: str = Field(..., min_length=1, description="Resumen del insight")
    priority: PriorityLevel = Field(..., description="Nivel de prioridad: Alta, Media, Baja")
    reasoning: str = Field(..., min_length=1, description="Justificación de la prioridad")
    evidence: list[str] = Field(default_factory=list, description="Evidencias textuales del feedback")


class InsightCreate(InsightBase):
    """Schema para crear un Insight"""
    pass


class InsightInDB(InsightBase):
    """Schema para Insight almacenado en BD"""
    insight_id: str = Field(..., description="ID único del insight")
    analysis_run_id: str = Field(..., description="ID del análisis que generó este insight")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "insight_id": "ins_001",
                "analysis_run_id": "run_001",
                "theme": "Pagos fallidos",
                "summary": "Usuarios reportan fallos recurrentes en el proceso de pago móvil",
                "priority": "Alta",
                "reasoning": "Bloquea la conversión y aparece en múltiples plataformas",
                "evidence": [
                    "No consigo completar el pago desde el móvil",
                    "La app se queda cargando al pagar"
                ]
            }
        }
    }


class InsightResponse(InsightInDB):
    """Schema para respuesta de API con Insight"""
    pass


class InsightsListResponse(BaseModel):
    """Respuesta con lista de insights"""
    total: int = Field(..., ge=0, description="Total de insights")
    insights: list[InsightResponse] = Field(default_factory=list, description="Lista de insights")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "total": 3,
                "insights": [
                    {
                        "insight_id": "ins_001",
                        "analysis_run_id": "run_001",
                        "theme": "Pagos fallidos",
                        "summary": "Usuarios reportan fallos en pago móvil",
                        "priority": "Alta",
                        "reasoning": "Bloquea conversión",
                        "evidence": ["No puedo pagar desde móvil"]
                    }
                ]
            }
        }
    }