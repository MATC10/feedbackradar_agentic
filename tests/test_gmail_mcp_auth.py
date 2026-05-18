"""
Tests para Gmail MCP Authentication
"""

import pytest
import os
from unittest.mock import Mock, patch, mock_open, MagicMock
from datetime import datetime, timedelta

from app.integrations.gmail_mcp.auth import (
    get_google_access_token,
    revoke_token,
    SCOPES,
)


class TestGetGoogleAccessToken:
    """Tests para obtención de access token."""
    
    @patch('app.integrations.gmail_mcp.auth.settings')
    @patch('app.integrations.gmail_mcp.auth.os.path.exists')
    @patch('app.integrations.gmail_mcp.auth.Credentials.from_authorized_user_file')
    def test_token_valido_existente(self, mock_from_file, mock_exists, mock_settings):
        """Test con token válido existente."""
        # Configurar settings
        mock_settings.gmail_mcp_credentials_file = "credentials.json"
        mock_settings.gmail_mcp_token_file = "token.json"
        
        # Simular que ambos archivos existen
        mock_exists.side_effect = lambda path: True
        
        # Mock de credenciales válidas
        mock_creds = Mock()
        mock_creds.valid = True
        mock_creds.token = "valid_access_token_12345"
        mock_from_file.return_value = mock_creds
        
        # Ejecutar
        token = get_google_access_token()
        
        # Verificar
        assert token == "valid_access_token_12345"
        assert isinstance(token, str)
        mock_from_file.assert_called_once_with("token.json", SCOPES)
    
    @patch('app.integrations.gmail_mcp.auth.settings')
    @patch('app.integrations.gmail_mcp.auth.os.path.exists')
    @patch('app.integrations.gmail_mcp.auth.Credentials.from_authorized_user_file')
    @patch('app.integrations.gmail_mcp.auth.Request')
    @patch('app.integrations.gmail_mcp.auth._save_token')
    def test_token_expirado_con_refresh(
        self, mock_save_token, mock_request, mock_from_file, mock_exists, mock_settings
    ):
        """Test con token expirado que se refresca."""
        # Configurar settings
        mock_settings.gmail_mcp_credentials_file = "credentials.json"
        mock_settings.gmail_mcp_token_file = "token.json"
        
        # Simular que ambos archivos existen
        mock_exists.side_effect = lambda path: True
        
        # Mock de credenciales expiradas con refresh_token
        mock_creds = Mock()
        # Inicialmente no válido y expirado
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh_token_xyz"
        mock_creds.token = "new_refreshed_token_67890"
        
        # Después del refresh, debe ser válido
        def side_effect_refresh(request):
            mock_creds.valid = True
        
        mock_creds.refresh = Mock(side_effect=side_effect_refresh)
        
        mock_from_file.return_value = mock_creds
        
        # Ejecutar
        token = get_google_access_token()
        
        # Verificar
        assert token == "new_refreshed_token_67890"
        mock_creds.refresh.assert_called_once()
        mock_save_token.assert_called_once_with("token.json", mock_creds)
    
    @patch('app.integrations.gmail_mcp.auth.settings')
    @patch('app.integrations.gmail_mcp.auth.os.path.exists')
    @patch('app.integrations.gmail_mcp.auth.InstalledAppFlow.from_client_secrets_file')
    @patch('builtins.open', new_callable=mock_open)
    def test_token_ausente_dispara_oauth(
        self, mock_file, mock_flow_class, mock_exists, mock_settings
    ):
        """Test cuando no existe token y se dispara OAuth."""
        # Configurar settings
        mock_settings.gmail_mcp_credentials_file = "credentials.json"
        mock_settings.gmail_mcp_token_file = "token.json"
        
        # Simular que credentials existe pero token no
        def exists_side_effect(path):
            return path == "credentials.json"
        
        mock_exists.side_effect = exists_side_effect
        
        # Mock del flujo OAuth
        mock_flow = Mock()
        mock_creds = Mock()
        mock_creds.token = "oauth_new_token_abcdef"
        mock_creds.to_json.return_value = '{"token": "oauth_new_token_abcdef"}'
        
        mock_flow.run_local_server.return_value = mock_creds
        mock_flow_class.return_value = mock_flow
        
        # Ejecutar
        token = get_google_access_token()
        
        # Verificar
        assert token == "oauth_new_token_abcdef"
        mock_flow_class.assert_called_once_with("credentials.json", SCOPES)
        mock_flow.run_local_server.assert_called_once_with(port=0)
        mock_file.assert_called()  # Verificar que se guardó el token
    
    @patch('app.integrations.gmail_mcp.auth.settings')
    @patch('app.integrations.gmail_mcp.auth.os.path.exists')
    def test_credentials_ausente(self, mock_exists, mock_settings):
        """Test cuando no existe credentials.json."""
        # Configurar settings
        mock_settings.gmail_mcp_credentials_file = "credentials.json"
        mock_settings.gmail_mcp_token_file = "token.json"
        
        # Simular que credentials.json no existe
        mock_exists.return_value = False
        
        # Ejecutar y verificar excepción
        with pytest.raises(FileNotFoundError) as exc_info:
            get_google_access_token()
        
        assert "credentials.json" in str(exc_info.value)
        assert "Google Cloud Console" in str(exc_info.value)
    
    @patch('app.integrations.gmail_mcp.auth.settings')
    @patch('app.integrations.gmail_mcp.auth.os.path.exists')
    @patch('app.integrations.gmail_mcp.auth.Credentials.from_authorized_user_file')
    def test_devuelve_string_access_token(
        self, mock_from_file, mock_exists, mock_settings
    ):
        """Test que devuelve string access token."""
        # Configurar settings
        mock_settings.gmail_mcp_credentials_file = "credentials.json"
        mock_settings.gmail_mcp_token_file = "token.json"
        
        # Simular que ambos archivos existen
        mock_exists.side_effect = lambda path: True
        
        # Mock de credenciales
        mock_creds = Mock()
        mock_creds.valid = True
        mock_creds.token = "test_token_string"
        mock_from_file.return_value = mock_creds
        
        # Ejecutar
        token = get_google_access_token()
        
        # Verificar que es string
        assert isinstance(token, str)
        assert token == "test_token_string"
        assert len(token) > 0


class TestRevokeToken:
    """Tests para revocación de token."""
    
    @patch('app.integrations.gmail_mcp.auth.settings')
    @patch('app.integrations.gmail_mcp.auth.os.path.exists')
    @patch('app.integrations.gmail_mcp.auth.os.remove')
    def test_revoke_token_existente(self, mock_remove, mock_exists, mock_settings):
        """Test revocación de token existente."""
        mock_settings.gmail_mcp_token_file = "token.json"
        mock_exists.return_value = True
        
        result = revoke_token()
        
        assert result is True
        mock_remove.assert_called_once_with("token.json")
    
    @patch('app.integrations.gmail_mcp.auth.settings')
    @patch('app.integrations.gmail_mcp.auth.os.path.exists')
    def test_revoke_token_no_existente(self, mock_exists, mock_settings):
        """Test revocación cuando no existe token."""
        mock_settings.gmail_mcp_token_file = "token.json"
        mock_exists.return_value = False
        
        result = revoke_token()
        
        assert result is False


class TestScopes:
    """Tests para verificación de scopes."""

    def test_scopes_gmail_requeridos(self):
        """Test que contiene los scopes requeridos por el Gmail MCP server."""
        assert "https://www.googleapis.com/auth/gmail.readonly" in SCOPES
        assert "https://www.googleapis.com/auth/gmail.compose" in SCOPES
        assert "https://mail.google.com/" in SCOPES
        assert len(SCOPES) == 3
