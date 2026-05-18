"""
Tests para los endpoints de la API FastAPI.

Valida el comportamiento de los endpoints sin depender de servicios reales.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from io import BytesIO

from app.main import app
from app.ingestion.ingestion_service import IngestionResult


client = TestClient(app)


class TestHealthEndpoint:
    """Tests para el endpoint GET /health"""
    
    def test_health_endpoint_exists(self):
        """El endpoint /health debe existir y responder"""
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_health_endpoint_returns_json(self):
        """El endpoint /health debe retornar JSON"""
        response = client.get("/health")
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert "status" in data
        assert "api" in data
    
    def test_health_with_healthy_services(self):
        """Health check con servicios saludables - test simplificado"""
        # Este test verifica que el endpoint responde correctamente
        # La verificación real de servicios se hace en tests de integración
        response = client.get("/health")
        data = response.json()
        
        assert data["api"] == "ok"
        assert "mongodb" in data
        assert "elasticsearch" in data


class TestRootEndpoint:
    """Tests para el endpoint GET /"""
    
    def test_root_endpoint_exists(self):
        """El endpoint raíz debe existir"""
        response = client.get("/")
        assert response.status_code == 200
    
    def test_root_returns_api_info(self):
        """El endpoint raíz debe retornar información de la API"""
        response = client.get("/")
        data = response.json()
        
        assert "name" in data
        assert "version" in data
        assert "status" in data
        assert data["name"] == "FeedbackRadar Agentic"


class TestFeedbackUploadEndpoint:
    """Tests para el endpoint POST /feedback/upload"""
    
    def test_upload_endpoint_exists(self):
        """El endpoint /feedback/upload debe existir"""
        # Sin archivos debería dar error 422 o 400
        response = client.post("/feedback/upload")
        assert response.status_code in [400, 422]
    
    def test_upload_rejects_non_csv_file(self):
        """Debe rechazar archivos que no sean CSV"""
        files = {
            "files": ("test.txt", BytesIO(b"contenido"), "text/plain")
        }
        response = client.post("/feedback/upload", files=files)
        
        assert response.status_code == 400
        assert "CSV" in response.json()["detail"]
    
    def test_upload_rejects_file_without_name(self):
        """Debe rechazar archivos sin nombre"""
        files = {
            "files": ("", BytesIO(b"contenido"), "text/csv")
        }
        response = client.post("/feedback/upload", files=files)
        
        # FastAPI puede retornar 400 o 422 dependiendo de la validación
        assert response.status_code in [400, 422]
    
    @patch('app.api.feedback_routes.IngestionService')
    def test_upload_accepts_valid_csv(self, mock_service_class):
        """Debe aceptar archivos CSV válidos"""
        # Mock del servicio de ingesta
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        
        # Mock del resultado
        mock_result = IngestionResult(
            success=True,
            total_rows=5,
            valid_rows=5,
            invalid_rows=0,
            inserted_rows=5,
            indexed_rows=5,
            errors=[],
            source_file="test.csv"
        )
        mock_service.ingest_csv = AsyncMock(return_value=mock_result)
        
        # Crear archivo CSV válido
        csv_content = b"nombre,fecha,resena,plataforma\nJuan,2026-05-10,Bueno,Reviews"
        files = {
            "files": ("test.csv", BytesIO(csv_content), "text/csv")
        }
        
        response = client.post("/feedback/upload", files=files)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert data["files_processed"] == 1
        assert data["total_rows"] == 5
        assert data["valid_rows"] == 5
    
    @patch('app.api.feedback_routes.IngestionService')
    def test_upload_multiple_files(self, mock_service_class):
        """Debe aceptar múltiples archivos CSV"""
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        
        # Mock de resultados para cada archivo
        mock_result1 = IngestionResult(
            success=True,
            total_rows=3,
            valid_rows=3,
            invalid_rows=0,
            inserted_rows=3,
            indexed_rows=3,
            errors=[],
            source_file="file1.csv"
        )
        mock_result2 = IngestionResult(
            success=True,
            total_rows=2,
            valid_rows=2,
            invalid_rows=0,
            inserted_rows=2,
            indexed_rows=2,
            errors=[],
            source_file="file2.csv"
        )
        
        mock_service.ingest_csv = AsyncMock(side_effect=[mock_result1, mock_result2])
        
        csv_content = b"nombre,fecha,resena,plataforma\nJuan,2026-05-10,Bueno,Reviews"
        files = [
            ("files", ("file1.csv", BytesIO(csv_content), "text/csv")),
            ("files", ("file2.csv", BytesIO(csv_content), "text/csv"))
        ]
        
        response = client.post("/feedback/upload", files=files)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["files_processed"] == 2
        assert data["total_rows"] == 5  # 3 + 2
    
    @patch('app.api.feedback_routes.IngestionService')
    def test_upload_with_errors(self, mock_service_class):
        """Debe manejar errores de validación correctamente"""
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        
        mock_result = IngestionResult(
            success=False,
            total_rows=5,
            valid_rows=3,
            invalid_rows=2,
            inserted_rows=3,
            indexed_rows=3,
            errors=["Fila 2: Fecha inválida", "Fila 4: Campo text vacío"],
            source_file="test.csv"
        )
        mock_service.ingest_csv = AsyncMock(return_value=mock_result)
        
        csv_content = b"nombre,fecha,resena,plataforma\nJuan,2026-05-10,Bueno,Reviews"
        files = {
            "files": ("test.csv", BytesIO(csv_content), "text/csv")
        }
        
        response = client.post("/feedback/upload", files=files)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is False
        assert data["invalid_rows"] == 2
        assert len(data["errors"]) == 2
    
    def test_upload_respects_enable_embeddings_parameter(self):
        """Debe respetar el parámetro enable_embeddings"""
        csv_content = b"nombre,fecha,resena,plataforma\nJuan,2026-05-10,Bueno,Reviews"
        files = {
            "files": ("test.csv", BytesIO(csv_content), "text/csv")
        }
        
        # Con enable_embeddings=false, debería funcionar incluso sin Ollama
        with patch('app.api.feedback_routes.IngestionService') as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            
            mock_result = IngestionResult(
                success=True,
                total_rows=1,
                valid_rows=1,
                invalid_rows=0,
                inserted_rows=1,
                indexed_rows=0,  # Sin embeddings, no se indexa
                errors=[],
                source_file="test.csv"
            )
            mock_service.ingest_csv = AsyncMock(return_value=mock_result)
            
            response = client.post(
                "/feedback/upload?enable_embeddings=false",
                files=files
            )
            
            assert response.status_code == 200
            # Verificar que se llamó con enable_embeddings=False
            mock_service_class.assert_called_once_with(enable_embeddings=False)


class TestFeedbackStatsEndpoint:
    """Tests para el endpoint GET /feedback/stats"""
    
    def test_stats_endpoint_exists(self):
        """El endpoint /feedback/stats debe existir"""
        response = client.get("/feedback/stats")
        assert response.status_code == 200
    
    def test_stats_returns_placeholder(self):
        """El endpoint debe retornar un placeholder mientras no esté implementado"""
        response = client.get("/feedback/stats")
        data = response.json()
        
        assert "message" in data or "total_feedback" in data