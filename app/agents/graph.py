# -*- coding: utf-8 -*-
"""
app/agents/graph.py

Workflow completo de análisis de feedback usando LangGraph.

Este módulo orquesta los 5 agentes especializados en un grafo de ejecución:
1. Theme Discovery Agent - Detecta temas recurrentes
2. Evidence Retrieval Agent - Recupera evidencias semánticas
3. Prioritization Agent - Prioriza temas
4. Recommendation Agent - Genera recomendaciones
5. Persistence Agent - Persiste resultados en MongoDB
"""

import logging
from typing import List, Dict, Any

from langgraph.graph import StateGraph, END

from app.agents.state import AgentState, create_initial_state
from app.agents.theme_agent import discover_themes
from app.agents.evidence_agent import retrieve_evidence
from app.agents.prioritization_agent import prioritize_themes
from app.agents.recommendation_agent import generate_recommendations
from app.agents.persistence_agent import persist_results
from app.agents.jira_action_agent import create_jira_issues
from app.agents.summary_agent import generate_executive_summary

logger = logging.getLogger(__name__)


def build_feedback_analysis_graph() -> StateGraph:
    """
    Construye el grafo de análisis de feedback con LangGraph.
    
    El grafo orquesta 5 agentes en secuencia:
    
    START
      ↓
    discover_themes (Theme Discovery Agent)
      ↓
    retrieve_evidence (Evidence Retrieval Agent)
      ↓
    prioritize_themes (Prioritization Agent)
      ↓
    generate_recommendations (Recommendation Agent)
      ↓
    persist_results (Persistence Agent)
      ↓
    END
    
    Returns:
        StateGraph compilado y listo para ejecutar
        
    Example:
        >>> graph = build_feedback_analysis_graph()
        >>> result = await graph.ainvoke(initial_state)
    """
    logger.info("Construyendo grafo de análisis de feedback")
    
    # Crear el grafo con el estado compartido
    workflow = StateGraph(AgentState)
    
    # Agregar nodos (agentes)
    workflow.add_node("discover_themes", discover_themes)
    workflow.add_node("retrieve_evidence", retrieve_evidence)
    workflow.add_node("prioritize_themes", prioritize_themes)
    workflow.add_node("generate_recommendations", generate_recommendations)
    workflow.add_node("persist_results", persist_results)
    workflow.add_node("create_jira_issues", create_jira_issues)
    workflow.add_node("generate_executive_summary", generate_executive_summary)

    # Definir el flujo (edges)
    workflow.set_entry_point("discover_themes")
    workflow.add_edge("discover_themes", "retrieve_evidence")
    workflow.add_edge("retrieve_evidence", "prioritize_themes")
    workflow.add_edge("prioritize_themes", "generate_recommendations")
    workflow.add_edge("generate_recommendations", "persist_results")
    workflow.add_edge("persist_results", "create_jira_issues")
    workflow.add_edge("create_jira_issues", "generate_executive_summary")
    workflow.add_edge("generate_executive_summary", END)
    
    # Compilar el grafo
    compiled_graph = workflow.compile()
    
    logger.info("Grafo de análisis de feedback construido exitosamente")
    logger.info("Nodos: discover_themes → retrieve_evidence → prioritize_themes → generate_recommendations → persist_results → create_jira_issues → generate_executive_summary")
    
    return compiled_graph


async def run_feedback_analysis_workflow(
    feedback_items: List[Dict[str, Any]]
) -> AgentState:
    """
    Ejecuta el workflow completo de análisis de feedback.
    
    Esta función de alto nivel:
    1. Crea el estado inicial con el feedback proporcionado
    2. Construye el grafo de análisis
    3. Ejecuta el workflow completo
    4. Retorna el estado final enriquecido
    
    Args:
        feedback_items: Lista de feedback para analizar
            Cada item debe tener al menos: {"text": str, "platform": str}
            
    Returns:
        Estado final con todos los resultados:
            - detected_themes: Temas detectados
            - evidence_by_theme: Evidencias por tema
            - prioritized_themes: Temas priorizados
            - recommendations: Recomendaciones generadas
            - actions_created: IDs de acciones persistidas
            - meta Metadata adicional
            - errors: Lista de errores si ocurrieron
            
    Raises:
        Exception: Si hay un error crítico en la ejecución del workflow
        
    Example:
        >>> feedback = [
        ...     {"text": "El pago falla", "platform": "Web"},
        ...     {"text": "Sistema lento", "platform": "App"}
        ... ]
        >>> result = await run_feedback_analysis_workflow(feedback)
        >>> print(f"Temas detectados: {len(result['detected_themes'])}")
        >>> print(f"Acciones creadas: {len(result['actions_created'])}")
    """
    logger.info(f"=== Iniciando workflow de análisis de feedback ===")
    logger.info(f"Feedback items a procesar: {len(feedback_items)}")
    
    # 1. Crear estado inicial
    initial_state = create_initial_state(feedback_items)
    logger.info("Estado inicial creado")
    
    # 2. Construir el grafo
    graph = build_feedback_analysis_graph()
    logger.info("Grafo construido")
    
    # 3. Ejecutar el workflow
    logger.info("Ejecutando workflow completo...")
    try:
        final_state = await graph.ainvoke(initial_state)
        logger.info("=== Workflow completado exitosamente ===")
        
        # Log de resumen
        logger.info(f"Temas detectados: {len(final_state.get('detected_themes', []))}")
        logger.info(f"Evidencias recuperadas: {sum(len(evs) for evs in final_state.get('evidence_by_theme', {}).values())}")
        logger.info(f"Temas priorizados: {len(final_state.get('prioritized_themes', []))}")
        logger.info(f"Recomendaciones generadas: {len(final_state.get('recommendations', []))}")
        logger.info(f"Acciones persistidas: {len(final_state.get('actions_created', []))}")
        
        if final_state.get('errors'):
            logger.warning(f"Errores registrados durante el workflow: {len(final_state['errors'])}")
            for error in final_state['errors']:
                logger.warning(f"  - {error}")
        
        return final_state
        
    except Exception as e:
        error_msg = f"Error crítico ejecutando workflow: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise Exception(error_msg) from e


def get_workflow_summary(state: AgentState) -> Dict[str, Any]:
    """
    Genera un resumen ejecutivo del workflow completado.
    
    Args:
        state: Estado final del workflow
        
    Returns:
        Diccionario con resumen de métricas y resultados
        
    Example:
        >>> summary = get_workflow_summary(final_state)
        >>> print(summary['themes_detected'])
        >>> print(summary['actions_created'])
    """
    return {
        "themes_detected": len(state.get("detected_themes", [])),
        "evidence_count": sum(len(evs) for evs in state.get("evidence_by_theme", {}).values()),
        "themes_prioritized": len(state.get("prioritized_themes", [])),
        "recommendations_generated": len(state.get("recommendations", [])),
        "actions_created": len(state.get("actions_created", [])),
        "insights_created": len(state.get("insights_created", [])),
        "errors_count": len(state.get("errors", [])),
        "has_errors": len(state.get("errors", [])) > 0,
        "workflow_completed": "actions_created" in state
    }