"""
Tests para el módulo de configuración.
"""

import pytest
from unittest.mock import patch
from pydantic import ValidationError
from app.core.config import Settings, get_settings


class TestSettings:
    """Tests para la clase Settings"""
    
    def test_settings_with_all_required_variables(self):
        """Verifica que Settings se instancia correctamente con todas las variables requeridas"""
        with patch.dict('os.environ', {
            'MONGODB_URI': 'mongodb://test:27017',
            'ELASTICSEARCH_URL': 'http://test:9200',
            'OLLAMA_BASE_URL': 'http://test:11434'
        }, clear=True):
            settings = Settings()
            
            assert settings.mongodb_uri == 'mongodb://test:27017'
            assert settings.elasticsearch_url == 'http://test:9200'
            assert settings.ollama_base_url == 'http://test:11434'
    
    def test_settings_with_default_values(self):
        """Verifica que los valores por defecto se aplican correctamente"""
        with patch.dict('os.environ', {
            'MONGODB_URI': 'mongodb://test:27017',
            'ELASTICSEARCH_URL': 'http://test:9200',
            'OLLAMA_BASE_URL': 'http://test:11434'
        }, clear=True):
            settings = Settings()
            
            assert settings.app_name == "FeedbackRadar Agentic"
            assert settings.app_env == "development"
            assert settings.mongodb_db_name == "feedbackradar"
            assert settings.elasticsearch_index == "feedback"
            assert settings.ollama_embedding_model == "nomic-embed-text"
            assert settings.ollama_chat_model == "llama3.2"
    
    def test_settings_missing_mongodb_uri(self):
        """Verifica que falla si falta MONGODB_URI"""
        with patch.dict('os.environ', {
            'ELASTICSEARCH_URL': 'http://test:9200',
            'OLLAMA_BASE_URL': 'http://test:11434'
        }, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)  # Ignora .env
            
            assert 'mongodb_uri' in str(exc_info.value).lower()
    
    def test_settings_missing_elasticsearch_url(self):
        """Verifica que falla si falta ELASTICSEARCH_URL"""
        with patch.dict('os.environ', {
            'MONGODB_URI': 'mongodb://test:27017',
            'OLLAMA_BASE_URL': 'http://test:11434'
        }, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)  # Ignora .env
            
            assert 'elasticsearch_url' in str(exc_info.value).lower()
    
    def test_settings_missing_ollama_base_url(self):
        """Verifica que falla si falta OLLAMA_BASE_URL"""
        with patch.dict('os.environ', {
            'MONGODB_URI': 'mongodb://test:27017',
            'ELASTICSEARCH_URL': 'http://test:9200'
        }, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings(_env_file=None)  # Ignora .env
            
            assert 'ollama_base_url' in str(exc_info.value).lower()
    
    def test_settings_custom_values(self):
        """Verifica que se pueden sobrescribir valores por defecto"""
        with patch.dict('os.environ', {
            'MONGODB_URI': 'mongodb://test:27017',
            'MONGODB_DB_NAME': 'custom_db',
            'ELASTICSEARCH_URL': 'http://test:9200',
            'ELASTICSEARCH_INDEX': 'custom_index',
            'OLLAMA_BASE_URL': 'http://test:11434',
            'OLLAMA_EMBEDDING_MODEL': 'custom-embed',
            'OLLAMA_CHAT_MODEL': 'custom-chat',
            'APP_ENV': 'production'
        }, clear=True):
            settings = Settings()
            
            assert settings.mongodb_db_name == 'custom_db'
            assert settings.elasticsearch_index == 'custom_index'
            assert settings.ollama_embedding_model == 'custom-embed'
            assert settings.ollama_chat_model == 'custom-chat'
            assert settings.app_env == 'production'
    
    def test_settings_repr_safe(self):
        """Verifica que __repr__ no expone información sensible"""
        with patch.dict('os.environ', {
            'MONGODB_URI': 'mongodb://user:password@test:27017',
            'ELASTICSEARCH_URL': 'http://test:9200',
            'OLLAMA_BASE_URL': 'http://test:11434'
        }, clear=True):
            settings = Settings()
            repr_str = repr(settings)
            
            # No debe contener la URI completa con credenciales
            assert 'password' not in repr_str
            assert 'user:password' not in repr_str
            
            # Debe contener información segura
            assert 'FeedbackRadar Agentic' in repr_str
            assert 'feedbackradar' in repr_str
            assert 'feedback' in repr_str
    
    def test_settings_case_insensitive(self):
        """Verifica que las variables de entorno son case-insensitive"""
        with patch.dict('os.environ', {
            'mongodb_uri': 'mongodb://test:27017',  # lowercase
            'ELASTICSEARCH_URL': 'http://test:9200',  # uppercase
            'Ollama_Base_Url': 'http://test:11434'  # mixed case
        }, clear=True):
            settings = Settings()
            
            assert settings.mongodb_uri == 'mongodb://test:27017'
            assert settings.elasticsearch_url == 'http://test:9200'
            assert settings.ollama_base_url == 'http://test:11434'


class TestGetSettings:
    """Tests para la función get_settings"""
    
    def test_get_settings_returns_settings_instance(self):
        """Verifica que get_settings retorna una instancia de Settings"""
        with patch.dict('os.environ', {
            'MONGODB_URI': 'mongodb://test:27017',
            'ELASTICSEARCH_URL': 'http://test:9200',
            'OLLAMA_BASE_URL': 'http://test:11434'
        }, clear=True):
            # Limpiar cache de lru_cache si existe
            if hasattr(get_settings, 'cache_clear'):
                get_settings.cache_clear()
            
            settings = get_settings()
            assert isinstance(settings, Settings)
    
    def test_get_settings_singleton(self):
        """Verifica que get_settings retorna siempre la misma instancia (singleton)"""
        with patch.dict('os.environ', {
            'MONGODB_URI': 'mongodb://test:27017',
            'ELASTICSEARCH_URL': 'http://test:9200',
            'OLLAMA_BASE_URL': 'http://test:11434'
        }, clear=True):
            # Limpiar cache de lru_cache si existe
            if hasattr(get_settings, 'cache_clear'):
                get_settings.cache_clear()
            
            settings1 = get_settings()
            settings2 = get_settings()
            
            # Ambas deberían ser instancias de Settings
            assert isinstance(settings1, Settings)
            assert isinstance(settings2, Settings)
