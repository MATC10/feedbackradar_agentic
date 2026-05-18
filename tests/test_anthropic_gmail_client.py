"""
Tests para Anthropic Gmail MCP Client
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import httpx

from app.integrations.gmail_mcp.anthropic_gmail_client import (
    fetch_emails_via_gmail_mcp,
    get_client_info,
    _build_gmail_search_prompt,
    _extract_emails_from_response,
    _validate_and_normalize_email,
)


class TestFetchEmailsViaGmailMCP:
    """Tests para la función principal de obtención de emails."""
    
    @pytest.mark.asyncio
    @patch('app.integrations.gmail_mcp.anthropic_gmail_client.get_google_access_token')
    @patch('app.integrations.gmail_mcp.anthropic_gmail_client.httpx.AsyncClient')
    @patch('app.integrations.gmail_mcp.anthropic_gmail_client.settings')
    async def test_fetch_emails_success(
        self, mock_settings, mock_async_client_class, mock_get_token
    ):
        """Test de obtención exitosa de emails con formato FeedbackRadar."""
        mock_settings.anthropic_api_key = "test_api_key"
        mock_settings.anthropic_model = "claude-sonnet-4-6"
        mock_settings.gmail_mcp_server_url = "https://gmailmcp.googleapis.com/mcp/v1"
        mock_settings.gmail_mcp_subject_filter = "notausuario"
        
        mock_get_token.return_value = "test_oauth_token_12345"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "stop_reason": "end_turn",
            "content": [{
                "type": "text",
                "text": '[{"id": "msg123", "nombre": "Juan Perez", "fecha": "2024-01-15", "reseña": "Contenido", "plataforma": "Email"}]'
            }]
        }
        mock_response.raise_for_status = Mock()
        
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_async_client_class.return_value.__aenter__.return_value = mock_client
        
        emails = await fetch_emails_via_gmail_mcp(subject="notausuario")
        
        assert len(emails) == 1
        assert emails[0]["nombre"] == "Juan Perez"
        assert emails[0]["plataforma"] == "Email"
        
        mock_get_token.assert_called_once()
        call_args = mock_client.post.call_args
        headers = call_args[1]["headers"]
        assert headers["anthropic-beta"] == "mcp-client-2025-11-20"
        assert headers["x-api-key"] == "test_api_key"
        
        payload = call_args[1]["json"]
        assert payload["model"] == "claude-sonnet-4-6"
        assert "mcp_servers" in payload
        assert payload["mcp_servers"][0]["authorization_token"] == "test_oauth_token_12345"
        assert payload["tools"][0]["type"] == "mcp_toolset"
    
    @pytest.mark.asyncio
    @patch('app.integrations.gmail_mcp.anthropic_gmail_client.settings')
    async def test_fetch_emails_no_api_key(self, mock_settings):
        """Test cuando no hay API key configurada."""
        mock_settings.anthropic_api_key = ""
        
        with pytest.raises(ValueError) as exc_info:
            await fetch_emails_via_gmail_mcp()
        
        assert "ANTHROPIC_API_KEY" in str(exc_info.value)


class TestBuildGmailSearchPrompt:
    """Tests para construcción de prompts."""
    
    def test_build_prompt_feedbackradar_format(self):
        """Test que el prompt pide formato FeedbackRadar."""
        prompt = _build_gmail_search_prompt("notausuario", 10)
        
        assert "notausuario" in prompt
        assert "nombre" in prompt
        assert "fecha" in prompt
        assert "reseña" in prompt
        assert "plataforma" in prompt
        assert "Email" in prompt
        assert "YYYY-MM-DD" in prompt


class TestExtractEmailsFromResponse:
    """Tests para extracción de emails de respuestas."""
    
    def test_extract_emails_feedbackradar_format(self):
        """Test extracción con formato FeedbackRadar."""
        response_data = {
            "content": [{
                "type": "text",
                "text": '[{"id": "m1", "nombre": "Test", "fecha": "2024-01-01", "reseña": "Body", "plataforma": "Email"}]'
            }]
        }
        
        emails = _extract_emails_from_response(response_data)
        
        assert len(emails) == 1
        assert emails[0]["nombre"] == "Test"
        assert emails[0]["plataforma"] == "Email"
    
    def test_extract_emails_empty_array(self):
        """Test con array vacío."""
        response_data = {
            "content": [{
                "type": "text",
                "text": '[]'
            }]
        }
        
        emails = _extract_emails_from_response(response_data)
        assert len(emails) == 0


class TestValidateAndNormalizeEmail:
    """Tests para validación de estructura de emails."""
    
    def test_validate_feedbackradar_format(self):
        """Test con formato FeedbackRadar válido."""
        email = {
            "id": "msg123",
            "nombre": "Juan Perez",
            "fecha": "2024-01-01",
            "reseña": "Contenido",
            "plataforma": "Email"
        }
        
        assert _validate_and_normalize_email(email) is True
    
    def test_validate_missing_field(self):
        """Test con campo faltante."""
        email = {
            "id": "msg123",
            "nombre": "Juan Perez",
            "fecha": "2024-01-01"
        }
        
        assert _validate_and_normalize_email(email) is False
    
    def test_normalize_plataforma(self):
        """Test que normaliza plataforma a Email."""
        email = {
            "id": "msg123",
            "nombre": "Juan Perez",
            "fecha": "2024-01-01",
            "reseña": "Contenido",
            "plataforma": "Gmail"
        }
        
        result = _validate_and_normalize_email(email)
        
        assert result is True
        assert email["plataforma"] == "Email"
    
    def test_validate_invalid_date_format(self):
        """Test con formato de fecha inválido."""
        email = {
            "id": "msg123",
            "nombre": "Juan Perez",
            "fecha": "2024/01/01",
            "reseña": "Contenido",
            "plataforma": "Email"
        }
        
        assert _validate_and_normalize_email(email) is False


class TestGetClientInfo:
    """Tests para información del cliente."""
    
    @patch('app.integrations.gmail_mcp.anthropic_gmail_client.settings')
    def test_get_client_info(self, mock_settings):
        """Test información del cliente."""
        mock_settings.anthropic_api_key = "test_key"
        mock_settings.anthropic_model = "claude-sonnet-4-6"
        mock_settings.gmail_mcp_server_url = "https://test.url"
        mock_settings.gmail_mcp_subject_filter = "test_filter"
        
        info = get_client_info()
        
        assert info["anthropic_api_key_configured"] is True
        assert info["anthropic_model"] == "claude-sonnet-4-6"