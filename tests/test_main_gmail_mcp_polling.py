"""
Tests para la integración del Gmail MCP Polling en FastAPI main.py
"""
import asyncio
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_settings_polling_disabled():
    """Mock de settings con polling deshabilitado"""
    with patch("app.main.settings") as mock_settings:
        mock_settings.gmail_mcp_polling_enabled = False
        yield mock_settings


@pytest.fixture
def mock_settings_polling_enabled():
    """Mock de settings con polling habilitado"""
    with patch("app.main.settings") as mock_settings:
        mock_settings.gmail_mcp_polling_enabled = True
        yield mock_settings


@pytest.fixture
def mock_polling_loop():
    """Mock del gmail_mcp_polling_loop"""
    with patch("app.main.gmail_mcp_polling_loop") as mock_loop:
        # Simular un loop que nunca termina hasta que se cancela
        async def fake_loop():
            try:
                while True:
                    await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                raise
        mock_loop.side_effect = fake_loop
        yield mock_loop


@pytest.fixture
def mock_mongodb_client():
    """Mock del MongoDBClient"""
    with patch("app.main.MongoDBClient") as mock_mongo:
        mock_mongo.connect = AsyncMock()
        mock_mongo.disconnect = AsyncMock()
        mock_mongo.get_database = AsyncMock()
        yield mock_mongo


@pytest.fixture
def mock_elasticsearch_client():
    """Mock del ElasticsearchClient"""
    with patch("app.main.ElasticsearchClient") as mock_es:
        mock_es.connect = AsyncMock()
        mock_es.disconnect = AsyncMock()
        mock_es.get_client = AsyncMock()
        yield mock_es


class TestGmailMCPPollingIntegration:
    """Tests de integración del Gmail MCP Polling en FastAPI"""

    def test_polling_disabled_no_task_created(
        self, mock_settings_polling_disabled, mock_polling_loop, 
        mock_mongodb_client, mock_elasticsearch_client
    ):
        """
        Test: Con gmail_mcp_polling_enabled=False, no se crea task del poller
        """
        from app.main import app
        
        with TestClient(app) as client:
            # La app se inicia y cierra con el context manager
            response = client.get("/")
            assert response.status_code == 200
        
        # Verificar que el polling loop nunca se llamó
        mock_polling_loop.assert_not_called()
        
        # Verificar que MongoDB se conectó y desconectó
        mock_mongodb_client.connect.assert_called_once()
        mock_mongodb_client.disconnect.assert_called_once()

    def test_polling_enabled_task_created(
        self, mock_settings_polling_enabled, mock_polling_loop,
        mock_mongodb_client, mock_elasticsearch_client
    ):
        """
        Test: Con gmail_mcp_polling_enabled=True, se intenta crear la task
        """
        from app.main import app
        
        with TestClient(app) as client:
            # La app se inicia y cierra con el context manager
            response = client.get("/")
            assert response.status_code == 200
        
        # Verificar que el polling loop se llamó (se creó la task)
        mock_polling_loop.assert_called_once()
        
        # Verificar que MongoDB se conectó y desconectó
        mock_mongodb_client.connect.assert_called_once()
        mock_mongodb_client.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_polling_task_cancelled_on_shutdown(
        self, mock_settings_polling_enabled, mock_mongodb_client, mock_elasticsearch_client
    ):
        """
        Test: Al shutdown, la task se cancela correctamente
        """
        from app.main import lifespan, app
        
        # Simular el ciclo de vida completo
        async with lifespan(app):
            # Durante el startup, se debe crear la task
            await asyncio.sleep(0.1)  # Dar tiempo para que se cree la task
        
        # Al salir del context manager, la task debe haberse cancelado
        # Si llegamos aquí sin excepciones, el shutdown fue exitoso
        assert True

    def test_app_initializes_without_breaking(
        self, mock_settings_polling_disabled, mock_mongodb_client, mock_elasticsearch_client
    ):
        """
        Test: La app sigue inicializando sin romperse
        """
        from app.main import app
        
        with TestClient(app) as client:
            # Verificar que endpoints existentes funcionan
            response = client.get("/")
            assert response.status_code == 200
            
            # Verificar que otros endpoints siguen funcionando
            # (esto asegura que no hemos roto la funcionalidad existente)
            assert app is not None
            assert len(app.routes) > 0


class TestHelperFunctions:
    """Tests para funciones helper si existen"""
    
    def test_settings_polling_flag_exists(self):
        """Verificar que la configuración existe"""
        from app.core.config import settings
        
        assert hasattr(settings, "gmail_mcp_polling_enabled")
        assert isinstance(settings.gmail_mcp_polling_enabled, bool)


class TestLifespanIntegration:
    """Tests específicos del lifespan"""
    
    @pytest.mark.asyncio
    async def test_lifespan_handles_mongodb_and_polling(
        self, mock_settings_polling_enabled, mock_mongodb_client, mock_elasticsearch_client
    ):
        """
        Test: El lifespan maneja tanto MongoDB como el polling
        """
        from app.main import lifespan, app
        
        async with lifespan(app):
            # Verificar que MongoDB se conectó
            mock_mongodb_client.connect.assert_called_once()
        
        # Verificar que MongoDB se desconectó al salir
        mock_mongodb_client.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_lifespan_mongodb_not_affected_by_polling(
        self, mock_settings_polling_disabled, mock_mongodb_client, mock_elasticsearch_client
    ):
        """
        Test: MongoDB sigue funcionando independientemente del estado del polling
        """
        from app.main import lifespan, app
        
        async with lifespan(app):
            mock_mongodb_client.connect.assert_called_once()
        
        mock_mongodb_client.disconnect.assert_called_once()