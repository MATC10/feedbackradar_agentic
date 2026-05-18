# -*- coding: utf-8 -*-
"""
Tests para el Prioritization Agent.

Este módulo contiene tests para verificar:
1. Priorización exitosa de uno o varios temas
2. Uso correcto de get_feedback_stats
3. Integración con respuesta estructurada del LLM mockeada
4. Manejo de fallo parcial de get_feedback_stats
5. Manejo de fallo del LLM sin romper el workflow
6. Preservación del estado previo
7. Validación de la salida prioritized_themes
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.agents import AgentState, create_initial_state, prioritize_themes
from app.schemas.analysis import DetectedTheme, Evidence, PrioritizedTheme


@pytest.fixture
def sample_state_with_themes():
    """Estado de ejemplo con temas y evidencias."""
    state = create_initial_state([])
    state["detected_themes"] = [
        DetectedTheme(name="Pagos fallidos", description="Problemas con checkout"),
        DetectedTheme(name="Performance", description="Lentitud del sistema"),
        DetectedTheme(name="Usabilidad", description="Interfaz confusa")
    ]
    state["evidence_by_theme"] = {
        "Pagos fallidos": [
            Evidence(feedback_id="fb_001", text="No puedo pagar", score=0.95, platform="Web"),
            Evidence(feedback_id="fb_002", text="Checkout falla", score=0.88, platform="App")
        ],
        "Performance": [
            Evidence(feedback_id="fb_003", text="Sistema lento", score=0.92, platform="Email")
        ],
        "Usabilidad": [
            Evidence(feedback_id="fb_004", text="Interfaz confusa", score=0.85, platform="Web")
        ]
    }
    return state


# ============================================================================
# Test 1: Priorización exitosa de varios temas
# ============================================================================

@pytest.mark.asyncio
async def test_prioritization_successful(sample_state_with_themes):
    """Test 1: Priorización exitosa de varios temas."""
    
    # Mock de get_feedback_stats
    async def mock_get_stats(theme):
        stats_map = {
            "Pagos fallidos": {
                "success": True,
                "theme": "Pagos fallidos",
                "total_feedback": 100,
                "related_count": 45
            },
            "Performance": {
                "success": True,
                "theme": "Performance",
                "total_feedback": 100,
                "related_count": 30
            },
            "Usabilidad": {
                "success": True,
                "theme": "Usabilidad",
                "total_feedback": 100,
                "related_count": 25
            }
        }
        return stats_map.get(theme, {"success": False, "error": "Not found"})
    
    # Mock del LLM que devuelve respuestas estructuradas
    async def mock_generate_structured(llm_client, prompt, response_model):
        if "Pagos fallidos" in prompt:
            return response_model(priority="Crítica", reasoning="Alto volumen (45) y bloquea conversión")
        elif "Performance" in prompt:
            return response_model(priority="Alta", reasoning="Impacta experiencia de usuario (30 menciones)")
        else:  # Usabilidad
            return response_model(priority="Media", reasoning="Afecta UX pero tiene workarounds (25 menciones)")
    
    with patch('app.agents.prioritization_agent.get_feedback_stats', new=mock_get_stats):
        with patch('app.agents.prioritization_agent.generate_structured_response', new=mock_generate_structured):
            result = await prioritize_themes(sample_state_with_themes)
    
    # Verificaciones
    assert "prioritized_themes" in result
    assert len(result["prioritized_themes"]) == 3
    
    # Verificar que todos los temas fueron priorizados
    theme_names = [pt.name for pt in result["prioritized_themes"]]
    assert "Pagos fallidos" in theme_names
    assert "Performance" in theme_names
    assert "Usabilidad" in theme_names
    
    # Verificar estructura de cada tema priorizado
    for pt in result["prioritized_themes"]:
        assert pt.name is not None
        assert pt.priority in ["Crítica", "Alta", "Media", "Baja"]
        assert len(pt.reasoning) >= 10
        assert pt.evidence_count >= 0


# ============================================================================
# Test 2: Uso correcto de get_feedback_stats
# ============================================================================

@pytest.mark.asyncio
async def test_prioritization_uses_get_feedback_stats(sample_state_with_themes):
    """Test 2: Verificar que se usa get_feedback_stats correctamente."""
    
    call_count = {"count": 0}
    
    async def mock_get_stats(theme):
        call_count["count"] += 1
        return {
            "success": True,
            "theme": theme,
            "total_feedback": 100,
            "related_count": 20
        }
    
    async def mock_generate_structured(llm_client, prompt, response_model):
        return response_model(priority="Media", reasoning="Test reasoning con datos reales")
    
    with patch('app.agents.prioritization_agent.get_feedback_stats', new=mock_get_stats):
        with patch('app.agents.prioritization_agent.generate_structured_response', new=mock_generate_structured):
            result = await prioritize_themes(sample_state_with_themes)
    
    # Verificar que se llamó a get_feedback_stats para cada tema
    assert call_count["count"] == 3
    assert "prioritized_themes" in result
    assert len(result["prioritized_themes"]) == 3


# ============================================================================
# Test 3: Integración con respuesta estructurada del LLM
# ============================================================================

@pytest.mark.asyncio
async def test_prioritization_with_llm_structured_response(sample_state_with_themes):
    """Test 3: Integración con respuesta estructurada del LLM mockeada."""
    
    async def mock_get_stats(theme):
        return {
            "success": True,
            "theme": theme,
            "total_feedback": 50,
            "related_count": 15
        }
    
    # Mock que verifica que el LLM recibe el prompt correcto
    prompts_received = []
    
    async def mock_generate_structured(llm_client, prompt, response_model):
        prompts_received.append(prompt)
        # Verificar que el prompt contiene información clave
        assert "TEMA A PRIORIZAR:" in prompt
        assert "ESTADÍSTICAS:" in prompt
        assert "EVIDENCIAS REALES" in prompt
        
        return response_model(
            priority="Alta",
            reasoning="Análisis basado en evidencias y estadísticas proporcionadas"
        )
    
    with patch('app.agents.prioritization_agent.get_feedback_stats', new=mock_get_stats):
        with patch('app.agents.prioritization_agent.generate_structured_response', new=mock_generate_structured):
            result = await prioritize_themes(sample_state_with_themes)
    
    # Verificar que se generaron prompts para todos los temas
    assert len(prompts_received) == 3
    
    # Verificar que las respuestas estructuradas se usaron
    for pt in result["prioritized_themes"]:
        assert pt.priority == "Alta"
        assert "evidencias" in pt.reasoning.lower() or "estadísticas" in pt.reasoning.lower()


# ============================================================================
# Test 4: Manejo de fallo parcial de get_feedback_stats
# ============================================================================

@pytest.mark.asyncio
async def test_prioritization_handles_partial_stats_failure(sample_state_with_themes):
    """Test 4: Manejo de fallo parcial de get_feedback_stats."""
    
    async def mock_get_stats_partial_fail(theme):
        if theme == "Pagos fallidos":
            return {
                "success": True,
                "theme": theme,
                "total_feedback": 100,
                "related_count": 40
            }
        else:
            # Falla para Performance y Usabilidad
            return {
                "success": False,
                "theme": theme,
                "error": "Error obteniendo estadísticas"
            }
    
    async def mock_generate_structured(llm_client, prompt, response_model):
        # El LLM debe poder priorizar incluso sin estadísticas
        return response_model(
            priority="Media",
            reasoning="Priorización basada en evidencias disponibles, sin estadísticas completas"
        )
    
    with patch('app.agents.prioritization_agent.get_feedback_stats', new=mock_get_stats_partial_fail):
        with patch('app.agents.prioritization_agent.generate_structured_response', new=mock_generate_structured):
            result = await prioritize_themes(sample_state_with_themes)
    
    # Debe completarse sin errores aunque falten algunas estadísticas
    assert "prioritized_themes" in result
    assert len(result["prioritized_themes"]) == 3
    
    # Todos los temas deben tener priorización
    for pt in result["prioritized_themes"]:
        assert pt.priority is not None
        assert len(pt.reasoning) > 0


# ============================================================================
# Test 5: Manejo de fallo del LLM sin romper el workflow
# ============================================================================

@pytest.mark.asyncio
async def test_prioritization_handles_llm_failure_gracefully(sample_state_with_themes):
    """Test 5: Manejo de fallo del LLM sin romper el workflow."""
    
    async def mock_get_stats(theme):
        return {
            "success": True,
            "theme": theme,
            "total_feedback": 100,
            "related_count": 30
        }
    
    call_count = {"count": 0}
    
    async def mock_generate_structured_with_failure(llm_client, prompt, response_model):
        call_count["count"] += 1
        # Falla solo para el segundo tema
        if call_count["count"] == 2:
            raise Exception("LLM connection error")
        return response_model(priority="Media", reasoning="Test reasoning")
    
    with patch('app.agents.prioritization_agent.get_feedback_stats', new=mock_get_stats):
        with patch('app.agents.prioritization_agent.generate_structured_response', new=mock_generate_structured_with_failure):
            result = await prioritize_themes(sample_state_with_themes)
    
    # El workflow debe continuar a pesar del fallo
    assert "prioritized_themes" in result
    # Solo 2 temas deben estar priorizados (el que falló se omite)
    assert len(result["prioritized_themes"]) == 2
    
    # Debe haber registrado el error
    assert len(result["errors"]) > 0
    assert any("Error" in err for err in result["errors"])


# ============================================================================
# Test 6: Preservación del estado previo
# ============================================================================

@pytest.mark.asyncio
async def test_prioritization_preserves_previous_state(sample_state_with_themes):
    """Test 6: Preservación del estado previo."""
    
    # Agregar datos adicionales al estado
    sample_state_with_themes["executive_summary"] = "Test summary"
    sample_state_with_themes["actions_created"] = ["action_1"]
    original_themes = sample_state_with_themes["detected_themes"].copy()
    
    async def mock_get_stats(theme):
        return {
            "success": True,
            "theme": theme,
            "total_feedback": 100,
            "related_count": 20
        }
    
    async def mock_generate_structured(llm_client, prompt, response_model):
        return response_model(priority="Media", reasoning="Test reasoning")
    
    with patch('app.agents.prioritization_agent.get_feedback_stats', new=mock_get_stats):
        with patch('app.agents.prioritization_agent.generate_structured_response', new=mock_generate_structured):
            result = await prioritize_themes(sample_state_with_themes)
    
    # Verificar que se agregó prioritized_themes
    assert "prioritized_themes" in result
    assert len(result["prioritized_themes"]) == 3
    
    # Verificar que se preservó el estado previo
    assert result["executive_summary"] == "Test summary"
    assert result["actions_created"] == ["action_1"]
    assert result["detected_themes"] == original_themes


# ============================================================================
# Test 7: Validación de la salida prioritized_themes
# ============================================================================

@pytest.mark.asyncio
async def test_prioritization_output_validation(sample_state_with_themes):
    """Test 7: Validación de la salida prioritized_themes."""
    
    async def mock_get_stats(theme):
        return {
            "success": True,
            "theme": theme,
            "total_feedback": 100,
            "related_count": 35
        }
    
    async def mock_generate_structured(llm_client, prompt, response_model):
        if "Pagos" in prompt:
            return response_model(priority="Crítica", reasoning="Problema bloqueante crítico para usuarios")
        elif "Performance" in prompt:
            return response_model(priority="Alta", reasoning="Impacto significativo en experiencia de usuario")
        else:
            return response_model(priority="Baja", reasoning="Problema menor con workarounds disponibles")
    
    with patch('app.agents.prioritization_agent.get_feedback_stats', new=mock_get_stats):
        with patch('app.agents.prioritization_agent.generate_structured_response', new=mock_generate_structured):
            result = await prioritize_themes(sample_state_with_themes)
    
    # Validar estructura de prioritized_themes
    assert isinstance(result["prioritized_themes"], list)
    
    for pt in result["prioritized_themes"]:
        # Verificar que es instancia de PrioritizedTheme
        assert isinstance(pt, PrioritizedTheme)
        
        # Verificar campos requeridos
        assert hasattr(pt, 'name')
        assert hasattr(pt, 'priority')
        assert hasattr(pt, 'reasoning')
        assert hasattr(pt, 'evidence_count')
        
        # Verificar tipos
        assert isinstance(pt.name, str)
        assert isinstance(pt.priority, str)
        assert isinstance(pt.reasoning, str)
        assert isinstance(pt.evidence_count, int)
        
        # Verificar valores válidos
        assert pt.name in ["Pagos fallidos", "Performance", "Usabilidad"]
        assert pt.priority in ["Crítica", "Alta", "Media", "Baja"]
        assert len(pt.reasoning) >= 10
        assert pt.evidence_count >= 0


# ============================================================================
# Test adicional: Estado sin temas detectados
# ============================================================================

@pytest.mark.asyncio
async def test_prioritization_no_themes():
    """Test con estado sin temas detectados."""
    state = create_initial_state([])
    state["detected_themes"] = []
    
    result = await prioritize_themes(state)
    
    # Debe manejar el caso sin romper
    assert "prioritized_themes" in result
    assert result["prioritized_themes"] == []
    assert len(result["errors"]) == 1
    assert "No hay temas detectados" in result["errors"][0]
