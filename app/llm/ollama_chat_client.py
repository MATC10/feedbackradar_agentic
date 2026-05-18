# -*- coding: utf-8 -*-
"""
app/llm/ollama_chat_client.py

Cliente para interactuar con modelos de chat de Ollama.
"""

import logging
import httpx
from typing import Any, Dict

from app.core.config import settings

logger = logging.getLogger(__name__)


class OllamaChatError(Exception):
    """Excepción específica para errores del cliente Ollama Chat."""
    pass


class OllamaChatClient:
    """
    Cliente para interactuar con modelos de chat de Ollama.
    
    Permite enviar prompts y recibir respuestas de texto del modelo.
    """
    
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 120.0
    ):
        """
        Inicializa el cliente de Ollama Chat.
        
        Args:
            base_url: URL base de Ollama (default: desde settings)
            model: Modelo a usar (default: desde settings)
            timeout: Timeout en segundos (default: 120.0)
        """
        self.base_url = base_url or settings.ollama_base_url
        self.model = model or settings.ollama_chat_model
        self.timeout = timeout
        self.chat_url = f"{self.base_url}/api/generate"
        
        logger.info(
            f"OllamaChatClient inicializado: base_url={self.base_url}, "
            f"model={self.model}, timeout={self.timeout}s"
        )
    
    async def generate_text(self, prompt: str, format: str = None) -> str:
        """
        Genera texto a partir de un prompt usando Ollama.
        
        Args:
            prompt: Texto de entrada para el modelo
            format: Formato de salida opcional (ej: "json" para forzar JSON válido)
            
        Returns:
            Texto generado por el modelo
            
        Raises:
            ValueError: Si el prompt está vacío
            OllamaChatError: Si hay errores de conexión o del modelo
        """
        # Validar prompt
        if not prompt or not prompt.strip():
            raise ValueError("El prompt no puede estar vacío")
        
        logger.info(f"Generando texto con modelo {self.model} (format={format})")
        logger.debug(f"Prompt length: {len(prompt)} caracteres")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Preparar payload
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                }
                
                # Añadir formato si se especifica
                if format:
                    payload["format"] = format
                
                # Realizar petición
                response = await client.post(
                    self.chat_url,
                    json=payload
                )
                
                # Verificar código de respuesta
                if response.status_code != 200:
                    error_msg = f"Ollama respondió con código {response.status_code}: {response.text}"
                    logger.error(error_msg)
                    raise OllamaChatError(error_msg)
                
                # Parsear respuesta
                try:
                    response_data = response.json()
                except Exception as e:
                    error_msg = f"Error parseando respuesta JSON de Ollama: {str(e)}"
                    logger.error(error_msg)
                    raise OllamaChatError(error_msg)
                
                # Extraer texto generado
                if "response" not in response_data:
                    error_msg = f"Respuesta de Ollama no contiene campo 'response': {response_data}"
                    logger.error(error_msg)
                    raise OllamaChatError(error_msg)
                
                generated_text = response_data["response"]
                
                logger.info(f"Texto generado exitosamente: {len(generated_text)} caracteres")
                logger.debug(f"Generated text preview: {generated_text[:100]}...")
                
                return generated_text
                
        except httpx.TimeoutException as e:
            error_msg = f"Timeout conectando a Ollama después de {self.timeout}s"
            logger.error(error_msg, exc_info=True)
            raise OllamaChatError(error_msg) from e
            
        except httpx.ConnectError as e:
            error_msg = f"Error de conexión a Ollama en {self.base_url}"
            logger.error(error_msg, exc_info=True)
            raise OllamaChatError(error_msg) from e
            
        except OllamaChatError:
            # Re-raise nuestras propias excepciones
            raise
            
        except Exception as e:
            error_msg = f"Error inesperado generando texto: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise OllamaChatError(error_msg) from e