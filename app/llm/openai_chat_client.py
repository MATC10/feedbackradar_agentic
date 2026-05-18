# -*- coding: utf-8 -*-
"""
app/llm/openai_chat_client.py

Cliente para interactuar con APIs compatibles con OpenAI.
"""

import logging
from typing import Optional

from openai import AsyncOpenAI, OpenAIError

from app.core.config import settings

logger = logging.getLogger(__name__)


class OpenAIChatError(Exception):
    """Excepción específica para errores del cliente OpenAI Chat."""
    pass


class OpenAIChatClient:
    """
    Cliente para interactuar con APIs compatibles con OpenAI.
    
    Permite enviar prompts y recibir respuestas de texto del modelo.
    Soporta endpoints OpenAI-compatible como el configurado.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 120.0
    ):
        """
        Inicializa el cliente de OpenAI Chat.
        
        Args:
            api_key: API key para autenticación (default: desde settings)
            base_url: URL base del endpoint (default: desde settings)
            model: Modelo a usar (default: desde settings)
            timeout: Timeout en segundos (default: 120.0)
        """
        self.api_key = api_key or settings.openai_api_key
        self.base_url = base_url or settings.openai_base_url
        self.model = model or settings.openai_model
        self.timeout = timeout
        
        # Headers personalizados opcionales (solo se incluyen si tienen valor)
        self.custom_headers = {
            k: v for k, v in {
                "provider": settings.openai_provider,
                "origin": settings.openai_origin,
                "origin-detail": settings.openai_origin_detail
            }.items() if v
        }

        # Validar configuración
        if not self.api_key:
            raise OpenAIChatError("OPENAI_API_KEY no configurada")
        if not self.base_url:
            raise OpenAIChatError("OPENAI_BASE_URL no configurada")

        # Inicializar cliente AsyncOpenAI
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
            default_headers=self.custom_headers if self.custom_headers else None
        )
        
        # Log seguro (sin exponer API key completa)
        masked_key = f"{self.api_key[:8]}...{self.api_key[-4:]}" if len(self.api_key) > 12 else "***"
        logger.info(
            f"OpenAIChatClient inicializado: base_url={self.base_url}, "
            f"model={self.model}, api_key={masked_key}, timeout={self.timeout}s"
        )
    
    async def generate_text(self, prompt: str, format: Optional[str] = None) -> str:
        """
        Genera texto a partir de un prompt usando el endpoint OpenAI-compatible.
        
        Args:
            prompt: Texto de entrada para el modelo
            format: Formato de salida opcional (ej: "json" para JSON estructurado)
                   Nota: Solo se usa si el endpoint soporta response_format
            
        Returns:
            Texto generado por el modelo
            
        Raises:
            ValueError: Si el prompt está vacío
            OpenAIChatError: Si hay errores de conexión o del modelo
        """
        # Validar prompt
        if not prompt or not prompt.strip():
            raise ValueError("El prompt no puede estar vacío")
        
        logger.info(f"Generando texto con modelo {self.model} (format={format})")
        logger.debug(f"Prompt length: {len(prompt)} caracteres")
        
        try:
            # Preparar mensajes
            messages = [
                {"role": "user", "content": prompt}
            ]
            
            # Preparar parámetros de la llamada
            call_params = {
                "model": self.model,
                "messages": messages,
            }
            
            # Intentar usar response_format si se solicita JSON
            if format == "json":
                try:
                    call_params["response_format"] = {"type": "json_object"}
                    logger.debug("Usando response_format=json_object")
                except Exception as e:
                    logger.warning(f"No se pudo configurar response_format: {e}. Continuando sin él.")
            
            # Realizar petición
            response = await self.client.chat.completions.create(**call_params)
            
            # Extraer texto generado
            if not response.choices:
                error_msg = "La respuesta no contiene choices"
                logger.error(error_msg)
                raise OpenAIChatError(error_msg)
            
            generated_text = response.choices[0].message.content
            
            if not generated_text:
                error_msg = "El contenido del mensaje está vacío"
                logger.error(error_msg)
                raise OpenAIChatError(error_msg)
            
            logger.info(f"Texto generado exitosamente: {len(generated_text)} caracteres")
            logger.debug(f"Generated text preview: {generated_text[:100]}...")
            
            return generated_text
            
        except OpenAIError as e:
            error_msg = f"Error de OpenAI API: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise OpenAIChatError(error_msg) from e
            
        except OpenAIChatError:
            # Re-raise nuestras propias excepciones
            raise
            
        except Exception as e:
            error_msg = f"Error inesperado generando texto: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise OpenAIChatError(error_msg) from e