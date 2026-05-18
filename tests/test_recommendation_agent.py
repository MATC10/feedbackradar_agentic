# -*- coding: utf-8 -*-
"""
Tests para el Recommendation Agent.

Este módulo contiene tests para verificar:
1. Generación exitosa de recomendaciones para uno o varios temas
2. Uso correcto de prioritized_themes como entrada
3. Recuperación de evidencias desde evidence_by_theme
4. Integración con respuesta estructurada del LLM mockeada
5. Manejo de fallo del LLM para un tema
6. Preservación del estado previo
7. Caso sin temas priorizados
8. Validación de la estructura de salida
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.agents import AgentState, create_initial_state, generate_recommendations
from app.schemas.analysis import DetectedTheme, Evidence, PrioritizedTheme, Recommendation


@pytest.fixture
def sample_state_with_prioritized_themes():
    """Estado de ejemplo con temas priorizados y evidencias."""
    state = create_initial_state([])
    state["detected_themes"] = [
        DetectedTheme(name="Pagos fallidos", description="Problemas con checkout"),
        DetectedTheme(name="Performance", description="Lentitud del sistema")
    ]
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
    state["evidence_by_theme"] = {
        "Pagos fallidos": [
            Evidence(feedback_id="fb_001", text="No puedo pagar", score=0.95, platform="Web"),
            Evidence(feedback_id="fb_002", text="Checkout falla", score=0.88, platform="App"),
            Evidence(feedback_id="fb_003", text="Error al procesar pago", score=0.85, platform="Email")
        ],
        "Performance": [
            Evidence(feedback_id="fb_004", text="Sistema muy lento", score=0.92, platform="Web"),
            Evidence(feedback_id="fb_005", text="Carga eterna", score=0.87, platform="App")
        ]
    }
    return state


# ============================================================================
# Test 1: Generación exitosa de recomendaciones para varios temas
# ============================================================================

@pytest.mark.asyncio
async def test_generate_recommendations_successful(sample_state_with_prioritized_themes):
    """Test 1: Generación exitosa de recomendaciones para varios temas."""
    
    # Mock del LLM que devuelve respuestas estructuradas
    async def mock_generate_structured(llm_client, prompt, response_model):
        if "Pagos fallidos" in prompt:
            return response_model(
                recommendation="Priorizar revisión inmediata del checkout móvil para detectar errores de flujo",
                action_title="Investigar fallos críticos en checkout móvil",
                action_description="Revisar logs, errores de frontend y comunicación con pasarela de pago",
                reasoning="Problema crítico que bloquea conversión con múltiples evidencias de usuarios"
            )
        else:  # Performance
            return response_model(
                recommendation="Implementar optimizaciones de rendimiento y monitoreo proactivo",
                action_title="Optimizar rendimiento del sistema",
                action_description="Analizar consultas lentas, implementar caché y optimizar queries de base de datos",
                reasoning="Impacta significativamente la experiencia del usuario según evidencias"
            )
    
    with patch('app.agents.recommendation_agent.generate_structured_response', new=mock_generate_structured):
        result = await generate_recommendations(sample_state_with_prioritized_themes)
    
    # Verificaciones
    assert "recommendations" in result
    assert len(result["recommendations"]) == 2
    
    # Verificar que se generaron recomendaciones para ambos temas
    titles = [rec.title for rec in result["recommendations"]]
    assert "Investigar fallos críticos en checkout móvil" in titles
    assert "Optimizar rendimiento del sistema" in titles
    
    # Verificar estructura de cada recomendación
    for rec in result["recommendations"]:
        assert isinstance(rec, Recommendation)
        assert rec.title is not None
        assert len(rec.title) >= 5
        assert rec.description is not None
        assert len(rec.description) >= 20
        assert rec.priority in ["Crítica", "Alta", "Media", "Baja"]
        assert len(rec.related_themes) > 0
        assert rec.expected_impact is not None


# ============================================================================
# Test 2: Uso correcto de prioritized_themes como entrada
# ============================================================================

@pytest.mark.asyncio
async def test_generate_recommendations_uses_prioritized_themes(sample_state_with_prioritized_themes):
    """Test 2: Verificar que se usa prioritized_themes correctamente."""
    
    themes_processed = []
    
    async def mock_generate_structured(llm_client, prompt, response_model):
        # Capturar qué temas se procesaron
        for theme in sample_state_with_prioritized_themes["prioritized_themes"]:
            if theme.name in prompt:
                themes_processed.append(theme.name)
                break
        
        return response_model(
            recommendation="Recomendación de prueba para el tema",
            action_title="Acción de prueba",
            action_description="Descripción detallada de la acción de prueba",
            reasoning="Razonamiento basado en prioridad y evidencias"
        )
    
    with patch('app.agents.recommendation_agent.generate_structured_response', new=mock_generate_structured):
        result = await generate_recommendations(sample_state_with_prioritized_themes)
    
    # Verificar que se procesaron todos los temas priorizados
    assert len(themes_processed) == 2
    assert "Pagos fallidos" in themes_processed
    assert "Performance" in themes_processed
    
    # Verificar que se generaron recomendaciones
    assert len(result["recommendations"]) == 2


# ============================================================================
# Test 3: Recuperación de evidencias desde evidence_by_theme
# ============================================================================

@pytest.mark.asyncio
async def test_generate_recommendations_uses_evidence(sample_state_with_prioritized_themes):
    """Test 3: Verificar que se recuperan evidencias desde evidence_by_theme."""
    
    prompts_received = []
    
    async def mock_generate_structured(llm_client, prompt, response_model):
        prompts_received.append(prompt)
        
        return response_model(
            recommendation="Recomendación basada en evidencias",
            action_title="Acción basada en evidencias",
            action_description="Descripción que considera las evidencias proporcionadas",
            reasoning="Razonamiento fundamentado en evidencias reales"
        )
    
    with patch('app.agents.recommendation_agent.generate_structured_response', new=mock_generate_structured):
        result = await generate_recommendations(sample_state_with_prioritized_themes)
    
    # Verificar que los prompts contienen evidencias
    assert len(prompts_received) == 2
    
    for prompt in prompts_received:
        assert "EVIDENCIAS REALES DE USUARIOS" in prompt
        # Al menos debe contener alguna evidencia
        assert "relevancia:" in prompt or "No hay evidencias disponibles" in prompt


# ============================================================================
# Test 4: Integración con respuesta estructurada del LLM mockeada
# ============================================================================

@pytest.mark.asyncio
async def test_generate_recommendations_llm_structured_response(sample_state_with_prioritized_themes):
    """Test 4: Integración con respuesta estructurada del LLM mockeada."""
    
    async def mock_generate_structured(llm_client, prompt, response_model):
        # Verificar que el prompt contiene información clave
        assert "TEMA PRIORIZADO:" in prompt
        assert "Prioridad:" in prompt
        assert "EVIDENCIAS REALES" in prompt
        assert "FORMATO DE RESPUESTA:" in prompt
        
        return response_model(
            recommendation="Implementar mejoras específicas basadas en análisis de evidencias",
            action_title="Mejorar funcionalidad crítica",
            action_description="Realizar análisis detallado, implementar correcciones y validar con usuarios",
            reasoning="Justificación clara que conecta prioridad, evidencias e impacto esperado"
        )
    
    with patch('app.agents.recommendation_agent.generate_structured_response', new=mock_generate_structured):
        result = await generate_recommendations(sample_state_with_prioritized_themes)
    
    # Verificar que las respuestas estructuradas se usaron correctamente
    assert len(result["recommendations"]) == 2
    
    for rec in result["recommendations"]:
        assert "mejoras" in rec.title.lower() or "mejorar" in rec.title.lower()
        assert len(rec.description) >= 20
        assert len(rec.expected_impact) >= 10


# ============================================================================
# Test 5: Manejo de fallo del LLM para un tema
# ============================================================================

@pytest.mark.asyncio
async def test_generate_recommendations_handles_llm_failure(sample_state_with_prioritized_themes):
    """Test 5: Manejo de fallo del LLM para un tema."""
    
    call_count = {"count": 0}
    
    async def mock_generate_structured_with_failure(llm_client, prompt, response_model):
        call_count["count"] += 1
        # Falla solo para el primer tema
        if call_count["count"] == 1:
            raise Exception("LLM connection error")
        
        return response_model(
            recommendation="Recomendación para tema exitoso",
            action_title="Acción exitosa",
            action_description="Descripción de acción que sí se pudo generar",
            reasoning="Razonamiento válido"
        )
    
    with patch('app.agents.recommendation_agent.generate_structured_response', new=mock_generate_structured_with_failure):
        result = await generate_recommendations(sample_state_with_prioritized_themes)
    
    # El workflow debe continuar a pesar del fallo
    assert "recommendations" in result
    # Solo 1 recomendación debe haberse generado (la que no falló)
    assert len(result["recommendations"]) == 1
    
    # Debe haber registrado el error
    assert len(result["errors"]) > 0
    assert any("Error" in err for err in result["errors"])


# ============================================================================
# Test 6: Preservación del estado previo
# ============================================================================

@pytest.mark.asyncio
async def test_generate_recommendations_preserves_state(sample_state_with_prioritized_themes):
    """Test 6: Preservación del estado previo."""
    
    # Agregar datos adicionales al estado
    sample_state_with_prioritized_themes["executive_summary"] = "Test summary"
    sample_state_with_prioritized_themes["actions_created"] = ["action_1"]
    original_themes = sample_state_with_prioritized_themes["prioritized_themes"].copy()
    
    async def mock_generate_structured(llm_client, prompt, response_model):
        return response_model(
            recommendation="Recomendación de prueba",
            action_title="Acción de prueba",
            action_description="Descripción de la acción de prueba",
            reasoning="Razonamiento de prueba"
        )
    
    with patch('app.agents.recommendation_agent.generate_structured_response', new=mock_generate_structured):
        result = await generate_recommendations(sample_state_with_prioritized_themes)
    
    # Verificar que se agregaron recomendaciones
    assert "recommendations" in result
    assert len(result["recommendations"]) == 2
    
    # Verificar que se preservó el estado previo
    assert result["executive_summary"] == "Test summary"
    assert result["actions_created"] == ["action_1"]
    assert result["prioritized_themes"] == original_themes


# ============================================================================
# Test 7: Caso sin temas priorizados
# ============================================================================

@pytest.mark.asyncio
async def test_generate_recommendations_no_prioritized_themes():
    """Test 7: Caso sin temas priorizados."""
    state = create_initial_state([])
    state["prioritized_themes"] = []
    
    result = await generate_recommendations(state)
    
    # Debe manejar el caso sin romper
    assert "recommendations" in result
    assert result["recommendations"] == []
    assert len(result["errors"]) == 1
    assert "No hay temas priorizados" in result["errors"][0]


# ============================================================================
# Test 8: Validación de la estructura de salida
# ============================================================================

@pytest.mark.asyncio
async def test_generate_recommendations_output_validation(sample_state_with_prioritized_themes):
    """Test 8: Validación de la estructura de salida."""
    
    async def mock_generate_structured(llm_client, prompt, response_model):
        if "Pagos" in prompt:
            return response_model(
                recommendation="Priorizar revisión del checkout para corregir errores críticos de pago",
                action_title="Corregir errores críticos de pago",
                action_description="Analizar logs de errores, identificar patrones de fallo y aplicar correcciones",
                reasoning="Crítico por bloquear conversión y afectar ingresos directamente"
            )
        else:
            return response_model(
                recommendation="Optimizar tiempos de carga mediante implementación de caché y CDN",
                action_title="Mejorar performance del sistema",
                action_description="Implementar sistema de caché distribuido y optimizar queries lentas",
                reasoning="Alto impacto en experiencia de usuario con evidencias claras de frustración"
            )
    
    with patch('app.agents.recommendation_agent.generate_structured_response', new=mock_generate_structured):
        result = await generate_recommendations(sample_state_with_prioritized_themes)
    
    # Validar estructura de recommendations
    assert isinstance(result["recommendations"], list)
    
    for rec in result["recommendations"]:
        # Verificar que es instancia de Recommendation
        assert isinstance(rec, Recommendation)
        
        # Verificar campos requeridos
        assert hasattr(rec, 'title')
        assert hasattr(rec, 'description')
        assert hasattr(rec, 'priority')
        assert hasattr(rec, 'related_themes')
        assert hasattr(rec, 'expected_impact')
        
        # Verificar tipos
        assert isinstance(rec.title, str)
        assert isinstance(rec.description, str)
        assert isinstance(rec.priority, str)
        assert isinstance(rec.related_themes, list)
        assert isinstance(rec.expected_impact, str)
        
        # Verificar valores válidos
        assert len(rec.title) >= 5
        assert len(rec.description) >= 20
        assert rec.priority in ["Crítica", "Alta", "Media", "Baja"]
        assert len(rec.related_themes) > 0
        assert len(rec.expected_impact) >= 10
        
        # Verificar que related_themes contiene temas válidos
        for theme_name in rec.related_themes:
            assert theme_name in ["Pagos fallidos", "Performance"]
