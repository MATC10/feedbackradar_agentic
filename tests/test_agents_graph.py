# -*- coding: utf-8 -*-
"""
Tests para el grafo completo de agentes con LangGraph.

Verifica:
1. El grafo se construye correctamente
2. El workflow ejecuta los 6 nodos en el orden esperado
3. El estado final contiene todos los campos esperados
4. Se integran correctamente los seis agentes mockeados
5. El workflow conserva el estado inicial
6. El workflow maneja correctamente errores parciales
7. La funcion de ejecucion de alto nivel funciona correctamente
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.agents import (
    AgentState,
    create_initial_state,
    build_feedback_analysis_graph,
    run_feedback_analysis_workflow,
    get_workflow_summary
)
from app.schemas.analysis import DetectedTheme, Evidence, PrioritizedTheme, Recommendation


def _mock_summary(state):
    state["executive_summary"] = {"narrative": "Test summary"}
    return state


# ============================================================================
# Test 1: El grafo se construye correctamente
# ============================================================================

def test_build_feedback_analysis_graph():
    """Test 1: El grafo se construye correctamente."""
    graph = build_feedback_analysis_graph()
    assert graph is not None
    assert hasattr(graph, 'ainvoke')
    assert hasattr(graph, 'invoke')


# ============================================================================
# Test 2: El workflow ejecuta los 6 nodos en el orden esperado
# ============================================================================

@pytest.mark.asyncio
async def test_workflow_executes_nodes_in_order():
    """Test 2: El workflow ejecuta los 6 nodos en el orden esperado."""

    execution_order = []

    async def mock_discover_themes(state):
        execution_order.append("discover_themes")
        state["detected_themes"] = [DetectedTheme(name="Test Theme", description="Test")]
        return state

    async def mock_retrieve_evidence(state):
        execution_order.append("retrieve_evidence")
        state["evidence_by_theme"] = {
            "Test Theme": [Evidence(feedback_id="fb_1", text="Test", score=0.9)]
        }
        return state

    async def mock_prioritize_themes(state):
        execution_order.append("prioritize_themes")
        state["prioritized_themes"] = [
            PrioritizedTheme(name="Test Theme", description="Test", priority="Alta", evidence_count=1, reasoning="Test")
        ]
        return state

    async def mock_generate_recommendations(state):
        execution_order.append("generate_recommendations")
        state["recommendations"] = [
            Recommendation(title="Test Action", description="Test", priority="Alta", related_themes=["Test Theme"], expected_impact="Test")
        ]
        return state

    async def mock_persist_results(state):
        execution_order.append("persist_results")
        state["actions_created"] = ["action_1"]
        state["insights_created"] = ["insight_1"]
        return state

    async def mock_generate_executive_summary(state):
        execution_order.append("generate_executive_summary")
        state["executive_summary"] = {"narrative": "Test summary"}
        return state

    with patch('app.agents.graph.discover_themes', new=mock_discover_themes):
        with patch('app.agents.graph.retrieve_evidence', new=mock_retrieve_evidence):
            with patch('app.agents.graph.prioritize_themes', new=mock_prioritize_themes):
                with patch('app.agents.graph.generate_recommendations', new=mock_generate_recommendations):
                    with patch('app.agents.graph.persist_results', new=mock_persist_results):
                        with patch('app.agents.graph.generate_executive_summary', new=mock_generate_executive_summary):
                            feedback = [{"text": "Test", "platform": "Web"}]
                            result = await run_feedback_analysis_workflow(feedback)

    assert execution_order == [
        "discover_themes",
        "retrieve_evidence",
        "prioritize_themes",
        "generate_recommendations",
        "persist_results",
        "generate_executive_summary"
    ]

    assert "detected_themes" in result
    assert "evidence_by_theme" in result
    assert "prioritized_themes" in result
    assert "recommendations" in result
    assert "actions_created" in result
    assert "executive_summary" in result


# ============================================================================
# Test 3: El estado final contiene todos los campos esperados
# ============================================================================

@pytest.mark.asyncio
async def test_workflow_final_state_contains_expected_fields():
    """Test 3: El estado final contiene todos los campos esperados."""

    async def mock_discover_themes(state):
        state["detected_themes"] = [DetectedTheme(name="Theme1", description="Desc1")]
        return state

    async def mock_retrieve_evidence(state):
        state["evidence_by_theme"] = {"Theme1": [Evidence(feedback_id="fb1", text="Test", score=0.9)]}
        return state

    async def mock_prioritize_themes(state):
        state["prioritized_themes"] = [
            PrioritizedTheme(name="Theme1", description="Desc1", priority="Alta", evidence_count=1, reasoning="Test")
        ]
        return state

    async def mock_generate_recommendations(state):
        state["recommendations"] = [
            Recommendation(title="Action1", description="Desc", priority="Alta", related_themes=["Theme1"], expected_impact="Impact")
        ]
        return state

    async def mock_persist_results(state):
        state["actions_created"] = ["action_123"]
        state["insights_created"] = ["insight_456"]
        return state

    async def mock_generate_executive_summary(state):
        state["executive_summary"] = {"narrative": "Summary"}
        return state

    with patch('app.agents.graph.discover_themes', new=mock_discover_themes):
        with patch('app.agents.graph.retrieve_evidence', new=mock_retrieve_evidence):
            with patch('app.agents.graph.prioritize_themes', new=mock_prioritize_themes):
                with patch('app.agents.graph.generate_recommendations', new=mock_generate_recommendations):
                    with patch('app.agents.graph.persist_results', new=mock_persist_results):
                        with patch('app.agents.graph.generate_executive_summary', new=mock_generate_executive_summary):
                            feedback = [{"text": "Test feedback", "platform": "Web"}]
                            result = await run_feedback_analysis_workflow(feedback)

    assert "detected_themes" in result
    assert len(result["detected_themes"]) == 1
    assert "evidence_by_theme" in result
    assert "Theme1" in result["evidence_by_theme"]
    assert "prioritized_themes" in result
    assert len(result["prioritized_themes"]) == 1
    assert "recommendations" in result
    assert len(result["recommendations"]) == 1
    assert "actions_created" in result
    assert len(result["actions_created"]) == 1
    assert "insights_created" in result
    assert len(result["insights_created"]) == 1
    assert "executive_summary" in result


# ============================================================================
# Test 4: Se integran correctamente los seis agentes mockeados
# ============================================================================

@pytest.mark.asyncio
async def test_workflow_integrates_six_agents():
    """Test 4: Se integran correctamente los seis agentes mockeados."""

    agents_called = set()

    async def mock_discover_themes(state):
        agents_called.add("discover_themes")
        state["detected_themes"] = [DetectedTheme(name="T1", description="D1")]
        return state

    async def mock_retrieve_evidence(state):
        agents_called.add("retrieve_evidence")
        state["evidence_by_theme"] = {}
        return state

    async def mock_prioritize_themes(state):
        agents_called.add("prioritize_themes")
        state["prioritized_themes"] = []
        return state

    async def mock_generate_recommendations(state):
        agents_called.add("generate_recommendations")
        state["recommendations"] = []
        return state

    async def mock_persist_results(state):
        agents_called.add("persist_results")
        state["actions_created"] = []
        state["insights_created"] = []
        return state

    async def mock_generate_executive_summary(state):
        agents_called.add("generate_executive_summary")
        state["executive_summary"] = {}
        return state

    with patch('app.agents.graph.discover_themes', new=mock_discover_themes):
        with patch('app.agents.graph.retrieve_evidence', new=mock_retrieve_evidence):
            with patch('app.agents.graph.prioritize_themes', new=mock_prioritize_themes):
                with patch('app.agents.graph.generate_recommendations', new=mock_generate_recommendations):
                    with patch('app.agents.graph.persist_results', new=mock_persist_results):
                        with patch('app.agents.graph.generate_executive_summary', new=mock_generate_executive_summary):
                            feedback = [{"text": "Test", "platform": "Email"}]
                            await run_feedback_analysis_workflow(feedback)

    assert len(agents_called) == 6
    assert "discover_themes" in agents_called
    assert "retrieve_evidence" in agents_called
    assert "prioritize_themes" in agents_called
    assert "generate_recommendations" in agents_called
    assert "persist_results" in agents_called
    assert "generate_executive_summary" in agents_called


# ============================================================================
# Test 5: El workflow conserva el estado inicial
# ============================================================================

@pytest.mark.asyncio
async def test_workflow_preserves_initial_state():
    """Test 5: El workflow conserva el estado inicial."""

    async def mock_agent(state):
        return state

    with patch('app.agents.graph.discover_themes', new=mock_agent):
        with patch('app.agents.graph.retrieve_evidence', new=mock_agent):
            with patch('app.agents.graph.prioritize_themes', new=mock_agent):
                with patch('app.agents.graph.generate_recommendations', new=mock_agent):
                    with patch('app.agents.graph.persist_results', new=mock_agent):
                        with patch('app.agents.graph.generate_executive_summary', new=mock_agent):
                            original_feedback = [
                                {"text": "Feedback 1", "platform": "Web"},
                                {"text": "Feedback 2", "platform": "App"}
                            ]
                            result = await run_feedback_analysis_workflow(original_feedback)

    assert "feedback_items" in result
    assert len(result["feedback_items"]) == 2
    assert result["feedback_items"][0]["text"] == "Feedback 1"
    assert result["feedback_items"][1]["text"] == "Feedback 2"


# ============================================================================
# Test 6: El workflow maneja correctamente errores parciales
# ============================================================================

@pytest.mark.asyncio
async def test_workflow_handles_partial_errors():
    """Test 6: El workflow maneja correctamente errores parciales."""

    async def mock_discover_themes(state):
        state["detected_themes"] = [DetectedTheme(name="T1", description="D1")]
        state["errors"] = ["Error en discovery"]
        return state

    async def mock_retrieve_evidence(state):
        state["evidence_by_theme"] = {}
        return state

    async def mock_prioritize_themes(state):
        state["prioritized_themes"] = []
        state["errors"].append("Error en prioritization")
        return state

    async def mock_generate_recommendations(state):
        state["recommendations"] = []
        return state

    async def mock_persist_results(state):
        state["actions_created"] = []
        state["insights_created"] = []
        return state

    async def mock_generate_executive_summary(state):
        state["executive_summary"] = {}
        return state

    with patch('app.agents.graph.discover_themes', new=mock_discover_themes):
        with patch('app.agents.graph.retrieve_evidence', new=mock_retrieve_evidence):
            with patch('app.agents.graph.prioritize_themes', new=mock_prioritize_themes):
                with patch('app.agents.graph.generate_recommendations', new=mock_generate_recommendations):
                    with patch('app.agents.graph.persist_results', new=mock_persist_results):
                        with patch('app.agents.graph.generate_executive_summary', new=mock_generate_executive_summary):
                            feedback = [{"text": "Test", "platform": "Web"}]
                            result = await run_feedback_analysis_workflow(feedback)

    assert "detected_themes" in result
    assert "actions_created" in result
    assert "errors" in result
    assert len(result["errors"]) == 2
    assert "Error en discovery" in result["errors"]
    assert "Error en prioritization" in result["errors"]


# ============================================================================
# Test 7: La funcion de ejecucion de alto nivel funciona correctamente
# ============================================================================

@pytest.mark.asyncio
async def test_run_feedback_analysis_workflow_high_level():
    """Test 7: La funcion de ejecucion de alto nivel funciona correctamente."""

    async def mock_discover_themes(state):
        state["detected_themes"] = [DetectedTheme(name="Theme A", description="Description A")]
        return state

    async def mock_retrieve_evidence(state):
        state["evidence_by_theme"] = {"Theme A": [Evidence(feedback_id="fb_a", text="Evidence A", score=0.95)]}
        return state

    async def mock_prioritize_themes(state):
        state["prioritized_themes"] = [
            PrioritizedTheme(name="Theme A", description="Description A", priority="Critica", evidence_count=1, reasoning="High impact")
        ]
        return state

    async def mock_generate_recommendations(state):
        state["recommendations"] = [
            Recommendation(title="Fix A", description="Fix description", priority="Critica", related_themes=["Theme A"], expected_impact="High")
        ]
        return state

    async def mock_persist_results(state):
        state["actions_created"] = ["action_a123"]
        state["insights_created"] = ["insight_b456"]
        return state

    async def mock_generate_executive_summary(state):
        state["executive_summary"] = {
            "narrative": "El principal problema es X.",
            "overall_sentiment": "Negativo",
            "top_themes": ["Theme A - alta frecuencia"],
            "urgent_problems": ["Problema critico A"],
            "feature_requests": [],
            "representative_examples": ["[App] Ejemplo real"],
            "product_recommendations": ["Recomendacion 1"]
        }
        return state

    with patch('app.agents.graph.discover_themes', new=mock_discover_themes):
        with patch('app.agents.graph.retrieve_evidence', new=mock_retrieve_evidence):
            with patch('app.agents.graph.prioritize_themes', new=mock_prioritize_themes):
                with patch('app.agents.graph.generate_recommendations', new=mock_generate_recommendations):
                    with patch('app.agents.graph.persist_results', new=mock_persist_results):
                        with patch('app.agents.graph.generate_executive_summary', new=mock_generate_executive_summary):
                            feedback = [
                                {"text": "System crashes frequently", "platform": "App"},
                                {"text": "Cannot complete payment", "platform": "Web"}
                            ]
                            result = await run_feedback_analysis_workflow(feedback)

    assert result is not None
    assert len(result["detected_themes"]) == 1
    assert len(result["prioritized_themes"]) == 1
    assert len(result["recommendations"]) == 1
    assert len(result["actions_created"]) == 1
    assert len(result["insights_created"]) == 1
    assert result["executive_summary"]["overall_sentiment"] == "Negativo"

    summary = get_workflow_summary(result)
    assert summary["themes_detected"] == 1
    assert summary["themes_prioritized"] == 1
    assert summary["recommendations_generated"] == 1
    assert summary["actions_created"] == 1
    assert summary["insights_created"] == 1
    assert summary["workflow_completed"] == True
