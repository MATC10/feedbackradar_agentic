"""
Test directo del servicio de embeddings para ver qué URL usa
"""
import sys
sys.path.insert(0, '.')

# Forzar recarga completa
import importlib
if 'app.core.config' in sys.modules:
    del sys.modules['app.core.config']
if 'app.embeddings.ollama_embeddings' in sys.modules:
    del sys.modules['app.embeddings.ollama_embeddings']

from app.embeddings.ollama_embeddings import OllamaEmbeddingService

# Crear servicio
service = OllamaEmbeddingService()

print(f"Base URL configurada: {service.base_url}")
print(f"Modelo configurado: {service.model}")

# Intentar generar un embedding
try:
    embedding = service.embed_text("test")
    print(f"\n✅ Embedding generado exitosamente!")
    print(f"Dimensión: {len(embedding)}")
except Exception as e:
    print(f"\n❌ Error: {e}")