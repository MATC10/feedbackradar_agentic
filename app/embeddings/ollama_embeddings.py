"""
app/embeddings/ollama_embeddings.py
Servicio para generar embeddings usando Ollama
"""
import logging
from typing import List
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class OllamaEmbeddingError(Exception):
    """Error específico para problemas con el servicio de embeddings de Ollama"""
    pass


class OllamaEmbeddingService:
    """
    Servicio para generar embeddings de texto usando Ollama.
    
    Utiliza el modelo configurado en OLLAMA_EMBEDDING_MODEL y se conecta
    al servidor Ollama en OLLAMA_BASE_URL.
    """
    
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_embedding_model
        self.timeout = 30.0
        
        logger.info(
            f"OllamaEmbeddingService inicializado: "
            f"URL={self.base_url}, Model={self.model}"
        )
    
    def embed_text(self, text: str) -> List[float]:
        """
        Genera un embedding vectorial para el texto dado.
        
        Args:
            text: Texto a convertir en embedding
            
        Returns:
            Lista de floats representando el vector de embedding
            
        Raises:
            OllamaEmbeddingError: Si hay problemas de conexión o respuesta inválida
            ValueError: Si el texto está vacío
        """
        if not text or not text.strip():
            raise ValueError("El texto no puede estar vacío")
        
        url = f"{self.base_url}/api/embeddings"
        payload = {
            "model": self.model,
            "prompt": text
        }
        
        try:
            logger.debug(f"Generando embedding para texto de {len(text)} caracteres")
            
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                
                data = response.json()
                
                # Validar que la respuesta contiene el embedding
                if "embedding" not in data:
                    raise OllamaEmbeddingError(
                        f"Respuesta inválida de Ollama: falta campo 'embedding'. "
                        f"Respuesta: {data}"
                    )
                
                embedding = data["embedding"]
                
                # Validar que el embedding es una lista de números
                if not isinstance(embedding, list) or len(embedding) == 0:
                    raise OllamaEmbeddingError(
                        f"Embedding inválido: esperaba lista no vacía, "
                        f"recibido: {type(embedding)}"
                    )
                
                # Validar que todos los elementos son números
                if not all(isinstance(x, (int, float)) for x in embedding):
                    raise OllamaEmbeddingError(
                        "Embedding contiene elementos no numéricos"
                    )
                
                logger.debug(f"Embedding generado exitosamente: dimensión={len(embedding)}")
                return embedding
                
        except httpx.TimeoutException as e:
            error_msg = (
                f"Timeout al conectar con Ollama en {url}. "
                f"Verifica que el servicio esté corriendo."
            )
            logger.error(error_msg)
            raise OllamaEmbeddingError(error_msg) from e
            
        except httpx.ConnectError as e:
            error_msg = (
                f"No se pudo conectar con Ollama en {url}. "
                f"Verifica que el servicio esté corriendo y la URL sea correcta."
            )
            logger.error(error_msg)
            raise OllamaEmbeddingError(error_msg) from e
            
        except httpx.HTTPStatusError as e:
            error_msg = (
                f"Error HTTP {e.response.status_code} de Ollama: {e.response.text}"
            )
            logger.error(error_msg)
            raise OllamaEmbeddingError(error_msg) from e
            
        except Exception as e:
            error_msg = f"Error inesperado al generar embedding: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise OllamaEmbeddingError(error_msg) from e
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Genera embeddings para múltiples textos.
        
        Args:
            texts: Lista de textos a convertir en embeddings
            
        Returns:
            Lista de embeddings (cada uno es una lista de floats)
            
        Raises:
            OllamaEmbeddingError: Si hay problemas al generar algún embedding
        """
        if not texts:
            return []
        
        logger.info(f"Generando embeddings para {len(texts)} textos")
        embeddings = []
        
        for i, text in enumerate(texts):
            try:
                embedding = self.embed_text(text)
                embeddings.append(embedding)
            except Exception as e:
                logger.error(f"Error al generar embedding {i+1}/{len(texts)}: {e}")
                raise
        
        logger.info(f"Embeddings generados exitosamente: {len(embeddings)}")
        return embeddings