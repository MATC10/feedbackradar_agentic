"""
Script de prueba para verificar la configuración.
"""

from app.core.config import settings, get_settings


def test_settings():
    """Prueba que la configuración se carga correctamente"""
    
    print("=" * 60)
    print("🔧 Verificando configuración de FeedbackRadar Agentic")
    print("=" * 60)
    print()
    
    # Información de la aplicación
    print(f"📱 Aplicación: {settings.app_name}")
    print(f"🌍 Entorno: {settings.app_env}")
    print()
    
    # MongoDB
    print("🗄️  MongoDB:")
    print(f"   URI: {settings.mongodb_uri}")
    print(f"   Database: {settings.mongodb_db_name}")
    print()
    
    # Elasticsearch
    print("🔍 Elasticsearch:")
    print(f"   URL: {settings.elasticsearch_url}")
    print(f"   Index: {settings.elasticsearch_index}")
    print()
    
    # Ollama
    print("🤖 Ollama:")
    print(f"   Base URL: {settings.ollama_base_url}")
    print(f"   Embedding Model: {settings.ollama_embedding_model}")
    print(f"   Chat Model: {settings.ollama_chat_model}")
    print()
    
    # Verificar que get_settings() devuelve la misma instancia
    settings2 = get_settings()
    assert settings is settings2, "get_settings() debe devolver la misma instancia (singleton)"
    print("✅ Singleton verificado: get_settings() devuelve la misma instancia")
    print()
    
    # Representación segura
    print(f"📋 Representación: {settings!r}")
    print()
    
    print("=" * 60)
    print("✅ Configuración cargada correctamente")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_settings()
    except Exception as e:
        print(f"❌ Error al cargar configuración: {e}")
        print()
        print("Verifica que:")
        print("1. El archivo .env existe en la raíz del proyecto")
        print("2. Todas las variables requeridas están definidas")
        print("3. Las URLs tienen el formato correcto")
        exit(1)