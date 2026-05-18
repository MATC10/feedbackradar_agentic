"""
app/mcp/agent_client.py

Cliente MCP in-process para uso interno de los agentes.

Los agentes usan este módulo para llamar a las tools del FeedbackRadar MCP Server
via el protocolo MCP real, sin importar las funciones de tools.py directamente.
El servidor es el mismo que se expone externamente en /mcp, por lo que internos
y externos comparten exactamente la misma interfaz.
"""

import json
import logging
from typing import Any

from fastmcp import Client

from app.mcp.instance import mcp
import app.mcp.tools  # noqa: F401 — asegura que los @mcp.tool() estén registrados

logger = logging.getLogger(__name__)


async def call_mcp_tool(tool_name: str, args: dict) -> Any:
    """
    Invoca una tool del FeedbackRadar MCP Server via protocolo MCP in-process.

    Args:
        tool_name: Nombre de la tool en el servidor (ej: "search_feedback_tool")
        args: Argumentos de la tool

    Returns:
        Dict con el resultado de la tool

    Raises:
        Exception si la tool falla o devuelve contenido inesperado
    """
    logger.debug(f"MCP call: {tool_name}({args})")
    async with Client(mcp) as client:
        result = await client.call_tool(tool_name, args)
        items = result.content if hasattr(result, "content") else result
        if items:
            return json.loads(items[0].text)
        return {}
