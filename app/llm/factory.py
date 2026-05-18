# -*- coding: utf-8 -*-
"""
app/llm/factory.py

Factory para crear clientes LLM según configuración.
"""

import logging
from typing import Union

from app.core.config import settings
from app.llm.ollama_chat_client import OllamaChatClient
from app.llm.openai_chat_client import OpenAIChatClient
from app.llm.llm_client import LLMClient

logger = logging.getLogger(__name__)


def get_chat_llm_client() -> Union[OpenAIChatClient, OllamaChatClient]:
    """
    Crea y retorna un cliente LLM según la configuración.
    
    Selecciona el proveedor basado en settings.chat_llm_provider:
    - "openai": Usa OpenAIChatClient con endpoint OpenAI-compatible
    - "ollama": Usa OllamaChatClient con Ollama local
    
    Returns:
        Cliente LLM configurado (OpenAIChatClient u OllamaChatClient)
        
    Raises:
        ValueError: Si el proveedor configurado no es válido
        
    Example:
        >>> client = get_chat_llm_client()
        >>> text = await client.generate_text("Hello, world!")
    """
    provider = settings.chat_llm_provider.lower()
    
    logger.info(f"Creando cliente LLM para proveedor: {provider}")
    
    if provider == "openai":
        logger.info(
            f"Inicializando OpenAI-compatible client: "
            f"base_url={settings.openai_base_url}, model={settings.openai_model}"
        )
        return OpenAIChatClient(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.openai_model
        )
    
    elif provider == "ollama":
        logger.info(
            f"Inicializando Ollama client: "
            f"base_url={settings.ollama_base_url}, model={settings.ollama_chat_model}"
        )
        return OllamaChatClient(
            base_url=settings.ollama_base_url,
            model=settings.ollama_chat_model
        )
    
    else:
        error_msg = (
            f"Proveedor LLM no válido: '{provider}'. "
            f"Valores permitidos: 'openai', 'ollama'"
        )
        logger.error(error_msg)
        raise ValueError(error_msg)


# Alias para mantener compatibilidad si se necesita
create_chat_client = get_chat_llm_client