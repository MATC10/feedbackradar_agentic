"""
app/databases/elasticsearch_client.py
Cliente para interactuar con Elasticsearch para búsqueda vectorial
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import ConnectionError as ESConnectionError

from app.core.config import settings

logger = logging.getLogger(__name__)


class ElasticsearchClientError(Exception):
    """Error específico para problemas con Elasticsearch"""
    pass


class ElasticsearchClient:
    """
    Cliente para gestionar documentos e índices en Elasticsearch.
    
    Proporciona funcionalidades para:
    - Crear índices con campos vectoriales
    - Indexar documentos con embeddings
    - Realizar búsquedas semánticas por similitud vectorial
    """
    
    _client: Optional[AsyncElasticsearch] = None
    
    @classmethod
    async def connect(cls) -> None:
        """Conecta al servidor Elasticsearch"""
        if cls._client is None:
            try:
                cls._client = AsyncElasticsearch(
                    [settings.elasticsearch_url],
                    verify_certs=False,
                    request_timeout=30,
                    headers={"accept": "application/json", "content-type": "application/json"}
                )
                
                # Verificar conexión
                info = await cls._client.info()
                logger.info(f"Conectado a Elasticsearch: {info['version']['number']}")
                
            except ESConnectionError as e:
                error_msg = f"Error conectando a Elasticsearch: {e}"
                logger.error(error_msg)
                raise ElasticsearchClientError(error_msg) from e
    
    @classmethod
    async def disconnect(cls) -> None:
        """Cierra la conexión a Elasticsearch"""
        if cls._client is not None:
            await cls._client.close()
            cls._client = None
            logger.info("Desconectado de Elasticsearch")
    
    @classmethod
    def get_client(cls) -> AsyncElasticsearch:
        """
        Obtiene la instancia del cliente Elasticsearch.
        
        Returns:
            AsyncElasticsearch: Cliente configurado
            
        Raises:
            RuntimeError: Si no está conectado
        """
        if cls._client is None:
            raise RuntimeError(
                "Elasticsearch no está conectado. Llama a ElasticsearchClient.connect() primero."
            )
        return cls._client
    
    @classmethod
    async def create_index(cls, embedding_dim: int = 768) -> bool:
        """
        Crea el índice si no existe, con la configuración de campos vectoriales.
        
        Args:
            embedding_dim: Dimensión del vector de embedding (por defecto 768)
            
        Returns:
            True si el índice se creó o ya existía
            
        Raises:
            ElasticsearchClientError: Si hay error al crear el índice
        """
        try:
            client = cls.get_client()
            index_name = settings.elasticsearch_index
            
            # Verificar si el índice ya existe
            if await client.indices.exists(index=index_name):
                logger.info(f"El índice '{index_name}' ya existe")
                return True
            
            # Configuración del índice con campo vectorial
            index_body = {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0
                },
                "mappings": {
                    "properties": {
                        "feedback_id": {"type": "keyword"},
                        "text": {"type": "text"},
                        "platform": {"type": "keyword"},
                        "date": {
                            "type": "date",
                            "format": "yyyy-MM-dd||yyyy-MM-dd'T'HH:mm:ss||yyyy-MM-dd'T'HH:mm:ss'Z'||yyyy-MM-dd'T'HH:mm:ssXXX"
                        },
                        "embedding": {
                            "type": "dense_vector",
                            "dims": embedding_dim,
                            "index": True,
                            "similarity": "cosine"
                        },
                        "indexed_at": {"type": "date"}
                    }
                }
            }
            
            await client.indices.create(index=index_name, body=index_body)
            logger.info(
                f"Índice '{index_name}' creado exitosamente "
                f"con dimensión vectorial {embedding_dim}"
            )
            return True
            
        except Exception as e:
            error_msg = f"Error al crear índice: {str(e)}"
            logger.error(error_msg)
            raise ElasticsearchClientError(error_msg) from e
    
    @classmethod
    async def index_document(
        cls,
        feedback_id: str,
        text: str,
        platform: str,
        date: datetime,
        embedding: List[float]
    ) -> str:
        """
        Indexa un documento con su embedding en Elasticsearch.
        
        Args:
            feedback_id: ID único del feedback
            text: Texto del feedback
            platform: Plataforma de origen
            date: Fecha del feedback
            embedding: Vector de embedding
            
        Returns:
            ID del documento indexado
            
        Raises:
            ElasticsearchClientError: Si hay error al indexar
        """
        try:
            client = cls.get_client()
            index_name = settings.elasticsearch_index
            
            # Asegurar que el índice existe
            if not await client.indices.exists(index=index_name):
                # Detectar dimensión del embedding
                await cls.create_index(embedding_dim=len(embedding))
            
            document = {
                "feedback_id": feedback_id,
                "text": text,
                "platform": platform,
                "date": date.isoformat(),
                "embedding": embedding,
                "indexed_at": datetime.utcnow().isoformat()
            }
            
            response = await client.index(
                index=index_name,
                id=feedback_id,
                document=document
            )
            
            logger.debug(
                f"Documento indexado: feedback_id={feedback_id}, "
                f"result={response['result']}"
            )
            
            return response["_id"]
            
        except Exception as e:
            error_msg = f"Error al indexar documento {feedback_id}: {str(e)}"
            logger.error(error_msg)
            raise ElasticsearchClientError(error_msg) from e
    
    @classmethod
    async def semantic_search(
        cls,
        query_embedding: List[float],
        top_k: int = 10,
        platform_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Realiza una búsqueda semántica por similitud vectorial.
        
        Args:
            query_embedding: Vector de embedding de la consulta
            top_k: Número máximo de resultados a retornar
            platform_filter: Filtro opcional por plataforma
            
        Returns:
            Lista de documentos similares con sus scores
            
        Raises:
            ElasticsearchClientError: Si hay error en la búsqueda
        """
        try:
            client = cls.get_client()
            index_name = settings.elasticsearch_index
            
            # Construir el query base con k-NN
            knn_query = {
                "field": "embedding",
                "query_vector": query_embedding,
                "k": top_k,
                "num_candidates": top_k * 2  # Candidatos a considerar
            }
            
            # Añadir filtro por plataforma si se especifica
            if platform_filter:
                knn_query["filter"] = {
                    "term": {"platform": platform_filter}
                }
            
            # Construir el body de la búsqueda
            search_body = {
                "knn": knn_query,
                "size": top_k,
                "_source": ["feedback_id", "text", "platform", "date"]
            }
            
            # Ejecutar búsqueda
            response = await client.search(
                index=index_name,
                body=search_body
            )
            
            # Extraer resultados
            hits = response.get("hits", {}).get("hits", [])
            results = []
            
            for hit in hits:
                result = hit["_source"]
                result["score"] = hit["_score"]
                results.append(result)
            
            logger.debug(
                f"Búsqueda semántica completada: {len(results)} resultados "
                f"(platform_filter={platform_filter})"
            )
            
            return results
            
        except Exception as e:
            error_msg = f"Error en búsqueda semántica: {str(e)}"
            logger.error(error_msg)
            raise ElasticsearchClientError(error_msg) from e


# Funciones helper
async def get_es_client() -> AsyncElasticsearch:
    """
    Obtiene el cliente de Elasticsearch.
    
    Uso en FastAPI:
        @app.get("/endpoint")
        async def endpoint(es: AsyncElasticsearch = Depends(get_es_client)):
            ...
    """
    return ElasticsearchClient.get_client()


async def initialize_feedback_index(embedding_dim: int = 768) -> None:
    """
    Inicializa el índice de feedback con mappings correctos.
    
    Args:
        embedding_dim: Dimensión del vector de embedding
    """
    await ElasticsearchClient.create_index(embedding_dim=embedding_dim)