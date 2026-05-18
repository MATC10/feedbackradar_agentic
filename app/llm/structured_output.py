# -*- coding: utf-8 -*-
"""
app/llm/structured_output.py

Utilidades para obtener y validar salidas estructuradas de LLMs.
"""

import json
import re
import logging
from typing import TypeVar, Type
from pydantic import BaseModel, ValidationError

from app.llm.llm_client import LLMClient

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class StructuredOutputError(Exception):
    """Excepción para errores en la generación de salidas estructuradas."""
    pass


def extract_json_from_text(text: str) -> dict:
    """
    Extrae un objeto JSON de un texto que puede contener contenido adicional.
    
    Intenta encontrar y parsear JSON de varias formas:
    1. Parseando el texto completo como JSON
    2. Buscando bloques de código JSON (```json ... ```)
    3. Buscando patrones de objetos JSON ({ ... })
    
    Args:
        text: Texto que contiene JSON
        
    Returns:
        Diccionario parseado del JSON
        
    Raises:
        StructuredOutputError: Si no se puede extraer JSON válido
    """
    if not text or not text.strip():
        raise StructuredOutputError("El texto está vacío")
    
    text = text.strip()
    
    # Intento 1: Parsear directamente
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.debug("No se pudo parsear el texto completo como JSON, buscando bloques")
    
    # Intento 2: Buscar bloques de código JSON
    json_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
    matches = re.findall(json_block_pattern, text, re.DOTALL)
    
    if matches:
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
    
    # Intento 3: Buscar objetos JSON en el texto usando balance de llaves
    start_idx = text.find('{')
    
    if start_idx != -1:
        # Encontrar el cierre correspondiente usando contador de llaves
        brace_count = 0
        end_idx = -1
        
        for i in range(start_idx, len(text)):
            if text[i] == '{':
                brace_count += 1
            elif text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i
                    break
        
        if end_idx != -1:
            potential_json = text[start_idx:end_idx + 1]
            try:
                return json.loads(potential_json)
            except json.JSONDecodeError as e:
                logger.debug(f"Error parseando JSON balanceado: {str(e)}")
    
    # Intento 4: Buscar desde el primer { hasta el último }
    start_idx = text.find('{')
    end_idx = text.rfind('}')
    
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        potential_json = text[start_idx:end_idx + 1]
        try:
            return json.loads(potential_json)
        except json.JSONDecodeError:
            pass
    
    # Si llegamos aquí, no pudimos extraer JSON
    # Mostrar más contexto para debugging
    error_msg = f"No se pudo extraer JSON válido del texto. Texto completo (primeros 500 chars): {text[:500]}"
    logger.error(error_msg)
    raise StructuredOutputError(error_msg)


def validate_with_pydantic(data: dict | str, response_model: Type[T]) -> T:
    """
    Valida datos contra un modelo Pydantic.
    
    Args:
         Diccionario o string JSON a validar
        response_model: Clase Pydantic para validar
        
    Returns:
        Instancia validada del modelo
        
    Raises:
        StructuredOutputError: Si la validación falla
    """
    # Si data es string, parsearlo
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError as e:
            error_msg = f"Error parseando JSON: {str(e)}"
            logger.error(error_msg)
            raise StructuredOutputError(error_msg) from e
    
    # Validar con Pydantic
    try:
        validated_instance = response_model(**data)
        logger.debug(f"Datos validados exitosamente contra {response_model.__name__}")
        return validated_instance
    except ValidationError as e:
        error_msg = f"Error de validación Pydantic: {str(e)}"
        logger.error(error_msg)
        raise StructuredOutputError(error_msg) from e
    except Exception as e:
        error_msg = f"Error inesperado validando datos: {str(e)}"
        logger.error(error_msg)
        raise StructuredOutputError(error_msg) from e


async def generate_structured_response(
    llm_client: LLMClient,
    prompt: str,
    response_model: Type[T],
    force_json_format: bool = True
) -> T:
    """
    Genera una respuesta estructurada usando un LLM.
    
    Orquesta el proceso completo:
    1. Solicita texto al LLM (con formato JSON si es posible)
    2. Extrae JSON del texto
    3. Valida contra el modelo Pydantic
    4. Retorna instancia validada
    
    Args:
        llm_client: Cliente LLM para generar texto
        prompt: Prompt para el modelo
        response_model: Modelo Pydantic esperado
        force_json_format: Si True, intenta forzar formato JSON en Ollama
        
    Returns:
        Instancia validada del modelo
        
    Raises:
        StructuredOutputError: Si hay errores en algún paso del proceso
        
    Example:
        >>> from pydantic import BaseModel
        >>> class Theme(BaseModel):
        ...     name: str
        ...     description: str
        >>> 
        >>> prompt = "Dame un tema de feedback en JSON con campos 'name' y 'description'"
        >>> result = await generate_structured_response(client, prompt, Theme)
        >>> print(result.name)
    """
    logger.info(f"Generando respuesta estructurada para modelo {response_model.__name__}")
    
    try:
        # Paso 1: Generar texto con el LLM
        # Intentar usar formato JSON si el cliente lo soporta
        if force_json_format and hasattr(llm_client, 'generate_text'):
            import inspect
            sig = inspect.signature(llm_client.generate_text)
            if 'format' in sig.parameters:
                text = await llm_client.generate_text(prompt, format="json")
                logger.debug(f"Texto generado con formato JSON: {len(text)} caracteres")
            else:
                text = await llm_client.generate_text(prompt)
                logger.debug(f"Texto generado: {len(text)} caracteres")
        else:
            text = await llm_client.generate_text(prompt)
            logger.debug(f"Texto generado: {len(text)} caracteres")
        
        # Paso 2: Extraer JSON del texto
        json_data = extract_json_from_text(text)
        logger.debug(f"JSON extraído: {list(json_data.keys())}")
        
        # Paso 3: Validar con Pydantic
        validated_response = validate_with_pydantic(json_data, response_model)
        
        logger.info(f"Respuesta estructurada generada exitosamente: {response_model.__name__}")
        return validated_response
        
    except StructuredOutputError:
        # Re-raise nuestras propias excepciones
        raise
    except Exception as e:
        error_msg = f"Error generando respuesta estructurada: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise StructuredOutputError(error_msg) from e