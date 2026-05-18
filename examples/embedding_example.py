"""
Ejemplo de uso de embeddings y búsqueda vectorial.

Demuestra cómo:
1. Conectar a Elasticsearch
2. Generar embeddings con Ollama
3. Indexar documentos con embeddings
4. Realizar búsquedas semánticas
"""

import asyncio
import logging
from datetime import datetime

from app.core.config import settings
from app.embeddings.ollama_embeddings import OllamaEmbeddingService
from app.databases.elasticsearch_client import ElasticsearchClient, initialize_feedback_index

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Ejemplo completo de embeddings y búsqueda vectorial"""
    
    try:
        # 1. Conectar a Elasticsearch
        logger.info("Conectando a Elasticsearch...")
        await ElasticsearchClient.connect()
        
        # 2. Inicializar servicio de embeddings
        logger.info("Inicializando servicio de embeddings...")
        embedding_service = OllamaEmbeddingService()
        
        # 3. Detectar dimensión del modelo
        logger.info("Detectando dimensión del modelo de embeddings...")
        test_embedding = embedding_service.embed_text("prueba")
        embedding_dim = len(test_embedding)
        logger.info(f"Dimensión del embedding: {embedding_dim}")
        
        # 4. Crear índice en Elasticsearch
        logger.info(f"Creando índice '{settings.elasticsearch_index}'...")
        await initialize_feedback_index(embedding_dim=embedding_dim)
        
        # 5. Indexar algunos documentos de ejemplo
        logger.info("\nIndexando documentos de ejemplo...")
        
        ejemplos = [
            {
                "feedback_id": "demo_001",
                "text": "La aplicación es muy lenta al cargar",
                "platform": "Reviews",
                "date": datetime(2026, 5, 10)
            },
            {
                "feedback_id": "demo_002",
                "text": "No puedo completar el pago desde el móvil",
                "platform": "Email",
                "date": datetime(2026, 5, 11)
            },
            {
                "feedback_id": "demo_003",
                "text": "El rendimiento de la app ha mejorado mucho",
                "platform": "Reviews",
                "date": datetime(2026, 5, 12)
            },
            {
                "feedback_id": "demo_004",
                "text": "El proceso de checkout falla constantemente",
                "platform": "Encuestas",
                "date": datetime(2026, 5, 13)
            }
        ]
        
        for ejemplo in ejemplos:
            # Generar embedding
            embedding = embedding_service.embed_text(ejemplo["text"])
            
            # Indexar en Elasticsearch
            await ElasticsearchClient.index_document(
                feedback_id=ejemplo["feedback_id"],
                text=ejemplo["text"],
                platform=ejemplo["platform"],
                date=ejemplo["date"],
                embedding=embedding
            )
            logger.info(f"✓ Indexado: {ejemplo['feedback_id']}")
        
        # 6. Realizar búsquedas semánticas
        logger.info("\n" + "="*60)
        logger.info("BÚSQUEDAS SEMÁNTICAS")
        logger.info("="*60)
        
        # Búsqueda 1: Problemas de rendimiento
        query1 = "problemas de velocidad y lentitud"
        logger.info(f"\n🔍 Query: '{query1}'")
        query_embedding = embedding_service.embed_text(query1)
        results = await ElasticsearchClient.semantic_search(
            query_embedding=query_embedding,
            top_k=3
        )
        
        logger.info(f"Resultados encontrados: {len(results)}")
        for i, result in enumerate(results, 1):
            logger.info(f"{i}. [{result['feedback_id']}] Score: {result['score']:.4f}")
            logger.info(f"   Texto: {result['text']}")
            logger.info(f"   Plataforma: {result['platform']}")
        
        # Búsqueda 2: Problemas de pago
        query2 = "fallo en el pago"
        logger.info(f"\n🔍 Query: '{query2}'")
        query_embedding = embedding_service.embed_text(query2)
        results = await ElasticsearchClient.semantic_search(
            query_embedding=query_embedding,
            top_k=3
        )
        
        logger.info(f"Resultados encontrados: {len(results)}")
        for i, result in enumerate(results, 1):
            logger.info(f"{i}. [{result['feedback_id']}] Score: {result['score']:.4f}")
            logger.info(f"   Texto: {result['text']}")
            logger.info(f"   Plataforma: {result['platform']}")
        
        # Búsqueda 3: Con filtro por plataforma
        query3 = "problemas con la aplicación"
        platform_filter = "Reviews"
        logger.info(f"\n🔍 Query: '{query3}' (filtro: {platform_filter})")
        query_embedding = embedding_service.embed_text(query3)
        results = await ElasticsearchClient.semantic_search(
            query_embedding=query_embedding,
            top_k=3,
            platform_filter=platform_filter
        )
        
        logger.info(f"Resultados encontrados: {len(results)}")
        for i, result in enumerate(results, 1):
            logger.info(f"{i}. [{result['feedback_id']}] Score: {result['score']:.4f}")
            logger.info(f"   Texto: {result['text']}")
            logger.info(f"   Plataforma: {result['platform']}")
        
        logger.info("\n" + "="*60)
        logger.info("✅ Ejemplo completado exitosamente")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}", exc_info=True)
    
    finally:
        # Desconectar
        await ElasticsearchClient.disconnect()


if __name__ == "__main__":
    asyncio.run(main())