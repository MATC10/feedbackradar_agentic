"""
app/mcp/server.py

Punto de entrada del FeedbackRadar MCP Server.

Las tools están definidas y registradas con @mcp.tool() directamente en tools.py.
Este módulo importa tools para activar el registro y expone main() para arranque CLI.
"""

import logging

from app.mcp.instance import mcp
import app.mcp.tools  # noqa: F401 — registra los @mcp.tool() al importar

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Punto de entrada CLI del servidor MCP (transporte stdio)."""
    logger.info("Iniciando FeedbackRadar MCP Server...")
    mcp.run()


if __name__ == "__main__":
    main()
