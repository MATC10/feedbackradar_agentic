"""
Anthropic Gmail MCP Client

Soporta dos modos de operación (controlado por GMAIL_USE_DIRECT_API en .env):

  GMAIL_USE_DIRECT_API=true  → Gmail API directa (gmail.googleapis.com)
  GMAIL_USE_DIRECT_API=false → Gmail Remote MCP Server (gmailmcp.googleapis.com)

Ambos modos devuelven emails en formato FeedbackRadar CSV.
"""

import base64
import logging
import re
import time
from email.utils import parseaddr, parsedate_to_datetime
from datetime import datetime
from typing import Optional
import httpx

from app.core.config import settings
from app.integrations.gmail_mcp.auth import get_google_access_token

logger = logging.getLogger(__name__)


async def fetch_emails_via_gmail_mcp(
    subject: Optional[str] = None,
    max_results: int = 10
) -> list[dict]:
    """
    Obtiene emails de Gmail en formato FeedbackRadar.

    Según GMAIL_USE_DIRECT_API:
      - True:  llama a gmail.googleapis.com directamente
      - False: usa Claude + Gmail Remote MCP Server

    Returns:
        list[dict]: Emails con campos id, nombre, fecha, reseña, plataforma
    """
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY no está configurada")

    subject_filter = subject if subject is not None else settings.gmail_mcp_subject_filter
    logger.info(f"Iniciando fetch de emails con filtro: '{subject_filter}'")

    access_token = get_google_access_token()
    logger.info("Access token obtenido exitosamente")

    if settings.gmail_use_direct_api:
        logger.info("Modo: Gmail API directa (GMAIL_USE_DIRECT_API=true)")
        emails = await _fetch_via_direct_api(subject_filter, max_results, access_token)
    else:
        logger.info("Modo: Gmail Remote MCP Server (GMAIL_USE_DIRECT_API=false)")
        emails = await _fetch_via_mcp(subject_filter, max_results, access_token)

    logger.info(f"Se obtuvieron {len(emails)} emails exitosamente")
    return emails


# ---------------------------------------------------------------------------
# Implementación A: Gmail API directa
# ---------------------------------------------------------------------------

async def _fetch_via_direct_api(
    subject_filter: str, max_results: int, access_token: str
) -> list[dict]:
    """Obtiene emails llamando a gmail.googleapis.com directamente."""
    auth_headers = {"Authorization": f"Bearer {access_token}"}
    emails = []

    # Solo traer emails llegados desde el último ciclo de polling (+ 30s de margen)
    cutoff = int(time.time()) - (settings.gmail_mcp_poll_interval_seconds + 30)
    query = f"subject:{subject_filter} after:{cutoff}"
    logger.info(f"Query Gmail: '{query}'")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Buscar threads
        search_resp = await client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/threads",
            headers=auth_headers,
            params={"q": query, "maxResults": max_results},
        )
        search_resp.raise_for_status()
        threads = search_resp.json().get("threads", [])
        logger.info(f"Gmail API directa: {len(threads)} threads encontrados")

        # 2. Obtener contenido completo de cada thread
        for thread in threads:
            try:
                thread_resp = await client.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/threads/{thread['id']}",
                    headers=auth_headers,
                    params={"format": "full"},
                )
                thread_resp.raise_for_status()
                thread_data = thread_resp.json()

                messages = thread_data.get("messages", [])
                if not messages:
                    continue

                first_msg = messages[0]
                payload = first_msg.get("payload", {})
                msg_headers = payload.get("headers", [])

                from_val = _get_header(msg_headers, "From")
                date_val = _get_header(msg_headers, "Date")
                body = _decode_body(payload)

                email_data = {
                    "id": first_msg.get("id", thread["id"]),
                    "nombre": _extract_name(from_val),
                    "fecha": _parse_date(date_val),
                    "reseña": body.strip(),
                    "plataforma": "Email",
                }

                if _validate_and_normalize_email(email_data):
                    emails.append(email_data)

            except Exception as e:
                logger.warning(f"Error procesando thread {thread['id']}: {e}")
                continue

    return emails


def _get_header(headers: list, name: str) -> str:
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _extract_name(from_header: str) -> str:
    name, addr = parseaddr(from_header)
    return name if name else addr


def _parse_date(date_str: str) -> str:
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")


def _decode_body(payload: dict) -> str:
    """Extrae texto plano del payload Gmail (maneja multipart recursivamente)."""
    mime_type = payload.get("mimeType", "")

    if mime_type == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        result = _decode_body(part)
        if result:
            return result

    data = payload.get("body", {}).get("data", "")
    if data:
        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")

    return ""


# ---------------------------------------------------------------------------
# Implementación B: Gmail Remote MCP Server (original)
# Para revertir: GMAIL_USE_DIRECT_API=false en .env
# ---------------------------------------------------------------------------

async def _fetch_via_mcp(
    subject_filter: str, max_results: int, access_token: str
) -> list[dict]:
    """Obtiene emails usando Claude + Gmail Remote MCP Server de Google."""
    prompt = _build_gmail_search_prompt(subject_filter, max_results)

    headers = {
        "Content-Type": "application/json",
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "anthropic-beta": "mcp-client-2025-11-20",
    }

    payload = {
        "model": settings.anthropic_model,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
        "mcp_servers": [
            {
                "type": "url",
                "url": settings.gmail_mcp_server_url,
                "name": "gmail",
                "authorization_token": access_token,
            }
        ],
        "tools": [{"type": "mcp_toolset", "mcp_server_name": "gmail"}],
    }

    logger.info("Llamando a Anthropic API con Gmail MCP...")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        response_data = response.json()

    logger.info(f"Respuesta Anthropic API: {response_data.get('stop_reason')}")

    content_blocks = response_data.get("content", [])
    logger.info(f"Bloques de contenido: {len(content_blocks)}")

    for i, block in enumerate(content_blocks):
        block_type = block.get("type", "unknown")
        if block_type == "mcp_tool_use":
            logger.info(f"MCP Tool usado: {block.get('name')} — input: {block.get('input')}")
        elif block_type == "mcp_tool_result":
            results = block.get("content", [])
            if results:
                logger.info(f"MCP Tool Result (preview): {str(results[0])[:300]}")
        elif block_type == "text":
            preview = block.get("text", "")[:300]
            logger.info(f"Bloque texto (preview): {preview}")

    return _extract_emails_from_response(response_data)


def _build_gmail_search_prompt(subject_filter: str, max_results: int) -> str:
    # Query activa: filtro por asunto
    search_query = f"subject:{subject_filter}"
    # Para filtrar por fecha, sustituir la línea anterior por:
    # search_query = "newer_than:1d"

    return f"""Debes usar las herramientas de Gmail MCP para buscar emails en la cuenta autorizada.

PASO 1: Usa la tool search_threads con esta query EXACTA:
{search_query}

PASO 2: Para cada thread encontrado, usa get_thread para obtener el contenido completo.

PASO 3: Devuelve ÚNICAMENTE un array JSON con este formato:

[
  {{
    "id": "<gmail_message_id>",
    "nombre": "<nombre completo del remitente>",
    "fecha": "YYYY-MM-DD",
    "reseña": "<contenido completo del email en texto plano>",
    "plataforma": "Email"
  }}
]

IMPORTANTE:
- La query de búsqueda debe ser EXACTAMENTE: {search_query}
- NO uses comillas en la query
- Usa search_threads primero, luego get_thread para cada resultado
- Si el body tiene HTML, extrae solo texto plano
- La fecha DEBE estar en formato YYYY-MM-DD
- El campo "plataforma" SIEMPRE debe ser "Email"
- Límite máximo: {max_results} emails
- Si no encuentras emails, devuelve: []
- NO incluyas markdown, solo JSON puro
"""


def _extract_emails_from_response(response: dict) -> list[dict]:
    emails = []
    try:
        content = response.get("content", [])
        for content_block in content:
            if content_block.get("type") == "text":
                text_content = content_block.get("text", "")
                json_match = re.search(r'\[[\s\S]*?\]', text_content)
                if json_match:
                    import json
                    try:
                        data = json.loads(json_match.group(0))
                        if isinstance(data, list):
                            emails = data
                            logger.info(f"Extraídos {len(emails)} emails del JSON MCP")
                            break
                    except json.JSONDecodeError as e:
                        logger.warning(f"Error al parsear JSON de respuesta MCP: {e}")
                        continue

        validated = []
        for email in emails:
            if _validate_and_normalize_email(email):
                validated.append(email)
        return validated
    except Exception as e:
        logger.error(f"Error al extraer emails de respuesta MCP: {e}")
        return []


# ---------------------------------------------------------------------------
# Validación común
# ---------------------------------------------------------------------------

def _validate_and_normalize_email(email: dict) -> bool:
    required_fields = ["id", "nombre", "fecha", "reseña", "plataforma"]

    if not isinstance(email, dict):
        return False

    for field in required_fields:
        if field not in email:
            logger.warning(f"Email sin campo requerido: {field}")
            return False
        if field != "reseña" and not email[field]:
            logger.warning(f"Email con campo vacío: {field}")
            return False

    if email["plataforma"] != "Email":
        email["plataforma"] = "Email"

    fecha = email["fecha"]
    if not isinstance(fecha, str) or len(fecha) != 10 or fecha.count("-") != 2:
        logger.warning(f"Fecha con formato inválido: {fecha}")
        return False

    return True


def get_client_info() -> dict:
    return {
        "mode": "direct_api" if settings.gmail_use_direct_api else "mcp_server",
        "anthropic_api_key_configured": bool(settings.anthropic_api_key),
        "anthropic_model": settings.anthropic_model,
        "gmail_mcp_server_url": settings.gmail_mcp_server_url,
        "gmail_mcp_subject_filter": settings.gmail_mcp_subject_filter,
    }
