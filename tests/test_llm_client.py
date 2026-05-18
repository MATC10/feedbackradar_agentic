# -*- coding: utf-8 -*-
"""
Tests para la capa LLM de FeedbackRadar.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import BaseModel

from app.llm.ollama_chat_client import OllamaChatClient, OllamaChatError
from app.llm.structured_output import (
    extract_json_from_text,
    validate_with_pydantic,
    generate_structured_response,
    StructuredOutputError
)


# Modelos Pydantic para tests
class TestTheme(BaseModel):
    """Modelo de prueba para temas."""
    name: str
    description: str


class TestInsight(BaseModel):
    """Modelo de prueba para insights."""
    title: str
    priority: str
    reasoning: str


# ============================================================================
# Tests para OllamaChatClient
# ============================================================================

@pytest.mark.asyncio
async def test_ollama_chat_client_generate_text_success():
    """Test de generación exitosa de texto."""
    with patch('app.llm.ollama_chat_client.httpx.AsyncClient') as mock_client_class:
        # Mock del cliente HTTP
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock de la respuesta
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Este es el texto generado por el modelo"}
        mock_client.post = AsyncMock(return_value=mock_response)
        
        # Crear cliente y generar texto
        client = OllamaChatClient()
        result = await client.generate_text("Test prompt")
        
        # Verificar
        assert result == "Este es el texto generado por el modelo"
        mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_ollama_chat_client_empty_prompt():
    """Test con prompt vacío debe lanzar ValueError."""
    client = OllamaChatClient()
    
    with pytest.raises(ValueError, match="El prompt no puede estar vacío"):
        await client.generate_text("")


@pytest.mark.asyncio
async def test_ollama_chat_client_http_error():
    """Test de error HTTP del servidor."""
    with patch('app.llm.ollama_chat_client.httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock respuesta con error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_client.post = AsyncMock(return_value=mock_response)
        
        client = OllamaChatClient()
        
        with pytest.raises(OllamaChatError, match="Ollama respondió con código 500"):
            await client.generate_text("Test prompt")


@pytest.mark.asyncio
async def test_ollama_chat_client_missing_response_field():
    """Test cuando la respuesta no tiene el campo 'response'."""
    with patch('app.llm.ollama_chat_client.httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        
        # Mock respuesta sin campo 'response'
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": "algo salió mal"}
        mock_client.post = AsyncMock(return_value=mock_response)
        
        client = OllamaChatClient()
        
        with pytest.raises(OllamaChatError, match="no contiene campo 'response'"):
            await client.generate_text("Test prompt")


# ============================================================================
# Tests para structured_output
# ============================================================================

def test_extract_json_from_text_direct():
    """Test de extracción de JSON directo."""
    json_text = '{"name": "Pagos", "description": "Problemas con pagos"}'
    result = extract_json_from_text(json_text)
    
    assert result == {"name": "Pagos", "description": "Problemas con pagos"}


def test_extract_json_from_text_with_markdown():
    """Test de extracción de JSON envuelto en markdown."""
    text_with_json = """
    Aquí está el JSON solicitado:
    ```json
    {"name": "Usabilidad", "description": "Mejoras de interfaz"}
    ```
    Espero que esto ayude.
    """
    result = extract_json_from_text(text_with_json)
    
    assert result == {"name": "Usabilidad", "description": "Mejoras de interfaz"}


def test_extract_json_from_text_embedded():
    """Test de extracción de JSON embebido en texto."""
    text = 'El resultado es: {"name": "Performance", "description": "Lentitud"} como puedes ver.'
    result = extract_json_from_text(text)
    
    assert result == {"name": "Performance", "description": "Lentitud"}


def test_extract_json_from_text_invalid():
    """Test con texto sin JSON válido."""
    text = "Este texto no contiene JSON válido"
    
    with pytest.raises(StructuredOutputError, match="No se pudo extraer JSON válido"):
        extract_json_from_text(text)


def test_validate_with_pydantic_success():
    """Test de validación exitosa con Pydantic."""
    data = {"name": "Test Theme", "description": "Test description"}
    result = validate_with_pydantic(data, TestTheme)
    
    assert isinstance(result, TestTheme)
    assert result.name == "Test Theme"
    assert result.description == "Test description"


def test_validate_with_pydantic_from_string():
    """Test de validación desde string JSON."""
    json_string = '{"name": "Theme", "description": "Desc"}'
    result = validate_with_pydantic(json_string, TestTheme)
    
    assert isinstance(result, TestTheme)
    assert result.name == "Theme"


def test_validate_with_pydantic_validation_error():
    """Test cuando los datos no cumplen el schema."""
    data = {"name": "Only name"}  # Falta 'description'
    
    with pytest.raises(StructuredOutputError, match="Error de validación Pydantic"):
        validate_with_pydantic(data, TestTheme)


@pytest.mark.asyncio
async def test_generate_structured_response_success():
    """Test del flujo completo de generación estructurada."""
    # Mock del cliente LLM
    mock_client = AsyncMock()
    mock_client.generate_text = AsyncMock(
        return_value='{"name": "Integration Test", "description": "Full flow test"}'
    )
    
    # Generar respuesta estructurada
    result = await generate_structured_response(
        llm_client=mock_client,
        prompt="Generate a theme",
        response_model=TestTheme
    )
    
    # Verificar
    assert isinstance(result, TestTheme)
    assert result.name == "Integration Test"
    assert result.description == "Full flow test"
    mock_client.generate_text.assert_called_once_with("Generate a theme")


@pytest.mark.asyncio
async def test_generate_structured_response_with_markdown():
    """Test con respuesta en formato markdown."""
    mock_client = AsyncMock()
    mock_client.generate_text = AsyncMock(
        return_value='''
        Here is the JSON:
        ```json
        {"title": "Optimize payments", "priority": "Alta", "reasoning": "Many complaints"}
        ```
        '''
    )
    
    result = await generate_structured_response(
        llm_client=mock_client,
        prompt="Generate insight",
        response_model=TestInsight
    )
    
    assert isinstance(result, TestInsight)
    assert result.title == "Optimize payments"
    assert result.priority == "Alta"


@pytest.mark.asyncio
async def test_generate_structured_response_invalid_json():
    """Test cuando el LLM no devuelve JSON válido."""
    mock_client = AsyncMock()
    mock_client.generate_text = AsyncMock(
        return_value="This is not JSON at all"
    )
    
    with pytest.raises(StructuredOutputError):
        await generate_structured_response(
            llm_client=mock_client,
            prompt="Generate something",
            response_model=TestTheme
        )