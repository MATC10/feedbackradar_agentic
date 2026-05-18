# -*- coding: utf-8 -*-
"""
app/mcp/jira_mcp_client.py

Cliente MCP que conecta al servidor externo mcp-atlassian para crear
issues en Jira Cloud via el protocolo Model Context Protocol (stdio).
"""

import json
import logging
import os
import re
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Dict, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.core.config import settings

logger = logging.getLogger(__name__)


def _find_mcp_atlassian_bin() -> str:
    """Localiza el ejecutable mcp-atlassian en el entorno virtual actual."""
    scripts_dir = Path(sys.executable).parent
    for name in ("mcp-atlassian.exe", "mcp-atlassian"):
        candidate = scripts_dir / name
        if candidate.exists():
            return str(candidate)
    raise RuntimeError(
        "mcp-atlassian no está instalado en el entorno virtual. "
        "Ejecuta: pip install mcp-atlassian"
    )


class JiraMCPClient:
    """
    Cliente async para el servidor MCP de Atlassian/Jira.

    Uso:
        async with JiraMCPClient() as jira:
            result = await jira.create_issue(summary, description, priority)
    """

    def __init__(self) -> None:
        env = {
            **os.environ,
            "JIRA_URL": settings.jira_base_url,
            "JIRA_USERNAME": settings.jira_user_email,
            "JIRA_API_TOKEN": settings.jira_api_token,
        }
        self._server_params = StdioServerParameters(
            command=_find_mcp_atlassian_bin(),
            args=[],
            env=env,
        )
        self._exit_stack: Optional[AsyncExitStack] = None
        self._session: Optional[ClientSession] = None

    async def __aenter__(self) -> "JiraMCPClient":
        self._exit_stack = AsyncExitStack()
        read, write = await self._exit_stack.enter_async_context(
            stdio_client(self._server_params)
        )
        self._session = await self._exit_stack.enter_async_context(
            ClientSession(read, write)
        )
        await self._session.initialize()
        logger.info("Conectado al servidor mcp-atlassian (Jira MCP)")
        return self

    async def __aexit__(self, *args) -> None:
        if self._exit_stack:
            await self._exit_stack.aclose()

    async def create_issue(
        self,
        summary: str,
        description: str,
        jira_priority: str,
    ) -> dict:
        """
        Crea una issue en Jira llamando a la tool jira_create_issue del servidor MCP.

        priority y labels se pasan via additional_fields (JSON string) según el schema
        de mcp-atlassian v0.21+.

        Returns:
            {"success": True, "key": "KAN-42", "url": "https://..."}
            {"success": False, "error": "..."}
        """
        if self._session is None:
            return {"success": False, "error": "Sesión MCP no inicializada"}

        additional: Dict[str, Any] = {
            "priority": {"name": jira_priority},
            "labels": ["feedbackradar", "automated"],
        }

        try:
            result = await self._session.call_tool(
                "jira_create_issue",
                {
                    "project_key": settings.jira_project_key,
                    "summary": summary,
                    "issue_type": settings.jira_default_issue_type,
                    "description": description,
                    "additional_fields": json.dumps(additional),
                },
            )

            if result.isError:
                error_text = " ".join(
                    getattr(c, "text", str(c)) for c in result.content
                )
                logger.error(f"Error MCP al crear issue: {error_text}")
                return {"success": False, "error": error_text}

            # Extraer texto de la respuesta
            text = " ".join(
                getattr(c, "text", "") for c in result.content if hasattr(c, "text")
            )
            logger.debug(f"Respuesta mcp-atlassian: {text[:300]}")

            # Intentar parsear como JSON
            try:
                data = json.loads(text)
                key = data.get("key") or data.get("id", "")
                url = data.get("url") or data.get("self", "")
                if not url and key:
                    url = f"{settings.jira_base_url}/browse/{key}"
                if key:
                    return {"success": True, "key": key, "url": url}
            except (json.JSONDecodeError, AttributeError):
                pass

            # Fallback: extraer clave con regex (ej: KAN-42)
            key_match = re.search(r'\b([A-Z]+-\d+)\b', text)
            if key_match:
                key = key_match.group(1)
                url = f"{settings.jira_base_url}/browse/{key}"
                logger.info(f"Issue key extraída por regex: {key}")
                return {"success": True, "key": key, "url": url}

            logger.warning(f"No se pudo extraer issue key de la respuesta MCP: {text[:200]}")
            return {"success": False, "error": f"Respuesta inesperada del servidor MCP: {text[:100]}"}

        except Exception as exc:
            logger.error(f"Excepción llamando a jira_create_issue: {exc}", exc_info=True)
            return {"success": False, "error": str(exc)}

    async def list_tools(self) -> list:
        """Retorna las herramientas disponibles en el servidor MCP (útil para debug)."""
        if self._session is None:
            return []
        response = await self._session.list_tools()
        return [t.name for t in response.tools]
