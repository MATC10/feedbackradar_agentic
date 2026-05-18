# -*- coding: utf-8 -*-
"""
app/agents/evidence_agent.py

Evidence Retrieval Agent - Segundo agente del workflow.

Responsable de recuperar evidencias textuales reales para cada tema
detectado usando búsqueda semántica.
"""

import logging
from typing import List, Dict

from app.agents.state import AgentState, add_error
from app.mcp.agent_client import call_mcp_tool
from app.schemas.analysis import DetectedTheme, Evidence

logger = logging.getLogger(__name__)


def build_search_query(theme: DetectedTheme) -> str:
    """
    Construye una query de búsqueda semántica para un tema.
    
    Args:
        theme: Tema para el cual buscar evidencias
        
    Returns:
        Query optimizada para búsqueda semántica
    """
    # Query simple y efectiva: nombre + descripción
    query = f"{theme.name}. {theme.description}"
    return query


async def retrieve_evidence(state: AgentState) -> AgentState:
    """
    Recupera evidencias reales para cada tema detectado.
    
    Este agente usa búsqueda semántica (MCP tool search_feedback) para
    encontrar feedback real que soporte cada tema detectado.
    
    Args:
        state: Estado actual del workflow
        
    Returns:
        Estado actualizado con evidencias por tema
        
    Raises:
        No lanza excepciones, registra errores en state["errors"]
    """
    logger.info("=== Evidence Retrieval Agent: Iniciando ===")
    
    # Validar que hay temas detectados
    detected_themes = state.get("detected_themes", [])
    
    if not detected_themes:
        logger.warning("No hay temas detectados para buscar evidencias")
        state["evidence_by_theme"] = {}
        return add_error(state, "No hay temas detectados para recuperar evidencias")
    
    logger.info(f"Recuperando evidencias para {len(detected_themes)} temas")
    
    # Inicializar diccionario de evidencias
    evidence_by_theme: Dict[str, List[Evidence]] = {}
    
    # Procesar cada tema
    for i, theme in enumerate(detected_themes, 1):
        theme_name = theme.name
        logger.info(f"[{i}/{len(detected_themes)}] Procesando tema: {theme_name}")
        
        try:
            # Construir query
            query = build_search_query(theme)
            logger.debug(f"Query para '{theme_name}': {query}")
            
            # Buscar feedback via MCP server
            search_result = await call_mcp_tool(
                "search_feedback_tool",
                {"query": query, "top_k": 10}
            )
            
            # Verificar éxito de la búsqueda
            if not search_result.get("success", False):
                error_msg = search_result.get("error", "Error desconocido")
                logger.error(f"Búsqueda falló para tema '{theme_name}': {error_msg}")
                evidence_by_theme[theme_name] = []
                add_error(state, f"Error buscando evidencias para '{theme_name}': {error_msg}")
                continue
            
            # Extraer resultados
            results = search_result.get("results", [])
            logger.info(f"Encontrados {len(results)} resultados para '{theme_name}'")
            
            # Transformar resultados a objetos Evidence
            evidence_list = []
            for result in results:
                try:
                    evidence = Evidence(
                        feedback_id=result.get("feedback_id", result.get("_id", "unknown")),
                        text=result.get("text", result.get("comment", "")),
                        score=result.get("score", result.get("_score", 0.0)),
                        platform=result.get("platform", result.get("source", None)),
                        date=result.get("date", result.get("created_at", None))
                    )
                    evidence_list.append(evidence)
                    logger.debug(f"  - Evidence: {evidence.text[:50]}... (score: {evidence.score:.2f})")
                except Exception as e:
                    logger.warning(f"Error transformando resultado a Evidence: {str(e)}")
                    continue
            
            # Guardar evidencias para este tema
            evidence_by_theme[theme_name] = evidence_list
            logger.info(f"Guardadas {len(evidence_list)} evidencias para '{theme_name}'")
            
        except Exception as e:
            error_msg = f"Error inesperado procesando tema '{theme_name}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            evidence_by_theme[theme_name] = []
            add_error(state, error_msg)
            continue
    
    # Actualizar estado
    state["evidence_by_theme"] = evidence_by_theme
    
    # Resumen final
    total_evidence = sum(len(ev_list) for ev_list in evidence_by_theme.values())
    logger.info(f"=== Evidence Retrieval Agent: Completado ===")
    logger.info(f"Total evidencias recuperadas: {total_evidence} para {len(evidence_by_theme)} temas")
    
    return state