"""
FeedbackRadar Agentic - FastAPI Application

API principal para ingesta y análisis de feedback de usuarios.
"""

import asyncio
import logging
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.databases.mongodb_client import MongoDBClient
from app.databases.elasticsearch_client import ElasticsearchClient
from app.api import feedback_routes, analysis_routes, chat_routes
from app.integrations.gmail_mcp.poller import gmail_mcp_polling_loop
from app.mcp.instance import mcp
import app.mcp.tools  # noqa: F401 — registra los @mcp.tool() al importar

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestiona el ciclo de vida de la aplicación.
    
    Conecta a las bases de datos al iniciar y desconecta al cerrar.
    También gestiona el Gmail MCP Polling si está habilitado.
    """
    # Startup
    logger.info("=" * 80)
    logger.info("Iniciando FeedbackRadar Agentic...")
    logger.info("=" * 80)
    
    # Logging explícito de configuración LLM
    logger.info("CONFIG LLM:")
    logger.info(f"   CHAT_LLM_PROVIDER: {settings.chat_llm_provider}")
    logger.info(f"   OLLAMA_BASE_URL: {settings.ollama_base_url}")
    logger.info(f"   OLLAMA_CHAT_MODEL: {settings.ollama_chat_model}")
    logger.info(f"   OLLAMA_EMBEDDING_MODEL: {settings.ollama_embedding_model}")

    # Verificar qué cliente se crea realmente
    try:
        from app.llm.factory import get_chat_llm_client
        llm_client = get_chat_llm_client()
        client_type = type(llm_client).__name__
        logger.info(f"   [OK] Cliente LLM creado: {client_type}")

        if hasattr(llm_client, 'base_url'):
            logger.info(f"   [OK] Base URL del cliente: {llm_client.base_url}")
        if hasattr(llm_client, 'model'):
            logger.info(f"   [OK] Modelo del cliente: {llm_client.model}")
    except Exception as e:
        logger.error(f"   [ERROR] Error creando cliente LLM: {e}")
    
    logger.info("-" * 80)
    
    try:
        # Conectar a MongoDB
        await MongoDBClient.connect()
        logger.info("[OK] MongoDB conectado")
    except Exception as e:
        logger.error(f"[ERROR] Error conectando a MongoDB: {e}")

    try:
        # Conectar a Elasticsearch
        await ElasticsearchClient.connect()
        logger.info("[OK] Elasticsearch conectado")
    except Exception as e:
        logger.error(f"[ERROR] Error conectando a Elasticsearch: {e}")
    
    # Gmail MCP Polling startup
    polling_task = None
    if settings.gmail_mcp_polling_enabled:
        logger.info("Gmail MCP Polling habilitado. Iniciando tarea en background...")
        polling_task = asyncio.create_task(gmail_mcp_polling_loop())
        logger.info("[OK] Gmail MCP Polling iniciado correctamente")
    else:
        logger.info("Gmail MCP Polling desactivado (GMAIL_MCP_POLLING_ENABLED=false)")
    
    # Arrancar frontend Streamlit automáticamente
    streamlit_process = None
    try:
        streamlit_bin = Path(sys.executable).parent / "streamlit"
        frontend_path = Path(__file__).parent.parent / "frontend" / "streamlit_app.py"
        streamlit_process = subprocess.Popen(
            [str(streamlit_bin), "run", str(frontend_path), "--server.port", "8501"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("[OK] Frontend Streamlit arrancado en http://localhost:8501")
    except Exception as e:
        logger.warning(f"[WARN] No se pudo arrancar Streamlit: {e}")

    logger.info("=" * 80)
    logger.info("Aplicacion iniciada correctamente")
    logger.info("=" * 80)

    yield

    # Shutdown
    logger.info("Cerrando FeedbackRadar Agentic...")
    if streamlit_process and streamlit_process.poll() is None:
        streamlit_process.terminate()
        logger.info("[OK] Frontend Streamlit detenido")
    
    # Gmail MCP Polling shutdown
    if polling_task is not None:
        logger.info("Cancelando tarea de Gmail MCP Polling...")
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            logger.info("[OK] Gmail MCP Polling cancelado correctamente")
    
    try:
        await MongoDBClient.disconnect()
        logger.info("[OK] MongoDB desconectado")
    except Exception as e:
        logger.error(f"[ERROR] Error desconectando MongoDB: {e}")

    try:
        await ElasticsearchClient.disconnect()
        logger.info("[OK] Elasticsearch desconectado")
    except Exception as e:
        logger.error(f"[ERROR] Error desconectando Elasticsearch: {e}")

    logger.info("Aplicacion cerrada")


# Crear aplicación FastAPI
app = FastAPI(
    title="FeedbackRadar Agentic",
    description="API para ingesta y análisis inteligente de feedback de usuarios",
    version="0.2.0",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Montar FeedbackRadar MCP Server como sub-app ASGI (accesible en /mcp)
# Los agentes internos lo usan via Client(mcp) in-process; clientes externos via SSE en /mcp
app.mount("/mcp", mcp.http_app(transport="streamable-http"))

# Incluir routers
app.include_router(
    feedback_routes.router,
    prefix="/feedback",
    tags=["Feedback"]
)

app.include_router(
    analysis_routes.router,
    prefix="/analysis",
    tags=["Analysis"]
)

app.include_router(
    chat_routes.router,
    prefix="/chat",
    tags=["Chat"]
)


@app.get("/", tags=["Root"])
async def root():
    """
    Endpoint raíz de la API.
    
    Returns:
        Información básica de la API
    """
    return {
        "name": "FeedbackRadar Agentic",
        "version": "0.2.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Endpoint de health check.
    
    Verifica que la API está respondiendo y que las conexiones
    a las bases de datos están activas.
    
    Returns:
        Estado de salud de la aplicación y sus dependencias
    """
    health_status = {
        "status": "healthy",
        "api": "ok",
        "mongodb": "unknown",
        "elasticsearch": "unknown"
    }
    
    # Verificar MongoDB
    try:
        db = MongoDBClient.get_database()
        await db.command('ping')
        health_status["mongodb"] = "ok"
    except Exception as e:
        health_status["mongodb"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Verificar Elasticsearch
    try:
        client = ElasticsearchClient.get_client()
        await client.ping()
        health_status["elasticsearch"] = "ok"
    except Exception as e:
        health_status["elasticsearch"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )