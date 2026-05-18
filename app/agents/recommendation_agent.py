# -*- coding: utf-8 -*-
"""
app/agents/recommendation_agent.py

Recommendation Agent - Cuarto agente del workflow.

Responsable de generar recomendaciones accionables y propuestas
de action items basadas en los temas priorizados y sus evidencias.
"""

import logging
from typing import List

from pydantic import BaseModel, Field

from app.agents.state import AgentState, add_error
from app.llm import get_chat_llm_client, generate_structured_response, StructuredOutputError
from app.schemas.analysis import PrioritizedTheme, Evidence, Recommendation

logger = logging.getLogger(__name__)


class RecommendationResponse(BaseModel):
    """Respuesta estructurada del LLM para generar una recomendación."""
    recommendation: str = Field(..., min_length=20, description="Recomendación ejecutiva clara y accionable")
    action_title: str = Field(..., min_length=5, description="Título conciso de la acción sugerida")
    action_description: str = Field(..., min_length=20, description="Descripción detallada de la acción propuesta")
    reasoning: str = Field(..., min_length=10, description="Justificación que conecta prioridad, evidencias e impacto")


def build_recommendation_prompt(
    theme: PrioritizedTheme,
    evidence_list: List[Evidence]
) -> str:
    """
    Construye el prompt para que el LLM genere una recomendación.
    
    Args:
        theme: Tema priorizado con su nivel de importancia
        evidence_list: Evidencias recuperadas para este tema
        
    Returns:
        Prompt formateado para el LLM
    """
    # Preparar evidencias
    evidence_texts = []
    for i, ev in enumerate(evidence_list[:10], 1):  # Limitar a 10 evidencias
        platform = ev.platform or "Unknown"
        score = ev.score
        text = ev.text[:200]  # Limitar longitud
        evidence_texts.append(f"{i}. [{platform}] (relevancia: {score:.2f}) \"{text}\"")
    
    evidence_section = "\n".join(evidence_texts) if evidence_texts else "No hay evidencias disponibles"
    
    prompt = f"""Eres un Product Manager experto. Debes generar una recomendación accionable para el siguiente tema detectado en feedback de usuarios.

TEMA PRIORIZADO:
Nombre: {theme.name}
Descripción: {theme.description}
Prioridad: {theme.priority}
Razonamiento de priorización: {theme.reasoning}
Número de evidencias: {theme.evidence_count}

EVIDENCIAS REALES DE USUARIOS (top {len(evidence_list)}):
{evidence_section}

TU TAREA:
Genera una recomendación clara y accionable que incluya:

1. RECOMENDACIÓN: Una sugerencia ejecutiva de qué hacer (mínimo 20 caracteres)
   - Debe ser específica y orientada a acción
   - Debe conectar con la prioridad y las evidencias
   - Debe ser realista y alcanzable

2. TÍTULO DE ACCIÓN: Un título conciso para la acción sugerida (mínimo 5 caracteres)
   - Debe ser claro y descriptivo
   - Ejemplo: "Optimizar proceso de checkout móvil"

3. DESCRIPCIÓN DE ACCIÓN: Una descripción detallada de la acción (mínimo 20 caracteres)
   - Debe explicar QUÉ hacer
   - Debe incluir pasos o áreas a revisar
   - Debe ser técnicamente viable

4. RAZONAMIENTO: Justificación de por qué esta recomendación (mínimo 10 caracteres)
   - Debe conectar con la prioridad asignada
   - Debe referenciar las evidencias disponibles
   - Debe explicar el impacto esperado

IMPORTANTE:
- Basa tu recomendación ÚNICAMENTE en la información proporcionada
- NO inventes datos, estadísticas o evidencias adicionales
- Sé específico y práctico
- Considera la prioridad "{theme.priority}" en tu recomendación

FORMATO DE RESPUESTA:
Devuelve ÚNICAMENTE un objeto JSON con este formato exacto:
{{
  "recommendation": "Recomendación ejecutiva clara...",
  "action_title": "Título de la acción",
  "action_description": "Descripción detallada de qué hacer...",
  "reasoning": "Justificación basada en prioridad, evidencias e impacto..."
}}

NO incluyas texto adicional fuera del JSON.
NO incluyas explicaciones antes o después del JSON.
Devuelve SOLO el JSON válido.
"""
    
    return prompt


async def generate_recommendations(state: AgentState) -> AgentState:
    """
    Genera recomendaciones accionables para cada tema priorizado.
    
    Este agente toma los temas priorizados, recupera sus evidencias,
    y usa el LLM para generar recomendaciones ejecutivas y propuestas
    de acciones concretas.
    
    Args:
        state: Estado actual del workflow
        
    Returns:
        Estado actualizado con recomendaciones generadas
        
    Raises:
        No lanza excepciones, registra errores en state["errors"]
    """
    logger.info("=== Recommendation Agent: Iniciando ===")
    
    # Validar que hay temas priorizados
    prioritized_themes = state.get("prioritized_themes", [])
    
    if not prioritized_themes:
        logger.warning("No hay temas priorizados para generar recomendaciones")
        state["recommendations"] = []
        return add_error(state, "No hay temas priorizados para generar recomendaciones")
    
    # Obtener evidencias por tema
    evidence_by_theme = state.get("evidence_by_theme", {})
    
    logger.info(f"Generando recomendaciones para {len(prioritized_themes)} temas")
    
    # Inicializar lista de recomendaciones
    recommendations: List[Recommendation] = []
    
    # Obtener cliente LLM según configuración
    llm_client = get_chat_llm_client()
    
    # Procesar cada tema priorizado
    for i, theme in enumerate(prioritized_themes, 1):
        theme_name = theme.name
        logger.info(f"[{i}/{len(prioritized_themes)}] Generando recomendación para: {theme_name}")
        
        try:
            # 1. Obtener evidencias del tema
            evidence_list = evidence_by_theme.get(theme_name, [])
            logger.info(f"Evidencias disponibles: {len(evidence_list)}")
            
            # 2. Construir prompt
            prompt = build_recommendation_prompt(theme, evidence_list)
            logger.debug(f"Prompt construido: {len(prompt)} caracteres")
            
            # 3. Generar recomendación estructurada
            logger.info(f"Solicitando recomendación al LLM para '{theme_name}'...")
            response = await generate_structured_response(
                llm_client=llm_client,
                prompt=prompt,
                response_model=RecommendationResponse
            )
            
            # 4. Crear objeto Recommendation
            recommendation = Recommendation(
                title=response.action_title,
                description=f"{response.recommendation}\n\nAcción propuesta: {response.action_description}",
                priority=theme.priority,
                related_themes=[theme_name],
                expected_impact=response.reasoning
            )
            
            recommendations.append(recommendation)
            
            logger.info(f"✓ Recomendación generada para '{theme_name}'")
            logger.debug(f"  Título: {response.action_title}")
            logger.debug(f"  Recomendación: {response.recommendation[:100]}...")
            
        except StructuredOutputError as e:
            error_msg = f"Error generando salida estructurada para tema '{theme_name}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            add_error(state, error_msg)
            # Continuar con siguiente tema
            continue
            
        except Exception as e:
            error_msg = f"Error inesperado generando recomendación para '{theme_name}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            add_error(state, error_msg)
            # Continuar con siguiente tema
            continue
    
    # Actualizar estado
    state["recommendations"] = recommendations
    
    # Resumen final
    logger.info(f"=== Recommendation Agent: Completado ===")
    logger.info(f"Recomendaciones generadas exitosamente: {len(recommendations)}/{len(prioritized_themes)}")
    
    # Resumen por prioridad
    priority_counts = {}
    for rec in recommendations:
        priority_counts[rec.priority] = priority_counts.get(rec.priority, 0) + 1
    
    for priority, count in sorted(priority_counts.items()):
        logger.info(f"  {priority}: {count} recomendación(es)")
    
    return state
