# -*- coding: utf-8 -*-
"""
Tests para el Persistence Agent.

Este módulo contiene tests para verificar:
1. Persistencia exitosa de insights y acciones
2. Uso correcto de save_insight
3. Uso correcto de create_action_item
4. Manejo de fallo de save_insight
5. Manejo de fallo de create_action_item
6. Caso sin temas priorizados
7. Caso sin recomendaciones
8. Actualización correcta de state["actions_created"]
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.agents import AgentState, create_initial_state, persist_results
from app.schemas.analysis import PrioritizedTheme, Recommendation


@pytest.fixture
def sample_state_with_results():
    """Estado de ejemplo con temas priorizados y recomendaciones."""
    state = create_initial_state([])
    state["prioritized_themes"] = [
        PrioritizedTheme(
            name="Pagos fallidos",
            description="Problemas con checkout",
            priority="Crítica",
            evidence_count=3,
            reasoning="Alto volumen y bloquea conversión"
        ),
        PrioritizedTheme(
            name="Performance",
            description="Lentitud del sistema",
            priority="Alta",
            evidence_count=2,
            reasoning="Impacta experiencia de usuario"
        )
    ]
    state["recommendations"] = [
        Recommendation(
            title="Investigar fallos en checkout móvil",
            description="Revisar logs y errores de pago",
            priority="Crítica",
            related_themes=["Pagos fallidos"],
            expected_impact="Reducir abandono de carrito"
        ),
        Recommendation(
            title="Optimizar rendimiento del sistema",
            description="Implementar caché y optimizar queries",
            priority="Alta",
            related_themes=["Performance"],
            expected_impact="Mejorar experiencia de usuario"
        )
    ]
    return state


# ============================================================================
# Test 1: Persistencia exitosa de insights y acciones
# ============================================================================

@pytest.mark.asyncio
async def test_persist_results_successful(sample_state_with_results):
    """Test 1: Persistencia exitosa de insights y acciones."""
    
    # Mock de save_insight
    async def mock_save_insight(theme, summary, priority, reasoning):
        return {
            "success": True,
            "insight_id": f"insight_{theme.lower().replace(' ', '_')}",
            "theme": theme,
            "priority": priority
        }
    
    # Mock de create_action_item
    async def mock_create_action(title, description, priority):
        return {
            "success": True,
            "action_id": f"action_{title.lower().replace(' ', '_')[:20]}",
            "title": title,
            "priority": priority,
            "status": "Pendiente"
        }
    
    with patch('app.agents.persistence_agent.save_insight', new=mock_save_insight):
        with patch('app.agents.persistence_agent.create_action_item', new=mock_create_action):
            result = await persist_results(sample_state_with_results)
    
    # Verificaciones
    assert "actions_created" in result
    assert len(result["actions_created"]) == 2

    # Verificar que se crearon IDs
    assert all(isinstance(action_id, str) for action_id in result["actions_created"])
    assert all(action_id.startswith("action_") for action_id in result["actions_created"])

    # Verificar insights_created
    assert "insights_created" in result
    assert len(result["insights_created"]) == 2


# ============================================================================
# Test 2: Uso correcto de save_insight
# ============================================================================

@pytest.mark.asyncio
async def test_persist_results_uses_save_insight(sample_state_with_results):
    """Test 2: Verificar que se usa save_insight correctamente."""
    
    save_insight_calls = []
    
    async def mock_save_insight(theme, summary, priority, reasoning):
        save_insight_calls.append({
            "theme": theme,
            "summary": summary,
            "priority": priority,
            "reasoning": reasoning
        })
        return {
            "success": True,
            "insight_id": f"insight_{len(save_insight_calls)}",
            "theme": theme,
            "priority": priority
        }
    
    async def mock_create_action(title, description, priority):
        return {
            "success": True,
            "action_id": f"action_{len(save_insight_calls)}",
            "title": title,
            "priority": priority,
            "status": "Pendiente"
        }
    
    with patch('app.agents.persistence_agent.save_insight', new=mock_save_insight):
        with patch('app.agents.persistence_agent.create_action_item', new=mock_create_action):
            result = await persist_results(sample_state_with_results)
    
    # Verificar que se llamó a save_insight para cada tema
    assert len(save_insight_calls) == 2
    
    # Verificar parámetros del primer tema
    first_call = save_insight_calls[0]
    assert first_call["theme"] == "Pagos fallidos"
    assert first_call["priority"] == "Crítica"
    assert "Alto volumen y bloquea conversión" in first_call["reasoning"]
    
    # Verificar parámetros del segundo tema
    second_call = save_insight_calls[1]
    assert second_call["theme"] == "Performance"
    assert second_call["priority"] == "Alta"


# ============================================================================
# Test 3: Uso correcto de create_action_item
# ============================================================================

@pytest.mark.asyncio
async def test_persist_results_uses_create_action_item(sample_state_with_results):
    """Test 3: Verificar que se usa create_action_item correctamente."""
    
    create_action_calls = []
    
    async def mock_save_insight(theme, summary, priority, reasoning):
        return {
            "success": True,
            "insight_id": f"insight_{theme}",
            "theme": theme,
            "priority": priority
        }
    
    async def mock_create_action(title, description, priority):
        create_action_calls.append({
            "title": title,
            "description": description,
            "priority": priority
        })
        return {
            "success": True,
            "action_id": f"action_{len(create_action_calls)}",
            "title": title,
            "priority": priority,
            "status": "Pendiente"
        }
    
    with patch('app.agents.persistence_agent.save_insight', new=mock_save_insight):
        with patch('app.agents.persistence_agent.create_action_item', new=mock_create_action):
            result = await persist_results(sample_state_with_results)
    
    # Verificar que se llamó a create_action_item para cada recomendación
    assert len(create_action_calls) == 2
    
    # Verificar parámetros de la primera acción
    first_call = create_action_calls[0]
    assert first_call["title"] == "Investigar fallos en checkout móvil"
    assert first_call["priority"] == "Crítica"
    assert "logs" in first_call["description"].lower() or "pago" in first_call["description"].lower()
    
    # Verificar parámetros de la segunda acción
    second_call = create_action_calls[1]
    assert second_call["title"] == "Optimizar rendimiento del sistema"
    assert second_call["priority"] == "Alta"


# ============================================================================
# Test 4: Manejo de fallo de save_insight
# ============================================================================

@pytest.mark.asyncio
async def test_persist_results_handles_save_insight_failure(sample_state_with_results):
    """Test 4: Manejo de fallo de save_insight."""
    
    call_count = {"count": 0}
    
    async def mock_save_insight_with_failure(theme, summary, priority, reasoning):
        call_count["count"] += 1
        # Falla solo para el primer tema
        if call_count["count"] == 1:
            return {
                "success": False,
                "insight_id": None,
                "theme": theme,
                "error": "Database connection error"
            }
        return {
            "success": True,
            "insight_id": f"insight_{theme}",
            "theme": theme,
            "priority": priority
        }
    
    async def mock_create_action(title, description, priority):
        return {
            "success": True,
            "action_id": f"action_{title[:10]}",
            "title": title,
            "priority": priority,
            "status": "Pendiente"
        }
    
    with patch('app.agents.persistence_agent.save_insight', new=mock_save_insight_with_failure):
        with patch('app.agents.persistence_agent.create_action_item', new=mock_create_action):
            result = await persist_results(sample_state_with_results)
    
    # El workflow debe continuar a pesar del fallo
    assert "actions_created" in result
    assert "insights_created" in result

    # Solo 1 insight debe haberse guardado (el que no falló)
    assert len(result["insights_created"]) == 1

    # Pero ambas acciones deben haberse creado
    assert len(result["actions_created"]) == 2

    # Debe haber registrado el error
    assert len(result["errors"]) > 0
    assert any("Error" in err for err in result["errors"])


# ============================================================================
# Test 5: Manejo de fallo de create_action_item
# ============================================================================

@pytest.mark.asyncio
async def test_persist_results_handles_create_action_failure(sample_state_with_results):
    """Test 5: Manejo de fallo de create_action_item."""
    
    call_count = {"count": 0}
    
    async def mock_save_insight(theme, summary, priority, reasoning):
        return {
            "success": True,
            "insight_id": f"insight_{theme}",
            "theme": theme,
            "priority": priority
        }
    
    async def mock_create_action_with_failure(title, description, priority):
        call_count["count"] += 1
        # Falla solo para la primera acción
        if call_count["count"] == 1:
            return {
                "success": False,
                "action_id": None,
                "title": title,
                "error": "Validation error"
            }
        return {
            "success": True,
            "action_id": f"action_{call_count['count']}",
            "title": title,
            "priority": priority,
            "status": "Pendiente"
        }
    
    with patch('app.agents.persistence_agent.save_insight', new=mock_save_insight):
        with patch('app.agents.persistence_agent.create_action_item', new=mock_create_action_with_failure):
            result = await persist_results(sample_state_with_results)
    
    # El workflow debe continuar a pesar del fallo
    assert "actions_created" in result
    assert "insights_created" in result

    # Ambos insights deben haberse guardado
    assert len(result["insights_created"]) == 2

    # Solo 1 acción debe haberse creado (la que no falló)
    assert len(result["actions_created"]) == 1

    # Debe haber registrado el error
    assert len(result["errors"]) > 0


# ============================================================================
# Test 6: Caso sin temas priorizados
# ============================================================================

@pytest.mark.asyncio
async def test_persist_results_no_prioritized_themes():
    """Test 6: Caso sin temas priorizados."""
    state = create_initial_state([])
    state["prioritized_themes"] = []
    state["recommendations"] = []
    
    result = await persist_results(state)
    
    # Debe manejar el caso sin romper
    assert "actions_created" in result
    assert result["actions_created"] == []
    assert len(result["errors"]) == 1
    assert "No hay temas priorizados" in result["errors"][0]


# ============================================================================
# Test 7: Caso sin recomendaciones
# ============================================================================

@pytest.mark.asyncio
async def test_persist_results_no_recommendations():
    """Test 7: Caso sin recomendaciones para algunos temas."""
    state = create_initial_state([])
    state["prioritized_themes"] = [
        PrioritizedTheme(
            name="Tema sin recomendación",
            description="Test",
            priority="Media",
            evidence_count=1,
            reasoning="Test reasoning"
        )
    ]
    state["recommendations"] = []  # Sin recomendaciones
    
    async def mock_save_insight(theme, summary, priority, reasoning):
        return {
            "success": True,
            "insight_id": f"insight_{theme}",
            "theme": theme,
            "priority": priority
        }
    
    with patch('app.agents.persistence_agent.save_insight', new=mock_save_insight):
        result = await persist_results(state)
    
    # Debe guardar el insight pero no crear acción
    assert "insights_created" in result
    assert len(result["insights_created"]) == 1
    assert len(result["actions_created"]) == 0

    # Debe registrar que no se encontró recomendación
    assert len(result["errors"]) > 0
    assert any("No se encontró recomendación" in err for err in result["errors"])


# ============================================================================
# Test 8: Actualización correcta de state["actions_created"]
# ============================================================================

@pytest.mark.asyncio
async def test_persist_results_updates_actions_created(sample_state_with_results):
    """Test 8: Verificar actualización correcta de state['actions_created']."""
    
    async def mock_save_insight(theme, summary, priority, reasoning):
        return {
            "success": True,
            "insight_id": f"insight_123_{theme[:5]}",
            "theme": theme,
            "priority": priority
        }
    
    async def mock_create_action(title, description, priority):
        return {
            "success": True,
            "action_id": f"action_456_{title[:5]}",
            "title": title,
            "priority": priority,
            "status": "Pendiente"
        }
    
    with patch('app.agents.persistence_agent.save_insight', new=mock_save_insight):
        with patch('app.agents.persistence_agent.create_action_item', new=mock_create_action):
            result = await persist_results(sample_state_with_results)
    
    # Verificar que actions_created contiene los IDs correctos
    assert "actions_created" in result
    assert len(result["actions_created"]) == 2

    # Verificar formato de IDs de acciones
    for action_id in result["actions_created"]:
        assert action_id.startswith("action_456_")

    # Verificar que insights_created también se actualizó
    assert "insights_created" in result
    assert len(result["insights_created"]) == 2

    for insight_id in result["insights_created"]:
        assert insight_id.startswith("insight_123_")
