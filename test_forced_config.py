"""
Test forzando la configuración directamente
"""
import os

# FORZAR variables de entorno ANTES de cualquier import
os.environ['OLLAMA_BASE_URL'] = 'http://localhost:11435'
os.environ['OLLAMA_EMBEDDING_MODEL'] = 'nomic-embed-text'

print("Variables de entorno forzadas:")
print(f"  OLLAMA_BASE_URL: {os.environ.get('OLLAMA_BASE_URL')}")
print(f"  OLLAMA_EMBEDDING_MODEL: {os.environ.get('OLLAMA_EMBEDDING_MODEL')}")

# Ahora importar
from app.embeddings.ollama_embeddings import OllamaEmbeddingService

service = OllamaEmbeddingService()
print(f"\nServicio inicializado:")
print(f"  Base URL: {service.base_url}")
print(f"  Modelo: {service.model}")

# Intentar generar embedding
try:
    embedding = service.embed_text("test de validación")
    print(f"\n✅ ¡ÉXITO! Embedding generado")
    print(f"   Dimensión: {len(embedding)}")
    print(f"   Primeros 5 valores: {embedding[:5]}")
except Exception as e:
    print(f"\n❌ Error: {e}")