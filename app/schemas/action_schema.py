"""
Schemas para ActionItems - Acciones recomendadas generadas por el sistema.
"""

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


# Tipo literal para prioridades
ActionPriority = Literal["Crítica", "Alta", "Media", "Baja"]

# Tipo literal para estados
ActionStatus = Literal["Pendiente", "En Progreso", "Completada", "Cancelada"]


class ActionItemBase(BaseModel):
    """Campos base de una acción"""
    title: str = Field(..., min_length=1, max_length=200, description="Título de la acción")
    description: str = Field(..., min_length=1, description="Descripción detallada de la acción")
    priority: ActionPriority = Field(..., description="Prioridad: Alta, Media, Baja")
    status: ActionStatus = Field(default="Pendiente", description="Estado de la acción")


class ActionItemCreate(ActionItemBase):
    """Schema para crear una acción"""
    pass


class ActionItemInDB(ActionItemBase):
    """Schema para acción almacenada en BD"""
    action_id: str = Field(..., description="ID único de la acción")
    analysis_run_id: str = Field(..., description="ID del análisis que generó esta acción")
    insight_id: str = Field(..., description="ID del insight relacionado")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Fecha de creación")
    # Jira integration fields
    theme_name: Optional[str] = Field(None, description="Nombre del tema relacionado")
    theme_name_normalized: Optional[str] = Field(None, description="Nombre normalizado para deduplicación")
    jira_issue_key: Optional[str] = Field(None, description="Clave de la issue en Jira (ej: KAN-42)")
    jira_issue_url: Optional[str] = Field(None, description="URL directa a la issue en Jira")
    jira_created_at: Optional[datetime] = Field(None, description="Momento de creación en Jira")
    jira_sync_status: Optional[str] = Field(None, description="Estado sync Jira: created | failed | skipped")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "action_id": "act_001",
                "analysis_run_id": "run_001",
                "insight_id": "ins_001",
                "title": "Investigar fallos en pagos móviles",
                "description": "Revisar el checkout móvil y analizar los errores de pago más recientes",
                "priority": "Alta",
                "status": "Pendiente",
                "created_at": "2026-05-12T10:30:00"
            }
        }
    }


class ActionItemUpdate(BaseModel):
    """Schema para actualizar una acción"""
    status: ActionStatus = Field(..., description="Nuevo estado de la acción")


class ActionItemResponse(ActionItemInDB):
    """Schema para respuesta de API con acción"""
    pass


class ActionsListResponse(BaseModel):
    """Respuesta con lista de acciones"""
    total: int = Field(..., ge=0, description="Total de acciones")
    actions: list[ActionItemResponse] = Field(default_factory=list, description="Lista de acciones")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "total": 2,
                "actions": [
                    {
                        "action_id": "act_001",
                        "analysis_run_id": "run_001",
                        "insight_id": "ins_001",
                        "title": "Investigar fallos en pagos móviles",
                        "description": "Revisar checkout móvil",
                        "priority": "Alta",
                        "status": "Pendiente",
                        "created_at": "2026-05-12T10:30:00"
                    }
                ]
            }
        }
    }