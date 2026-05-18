# -*- coding: utf-8 -*-
"""
Modulo MCP (Model Context Protocol) para FeedbackRadar Agentic.

Expone herramientas que encapsulan las capacidades del sistema para ser
consumidas por agentes LangGraph sin dependencia directa de repositorios.
"""

from app.mcp.tools import (
    search_feedback,
    get_feedback_stats,
    save_insight,
    create_action_item,
    get_recent_feedback,
)

__all__ = [
    "search_feedback",
    "get_feedback_stats",
    "save_insight",
    "create_action_item",
    "get_recent_feedback",
]