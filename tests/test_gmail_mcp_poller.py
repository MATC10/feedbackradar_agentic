"""
Tests para Gmail MCP Poller
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock, Mock

from app.integrations.gmail_mcp.poller import (
    run_gmail_mcp_poll_once,
    gmail_mcp_polling_loop,
    get_poller_info,
)


class TestRunGmailMCPPollOnce:
    """Tests para la función de polling único."""
    
    @pytest.mark.asyncio
    @patch('app.integrations.gmail_mcp.poller.append_new_gmail_mcp_feedback')
    @patch('app.integrations.gmail_mcp.poller.fetch_emails_via_gmail_mcp')
    @patch('app.integrations.gmail_mcp.poller.settings')
    async def test_poll_once_llama_fetch_emails(
        self, mock_settings, mock_fetch, mock_append
    ):
        """Test que poll_once llama a fetch_emails_via_gmail_mcp."""
        mock_settings.gmail_mcp_subject_filter = "notausuario"
        mock_settings.gmail_mcp_output_csv = "test.csv"
        
        mock_fetch.return_value = [
            {
                "id": "msg1",
                "nombre": "Test User",
                "fecha": "2024-01-01",
                "reseña": "Content",
                "plataforma": "Email"
            }
        ]
        mock_append.return_value = 1
        
        await run_gmail_mcp_poll_once()
        
        # Verificar que se llamó a fetch con el subject correcto
        mock_fetch.assert_called_once_with(subject="notausuario")
    
    @pytest.mark.asyncio
    @patch('app.integrations.gmail_mcp.poller.append_new_gmail_mcp_feedback')
    @patch('app.integrations.gmail_mcp.poller.fetch_emails_via_gmail_mcp')
    @patch('app.integrations.gmail_mcp.poller.settings')
    async def test_poll_once_llama_append_feedback(
        self, mock_settings, mock_fetch, mock_append
    ):
        """Test que poll_once llama a append_new_gmail_mcp_feedback."""
        mock_settings.gmail_mcp_subject_filter = "notausuario"
        mock_settings.gmail_mcp_output_csv = "output.csv"
        
        emails = [
            {
                "id": "msg1",
                "nombre": "User",
                "fecha": "2024-01-01",
                "reseña": "Content",
                "plataforma": "Email"
            }
        ]
        mock_fetch.return_value = emails
        mock_append.return_value = 1
        
        await run_gmail_mcp_poll_once()
        
        # Verificar que se llamó a append con los emails y csv path correcto
        mock_append.assert_called_once_with(emails, "output.csv")
    
    @pytest.mark.asyncio
    @patch('app.integrations.gmail_mcp.poller.append_new_gmail_mcp_feedback')
    @patch('app.integrations.gmail_mcp.poller.fetch_emails_via_gmail_mcp')
    @patch('app.integrations.gmail_mcp.poller.settings')
    async def test_poll_once_devuelve_numero_escritos(
        self, mock_settings, mock_fetch, mock_append
    ):
        """Test que poll_once devuelve el número de emails escritos."""
        mock_settings.gmail_mcp_subject_filter = "test"
        mock_settings.gmail_mcp_output_csv = "test.csv"
        
        mock_fetch.return_value = [
            {"id": "1", "nombre": "A", "fecha": "2024-01-01", "reseña": "X", "plataforma": "Email"},
            {"id": "2", "nombre": "B", "fecha": "2024-01-02", "reseña": "Y", "plataforma": "Email"}
        ]
        mock_append.return_value = 2
        
        result = await run_gmail_mcp_poll_once()
        
        assert result == 2
    
    @pytest.mark.asyncio
    @patch('app.integrations.gmail_mcp.poller.fetch_emails_via_gmail_mcp')
    @patch('app.integrations.gmail_mcp.poller.settings')
    async def test_poll_once_devuelve_cero_sin_emails(
        self, mock_settings, mock_fetch
    ):
        """Test que poll_once devuelve 0 cuando no hay emails."""
        mock_settings.gmail_mcp_subject_filter = "test"
        mock_settings.gmail_mcp_output_csv = "test.csv"
        
        mock_fetch.return_value = []
        
        result = await run_gmail_mcp_poll_once()
        
        assert result == 0
    
    @pytest.mark.asyncio
    @patch('app.integrations.gmail_mcp.poller.fetch_emails_via_gmail_mcp')
    @patch('app.integrations.gmail_mcp.poller.settings')
    async def test_poll_once_propaga_error_cliente(
        self, mock_settings, mock_fetch
    ):
        """Test que poll_once propaga error del cliente Anthropic."""
        mock_settings.gmail_mcp_subject_filter = "test"
        mock_settings.gmail_mcp_output_csv = "test.csv"
        
        mock_fetch.side_effect = Exception("API Error")
        
        with pytest.raises(Exception) as exc_info:
            await run_gmail_mcp_poll_once()
        
        assert "API Error" in str(exc_info.value)


class TestGmailMCPPollingLoop:
    """Tests para el loop de polling."""
    
    @pytest.mark.asyncio
    @patch('app.integrations.gmail_mcp.poller.run_gmail_mcp_poll_once')
    @patch('app.integrations.gmail_mcp.poller.settings')
    async def test_loop_captura_error_y_continua(
        self, mock_settings, mock_poll_once
    ):
        """Test que el loop captura errores y continúa."""
        mock_settings.gmail_mcp_poll_interval_seconds = 0.01
        
        # Primera llamada falla, segunda tiene éxito, tercera termina el test
        call_count = 0
        
        async def side_effect():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Test error")
            elif call_count == 2:
                return 1
            else:
                # Cancelar el loop después de 2 iteraciones
                raise asyncio.CancelledError()
        
        mock_poll_once.side_effect = side_effect
        
        # Ejecutar el loop y esperar que se cancele
        with pytest.raises(asyncio.CancelledError):
            await gmail_mcp_polling_loop()
        
        # Verificar que se llamó múltiples veces (capturó el error y continuó)
        assert mock_poll_once.call_count >= 2
    
    @pytest.mark.asyncio
    @patch('app.integrations.gmail_mcp.poller.run_gmail_mcp_poll_once')
    @patch('app.integrations.gmail_mcp.poller.settings')
    async def test_loop_respeta_intervalo(
        self, mock_settings, mock_poll_once
    ):
        """Test que el loop respeta el intervalo configurado."""
        mock_settings.gmail_mcp_poll_interval_seconds = 0.05
        
        call_times = []
        
        async def side_effect():
            import time
            call_times.append(time.time())
            if len(call_times) >= 3:
                raise asyncio.CancelledError()
            return 0
        
        mock_poll_once.side_effect = side_effect
        
        # Ejecutar el loop
        with pytest.raises(asyncio.CancelledError):
            await gmail_mcp_polling_loop()
        
        # Verificar que hubo al menos 2 llamadas
        assert len(call_times) >= 2
        
        # Verificar que el intervalo entre llamadas es aproximadamente correcto
        if len(call_times) >= 2:
            interval = call_times[1] - call_times[0]
            # Permitir cierta tolerancia (entre 0.04 y 0.15 segundos)
            assert 0.04 <= interval <= 0.15
    
    @pytest.mark.asyncio
    @patch('app.integrations.gmail_mcp.poller.run_gmail_mcp_poll_once')
    @patch('app.integrations.gmail_mcp.poller.settings')
    async def test_loop_ejecuta_poll_once_repetidamente(
        self, mock_settings, mock_poll_once
    ):
        """Test que el loop ejecuta poll_once repetidamente."""
        mock_settings.gmail_mcp_poll_interval_seconds = 0.01
        
        call_count = 0
        
        async def side_effect():
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                raise asyncio.CancelledError()
            return call_count
        
        mock_poll_once.side_effect = side_effect
        
        with pytest.raises(asyncio.CancelledError):
            await gmail_mcp_polling_loop()
        
        # Verificar que se ejecutó múltiples veces
        assert mock_poll_once.call_count >= 3


class TestGetPollerInfo:
    """Tests para información del poller."""
    
    @patch('app.integrations.gmail_mcp.poller.settings')
    def test_get_poller_info(self, mock_settings):
        """Test que devuelve información correcta del poller."""
        mock_settings.gmail_mcp_polling_enabled = True
        mock_settings.gmail_mcp_poll_interval_seconds = 60
        mock_settings.gmail_mcp_subject_filter = "notausuario"
        mock_settings.gmail_mcp_output_csv = "data/raw/gmail.csv"
        
        info = get_poller_info()
        
        assert info["polling_enabled"] is True
        assert info["poll_interval_seconds"] == 60
        assert info["subject_filter"] == "notausuario"
        assert info["output_csv"] == "data/raw/gmail.csv"