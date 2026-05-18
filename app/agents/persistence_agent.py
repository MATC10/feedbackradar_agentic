# -*- coding: utf-8 -*-
"""
app/agents/persistence_agent.py

Persistence Agent - Quinto agente del workflow.

Responsable de persistir los resultados del análisis usando MCP tools:
- save_insight: Para guardar insights de temas priorizados
- create_action_item: Para crear acciones recomendadas
"""

import logging
from typing import List, Dict, Any

from app.agents.state import AgentState, add_error
from app.mcp.agent_client import call_mcp_tool
from app.schemas.analysis import PrioritizedTheme, Recommendation

logger = logging.getLogger(__name__)


async def persist_results(state: AgentState) -> AgentState:
    """
    Persiste los resultados del análisis en MongoDB usando MCP tools.
    
    Este agente toma los temas priorizados y recomendaciones generadas,
    y los persiste usando las herramientas MCP save_insight y create_action_item.
    
    Para cada tema priorizado:
    1. Guarda un insight con save_insight
    2. Busca la recomendación asociada
    3. Crea una acción con create_action_item
    4. Registra los IDs generados
    
    Args:
        state: Estado actual del workflow
        
    Returns:
        Estado actualizado con IDs de insights y acciones creadas
        
    Raises:
        No lanza excepciones, registra errores en state["errors"]
    """
    logger.info("=== Persistence Agent: Iniciando ===")
    
    # Validar que hay temas priorizados
    prioritized_themes = state.get("prioritized_themes", [])
    
    if not prioritized_themes:
        logger.warning("No hay temas priorizados para persistir")
        state["actions_created"] = []
        return add_error(state, "No hay temas priorizados para persistir")
    
    # Obtener recomendaciones
    recommendations = state.get("recommendations", [])
    
    logger.info(f"Persistiendo resultados para {len(prioritized_themes)} temas")
    logger.info(f"Recomendaciones disponibles: {len(recommendations)}")
    
    # Crear mapa de recomendaciones por tema para búsqueda eficiente
    recommendations_by_theme: Dict[str, Recommendation] = {}
    for rec in recommendations:
        # Una recomendación puede estar relacionada con múltiples temas
        # pero típicamente tendrá uno principal
        if rec.related_themes:
            theme_name = rec.related_themes[0]
            recommendations_by_theme[theme_name] = rec
    
    # Listas para tracking
    insights_created: List[str] = []
    actions_created: List[str] = []
    
    # Procesar cada tema priorizado
    for i, theme in enumerate(prioritized_themes, 1):
        theme_name = theme.name
        logger.info(f"[{i}/{len(prioritized_themes)}] Persistiendo: {theme_name}")
        
        try:
            # 1. Guardar insight del tema priorizado
            logger.info(f"Guardando insight para '{theme_name}'...")
            
            insight_summary = f"{theme.description}. Prioridad asignada: {theme.priority}"
            
            insight_result = await call_mcp_tool("save_insight_tool", {
                "theme": theme_name,
                "summary": insight_summary,
                "priority": theme.priority,
                "reasoning": theme.reasoning,
            })
            
            if insight_result.get("success"):
                insight_id = insight_result.get("insight_id")
                insights_created.append(insight_id)
                logger.info(f"✓ Insight guardado: {insight_id}")
            else:
                error_msg = f"Error guardando insight para '{theme_name}': {insight_result.get('error')}"
                logger.warning(error_msg)
                add_error(state, error_msg)
            
            # 2. Buscar y guardar acción recomendada
            recommendation = recommendations_by_theme.get(theme_name)
            
            if recommendation:
                logger.info(f"Creando acción para '{theme_name}'...")
                
                action_result = await call_mcp_tool("create_action_item_tool", {
                    "title": recommendation.title,
                    "description": recommendation.description,
                    "priority": recommendation.priority,
                })
                
                if action_result.get("success"):
                    action_id = action_result.get("action_id")
                    actions_created.append(action_id)
                    logger.info(f"✓ Acción creada: {action_id}")
                else:
                    error_msg = f"Error creando acción para '{theme_name}': {action_result.get('error')}"
                    logger.warning(error_msg)
                    add_error(state, error_msg)
            else:
                logger.warning(f"No se encontró recomendación para '{theme_name}', se omite creación de acción")
                add_error(state, f"No se encontró recomendación para tema '{theme_name}'")
        
        except Exception as e:
            error_msg = f"Error inesperado persistiendo '{theme_name}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            add_error(state, error_msg)
            # Continuar con siguiente tema
            continue
    
    # Actualizar estado
    state["actions_created"] = actions_created
    state["insights_created"] = insights_created
    
    # Resumen final
    logger.info(f"=== Persistence Agent: Completado ===")
    logger.info(f"Insights guardados: {len(insights_created)}/{len(prioritized_themes)}")
    logger.info(f"Acciones creadas: {len(actions_created)}/{len(recommendations)}")
    
    if len(insights_created) < len(prioritized_themes):
        logger.warning(f"Algunos insights no se pudieron guardar")
    
    if len(actions_created) < len(recommendations):
        logger.warning(f"Algunas acciones no se pudieron crear")
    
    return state