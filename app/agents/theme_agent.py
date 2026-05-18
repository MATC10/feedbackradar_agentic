# -*- coding: utf-8 -*-
"""
app/agents/theme_agent.py

Theme Discovery Agent - Primer agente del workflow.

Responsable de analizar el feedback inicial y detectar los principales
temas o categorías recurrentes.
"""

import logging
from typing import List, Dict, Any, Optional

from app.agents.state import AgentState, add_error
from app.llm import get_chat_llm_client, generate_structured_response, StructuredOutputError
from app.schemas.analysis import ThemeDiscoveryResponse, DetectedTheme

logger = logging.getLogger(__name__)


def build_theme_discovery_prompt(
    feedback_items: List[Dict[str, Any]],
    existing_themes: Optional[List[str]] = None,
) -> str:
    """
    Construye el prompt para el LLM para descubrir temas.

    Args:
        feedback_items: Lista de feedback a analizar
        existing_themes: Nombres de temas ya conocidos en el sistema (para reutilizarlos)

    Returns:
        Prompt formateado para el LLM
    """
    feedback_texts = []
    for i, item in enumerate(feedback_items[:50], 1):
        text = item.get("text", "")
        platform = item.get("platform", "Unknown")
        feedback_texts.append(f"{i}. [{platform}] {text}")

    feedback_section = "\n".join(feedback_texts)

    existing_section = ""
    if existing_themes:
        names = "\n".join(f"- {t}" for t in existing_themes)
        existing_section = f"""
TEMAS YA EXISTENTES EN EL SISTEMA:
{names}

REGLA IMPORTANTE: Si detectas un tema igual o muy similar a alguno de los anteriores,
usa EXACTAMENTE el mismo nombre que aparece en la lista. Solo crea un nombre nuevo
si el tema es genuinamente distinto a todos los existentes.
"""

    prompt = f"""Eres un experto analista de producto. Analiza el siguiente feedback de usuarios y detecta los principales temas o categorías recurrentes.

FEEDBACK A ANALIZAR:
{feedback_section}
{existing_section}
INSTRUCCIONES:
1. Analiza ÚNICAMENTE el feedback proporcionado arriba
2. NO inventes comentarios ni temas que no aparezcan en el feedback
3. Detecta entre 3 y 7 temas principales recurrentes
4. Prioriza temas útiles para producto y negocio
5. Evita duplicar temas casi idénticos
6. Cada tema debe tener un nombre claro y una descripción concisa

FORMATO DE RESPUESTA:
Devuelve ÚNICAMENTE un objeto JSON con este formato exacto:
{{
  "themes": [
    {{
      "name": "Nombre del tema",
      "description": "Descripción breve y clara del tema"
    }}
  ]
}}

NO incluyas texto adicional fuera del JSON.
NO incluyas explicaciones antes o después del JSON.
Devuelve SOLO el JSON válido.
"""

    return prompt


async def discover_themes(state: AgentState) -> AgentState:
    """
    Descubre temas principales en el feedback.
    
    Este agente analiza el feedback inicial y detecta los temas
    o categorías recurrentes más importantes.
    
    Args:
        state: Estado actual del workflow
        
    Returns:
        Estado actualizado con temas detectados
        
    Raises:
        No lanza excepciones, registra errores en state["errors"]
    """
    logger.info("=== Theme Discovery Agent: Iniciando ===")
    
    # Validar que hay feedback
    feedback_items = state.get("feedback_items", [])
    
    if not feedback_items:
        error_msg = "No hay feedback disponible para analizar"
        logger.warning(error_msg)
        state["detected_themes"] = []
        return add_error(state, error_msg)
    
    logger.info(f"Analizando {len(feedback_items)} items de feedback")

    # Cargar temas ya existentes para que el LLM los reutilice
    existing_themes: List[str] = []
    try:
        from app.databases.repositories import InsightRepository
        recent = await InsightRepository.find_latest_per_theme(limit=50)
        existing_themes = [r["theme"] for r in recent if r.get("theme")]
        if existing_themes:
            logger.info(f"Temas existentes cargados para contexto: {existing_themes}")
    except Exception as e:
        logger.warning(f"No se pudieron cargar temas existentes: {e}")

    try:
        # Construir prompt con temas existentes
        prompt = build_theme_discovery_prompt(feedback_items, existing_themes=existing_themes)
        logger.debug(f"Prompt construido: {len(prompt)} caracteres")
        
        # Obtener cliente LLM según configuración
        llm_client = get_chat_llm_client()
        logger.info("Solicitando análisis al LLM...")
        response = await generate_structured_response(
            llm_client=llm_client,
            prompt=prompt,
            response_model=ThemeDiscoveryResponse
        )
        
        # Extraer temas
        detected_themes = response.themes
        logger.info(f"Temas detectados: {len(detected_themes)}")
        
        # Logging de temas detectados
        for i, theme in enumerate(detected_themes, 1):
            logger.info(f"  {i}. {theme.name}: {theme.description[:60]}...")
        
        # Actualizar estado
        state["detected_themes"] = detected_themes
        
        logger.info("=== Theme Discovery Agent: Completado exitosamente ===")
        return state
        
    except StructuredOutputError as e:
        error_msg = f"Error generando salida estructurada: {str(e)}"
        logger.error(error_msg, exc_info=True)
        state["detected_themes"] = []
        return add_error(state, error_msg)
        
    except Exception as e:
        error_msg = f"Error inesperado en Theme Discovery Agent: {str(e)}"
        logger.error(error_msg, exc_info=True)
        state["detected_themes"] = []
        return add_error(state, error_msg)