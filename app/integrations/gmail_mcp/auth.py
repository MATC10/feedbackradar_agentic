"""
Gmail OAuth Authentication Module

Este módulo gestiona la autenticación OAuth 2.0 con Gmail para el Gmail MCP Collector.
NO lee Gmail directamente; solo obtiene tokens OAuth que luego se pasan a Anthropic API.

IMPORTANTE: El Gmail Remote MCP Server (gmailmcp.googleapis.com) requiere credenciales
de tipo "Web application", NO "Desktop app". Descarga credentials_web.json desde
Google Cloud Console con tipo Web application y redirect URI http://localhost:8080.
"""

import json
import logging
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional
from urllib.parse import parse_qs, urlparse
import webbrowser

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow, InstalledAppFlow

from app.core.config import settings

logger = logging.getLogger(__name__)

# Scopes requeridos por el Gmail MCP Server (documentados por Google)
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://mail.google.com/",
]

# Puerto local para el callback OAuth de Web Application
_WEB_APP_REDIRECT_PORT = 8080
_WEB_APP_REDIRECT_URI = f"http://localhost:{_WEB_APP_REDIRECT_PORT}/"


def _load_credentials_type(credentials_file: str) -> str:
    """
    Detecta el tipo de credenciales OAuth ('installed' o 'web').

    Returns:
        str: 'installed' para Desktop App, 'web' para Web Application
    """
    with open(credentials_file) as f:
        data = json.load(f)
    if "installed" in data:
        return "installed"
    if "web" in data:
        return "web"
    raise ValueError(
        f"Formato de credenciales desconocido en {credentials_file}. "
        "Debe contener 'installed' o 'web'."
    )


def _run_web_app_oauth_flow(credentials_file: str) -> Credentials:
    """
    Ejecuta el flujo OAuth para credenciales de tipo Web Application.

    Abre el navegador, levanta un servidor local en el puerto 8080 para capturar
    el código de autorización y devuelve las credenciales.

    Args:
        credentials_file: Ruta al credentials.json de tipo web

    Returns:
        Credentials: Credenciales OAuth obtenidas

    Raises:
        ValueError: Si la autorización falla o no se recibe código
    """
    flow = Flow.from_client_secrets_file(
        credentials_file,
        scopes=SCOPES,
        redirect_uri=_WEB_APP_REDIRECT_URI,
    )

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )

    authorization_code: Optional[str] = None
    auth_error: Optional[str] = None

    class _OAuthCallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal authorization_code, auth_error
            params = parse_qs(urlparse(self.path).query)
            if "code" in params:
                authorization_code = params["code"][0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(
                    b"<html><body><h2>Autorizacion completada.</h2>"
                    b"<p>Puedes cerrar esta pestana.</p></body></html>"
                )
            elif "error" in params:
                auth_error = params.get("error", ["unknown"])[0]
                self.send_response(400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(
                    f"<html><body><h2>Error: {auth_error}</h2></body></html>".encode("ascii", errors="replace")
                )

        def log_message(self, format, *args):
            pass  # Silenciar logs del servidor HTTP

    logger.info(f"Iniciando OAuth Web Application flow...")
    logger.info(f"Abriendo navegador para autorización...")
    logger.info(f"Si el navegador no se abre, visita: {auth_url}")

    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", _WEB_APP_REDIRECT_PORT), _OAuthCallbackHandler)
    server.handle_request()
    server.server_close()

    if auth_error:
        raise ValueError(f"OAuth authorization failed: {auth_error}")
    if not authorization_code:
        raise ValueError("No se recibió código de autorización en el callback OAuth")

    flow.fetch_token(code=authorization_code)
    logger.info("OAuth Web Application flow completado exitosamente")
    return flow.credentials


def _save_token(token_file: str, creds: Credentials) -> None:
    """
    Guarda las credenciales OAuth en un archivo JSON.

    Args:
        token_file: Ruta del archivo donde guardar el token
        creds: Credenciales de Google OAuth
    """
    try:
        with open(token_file, "w") as token:
            token.write(creds.to_json())
        logger.info(f"Token guardado en {token_file}")
    except Exception as e:
        logger.error(f"Error al guardar token: {e}")
        raise


def get_google_access_token() -> str:
    """
    Obtiene un token de acceso válido de Google OAuth.

    Soporta credenciales de tipo 'installed' (Desktop App) y 'web' (Web Application).
    El Gmail Remote MCP Server requiere credenciales de tipo 'web'.

    Flujo:
    1. Si no existe credentials.json (ni credentials_web.json), lanza FileNotFoundError
    2. Si existe token.json, lo carga
    3. Si el token es válido, lo devuelve
    4. Si expiró y tiene refresh token, lo refresca
    5. Si no hay credenciales válidas, inicia el flujo OAuth apropiado
    6. Guarda el token actualizado
    7. Devuelve el token como string

    Returns:
        str: Token de acceso válido

    Raises:
        FileNotFoundError: Si no existe credentials.json ni credentials_web.json
        ValueError: Si no se pudo obtener un token válido
    """
    token_file = settings.gmail_mcp_token_file

    # Resolver qué archivo de credenciales usar.
    # Prioridad: credentials_web.json (Web App) > credentials.json (Desktop App)
    credentials_file = _resolve_credentials_file()

    creds: Optional[Credentials] = None

    # Cargar token existente si existe
    if os.path.exists(token_file):
        try:
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)
            logger.info(f"Token cargado desde {token_file}")
        except Exception as e:
            logger.warning(f"Error al cargar token existente: {e}")
            creds = None

    # Si no hay credenciales válidas, obtenerlas
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                logger.info("Refrescando token expirado...")
                creds.refresh(Request())
                logger.info("Token refrescado exitosamente")
            except Exception as e:
                logger.error(f"Error al refrescar token: {e}")
                creds = None

        # Si aún no hay credenciales válidas, iniciar OAuth flow
        if not creds or not creds.valid:
            cred_type = _load_credentials_type(credentials_file)
            logger.info(f"Iniciando OAuth flow (tipo: {cred_type})...")

            if cred_type == "web":
                try:
                    creds = _run_web_app_oauth_flow(credentials_file)
                except Exception as e:
                    logger.error(f"Error en OAuth Web App flow: {e}")
                    raise ValueError(f"No se pudo completar el OAuth flow: {e}")
            else:
                # Installed (Desktop App) — mantener compatibilidad
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_file, SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    logger.info("OAuth Installed App flow completado exitosamente")
                except Exception as e:
                    logger.error(f"Error en OAuth flow: {e}")
                    raise ValueError(f"No se pudo completar el OAuth flow: {e}")

            _save_token(token_file, creds)

    if not creds or not creds.token:
        raise ValueError("No se pudo obtener un token de acceso válido")

    logger.info("Token de acceso obtenido exitosamente")
    return creds.token


def _resolve_credentials_file() -> str:
    """
    Determina qué archivo de credenciales usar.

    Prioridad:
    1. credentials_web.json (Web Application — requerido por Gmail MCP Server)
    2. credentials.json (Desktop App — solo para compatibilidad)

    Returns:
        str: Ruta al archivo de credenciales a usar

    Raises:
        FileNotFoundError: Si no se encuentra ningún archivo de credenciales
    """
    # Probar primero Web Application credentials
    web_creds = "credentials_web.json"
    if os.path.exists(web_creds):
        logger.info(f"Usando credenciales Web Application: {web_creds}")
        return web_creds

    # Fallback a Desktop App credentials
    desktop_creds = settings.gmail_mcp_credentials_file
    if os.path.exists(desktop_creds):
        cred_type = _load_credentials_type(desktop_creds)
        if cred_type == "installed":
            logger.warning(
                "Usando credenciales Desktop App (tipo 'installed'). "
                "El Gmail MCP Server requiere credenciales Web Application. "
                "Crea credentials_web.json con tipo 'Web application' en Google Cloud Console."
            )
        return desktop_creds

    raise FileNotFoundError(
        f"No se encontró credentials_web.json ni {desktop_creds}. "
        "Descarga las credenciales desde Google Cloud Console "
        "(tipo 'Web application' para Gmail MCP Server)."
    )


def revoke_token() -> bool:
    """
    Revoca el token OAuth eliminando el archivo token.json.

    Returns:
        bool: True si se eliminó el token, False si no existía
    """
    token_file = settings.gmail_mcp_token_file

    if os.path.exists(token_file):
        try:
            os.remove(token_file)
            logger.info(f"Token revocado: {token_file} eliminado")
            return True
        except Exception as e:
            logger.error(f"Error al eliminar token: {e}")
            raise
    else:
        logger.info(f"No hay token para revocar: {token_file} no existe")
        return False
