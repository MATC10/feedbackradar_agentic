"""
Schemas para AnalysisRun - Ejecuciones de anรกlisis de feedback.
"""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

from app.schemas.insight_schema import InsightResponse
from app.schemas.action_schema import ActionItemResponse


# Tipo literal para estados de anรกlisis
AnalysisStatus = Literal["En Progreso", "Completado", "Fallido"]


class ThemeSummary(BaseModel):
    """Resumen de un tema detectado"""
    theme: str = Field(..., description="Nombre del tema")
    priority: Literal["Crítica", "Alta", "Media", "Baja"] = Field(..., description="Prioridad del tema")
    evidence_count: int = Field(..., ge=0, description="Nรบmero de evidencias encontradas")
    recommendation: str = Field(..., description="Recomendaciรณn para este tema")


class AnalysisRunBase(BaseModel):
    """Campos base de un anรกlisis"""
    executive_summary: str = Field(..., min_length=1, description="Resumen ejecutivo del anรกlisis")
    top_themes: list[ThemeSummary] = Field(default_factory=list, description="Principales temas detectados")
    total_feedback_analyzed: int = Field(..., ge=0, description="Total de feedback analizado")
    status: AnalysisStatus = Field(default="En Progreso", description="Estado del anรกlisis")


class AnalysisRunCreate(BaseModel):
    """Schema para iniciar un anรกlisis"""
    feedback_filter: dict = Field(default_factory=dict, description="Filtros opcionales para el feedback")


class AnalysisRunInDB(AnalysisRunBase):
    """Schema para anรกlisis almacenado en BD"""
    run_id: str = Field(..., description="ID รบnico del anรกlisis")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Fecha de creaciรณn")
    completed_at: datetime | None = Field(None, description="Fecha de finalizaciรณn")
    error_message: str | None = Field(None, description="Mensaje de error si fallรณ")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "run_id": "run_001",
                "executive_summary": "El principal problema detectado estรก relacionado con fallos en pagos",
                "top_themes": [
                    {
                        "theme": "Pagos fallidos",
                        "priority": "Alta",
                        "evidence_count": 15,
                        "recommendation": "Revisar checkout mรณvil"
                    }
                ],
                "total_feedback_analyzed": 150,
                "status": "Completado",
                "created_at": "2026-05-12T10:00:00",
                "completed_at": "2026-05-12T10:15:00",
                "error_message": None
            }
        }
    }


class AnalysisRunResponse(AnalysisRunInDB):
    """Schema para respuesta de API con anรกlisis"""
    pass


class AnalysisRunDetailResponse(AnalysisRunInDB):
    """Respuesta detallada de un anรกlisis con insights y acciones"""
    insights: list[InsightResponse] = Field(default_factory=list, description="Insights generados")
    actions: list[ActionItemResponse] = Field(default_factory=list, description="Acciones creadas")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "run_id": "run_001",
                "executive_summary": "Principales problemas en pagos mรณviles",
                "top_themes": [
                    {
                        "theme": "Pagos fallidos",
                        "priority": "Alta",
                        "evidence_count": 15,
                        "recommendation": "Revisar checkout mรณvil"
                    }
                ],
                "total_feedback_analyzed": 150,
                "status": "Completado",
                "created_at": "2026-05-12T10:00:00",
                "completed_at": "2026-05-12T10:15:00",
                "error_message": None,
                "insights": [],
                "actions": []
            }
        }
    }


class AnalysisRunStartResponse(BaseModel):
    """Respuesta al iniciar un anรกlisis"""
    run_id: str = Field(..., description="ID del anรกlisis iniciado")
    status: AnalysisStatus = Field(..., description="Estado inicial")
    message: str = Field(..., description="Mensaje informativo")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "run_id": "run_001",
                "status": "En Progreso",
                "message": "Anรกlisis iniciado correctamente. Procesando feedback..."
            }
        }
    }


class AnalysisListResponse(BaseModel):
    """Respuesta con lista de anรกlisis"""
    total: int = Field(..., ge=0, description="Total de anรกlisis")
    analyses: list[AnalysisRunResponse] = Field(default_factory=list, description="Lista de anรกlisis")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "total": 1,
                "analyses": [
                    {
                        "run_id": "run_001",
                        "executive_summary": "Anรกlisis de feedback de mayo",
                        "top_themes": [],
                        "total_feedback_analyzed": 150,
                        "status": "Completado",
                        "created_at": "2026-05-12T10:00:00",
                        "completed_at": "2026-05-12T10:15:00",
                        "error_message": None
                    }
                ]
            }
        }
    }