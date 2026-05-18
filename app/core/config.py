"""
Configuración centralizada de la aplicación mediante variables de entorno.
"""

from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).parent.parent.parent / ".env"
# El .env es la fuente autoritativa: override=True para que gane sobre variables de sesión
load_dotenv(dotenv_path=_ENV_FILE, override=True)


class Settings(BaseSettings):
    """
    Configuración global de FeedbackRadar Agentic.
    
    Carga automáticamente variables desde .env y entorno del sistema.
    """
    
    # Información de la aplicación
    app_name: str = "FeedbackRadar Agentic"
    app_env: str = "development"
    
    # MongoDB - Base de datos principal
    mongodb_uri: str
    mongodb_db_name: str = "feedbackradar"
    
    # Elasticsearch - Búsqueda vectorial
    elasticsearch_url: str
    elasticsearch_index: str = "feedback"
    
    # Ollama - Embeddings y LLM
    ollama_base_url: str
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_chat_model: str = "llama3.2"
    
    # OpenAI-Compatible API Configuration (para agentes)
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = "gpt-5"
    openai_provider: str = "openai"  # Header 'provider' requerido por el endpoint
    openai_origin: str = "feedbackradar"  # Header 'origin' requerido por el endpoint
    openai_origin_detail: str = "agentic-analysis"  # Header 'origin-detail' requerido
    
    # Chat LLM Provider Selection
    chat_llm_provider: str = "ollama"  # "openai" o "ollama"
    
    # Gmail MCP Collector - Configuración de polling con Anthropic
    gmail_mcp_polling_enabled: bool = False
    gmail_mcp_poll_interval_seconds: int = 60
    gmail_mcp_subject_filter: str = "notausuario"
    gmail_mcp_output_csv: str = "data/raw/gmail_notausuario.csv"
    gmail_mcp_credentials_file: str = "credentials.json"
    gmail_mcp_token_file: str = "token.json"
    gmail_mcp_server_url: str = "https://gmailmcp.googleapis.com/mcp/v1"
    gmail_use_direct_api: bool = False  # True = Gmail API directa; False = MCP server

    # Anthropic API Configuration
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    # Jira MCP Integration
    jira_mcp_enabled: bool = False
    jira_base_url: str = ""
    jira_user_email: str = ""
    jira_api_token: str = ""
    jira_project_key: str = "KAN"
    jira_default_issue_type: str = "Task"
    jira_priority_critica: str = "Highest"
    jira_priority_alta: str = "High"
    jira_dedup_days: int = 7
    
    # Configuración de Pydantic Settings
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignora variables de entorno no definidas
    )
    
    def __repr__(self) -> str:
        """Representación segura sin exponer credenciales"""
        return (
            f"Settings(app_name='{self.app_name}', "
            f"app_env='{self.app_env}', "
            f"mongodb_db='{self.mongodb_db_name}', "
            f"elasticsearch_index='{self.elasticsearch_index}')"
        )


@lru_cache
def get_settings() -> Settings:
    """
    Obtiene la instancia singleton de configuración.
    
    Usa lru_cache para asegurar una única instancia durante
    la ejecución de la aplicación.
    
    Returns:
        Settings: Instancia de configuración cargada
        
    Raises:
        ValidationError: Si faltan variables críticas o tienen formato inválido
    """
    return Settings()


# Instancia global para importación directa
settings = get_settings()