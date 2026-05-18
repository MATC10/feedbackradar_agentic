# -*- coding: utf-8 -*-
"""
Tests para el Theme Discovery Agent.
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.agents import AgentState, create_initial_state, discover_themes
from app.schemas.analysis import DetectedTheme, ThemeDiscoveryResponse


# ============================================================================
# Tests para create_initial_state
# ============================================================================

def test_create_initial_state_with_feedback():
    """Test de creación de estado inicial con feedback."""
    feedback = [
        {"text": "El sistema es lento", "platform": "Email"},
        {"text": "No puedo completar el pago", "platform": "Web"}
    ]
    
    state = create_initial_state(feedback)
    
    assert state["feedback_items"] == feedback
    assert state["detected_themes"] == []
    assert state["evidence_by_theme"] == {}
    assert state["prioritized_themes"] == []
    assert state["recommendations"] == []
    assert state["actions_created"] == []
    assert state["executive_summary"] == {}
    assert state["errors"] == []


def test_create_initial_state_empty():
    """Test de creación de estado con feedback vacío."""
    state = create_initial_state([])
    
    assert state["feedback_items"] == []
    assert state["detected_themes"] == []


# ============================================================================
# Tests para discover_themes
# ============================================================================

@pytest.mark.asyncio
async def test_discover_themes_success():
    """Test de descubrimiento exitoso de temas."""
    # Estado inicial
    feedback = [
        {"text": "El proceso de pago falla constantemente", "platform": "Email"},
        {"text": "No puedo completar mi compra", "platform": "Web"},
        {"text": "El sistema es muy lento", "platform": "App"}
    ]
    state = create_initial_state(feedback)
    
    # Mock del LLM
    mock_themes = ThemeDiscoveryResponse(
        themes=[
            DetectedTheme(name="Pagos fallidos", description="Problemas con checkout"),
            DetectedTheme(name="Performance", description="Lentitud del sistema")
        ]
    )
    
    with patch('app.agents.theme_agent.generate_structured_response', new=AsyncMock(return_value=mock_themes)):
        # Ejecutar agente
        result_state = await discover_themes(state)
        
        # Verificar
        assert len(result_state["detected_themes"]) == 2
        assert result_state["detected_themes"][0].name == "Pagos fallidos"
        assert result_state["detected_themes"][1].name == "Performance"
        assert len(result_state["errors"]) == 0


@pytest.mark.asyncio
async def test_discover_themes_empty_feedback():
    """Test con feedback vacío."""
    state = create_initial_state([])
    
    result_state = await discover_themes(state)
    
    assert result_state["detected_themes"] == []
    assert len(result_state["errors"]) == 1
    assert "No hay feedback disponible" in result_state["errors"][0]


@pytest.mark.asyncio
async def test_discover_themes_llm_error():
    """Test cuando el LLM falla."""
    feedback = [{"text": "Test feedback", "platform": "Web"}]
    state = create_initial_state(feedback)
    
    # Mock que lanza excepción
    with patch('app.agents.theme_agent.generate_structured_response', new=AsyncMock(side_effect=Exception("LLM Error"))):
        result_state = await discover_themes(state)
        
        # Verificar
        assert result_state["detected_themes"] == []
        assert len(result_state["errors"]) == 1
        assert "Error inesperado" in result_state["errors"][0]


@pytest.mark.asyncio
async def test_discover_themes_preserves_other_state():
    """Test que el agente no modifica otros campos del estado."""
    feedback = [{"text": "Test", "platform": "Web"}]
    state = create_initial_state(feedback)
    
    # Agregar datos adicionales al estado
    state["executive_summary"] = "Test summary"
    state["actions_created"] = ["action_1"]
    
    mock_themes = ThemeDiscoveryResponse(
        themes=[DetectedTheme(name="Test Theme", description="Test description")]
    )
    
    with patch('app.agents.theme_agent.generate_structured_response', new=AsyncMock(return_value=mock_themes)):
        result_state = await discover_themes(state)
        
        # Verificar que no se modificaron otros campos
        assert result_state["executive_summary"] == "Test summary"
        assert result_state["actions_created"] == ["action_1"]
        assert len(result_state["detected_themes"]) == 1


# ============================================================================
# Tests para schemas
# ============================================================================

def test_detected_theme_valid():
    """Test de creación válida de DetectedTheme."""
    theme = DetectedTheme(
        name="Pagos",
        description="Problemas con pagos"
    )
    
    assert theme.name == "Pagos"
    assert theme.description == "Problemas con pagos"


def test_detected_theme_strips_whitespace():
    """Test que DetectedTheme hace strip de espacios."""
    theme = DetectedTheme(
        name="  Pagos  ",
        description="  Descripción  "
    )
    
    assert theme.name == "Pagos"
    assert theme.description == "Descripción"


def test_detected_theme_empty_name_fails():
    """Test que DetectedTheme rechaza nombre vacío."""
    with pytest.raises(ValueError):
        DetectedTheme(name="", description="Test")


def test_detected_theme_empty_description_fails():
    """Test que DetectedTheme rechaza descripción vacía."""
    with pytest.raises(ValueError):
        DetectedTheme(name="Test", description="")


def test_theme_discovery_response_valid():
    """Test de ThemeDiscoveryResponse válida."""
    response = ThemeDiscoveryResponse(
        themes=[
            DetectedTheme(name="Theme 1", description="Desc 1"),
            DetectedTheme(name="Theme 2", description="Desc 2")
        ]
    )
    
    assert len(response.themes) == 2


def test_theme_discovery_response_empty():
    """Test de ThemeDiscoveryResponse vacía."""
    response = ThemeDiscoveryResponse(themes=[])
    
    assert response.themes == []


def test_theme_discovery_response_too_many_themes():
    """Test que ThemeDiscoveryResponse rechaza más de 10 temas."""
    themes = [DetectedTheme(name=f"Theme {i}", description=f"Desc {i}") for i in range(11)]
    
    with pytest.raises(ValueError, match="No se pueden detectar más de 10 temas"):
        ThemeDiscoveryResponse(themes=themes)