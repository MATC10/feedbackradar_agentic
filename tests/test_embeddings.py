"""
Tests para el servicio de embeddings con Ollama.

Usa mocks para no depender del servicio real de Ollama.
"""

import pytest
from unittest.mock import patch, MagicMock
import httpx

from app.embeddings.ollama_embeddings import (
    OllamaEmbeddingService,
    OllamaEmbeddingError
)


class TestOllamaEmbeddingService:
    """Tests para OllamaEmbeddingService"""
    
    def test_service_initialization(self):
        """El servicio debe inicializarse correctamente"""
        service = OllamaEmbeddingService()
        
        assert service.base_url is not None
        assert service.model is not None
        assert service.timeout == 30.0
    
    @patch('app.embeddings.ollama_embeddings.httpx.Client')
    def test_embed_text_success(self, mock_client_class):
        """Debe generar embeddings correctamente con respuesta válida"""
        # Mock de la respuesta HTTP
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "embedding": [0.1, 0.2, 0.3, 0.4, 0.5]
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        service = OllamaEmbeddingService()
        result = service.embed_text("texto de prueba")
        
        assert isinstance(result, list)
        assert len(result) == 5
        assert all(isinstance(x, (int, float)) for x in result)
    
    def test_embed_text_empty_string(self):
        """Debe rechazar texto vacío"""
        service = OllamaEmbeddingService()
        
        with pytest.raises(ValueError, match="vacío"):
            service.embed_text("")
        
        with pytest.raises(ValueError, match="vacío"):
            service.embed_text("   ")
    
    @patch('app.embeddings.ollama_embeddings.httpx.Client')
    def test_embed_text_missing_embedding_field(self, mock_client_class):
        """Debe fallar si la respuesta no contiene el campo 'embedding'"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": "algo salió mal"}
        mock_response.raise_for_status = MagicMock()
        
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        service = OllamaEmbeddingService()
        
        with pytest.raises(OllamaEmbeddingError, match="embedding"):
            service.embed_text("texto")
    
    @patch('app.embeddings.ollama_embeddings.httpx.Client')
    def test_embed_text_empty_embedding(self, mock_client_class):
        """Debe fallar si el embedding está vacío"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"embedding": []}
        mock_response.raise_for_status = MagicMock()
        
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        service = OllamaEmbeddingService()
        
        with pytest.raises(OllamaEmbeddingError, match="vacía"):
            service.embed_text("texto")
    
    @patch('app.embeddings.ollama_embeddings.httpx.Client')
    def test_embed_text_invalid_embedding_type(self, mock_client_class):
        """Debe fallar si el embedding no es una lista"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"embedding": "not a list"}
        mock_response.raise_for_status = MagicMock()
        
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        service = OllamaEmbeddingService()
        
        with pytest.raises(OllamaEmbeddingError, match="lista"):
            service.embed_text("texto")
    
    @patch('app.embeddings.ollama_embeddings.httpx.Client')
    def test_embed_text_non_numeric_values(self, mock_client_class):
        """Debe fallar si el embedding contiene valores no numéricos"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"embedding": [0.1, "text", 0.3]}
        mock_response.raise_for_status = MagicMock()
        
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        service = OllamaEmbeddingService()
        
        with pytest.raises(OllamaEmbeddingError, match="numéricos"):
            service.embed_text("texto")
    
    @patch('app.embeddings.ollama_embeddings.httpx.Client')
    def test_embed_text_connection_error(self, mock_client_class):
        """Debe manejar errores de conexión"""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")
        mock_client_class.return_value = mock_client
        
        service = OllamaEmbeddingService()
        
        with pytest.raises(OllamaEmbeddingError, match="conectar"):
            service.embed_text("texto")
    
    @patch('app.embeddings.ollama_embeddings.httpx.Client')
    def test_embed_text_timeout(self, mock_client_class):
        """Debe manejar timeouts"""
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.side_effect = httpx.TimeoutException("Timeout")
        mock_client_class.return_value = mock_client
        
        service = OllamaEmbeddingService()
        
        with pytest.raises(OllamaEmbeddingError, match="Timeout"):
            service.embed_text("texto")
    
    @patch('app.embeddings.ollama_embeddings.httpx.Client')
    def test_embed_batch_success(self, mock_client_class):
        """Debe generar embeddings en batch correctamente"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "embedding": [0.1, 0.2, 0.3]
        }
        mock_response.raise_for_status = MagicMock()
        
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        service = OllamaEmbeddingService()
        results = service.embed_batch(["texto1", "texto2"])
        
        assert len(results) == 2
        assert all(isinstance(r, list) for r in results)
        assert all(len(r) == 3 for r in results)
    
    def test_embed_batch_empty_list(self):
        """Debe retornar lista vacía si se pasa lista vacía"""
        service = OllamaEmbeddingService()
        results = service.embed_batch([])
        
        assert results == []