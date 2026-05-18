"""
Tests para las herramientas MCP de FeedbackRadar.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from app.mcp.tools import (
    search_feedback,
    get_feedback_stats,
    get_recent_feedback,
    save_insight,
    create_action_item
)


@pytest.mark.asyncio
async def test_search_feedback():
    """Test de búsqueda semántica de feedback."""
    with patch('app.mcp.tools.OllamaEmbeddingService') as mock_embedding, \
         patch('app.mcp.tools.ElasticsearchClient') as mock_es:
        
        # Mock del servicio de embeddings
        mock_embedding_instance = MagicMock()
        mock_embedding_instance.embed_text.return_value = [0.1] * 768
        mock_embedding.return_value = mock_embedding_instance
        
        # Mock de Elasticsearch
        mock_es.semantic_search = AsyncMock(return_value=[
            {"feedback_id": "fb1", "text": "El sistema es lento", "score": 0.95},
            {"feedback_id": "fb2", "text": "Problemas de velocidad", "score": 0.88}
        ])
        
        # Ejecutar búsqueda
        result = await search_feedback(query="sistema lento", top_k=5)
        
        # Verificar resultado
        assert result["success"] is True
        assert result["query"] == "sistema lento"
        assert result["results_count"] == 2
        assert len(result["results"]) == 2
        assert result["results"][0]["score"] == 0.95


@pytest.mark.asyncio
async def test_get_feedback_stats():
    """Test de estadísticas de feedback por tema."""
    with patch('app.mcp.tools.FeedbackRepository') as mock_repo, \
         patch('app.mcp.tools.OllamaEmbeddingService') as mock_embedding, \
         patch('app.mcp.tools.ElasticsearchClient') as mock_es:
        
        # Mock del repositorio
        mock_repo.count_all = AsyncMock(return_value=150)
        
        # Mock del servicio de embeddings
        mock_embedding_instance = MagicMock()
        mock_embedding_instance.embed_text.return_value = [0.1] * 768
        mock_embedding.return_value = mock_embedding_instance
        
        # Mock de Elasticsearch
        mock_es.semantic_search = AsyncMock(return_value=[
            {"feedback_id": f"fb{i}"} for i in range(25)
        ])
        
        # Ejecutar estadísticas
        result = await get_feedback_stats(theme="pagos")
        
        # Verificar resultado
        assert result["success"] is True
        assert result["theme"] == "pagos"
        assert result["total_feedback"] == 150
        assert result["related_count"] == 25


@pytest.mark.asyncio
async def test_get_recent_feedback():
    """Test de obtención de feedback reciente."""
    with patch('app.mcp.tools.FeedbackRepository') as mock_repo:
        
        # Mock del repositorio
        mock_repo.find_recent = AsyncMock(return_value=[
            {"feedback_id": "fb1", "text": "Feedback 1", "created_at": datetime.utcnow()},
            {"feedback_id": "fb2", "text": "Feedback 2", "created_at": datetime.utcnow()},
            {"feedback_id": "fb3", "text": "Feedback 3", "created_at": datetime.utcnow()}
        ])
        
        # Ejecutar obtención
        result = await get_recent_feedback(days=7)
        
        # Verificar resultado
        assert result["success"] is True
        assert result["days"] == 7
        assert result["count"] == 3
        assert len(result["feedbacks"]) == 3


@pytest.mark.asyncio
async def test_save_insight():
    """Test de guardado de insight."""
    with patch('app.mcp.tools.InsightRepository') as mock_repo:
        
        # Mock del repositorio que retorna el ID directamente
        mock_repo.insert_one = AsyncMock(return_value="insight_abc123")
        
        # Mock de InsightInDB para evitar validación
        with patch('app.mcp.tools.InsightInDB') as mock_insight_class:
            mock_insight_instance = MagicMock()
            mock_insight_class.return_value = mock_insight_instance
            
            # Ejecutar guardado
            result = await save_insight(
                theme="Pagos",
                summary="Problemas con checkout",
                priority="Alta",
                reasoning="Múltiples reportes de errores"
            )
            
            # Verificar resultado
            assert result["success"] is True
            assert result["insight_id"] == "insight_abc123"
            assert result["theme"] == "Pagos"
            assert result["priority"] == "Alta"


@pytest.mark.asyncio
async def test_create_action_item():
    """Test de creación de acción."""
    with patch('app.mcp.tools.ActionRepository') as mock_repo:
        
        # Mock del repositorio que retorna el ID directamente
        mock_repo.insert_one = AsyncMock(return_value="action_xyz789")
        
        # Mock de ActionItemInDB para evitar validación
        with patch('app.mcp.tools.ActionItemInDB') as mock_action_class:
            mock_action_instance = MagicMock()
            mock_action_class.return_value = mock_action_instance
            
            # Ejecutar creación
            result = await create_action_item(
                title="Optimizar proceso de pago",
                description="Implementar caché y optimizar queries",
                priority="Alta"
            )
            
            # Verificar resultado
            assert result["success"] is True
            assert result["action_id"] == "action_xyz789"
            assert result["title"] == "Optimizar proceso de pago"
            assert result["priority"] == "Alta"
            assert result["status"] == "Pendiente"
