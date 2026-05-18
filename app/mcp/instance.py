"""
app/mcp/instance.py

Instancia singleton del FeedbackRadar MCP Server.

Módulo separado para evitar imports circulares:
  tools.py  importa mcp desde aquí (para @mcp.tool())
  server.py importa mcp desde aquí (para mcp.run() y montaje ASGI)
"""

from fastmcp import FastMCP

mcp = FastMCP("FeedbackRadar MCP Server")
