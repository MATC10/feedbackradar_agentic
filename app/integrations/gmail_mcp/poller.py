"""
Gmail MCP Poller

Ejecuta polling periódico para obtener emails de Gmail via Anthropic + Gmail MCP
y guardarlos en CSV compatible con FeedbackRadar.
"""

import asyncio
import logging
from typing import Optional

from app.core.config import settings
from app.integrations.gmail_mcp.anthropic_gmail_client import fetch_emails_via_gmail_mcp
from app.integrations.gmail_mcp.csv_writer import append_new_gmail_mcp_feedback
from app.ingestion.ingestion_service import IngestionService

logger = logging.getLogger(__name__)


async def run_gmail_mcp_poll_once() -> int:
    """
    Ejecuta un ciclo de polling: obtiene emails de Gmail MCP y los guarda en CSV.
    
    Flujo:
    1. Obtiene emails via fetch_emails_via_gmail_mcp
    2. Guarda emails nuevos en CSV via append_new_gmail_mcp_feedback
    3. Devuelve número de emails escritos
    
    Returns:
        int: Número de emails nuevos escritos en CSV
        
    Raises:
        Exception: Si hay error en la obtención o escritura de emails
    """
    logger.info("Iniciando ciclo de polling Gmail MCP")
    
    try:
        # 1. Obtener emails via Gmail MCP
        logger.info(f"Buscando emails con asunto: '{settings.gmail_mcp_subject_filter}'")
        
        emails = await fetch_emails_via_gmail_mcp(
            subject=settings.gmail_mcp_subject_filter
        )
        
        logger.info(f"Claude encontró {len(emails)} emails")
        
        # Si no hay emails, retornar 0
        if not emails:
            logger.info("No hay emails para procesar")
            return 0
        
        # 2. Guardar emails nuevos en CSV (deduplicado por .ids)
        logger.info(f"Guardando emails en {settings.gmail_mcp_output_csv}")

        written, new_emails = await asyncio.to_thread(
            append_new_gmail_mcp_feedback,
            emails,
            settings.gmail_mcp_output_csv
        )

        logger.info(f"Escritos {written} emails nuevos en CSV")

        # 3. Ingestar emails nuevos a MongoDB + Elasticsearch
        if new_emails:
            logger.info(f"Ingiriendo {len(new_emails)} emails en MongoDB + Elasticsearch...")
            ingestion_service = IngestionService(enable_embeddings=True)
            result = await ingestion_service.ingest_from_dicts(new_emails, source_name="gmail")
            logger.info(
                f"Ingesta completada: {result.inserted_rows} en MongoDB, "
                f"{result.indexed_rows} en Elasticsearch"
            )
            if result.errors:
                logger.warning(f"Errores durante ingesta: {result.errors}")

        return written
        
    except Exception as e:
        logger.error(f"Error en ciclo de polling: {e}", exc_info=True)
        raise


async def gmail_mcp_polling_loop() -> None:
    """
    Loop infinito de polling para Gmail MCP.
    
    Ejecuta run_gmail_mcp_poll_once() cada gmail_mcp_poll_interval_seconds.
    Captura errores por iteración y continúa el loop.
    
    Este loop está diseñado para ejecutarse como background task en FastAPI.
    """
    logger.info(
        f"Iniciando Gmail MCP polling loop "
        f"(intervalo: {settings.gmail_mcp_poll_interval_seconds}s)"
    )
    
    iteration = 0
    
    while True:
        iteration += 1
        logger.debug(f"Polling iteration #{iteration}")
        
        try:
            # Ejecutar un ciclo de polling
            written = await run_gmail_mcp_poll_once()
            
            if written > 0:
                logger.info(f"Iteration #{iteration}: {written} emails nuevos procesados")
            else:
                logger.debug(f"Iteration #{iteration}: No hay emails nuevos")
                
        except Exception as e:
            # Capturar error pero continuar el loop
            logger.error(
                f"Error en iteration #{iteration}: {e}",
                exc_info=True
            )
            logger.info("Continuando con siguiente iteración...")
        
        # Esperar antes de la siguiente iteración
        logger.debug(f"Esperando {settings.gmail_mcp_poll_interval_seconds}s hasta próximo poll")
        await asyncio.sleep(settings.gmail_mcp_poll_interval_seconds)


# Función auxiliar para obtener información del poller
def get_poller_info() -> dict:
    """
    Devuelve información sobre la configuración del poller.
    
    Returns:
        dict: Configuración actual del poller
    """
    return {
        "polling_enabled": settings.gmail_mcp_polling_enabled,
        "poll_interval_seconds": settings.gmail_mcp_poll_interval_seconds,
        "subject_filter": settings.gmail_mcp_subject_filter,
        "output_csv": settings.gmail_mcp_output_csv,
    }