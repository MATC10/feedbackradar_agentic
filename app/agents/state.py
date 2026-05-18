# -*- coding: utf-8 -*-
"""
app/agents/state.py

Estado compartido del workflow agentic de FeedbackRadar.
"""

from typing import TypedDict, List, Dict, Any, Optional
from app.schemas.analysis import (
    DetectedTheme,
    Evidence,
    PrioritizedTheme,
    Recommendation
)


class AgentState(TypedDict, total=False):
    """
    Estado compartido entre todos los agentes del workflow.
    
    Este estado se pasa entre agentes y se actualiza incrementalmente
    a medida que cada agente completa su trabajo.
    
    Campos:
        feedback_items: Feedback inicial disponible para análisis
        detected_themes: Temas detectados por Theme Discovery Agent
        evidence_by_theme: Evidencias recuperadas por tema (Evidence Retrieval Agent)
        prioritized_themes: Temas priorizados (Prioritization Agent)
        recommendations: Recomendaciones generadas (Recommendation Agent)
        actions_created: IDs de acciones persistidas (Persistence Agent)
        executive_summary: Resumen ejecutivo del análisis completo
        errors: Lista de errores acumulados durante el workflow
    """
    # Entrada inicial
    feedback_items: List[Dict[str, Any]]
    
    # Theme Discovery Agent
    detected_themes: List[DetectedTheme]
    
    # Evidence Retrieval Agent
    evidence_by_theme: Dict[str, List[Evidence]]
    
    # Prioritization Agent
    prioritized_themes: List[PrioritizedTheme]
    
    # Recommendation Agent
    recommendations: List[Recommendation]
    
    # Persistence Agent
    actions_created: List[str]
    insights_created: List[str]
    
    # Summary Agent (resumen ejecutivo estructurado)
    executive_summary: Dict[str, Any]

    # Jira Action Agent
    jira_issues_created: List[Dict[str, Any]]

    # Control de errores
    errors: List[str]


def create_initial_state(feedback_items: List[Dict[str, Any]]) -> AgentState:
    """
    Crea el estado inicial del workflow con feedback.
    
    Args:
        feedback_items: Lista de feedback para analizar
        
    Returns:
        Estado inicial configurado
        
    Example:
        >>> feedback = [{"text": "El sistema es lento", "platform": "Email"}]
        >>> state = create_initial_state(feedback)
        >>> state["feedback_items"]
        [{'text': 'El sistema es lento', 'platform': 'Email'}]
    """
    return AgentState(
        feedback_items=feedback_items,
        detected_themes=[],
        evidence_by_theme={},
        prioritized_themes=[],
        recommendations=[],
        actions_created=[],
        insights_created=[],
        executive_summary={},
        jira_issues_created=[],
        errors=[]
    )


def add_error(state: AgentState, error_message: str) -> AgentState:
    """
    Agrega un error al estado.
    
    Args:
        state: Estado actual
        error_message: Mensaje de error a agregar
        
    Returns:
        Estado actualizado con el error
    """
    if "errors" not in state:
        state["errors"] = []
    state["errors"].append(error_message)
    return state