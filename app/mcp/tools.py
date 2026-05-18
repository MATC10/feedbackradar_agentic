"""
app/mcp/tools.py

Herramientas MCP de FeedbackRadar, registradas directamente con @mcp.tool().

La instancia mcp vive en instance.py para evitar imports circulares con server.py.
"""

import logging
from typing import List, Optional
from datetime import datetime, timedelta

from app.mcp.instance import mcp
from app.databases.repositories import (
    FeedbackRepository,
    InsightRepository,
    ActionRepository,
)
from app.databases.elasticsearch_client import ElasticsearchClient
from app.embeddings.ollama_embeddings import OllamaEmbeddingService
from app.schemas import InsightInDB, ActionItemInDB

logger = logging.getLogger(__name__)


@mcp.tool(name="search_feedback_tool")
async def search_feedback(
    query: str,
    platform: Optional[str] = None,
    top_k: int = 5
) -> dict:
    """
    Busca feedback semánticamente similar a una consulta.

    Args:
        query: Consulta en lenguaje natural (ej: "problemas con el pago")
        platform: Filtro opcional por plataforma (ej: "Reviews", "Email")
        top_k: Número máximo de resultados a retornar (default: 5)

    Returns:
        Dict con success, query, results_count y results con score de similitud.
    """
    try:
        logger.info(f"MCP Tool: search_feedback - query='{query}', top_k={top_k}, platform={platform}")

        embedding_service = OllamaEmbeddingService()
        query_embedding = embedding_service.embed_text(query)

        results = await ElasticsearchClient.semantic_search(
            query_embedding=query_embedding,
            top_k=top_k,
            platform_filter=platform
        )

        logger.info(f"Búsqueda semántica completada: {len(results)} resultados")

        return {
            "success": True,
            "query": query,
            "results_count": len(results),
            "results": results,
            "platform": platform,
        }

    except Exception as e:
        error_msg = f"Error en búsqueda semántica: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "query": query,
            "results_count": 0,
            "results": [],
            "error": error_msg,
        }


@mcp.tool(name="get_feedback_stats_tool")
async def get_feedback_stats(theme: str) -> dict:
    """
    Obtiene estadísticas de feedback filtradas por tema.

    Args:
        theme: Tema para filtrar el feedback (ej: "pagos", "usabilidad")

    Returns:
        Dict con success, theme, total_feedback, related_count y timestamp.
    """
    try:
        logger.info(f"MCP Tool: get_feedback_stats - theme='{theme}'")

        total = await FeedbackRepository.count_all()
        all_feedback = await FeedbackRepository.find_all(limit=10000)

        stop_words = {
            'de', 'la', 'el', 'y', 'en', 'con', 'para', 'del', 'por',
            'los', 'las', 'una', 'un', 'se', 'que', 'es', 'no', 'al',
            'lo', 'su', 'sus', 'más', 'pero', 'muy', 'hay'
        }
        keywords = [
            w.lower() for w in theme.replace('-', ' ').split()
            if len(w) > 3 and w.lower() not in stop_words
        ]

        related_count = (
            sum(
                1 for f in all_feedback
                if any(kw in f.get('text', '').lower() for kw in keywords)
            )
            if keywords else 0
        )

        logger.info(
            f"Estadísticas '{theme}': total={total}, "
            f"keywords={keywords}, relacionados={related_count}"
        )

        return {
            "success": True,
            "theme": theme,
            "total_feedback": total,
            "related_count": related_count,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        error_msg = f"Error obteniendo estadísticas: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "theme": theme,
            "total_feedback": 0,
            "related_count": 0,
            "error": error_msg,
        }


@mcp.tool(name="get_recent_feedback_tool")
async def get_recent_feedback(days: int = 7) -> dict:
    """
    Obtiene feedback de los últimos N días.

    Args:
        days: Número de días hacia atrás (default: 7)

    Returns:
        Dict con success, days, count y feedbacks.
    """
    try:
        logger.info(f"MCP Tool: get_recent_feedback - days={days}")

        feedbacks = await FeedbackRepository.find_recent(days=days, limit=50)

        logger.info(f"Feedback reciente obtenido: {len(feedbacks)} documentos")

        return {
            "success": True,
            "days": days,
            "count": len(feedbacks),
            "feedbacks": feedbacks,
        }

    except Exception as e:
        error_msg = f"Error obteniendo feedback reciente: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "days": days,
            "count": 0,
            "feedbacks": [],
            "error": error_msg,
        }


@mcp.tool(name="save_insight_tool")
async def save_insight(
    theme: str,
    summary: str,
    priority: str,
    reasoning: str,
    evidence_feedback_ids: Optional[List[str]] = None,
    analysis_run_id: str = "mcp_tool"
) -> dict:
    """
    Guarda un insight generado por análisis de feedback.

    Args:
        theme: Tema principal del insight (ej: "Pagos")
        summary: Resumen del insight descubierto
        priority: Prioridad ("Crítica", "Alta", "Media", "Baja")
        reasoning: Razonamiento que justifica el insight
        evidence_feedback_ids: IDs de feedback que soportan este insight
        analysis_run_id: ID del análisis que generó este insight

    Returns:
        Dict con success, insight_id, theme y priority.
    """
    try:
        logger.info(f"MCP Tool: save_insight - theme='{theme}', priority={priority}")

        import uuid
        insight_id = f"insight_{uuid.uuid4().hex[:12]}"

        insight = InsightInDB(
            insight_id=insight_id,
            theme=theme,
            summary=summary,
            priority=priority,
            reasoning=reasoning,
            evidence=evidence_feedback_ids or [],
            analysis_run_id=analysis_run_id,
        )

        saved_id = await InsightRepository.insert_one(insight)

        logger.info(f"Insight guardado exitosamente: {saved_id}")

        return {
            "success": True,
            "insight_id": saved_id,
            "theme": theme,
            "priority": priority,
        }

    except Exception as e:
        error_msg = f"Error guardando insight: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "insight_id": None,
            "theme": theme,
            "error": error_msg,
        }


@mcp.tool(name="create_action_item_tool")
async def create_action_item(
    title: str,
    description: str,
    priority: str
) -> dict:
    """
    Crea un ítem de acción basado en insights.

    Args:
        title: Título de la acción (ej: "Optimizar proceso de pago")
        description: Descripción detallada de la acción propuesta
        priority: Prioridad ("Crítica", "Alta", "Media", "Baja")

    Returns:
        Dict con success, action_id, title, priority y status.
    """
    try:
        logger.info(f"MCP Tool: create_action_item - title='{title}', priority={priority}")

        import uuid
        action_id = f"action_{uuid.uuid4().hex[:12]}"

        action = ActionItemInDB(
            action_id=action_id,
            analysis_run_id="mcp_tool",
            insight_id="",
            title=title,
            description=description,
            priority=priority,
            status="Pendiente",
            created_at=datetime.utcnow(),
        )

        saved_id = await ActionRepository.insert_one(action)

        logger.info(f"Acción creada exitosamente: {saved_id}")

        return {
            "success": True,
            "action_id": saved_id,
            "title": title,
            "priority": priority,
            "status": "Pendiente",
        }

    except Exception as e:
        error_msg = f"Error creando acción: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "action_id": None,
            "title": title,
            "error": error_msg,
        }
