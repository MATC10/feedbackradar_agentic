# -*- coding: utf-8 -*-
"""
app/llm/llm_client.py

Interfaz base para clientes LLM.
"""

from typing import Protocol
from pydantic import BaseModel


class LLMClient(Protocol):
    """
    Protocolo que define la interfaz para clientes LLM.
    
    Cualquier implementación debe proporcionar métodos para generar
    texto a partir de prompts.
    """
    
    async def generate_text(self, prompt: str) -> str:
        """
        Genera texto a partir de un prompt.
        
        Args:
            prompt: Texto de entrada para el modelo
            
        Returns:
            Texto generado por el modelo
            
        Raises:
            ValueError: Si el prompt está vacío
            Exception: Si hay errores de conexión o del modelo
        """
        ...