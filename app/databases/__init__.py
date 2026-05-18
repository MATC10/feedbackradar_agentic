"""
Capa de persistencia para FeedbackRadar Agentic.

Este módulo proporciona clientes y repositorios para interactuar
con MongoDB y Elasticsearch.
"""

# MongoDB Client
from app.databases.mongodb_client import (
    MongoDBClient,
    Collections,
    get_feedback_collection,
    get_analysis_runs_collection,
    get_insights_collection,
    get_actions_collection,
    get_db,
)

# Elasticsearch Client
from app.databases.elasticsearch_client import (
    ElasticsearchClient,
    get_es_client,
    initialize_feedback_index,
)

# Repositories
from app.databases.repositories import (
    FeedbackRepository,
    AnalysisRunRepository,
    InsightRepository,
    ActionRepository,
)

__all__ = [
    # MongoDB
    "MongoDBClient",
    "Collections",
    "get_feedback_collection",
    "get_analysis_runs_collection",
    "get_insights_collection",
    "get_actions_collection",
    "get_db",
    # Elasticsearch
    "ElasticsearchClient",
    "get_es_client",
    "initialize_feedback_index",
    # Repositories
    "FeedbackRepository",
    "AnalysisRunRepository",
    "InsightRepository",
    "ActionRepository",
]