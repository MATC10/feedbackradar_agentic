# -*- coding: utf-8 -*-
"""
app/agents/prioritization_agent.py

Prioritization Agent - Tercer agente del workflow.

Responsable de priorizar los temas detectados usando evidencias,
estadísticas y análisis de impacto.
"""

import logging
from typing import List

from pydantic import BaseModel, Field, field_validator

from app.agents.state import AgentState, add_error
from app.mcp.agent_client import call_mcp_tool
from app.llm import get_chat_llm_client, generate_structured_response, StructuredOutputError
from app.schemas.analysis import DetectedTheme, Evidence, PrioritizedTheme

logger = logging.getLogger(__name__)


class ThemePrioritizationResponse(BaseModel):
    """Respuesta estructurada para la priorización de un tema."""
    priority: str = Field(..., description="Prioridad: Crítica, Alta, Media, Baja")
    reasoning: str = Field(..., min_length=10, description="Razonamiento de la priorización")
    
    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v: str) -> str:
        """Valida que la prioridad sea una de las permitidas."""
        allowed = ["Crítica", "Alta", "Media", "Baja"]
        if v not in allowed:
            raise ValueError(f"Prioridad debe ser una de: {', '.join(allowed)}")
        return v


def build_prioritization_prompt(
    theme: DetectedTheme,
    evidence_list: List[Evidence],
    stats: dict
) -> str:
    """
    Construye el prompt para que el LLM priorice un tema.
    
    Args:
        theme: Tema a priorizar
        evidence_list: Evidencias recuperadas para este tema
        stats: Estadísticas del tema obtenidas de get_feedback_stats
        
    Returns:
        Prompt formateado para el LLM
    """
    # Preparar evidencias
    evidence_texts = []
    for i, ev in enumerate(evidence_list[:10], 1):  # Limitar a 10 evidencias
        platform = ev.platform or "Unknown"
        score = ev.score
        text = ev.text[:200]  # Limitar longitud
        evidence_texts.append(f"{i}. [{platform}] (relevancia: {score:.2f}) {text}")
    
    evidence_section = "\n".join(evidence_texts) if evidence_texts else "No hay evidencias disponibles"
    
    # Preparar estadísticas
    stats_success = stats.get("success", False)
    if stats_success:
        total_feedback = stats.get("total_feedback", 0)
        related_count = stats.get("related_count", 0)
        percentage = (related_count / total_feedback * 100) if total_feedback > 0 else 0
        stats_section = f"""
Total de feedback en sistema: {total_feedback}
Feedback relacionado con este tema: {related_count}
Porcentaje: {percentage:.1f}%
"""
    else:
        stats_section = f"No se pudieron obtener estadísticas: {stats.get('error', 'Error desconocido')}"
    
    prompt = f"""Eres un experto Product Manager. Debes priorizar el siguiente tema detectado en feedback de usuarios.

TEMA A PRIORIZAR:
Nombre: {theme.name}
Descripción: {theme.description}

ESTADÍSTICAS:
{stats_section}

EVIDENCIAS REALES DE USUARIOS (top {len(evidence_list)}):
{evidence_section}

CRITERIOS DE PRIORIZACIÓN:
1. Frecuencia: ¿Cuántos usuarios mencionan este problema?
2. Impacto: ¿Es bloqueante o crítico para la experiencia del usuario?
3. Severidad: ¿Hay señales de frustración o pérdida de negocio?
4. Alcance: ¿Afecta a funcionalidad core o secundaria?

PRIORIDADES PERMITIDAS:
- Crítica: Problema bloqueante crítico que impide funcionalidad esencial o causa pérdida directa de negocio
- Alta: Problema bloqueante o muy importante que afecta significativamente a usuarios
- Media: Problema que degrada la experiencia pero tiene workarounds
- Baja: Problema menor o de baja frecuencia

INSTRUCCIONES:
1. Analiza ÚNICAMENTE la información proporcionada arriba
2. NO inventes datos ni estadísticas
3. Asigna una prioridad basada en los criterios
4. Justifica tu decisión con evidencia concreta

FORMATO DE RESPUESTA:
Devuelve ÚNICAMENTE un objeto JSON con este formato exacto:
{{
  "priority": "Crítica|Alta|Media|Baja",
  "reasoning": "Explicación detallada de por qué se asigna esta prioridad, citando evidencias y estadísticas concretas"
}}

NO incluyas texto adicional fuera del JSON.
NO incluyas explicaciones antes o después del JSON.
Devuelve SOLO el JSON válido.
"""
    
    return prompt


async def prioritize_themes(state: AgentState) -> AgentState:
    """
    Prioriza los temas detectados usando evidencias y estadísticas.
    
    Este agente analiza cada tema detectado, consulta estadísticas mediante
    get_feedback_stats, combina con evidencias recuperadas, y usa el LLM
    para asignar una prioridad razonada.
    
    Args:
        state: Estado actual del workflow
        
    Returns:
        Estado actualizado con temas priorizados
        
    Raises:
        No lanza excepciones, registra errores en state["errors"]
    """
    logger.info("=== Prioritization Agent: Iniciando ===")
    
    # Validar que hay temas detectados
    detected_themes = state.get("detected_themes", [])
    
    if not detected_themes:
        logger.warning("No hay temas detectados para priorizar")
        state["prioritized_themes"] = []
        return add_error(state, "No hay temas detectados para priorizar")
    
    # Obtener evidencias por tema
    evidence_by_theme = state.get("evidence_by_theme", {})
    
    logger.info(f"Priorizando {len(detected_themes)} temas")
    
    # Inicializar lista de temas priorizados
    prioritized_themes: List[PrioritizedTheme] = []
    
    # Obtener cliente LLM según configuración
    llm_client = get_chat_llm_client()
    
    # Procesar cada tema
    for i, theme in enumerate(detected_themes, 1):
        theme_name = theme.name
        logger.info(f"[{i}/{len(detected_themes)}] Priorizando tema: {theme_name}")
        
        try:
            # 1. Obtener estadísticas del tema via MCP server
            logger.debug(f"Consultando estadísticas para '{theme_name}'...")
            stats = await call_mcp_tool("get_feedback_stats_tool", {"theme": theme_name})
            
            if not stats.get("success", False):
                logger.warning(f"No se pudieron obtener estadísticas para '{theme_name}': {stats.get('error')}")
                # Continuar con estadísticas vacías
            else:
                logger.info(f"Estadísticas obtenidas: {stats.get('related_count', 0)} feedback relacionados")
            
            # 2. Obtener evidencias
            evidence_list = evidence_by_theme.get(theme_name, [])
            logger.info(f"Evidencias disponibles: {len(evidence_list)}")
            
            # 3. Construir prompt
            prompt = build_prioritization_prompt(theme, evidence_list, stats)
            logger.debug(f"Prompt construido: {len(prompt)} caracteres")
            
            # 4. Generar priorización estructurada
            logger.info(f"Solicitando priorización al LLM para '{theme_name}'...")
            response = await generate_structured_response(
                llm_client=llm_client,
                prompt=prompt,
                response_model=ThemePrioritizationResponse
            )
            
            # 5. Crear tema priorizado
            prioritized_theme = PrioritizedTheme(
                name=theme_name,
                description=theme.description,
                priority=response.priority,
                evidence_count=len(evidence_list),
                reasoning=response.reasoning
            )
            
            prioritized_themes.append(prioritized_theme)
            
            logger.info(f"✓ Tema '{theme_name}' priorizado como: {response.priority}")
            logger.debug(f"  Razonamiento: {response.reasoning[:100]}...")
            
        except StructuredOutputError as e:
            error_msg = f"Error generando salida estructurada para tema '{theme_name}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            add_error(state, error_msg)
            # Continuar con siguiente tema
            continue
            
        except Exception as e:
            error_msg = f"Error inesperado priorizando tema '{theme_name}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            add_error(state, error_msg)
            # Continuar con siguiente tema
            continue
    
    # Actualizar estado
    state["prioritized_themes"] = prioritized_themes
    
    # Resumen final
    logger.info(f"=== Prioritization Agent: Completado ===")
    logger.info(f"Temas priorizados exitosamente: {len(prioritized_themes)}/{len(detected_themes)}")
    
    # Resumen por prioridad
    priority_counts = {}
    for pt in prioritized_themes:
        priority_counts[pt.priority] = priority_counts.get(pt.priority, 0) + 1
    
    for priority, count in sorted(priority_counts.items()):
        logger.info(f"  {priority}: {count} tema(s)")
    
    return state