# -*- coding: utf-8 -*-
"""
app/agents/jira_action_agent.py

Jira Action Agent - Séptimo agente del workflow.

Evalúa las acciones generadas y crea automáticamente issues en Jira
para aquellas con prioridad Crítica o Alta, usando el servidor MCP externo
mcp-atlassian via protocolo stdio.

Deduplicación:
  - Nivel 1: si el action_id ya tiene jira_sync_status, se omite.
  - Nivel 2: si el mismo tema ya tiene un ticket creado en los últimos
    JIRA_DEDUP_DAYS días, se reutiliza y no se crea uno nuevo.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from app.agents.state import AgentState, add_error
from app.core.config import settings
from app.databases.repositories import ActionRepository
from app.mcp.jira_mcp_client import JiraMCPClient
from app.schemas.analysis import PrioritizedTheme, Recommendation

logger = logging.getLogger(__name__)

JIRA_ELIGIBLE_PRIORITIES = {"Crítica", "Alta"}

PRIORITY_MAP = {
    "Crítica": settings.jira_priority_critica,
    "Alta":    settings.jira_priority_alta,
}


def build_jira_description(
    theme: PrioritizedTheme,
    recommendation: Recommendation,
    evidence_by_theme: Dict,
) -> str:
    """Construye la descripción de la issue Jira en formato Markdown."""
    lines = [
        f"## Tema detectado",
        f"**{theme.name}** — Prioridad: {theme.priority}",
        "",
        "## Descripción del problema",
        theme.description,
        "",
        "## Recomendación de FeedbackRadar",
        recommendation.description,
        "",
    ]

    if recommendation.expected_impact:
        lines += [
            "## Impacto esperado",
            recommendation.expected_impact,
            "",
        ]

    evidence_list = evidence_by_theme.get(theme.name, [])
    if evidence_list:
        lines.append("## Evidencias de usuarios (muestra)")
        for ev in evidence_list[:3]:
            platform = ev.platform or "Desconocida"
            text = ev.text[:200].replace('"', "'")
            lines.append(f'- [{platform}] "{text}"')
        lines.append("")

    lines += [
        "## Metadatos",
        "- Fuente: FeedbackRadar Agentic (análisis automatizado de feedback)",
        f"- Fecha de generación: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        f"- Evidencias analizadas: {theme.evidence_count}",
    ]

    return "\n".join(lines)


async def create_jira_issues(state: AgentState) -> AgentState:
    """
    Crea issues en Jira para las acciones con prioridad Crítica o Alta.

    Proceso por cada tema elegible:
    1. Verifica deduplicación en MongoDB (mismo tema, últimos N días).
    2. Si no hay ticket previo, llama al servidor MCP mcp-atlassian.
    3. Actualiza el documento de acción en MongoDB con jira_issue_key.
    4. Acumula resultado en state["jira_issues_created"].
    """
    logger.info("=== Jira Action Agent: Iniciando ===")
    state["jira_issues_created"] = []

    if not settings.jira_mcp_enabled:
        logger.info("Integración Jira deshabilitada (JIRA_MCP_ENABLED=false) — omitiendo")
        return state

    prioritized_themes: List[PrioritizedTheme] = state.get("prioritized_themes", [])
    recommendations: List[Recommendation] = state.get("recommendations", [])
    evidence_by_theme: Dict = state.get("evidence_by_theme", {})

    if not prioritized_themes:
        logger.warning("No hay temas priorizados — Jira Agent sin trabajo")
        return state

    # Mapa tema → recomendación
    rec_by_theme: Dict[str, Recommendation] = {}
    for rec in recommendations:
        if rec.related_themes:
            rec_by_theme[rec.related_themes[0]] = rec

    jira_issues: List[Dict] = []

    try:
        async with JiraMCPClient() as jira:
            tools = await jira.list_tools()
            logger.info(f"Herramientas MCP disponibles: {tools}")

            for theme in prioritized_themes:
                if theme.priority not in JIRA_ELIGIBLE_PRIORITIES:
                    logger.info(f"Omitido '{theme.name}' (prioridad: {theme.priority})")
                    continue

                rec = rec_by_theme.get(theme.name)
                if not rec:
                    logger.warning(f"Sin recomendación para '{theme.name}' — no se crea ticket")
                    continue

                # ── Deduplicación nivel 2: mismo tema en los últimos N días ──
                existing = await ActionRepository.find_recent_jira_by_theme(
                    theme.name, days=settings.jira_dedup_days
                )
                if existing:
                    key = existing.get("jira_issue_key", "")
                    url = existing.get("jira_issue_url", "")
                    logger.info(
                        f"Ticket ya existe para '{theme.name}' en los últimos "
                        f"{settings.jira_dedup_days} días: {key} — reutilizando"
                    )
                    jira_issues.append({
                        "theme": theme.name,
                        "key": key,
                        "url": url,
                        "priority": theme.priority,
                        "reused": True,
                    })
                    continue

                # ── Crear issue en Jira ──
                summary = f"[FeedbackRadar] {rec.title}"
                description = build_jira_description(theme, rec, evidence_by_theme)
                jira_priority = PRIORITY_MAP[theme.priority]

                logger.info(f"Creando issue Jira para '{theme.name}' (prioridad Jira: {jira_priority})…")
                result = await jira.create_issue(
                    summary=summary,
                    description=description,
                    jira_priority=jira_priority,
                )

                if result.get("success"):
                    issue_key: str = result["key"]
                    issue_url: str = result.get("url", f"{settings.jira_base_url}/browse/{issue_key}")

                    # Actualizar documento de acción en MongoDB
                    action_doc = await ActionRepository.find_by_title_recent(rec.title)
                    if action_doc:
                        await ActionRepository.update_jira_fields(
                            action_id=action_doc["action_id"],
                            theme_name=theme.name,
                            jira_issue_key=issue_key,
                            jira_issue_url=issue_url,
                            jira_sync_status="created",
                        )
                    else:
                        logger.warning(
                            f"No se encontró action en MongoDB con título '{rec.title}' "
                            "para actualizar campos Jira"
                        )

                    jira_issues.append({
                        "theme": theme.name,
                        "key": issue_key,
                        "url": issue_url,
                        "priority": theme.priority,
                        "reused": False,
                    })
                    logger.info(f"✓ Issue creada: {issue_key} — {issue_url}")

                else:
                    error_msg = result.get("error", "Error desconocido")
                    logger.error(f"Error creando issue para '{theme.name}': {error_msg}")

                    # Marcar como fallido en MongoDB (deduplicación: no reintentar)
                    action_doc = await ActionRepository.find_by_title_recent(rec.title)
                    if action_doc:
                        await ActionRepository.update_jira_fields(
                            action_id=action_doc["action_id"],
                            theme_name=theme.name,
                            jira_issue_key=None,
                            jira_issue_url=None,
                            jira_sync_status="failed",
                        )
                    add_error(state, f"Error creando ticket Jira para '{theme.name}': {error_msg}")

    except Exception as exc:
        error_msg = f"Error crítico en Jira Action Agent: {exc}"
        logger.error(error_msg, exc_info=True)
        add_error(state, error_msg)

    state["jira_issues_created"] = jira_issues

    logger.info("=== Jira Action Agent: Completado ===")
    logger.info(
        f"Issues procesadas: {len(jira_issues)} "
        f"({sum(1 for i in jira_issues if not i.get('reused'))} nuevas, "
        f"{sum(1 for i in jira_issues if i.get('reused'))} reutilizadas)"
    )
    return state
