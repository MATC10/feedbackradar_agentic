"""
app/api/analysis_routes.py

Endpoints para ejecutar y consultar análisis de feedback.
"""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, Field

from app.agents.graph import run_feedback_analysis_workflow, get_workflow_summary
from app.databases.repositories import FeedbackRepository, InsightRepository, ActionRepository
from app.schemas import InsightInDB, ActionItemInDB

logger = logging.getLogger(__name__)

router = APIRouter()


class AnalysisRequest(BaseModel):
    """Request para ejecutar análisis de feedback."""
    limit: Optional[int] = Field(default=100, ge=1, le=1000, description="Límite de feedback a analizar")
    days: Optional[int] = Field(default=None, ge=1, description="Días hacia atrás (None = todo el feedback)")


class AnalysisResponse(BaseModel):
    """Respuesta del análisis de feedback."""
    success: bool = Field(..., description="Indica si el análisis fue exitoso")
    feedback_analyzed: int = Field(..., ge=0, description="Cantidad de feedback analizado")
    themes_detected: int = Field(..., ge=0, description="Temas detectados")
    evidence_count: int = Field(..., ge=0, description="Evidencias recuperadas")
    themes_prioritized: int = Field(..., ge=0, description="Temas priorizados")
    recommendations_generated: int = Field(..., ge=0, description="Recomendaciones generadas")
    actions_created: int = Field(..., ge=0, description="Acciones creadas")
    insights_created: int = Field(..., ge=0, description="Insights creados")
    jira_issues_created: List[dict] = Field(default_factory=list, description="Tickets Jira creados")
    executive_summary: Optional[dict] = Field(None, description="Resumen ejecutivo estructurado")
    errors: List[str] = Field(default_factory=list, description="Errores durante el análisis")
    execution_time_seconds: Optional[float] = Field(None, description="Tiempo de ejecución")


@router.post(
    "/run",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Ejecutar análisis de feedback",
    description="Ejecuta el workflow completo de análisis con agentes LangGraph"
)
async def run_analysis(request: AnalysisRequest = AnalysisRequest()) -> AnalysisResponse:
    """
    Ejecuta el análisis completo de feedback usando el workflow de agentes.
    
    Proceso:
    1. Recupera feedback de MongoDB
    2. Ejecuta workflow de agentes (detección, evidencia, priorización, recomendaciones)
    3. Persiste insights y acciones
    4. Retorna resumen de resultados
    
    Args:
        request: Parámetros del análisis (limit, days)
        
    Returns:
        AnalysisResponse con métricas del análisis ejecutado
    """
    start_time = datetime.utcnow()
    logger.info(f"=== Iniciando análisis de feedback (limit={request.limit}, days={request.days}) ===")
    
    try:
        # 1. Recuperar feedback de MongoDB
        if request.days:
            feedbacks = await FeedbackRepository.find_recent(days=request.days, limit=request.limit)
            logger.info(f"Recuperados {len(feedbacks)} feedbacks de los últimos {request.days} días")
        else:
            feedbacks = await FeedbackRepository.find_all(limit=request.limit)
            logger.info(f"Recuperados {len(feedbacks)} feedbacks (todos)")
        
        if not feedbacks:
            logger.warning("No hay feedback disponible para analizar")
            return AnalysisResponse(
                success=False,
                feedback_analyzed=0,
                themes_detected=0,
                evidence_count=0,
                themes_prioritized=0,
                recommendations_generated=0,
                actions_created=0,
                insights_created=0,
                errors=["No hay feedback disponible para analizar"],
                execution_time_seconds=0.0
            )
        
        # 2. Preparar feedback para el workflow
        feedback_items = [
            {
                "feedback_id": fb.get("feedback_id"),
                "text": fb.get("text"),
                "platform": fb.get("platform"),
                "date": fb.get("date"),
                "author_name": fb.get("author_name")
            }
            for fb in feedbacks
        ]
        
        # 3. Ejecutar workflow de agentes
        logger.info(f"Ejecutando workflow con {len(feedback_items)} items")
        final_state = await run_feedback_analysis_workflow(feedback_items)
        
        # 4. Obtener resumen del workflow
        summary = get_workflow_summary(final_state)
        
        # 5. Calcular tiempo de ejecución
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds()
        
        logger.info(f"=== Análisis completado en {execution_time:.2f}s ===")
        
        executive_summary = final_state.get("executive_summary") or None

        return AnalysisResponse(
            success=summary["workflow_completed"] and not summary["has_errors"],
            feedback_analyzed=len(feedback_items),
            themes_detected=summary["themes_detected"],
            evidence_count=summary["evidence_count"],
            themes_prioritized=summary["themes_prioritized"],
            recommendations_generated=summary["recommendations_generated"],
            actions_created=summary["actions_created"],
            insights_created=summary["insights_created"],
            jira_issues_created=final_state.get("jira_issues_created", []),
            executive_summary=executive_summary if executive_summary else None,
            errors=final_state.get("errors", []),
            execution_time_seconds=execution_time
        )
        
    except Exception as e:
        error_msg = f"Error ejecutando análisis: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds()
        
        return AnalysisResponse(
            success=False,
            feedback_analyzed=0,
            themes_detected=0,
            evidence_count=0,
            themes_prioritized=0,
            recommendations_generated=0,
            actions_created=0,
            insights_created=0,
            errors=[error_msg],
            execution_time_seconds=execution_time
        )


@router.get(
    "/insights",
    response_model=List[InsightInDB],
    summary="Obtener insights generados",
    description="Retorna los insights creados por el análisis de feedback"
)
async def get_insights(
    limit: int = Query(default=50, ge=1, le=500, description="Número máximo de insights a retornar")
) -> List[InsightInDB]:
    """
    Obtiene los insights generados por el análisis.
    Devuelve el insight más reciente por tema (deduplicado entre ejecuciones).

    Args:
        limit: Número máximo de resultados

    Returns:
        Lista de insights deduplicados, uno por tema, ordenados por fecha descendente
    """
    try:
        logger.info(f"Obteniendo insights deduplicados por tema (limit={limit})")
        insights = await InsightRepository.find_latest_per_theme(limit=limit)
        logger.info(f"Retornando {len(insights)} insights (deduplicados)")
        return insights
        
    except Exception as e:
        error_msg = f"Error obteniendo insights: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )


@router.get(
    "/actions",
    response_model=List[ActionItemInDB],
    summary="Obtener acciones generadas",
    description="Retorna las acciones creadas por el análisis de feedback"
)
async def get_actions(
    limit: int = Query(default=50, ge=1, le=500, description="Número máximo de acciones a retornar"),
    status_filter: Optional[str] = Query(default=None, description="Filtrar por estado (Pendiente, En Progreso, Completada)")
) -> List[ActionItemInDB]:
    """
    Obtiene las acciones generadas por el análisis.
    
    Args:
        limit: Número máximo de resultados
        status_filter: Filtro opcional por estado
        
    Returns:
        Lista de acciones ordenadas por fecha de creación (más recientes primero)
    """
    try:
        logger.info(f"Obteniendo acciones (limit={limit}, status={status_filter})")
        
        if status_filter:
            actions = await ActionRepository.find_by_status(status_filter, limit=limit)
        else:
            actions = await ActionRepository.find_all(limit=limit)
        
        logger.info(f"Retornando {len(actions)} acciones")
        return actions
        
    except Exception as e:
        error_msg = f"Error obteniendo acciones: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )