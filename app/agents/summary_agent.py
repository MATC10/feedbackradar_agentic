# -*- coding: utf-8 -*-
"""
app/agents/summary_agent.py

Summary Agent - Sexto agente del workflow.

Genera un resumen ejecutivo con: top temas, sentimiento general,
problemas urgentes, features solicitadas, ejemplos textuales y
recomendaciones de producto.
"""

import logging
from typing import List

from pydantic import BaseModel, Field

from app.agents.state import AgentState, add_error
from app.llm import get_chat_llm_client, generate_structured_response, StructuredOutputError

logger = logging.getLogger(__name__)


class SummaryResponse(BaseModel):
    narrative: str = Field(..., min_length=50, description="Resumen narrativo ejecutivo en 2-3 frases")
    overall_sentiment: str = Field(..., description="Sentimiento general: Negativo, Mixto o Positivo")
    top_themes: List[str] = Field(..., description="Top 5 temas mas recurrentes con frecuencia estimada")
    urgent_problems: List[str] = Field(..., description="Problemas mas urgentes que requieren atencion inmediata")
    feature_requests: List[str] = Field(..., description="Features o mejoras mas solicitadas por usuarios")
    representative_examples: List[str] = Field(..., description="3-5 citas textuales reales del feedback")
    product_recommendations: List[str] = Field(..., description="Recomendaciones accionables para el equipo de producto")


def build_summary_prompt(state: AgentState) -> str:
    feedback_items = state.get("feedback_items", [])
    prioritized_themes = state.get("prioritized_themes", [])
    evidence_by_theme = state.get("evidence_by_theme", {})
    recommendations = state.get("recommendations", [])

    total = len(feedback_items)

    themes_section = ""
    for t in prioritized_themes:
        themes_section += f"- {t.name} (prioridad: {t.priority}, evidencias encontradas: {t.evidence_count}): {t.description}\n"
        themes_section += f"  Datos del analisis: {t.reasoning[:300]}\n"

    evidence_section = ""
    all_examples = []
    for theme_name, evidence_list in evidence_by_theme.items():
        evidence_section += f"\nTema: {theme_name}\n"
        for ev in evidence_list[:3]:
            quote = ev.text[:200]
            evidence_section += f'  - [{ev.platform}] "{quote}"\n'
            all_examples.append(f'[{ev.platform}] "{ev.text[:150]}"')

    recs_section = ""
    for rec in recommendations:
        recs_section += f"- {rec.title} ({rec.priority}): {rec.description[:150]}\n"

    prompt = f"""Eres un analista experto de producto. Analiza el siguiente feedback de usuarios y genera un informe ejecutivo completo.

DATOS DISPONIBLES:
- Total de feedback analizado: {total} comentarios
- Temas detectados y priorizados: {len(prioritized_themes)}

TEMAS PRIORIZADOS:
{themes_section}

EVIDENCIAS REALES DE USUARIOS (muestra):
{evidence_section}

RECOMENDACIONES GENERADAS:
{recs_section}

TU TAREA:
Genera un informe ejecutivo estructurado con los siguientes elementos:

1. NARRATIVE: Un parrafo narrativo de 2-3 frases que resuma los hallazgos principales con datos concretos.
   Ejemplo del estilo esperado: "El principal foco de frustracion esta en el proceso de pago, mencionado en 18 de {total} comentarios. El segundo problema es la dificultad para encontrar facturas. Recomendacion: priorizar estabilidad del checkout y rediseno del area de cuenta."

2. OVERALL_SENTIMENT: Una palabra: "Negativo", "Mixto" o "Positivo", segun el tono general del feedback.

3. TOP_THEMES: Lista de los 5 temas mas recurrentes. Usa EXACTAMENTE este formato para TODOS:
   "Nombre del tema - X.X% de afectacion, prioridad: Y"
   - Extrae el porcentaje X.X de los "Datos del analisis" de cada tema.
   - Si el razonamiento contiene "N de M comentarios", calcula: X.X = round(N/M*100, 1).
   - La prioridad Y puede ser Critica, Alta, Media o Baja (cada tema tiene la suya, no todas son iguales).
   - TODOS los temas deben tener porcentaje y prioridad. No omitas el porcentaje de ningun tema.

4. URGENT_PROBLEMS: Lista de los problemas mas urgentes (prioridad Critica o Alta) que necesitan atencion inmediata.
   Cada item debe ser una frase accionable.

5. FEATURE_REQUESTS: Lista de features o mejoras que los usuarios piden explicitamente.
   Si no hay features solicitadas claras, indica ["No se detectaron solicitudes de features especificas"].

6. REPRESENTATIVE_EXAMPLES: Selecciona 3-5 citas textuales reales del feedback proporcionado arriba.
   Deben ser representativas de los problemas principales. Usa el texto real, no lo inventes.

7. PRODUCT_RECOMMENDATIONS: Lista de 3-5 recomendaciones concretas y accionables para el equipo de producto,
   basadas en los datos analizados. Cada recomendacion debe ser especifica y priorizada.

IMPORTANTE:
- Usa SOLO los datos proporcionados arriba
- NO inventes feedback ni estadisticas
- Las citas en representative_examples deben ser textuales del feedback real mostrado
- Se concreto y orientado a negocio

FORMATO DE RESPUESTA:
Devuelve UNICAMENTE un objeto JSON con este formato exacto:
{{
  "narrative": "Parrafo narrativo ejecutivo...",
  "overall_sentiment": "Negativo|Mixto|Positivo",
  "top_themes": ["Tema 1 - descripcion frecuencia", "Tema 2 - ...", ...],
  "urgent_problems": ["Problema urgente 1", "Problema urgente 2", ...],
  "feature_requests": ["Feature solicitada 1", ...],
  "representative_examples": ["[Plataforma] Cita textual real...", ...],
  "product_recommendations": ["Recomendacion 1", "Recomendacion 2", ...]
}}

NO incluyas texto adicional fuera del JSON.
Devuelve SOLO el JSON valido.
"""
    return prompt


async def generate_executive_summary(state: AgentState) -> AgentState:
    logger.info("=== Summary Agent: Iniciando ===")

    prioritized_themes = state.get("prioritized_themes", [])
    if not prioritized_themes:
        logger.warning("No hay temas priorizados, omitiendo resumen ejecutivo")
        state["executive_summary"] = {}
        return state

    try:
        llm_client = get_chat_llm_client()
        prompt = build_summary_prompt(state)
        logger.info("Solicitando resumen ejecutivo al LLM...")

        response = await generate_structured_response(
            llm_client=llm_client,
            prompt=prompt,
            response_model=SummaryResponse
        )

        state["executive_summary"] = {
            "narrative": response.narrative,
            "overall_sentiment": response.overall_sentiment,
            "top_themes": response.top_themes,
            "urgent_problems": response.urgent_problems,
            "feature_requests": response.feature_requests,
            "representative_examples": response.representative_examples,
            "product_recommendations": response.product_recommendations,
        }

        logger.info("=== Summary Agent: Completado ===")
        logger.info(f"Sentimiento general: {response.overall_sentiment}")
        logger.info(f"Top themes: {len(response.top_themes)}")

    except StructuredOutputError as e:
        error_msg = f"Error generando resumen ejecutivo: {str(e)}"
        logger.error(error_msg)
        state["executive_summary"] = {}
        add_error(state, error_msg)

    except Exception as e:
        error_msg = f"Error inesperado en Summary Agent: {str(e)}"
        logger.error(error_msg, exc_info=True)
        state["executive_summary"] = {}
        add_error(state, error_msg)

    return state
