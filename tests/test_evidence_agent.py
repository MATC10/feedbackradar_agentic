# -*- coding: utf-8 -*-
"""
Tests para el Evidence Retrieval Agent.
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.agents import AgentState, create_initial_state, retrieve_evidence
from app.schemas.analysis import DetectedTheme, Evidence


# ============================================================================
# Tests para retrieve_evidence
# ============================================================================

@pytest.mark.asyncio
async def test_retrieve_evidence_success():
    """Test de recuperación exitosa de evidencias."""
    # Estado inicial con temas detectados
    state = create_initial_state([])
    state["detected_themes"] = [
        DetectedTheme(name="Pagos fallidos", description="Problemas con checkout"),
        DetectedTheme(name="Performance", description="Lentitud del sistema")
    ]
    
    # Mock de search_feedback
    async def mock_search(query, platform, top_k):
        if "Pagos" in query:
            return {
                "success": True,
                "results": [
                    {
                        "feedback_id": "fb_001",
                        "text": "No puedo completar el pago",
                        "score": 0.95,
                        "platform": "Web",
                        "date": "2026-05-10"
                    },
                    {
                        "feedback_id": "fb_002",
                        "text": "El checkout falla",
                        "score": 0.88,
                        "platform": "App",
                        "date": "2026-05-11"
                    }
                ]
            }
        else:  # Performance
            return {
                "success": True,
                "results": [
                    {
                        "feedback_id": "fb_003",
                        "text": "El sistema es muy lento",
                        "score": 0.92,
                        "platform": "Email",
                        "date": "2026-05-12"
                    }
                ]
            }
    
    with patch('app.agents.evidence_agent.search_feedback', new=mock_search):
        # Ejecutar agente
        result_state = await retrieve_evidence(state)
        
        # Verificar
        assert "evidence_by_theme" in result_state
        assert len(result_state["evidence_by_theme"]) == 2
        assert "Pagos fallidos" in result_state["evidence_by_theme"]
        assert "Performance" in result_state["evidence_by_theme"]
        
        # Verificar evidencias de Pagos
        pagos_evidence = result_state["evidence_by_theme"]["Pagos fallidos"]
        assert len(pagos_evidence) == 2
        assert pagos_evidence[0].feedback_id == "fb_001"
        assert pagos_evidence[0].score == 0.95
        
        # Verificar evidencias de Performance
        perf_evidence = result_state["evidence_by_theme"]["Performance"]
        assert len(perf_evidence) == 1
        assert perf_evidence[0].feedback_id == "fb_003"
        
        # Verificar que no hay errores
        assert len(result_state["errors"]) == 0


@pytest.mark.asyncio
async def test_retrieve_evidence_no_themes():
    """Test con temas detectados vacíos."""
    state = create_initial_state([])
    state["detected_themes"] = []
    
    result_state = await retrieve_evidence(state)
    
    assert result_state["evidence_by_theme"] == {}
    assert len(result_state["errors"]) == 1
    assert "No hay temas detectados" in result_state["errors"][0]


@pytest.mark.asyncio
async def test_retrieve_evidence_no_results():
    """Test cuando la búsqueda no devuelve resultados."""
    state = create_initial_state([])
    state["detected_themes"] = [
        DetectedTheme(name="Tema sin resultados", description="Test")
    ]
    
    # Mock que devuelve búsqueda exitosa pero sin resultados
    async def mock_search_empty(query, platform, top_k):
        return {
            "success": True,
            "results": []
        }
    
    with patch('app.agents.evidence_agent.search_feedback', new=mock_search_empty):
        result_state = await retrieve_evidence(state)
        
        # Verificar que se guardó lista vacía
        assert "Tema sin resultados" in result_state["evidence_by_theme"]
        assert result_state["evidence_by_theme"]["Tema sin resultados"] == []
        assert len(result_state["errors"]) == 0


@pytest.mark.asyncio
async def test_retrieve_evidence_search_fails():
    """Test cuando search_feedback falla para un tema."""
    state = create_initial_state([])
    state["detected_themes"] = [
        DetectedTheme(name="Tema exitoso", description="Test 1"),
        DetectedTheme(name="Tema fallido", description="Test 2")
    ]
    
    # Mock que falla solo para el segundo tema
    async def mock_search_partial_fail(query, platform, top_k):
        if "exitoso" in query:
            return {
                "success": True,
                "results": [
                    {
                        "feedback_id": "fb_001",
                        "text": "Test feedback",
                        "score": 0.9,
                        "platform": "Web"
                    }
                ]
            }
        else:
            return {
                "success": False,
                "error": "Error de búsqueda"
            }
    
    with patch('app.agents.evidence_agent.search_feedback', new=mock_search_partial_fail):
        result_state = await retrieve_evidence(state)
        
        # Verificar que el tema exitoso tiene evidencias
        assert "Tema exitoso" in result_state["evidence_by_theme"]
        assert len(result_state["evidence_by_theme"]["Tema exitoso"]) == 1
        
        # Verificar que el tema fallido tiene lista vacía
        assert "Tema fallido" in result_state["evidence_by_theme"]
        assert result_state["evidence_by_theme"]["Tema fallido"] == []
        
        # Verificar que se registró el error
        assert len(result_state["errors"]) > 0
        assert any("Tema fallido" in err for err in result_state["errors"])


@pytest.mark.asyncio
async def test_retrieve_evidence_exception():
    """Test cuando ocurre una excepción inesperada."""
    state = create_initial_state([])
    state["detected_themes"] = [
        DetectedTheme(name="Tema con excepción", description="Test")
    ]
    
    # Mock que lanza excepción
    async def mock_search_exception(query, platform, top_k):
        raise Exception("Error inesperado")
    
    with patch('app.agents.evidence_agent.search_feedback', new=mock_search_exception):
        result_state = await retrieve_evidence(state)
        
        # Verificar que se manejó el error
        assert "Tema con excepción" in result_state["evidence_by_theme"]
        assert result_state["evidence_by_theme"]["Tema con excepción"] == []
        assert len(result_state["errors"]) > 0


@pytest.mark.asyncio
async def test_retrieve_evidence_preserves_state():
    """Test que el agente no modifica otros campos del estado."""
    state = create_initial_state([])
    state["detected_themes"] = [
        DetectedTheme(name="Test Theme", description="Test")
    ]
    
    # Agregar datos adicionales al estado
    state["executive_summary"] = "Test summary"
    state["actions_created"] = ["action_1"]
    
    async def mock_search(query, platform, top_k):
        return {
            "success": True,
            "results": [
                {
                    "feedback_id": "fb_001",
                    "text": "Test",
                    "score": 0.9,
                    "platform": "Web"
                }
            ]
        }
    
    with patch('app.agents.evidence_agent.search_feedback', new=mock_search):
        result_state = await retrieve_evidence(state)
        
        # Verificar que no se modificaron otros campos
        assert result_state["executive_summary"] == "Test summary"
        assert result_state["actions_created"] == ["action_1"]
        assert len(result_state["detected_themes"]) == 1


# ============================================================================
# Tests para schema Evidence
# ============================================================================

def test_evidence_valid():
    """Test de creación válida de Evidence."""
    evidence = Evidence(
        feedback_id="fb_123",
        text="Test feedback",
        score=0.95,
        platform="Web",
        date="2026-05-10"
    )
    
    assert evidence.feedback_id == "fb_123"
    assert evidence.text == "Test feedback"
    assert evidence.score == 0.95
    assert evidence.platform == "Web"
    assert evidence.date == "2026-05-10"


def test_evidence_optional_fields():
    """Test de Evidence con campos opcionales."""
    evidence = Evidence(
        feedback_id="fb_123",
        text="Test",
        score=0.8
    )
    
    assert evidence.platform is None
    assert evidence.date is None


def test_evidence_score_validation():
    """Test de validación de score."""
    # Score válido
    evidence = Evidence(feedback_id="fb_1", text="Test", score=0.5)
    assert evidence.score == 0.5
    
    # Score inválido > 1
    with pytest.raises(ValueError):
        Evidence(feedback_id="fb_1", text="Test", score=1.5)
    
    # Score inválido < 0
    with pytest.raises(ValueError):
        Evidence(feedback_id="fb_1", text="Test", score=-0.1)