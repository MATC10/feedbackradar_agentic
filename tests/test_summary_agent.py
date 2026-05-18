# -*- coding: utf-8 -*-
"""
Tests para el Summary Agent.

Verifica:
1. Generacion exitosa del resumen ejecutivo con todos los campos
2. Estado sin temas priorizados devuelve resumen vacio sin error
3. StructuredOutputError es capturado y registrado en errors
4. Excepcion inesperada es capturada y registrada en errors
5. El estado inicial no es modificado salvo executive_summary
6. build_summary_prompt incluye datos clave del estado
7. El resumen contiene los 7 campos requeridos
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.agents import AgentState, create_initial_state
from app.agents.summary_agent import generate_executive_summary, build_summary_prompt, SummaryResponse
from app.llm import StructuredOutputError
from app.schemas.analysis import DetectedTheme, Evidence, PrioritizedTheme, Recommendation


@pytest.fixture
def full_state():
    """Estado completo con datos de todos los agentes previos."""
    state = create_initial_state([
        {"text": "El pago falla constantemente en movil", "platform": "App"},
        {"text": "No puedo descargar mi factura", "platform": "Web"},
        {"text": "La app va muy lenta", "platform": "App"},
    ])
    state["detected_themes"] = [
        DetectedTheme(name="Pagos fallidos", description="Errores en checkout"),
        DetectedTheme(name="Facturas", description="Problemas con facturas"),
    ]
    state["evidence_by_theme"] = {
        "Pagos fallidos": [
            Evidence(feedback_id="fb_1", text="El pago falla constantemente en movil", score=0.95, platform="App"),
            Evidence(feedback_id="fb_2", text="No puedo pagar con tarjeta", score=0.9, platform="Web"),
        ],
        "Facturas": [
            Evidence(feedback_id="fb_3", text="No puedo descargar mi factura", score=0.88, platform="Web"),
        ],
    }
    state["prioritized_themes"] = [
        PrioritizedTheme(
            name="Pagos fallidos",
            description="Errores en checkout",
            priority="Critica",
            evidence_count=2,
            reasoning="Alto impacto en conversion, bloquea ventas"
        ),
        PrioritizedTheme(
            name="Facturas",
            description="Problemas con facturas",
            priority="Alta",
            evidence_count=1,
            reasoning="Genera reclamaciones al soporte"
        ),
    ]
    state["recommendations"] = [
        Recommendation(
            title="Auditar flujo de pago movil",
            description="Revisar logs de errores en checkout",
            priority="Critica",
            related_themes=["Pagos fallidos"],
            expected_impact="Reducir abandono de carrito"
        ),
        Recommendation(
            title="Redisenar seccion de facturas",
            description="Facilitar acceso y descarga de facturas",
            priority="Alta",
            related_themes=["Facturas"],
            expected_impact="Reducir tickets de soporte"
        ),
    ]
    return state


def _make_summary_response():
    return SummaryResponse(
        narrative="El principal problema es el proceso de pago, con errores criticos en movil. Las facturas tambien generan friccion. Se recomienda priorizar el checkout y redisenar el area de cuenta.",
        overall_sentiment="Negativo",
        top_themes=["Pagos fallidos - critico, alta frecuencia", "Facturas - alta prioridad"],
        urgent_problems=["Errores en checkout bloquean ventas", "Facturas inaccesibles"],
        feature_requests=["Notificaciones de estado del pedido"],
        representative_examples=["[App] El pago falla constantemente en movil", "[Web] No puedo descargar mi factura"],
        product_recommendations=["Auditar y estabilizar el checkout", "Redisenar seccion de facturas"]
    )


# ============================================================================
# Test 1: Generacion exitosa con todos los campos
# ============================================================================

@pytest.mark.asyncio
async def test_generate_executive_summary_success(full_state):
    """Test 1: Generacion exitosa del resumen ejecutivo con todos los campos."""
    mock_response = _make_summary_response()

    with patch('app.agents.summary_agent.get_chat_llm_client', return_value=MagicMock()):
        with patch('app.agents.summary_agent.generate_structured_response', new=AsyncMock(return_value=mock_response)):
            result = await generate_executive_summary(full_state)

    assert "executive_summary" in result
    summary = result["executive_summary"]

    assert "narrative" in summary
    assert "overall_sentiment" in summary
    assert "top_themes" in summary
    assert "urgent_problems" in summary
    assert "feature_requests" in summary
    assert "representative_examples" in summary
    assert "product_recommendations" in summary


# ============================================================================
# Test 2: Estado sin temas priorizados devuelve resumen vacio sin error
# ============================================================================

@pytest.mark.asyncio
async def test_generate_executive_summary_no_themes():
    """Test 2: Estado sin temas priorizados devuelve resumen vacio sin error."""
    state = create_initial_state([{"text": "Test", "platform": "Web"}])
    state["prioritized_themes"] = []

    result = await generate_executive_summary(state)

    assert result["executive_summary"] == {}
    assert len(result["errors"]) == 0


# ============================================================================
# Test 3: StructuredOutputError es capturado y registrado
# ============================================================================

@pytest.mark.asyncio
async def test_generate_executive_summary_structured_output_error(full_state):
    """Test 3: StructuredOutputError es capturado, registrado y no propaga."""
    with patch('app.agents.summary_agent.get_chat_llm_client', return_value=MagicMock()):
        with patch('app.agents.summary_agent.generate_structured_response',
                   new=AsyncMock(side_effect=StructuredOutputError("JSON invalido del LLM"))):
            result = await generate_executive_summary(full_state)

    assert result["executive_summary"] == {}
    assert len(result["errors"]) == 1
    assert "Error generando resumen ejecutivo" in result["errors"][0]


# ============================================================================
# Test 4: Excepcion inesperada es capturada y registrada
# ============================================================================

@pytest.mark.asyncio
async def test_generate_executive_summary_unexpected_exception(full_state):
    """Test 4: Excepcion inesperada es capturada, registrada y no propaga."""
    with patch('app.agents.summary_agent.get_chat_llm_client',
               side_effect=RuntimeError("Conexion rechazada")):
        result = await generate_executive_summary(full_state)

    assert result["executive_summary"] == {}
    assert len(result["errors"]) == 1
    assert "Error inesperado en Summary Agent" in result["errors"][0]


# ============================================================================
# Test 5: El estado no es modificado salvo executive_summary
# ============================================================================

@pytest.mark.asyncio
async def test_generate_executive_summary_preserves_state(full_state):
    """Test 5: El agente no modifica ningún campo del estado excepto executive_summary."""
    original_themes = list(full_state["prioritized_themes"])
    original_recommendations = list(full_state["recommendations"])
    original_feedback = list(full_state["feedback_items"])
    original_errors = list(full_state["errors"])

    mock_response = _make_summary_response()

    with patch('app.agents.summary_agent.get_chat_llm_client', return_value=MagicMock()):
        with patch('app.agents.summary_agent.generate_structured_response', new=AsyncMock(return_value=mock_response)):
            result = await generate_executive_summary(full_state)

    assert result["prioritized_themes"] == original_themes
    assert result["recommendations"] == original_recommendations
    assert result["feedback_items"] == original_feedback
    assert result["errors"] == original_errors


# ============================================================================
# Test 6: build_summary_prompt incluye datos clave del estado
# ============================================================================

def test_build_summary_prompt_contains_key_data(full_state):
    """Test 6: El prompt contiene los datos relevantes del estado."""
    prompt = build_summary_prompt(full_state)

    assert "Pagos fallidos" in prompt
    assert "Facturas" in prompt
    assert "Critica" in prompt
    assert "Alta" in prompt
    assert "3" in prompt  # total feedback items


# ============================================================================
# Test 7: El resumen contiene los 7 campos requeridos con tipos correctos
# ============================================================================

@pytest.mark.asyncio
async def test_generate_executive_summary_all_seven_fields(full_state):
    """Test 7: El resumen ejecutivo contiene los 7 campos requeridos con tipos correctos."""
    mock_response = _make_summary_response()

    with patch('app.agents.summary_agent.get_chat_llm_client', return_value=MagicMock()):
        with patch('app.agents.summary_agent.generate_structured_response', new=AsyncMock(return_value=mock_response)):
            result = await generate_executive_summary(full_state)

    summary = result["executive_summary"]

    assert isinstance(summary["narrative"], str)
    assert len(summary["narrative"]) >= 50

    assert summary["overall_sentiment"] in ("Negativo", "Mixto", "Positivo")

    assert isinstance(summary["top_themes"], list)
    assert len(summary["top_themes"]) > 0

    assert isinstance(summary["urgent_problems"], list)
    assert isinstance(summary["feature_requests"], list)
    assert isinstance(summary["representative_examples"], list)
    assert isinstance(summary["product_recommendations"], list)
