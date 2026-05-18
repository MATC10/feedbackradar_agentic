# -*- coding: utf-8 -*-
"""
app/llm/__init__.py

Módulo LLM para FeedbackRadar Agentic.

Proporciona clientes y utilidades para interactuar con modelos de lenguaje.
"""

from app.llm.llm_client import LLMClient
from app.llm.ollama_chat_client import OllamaChatClient, OllamaChatError
from app.llm.openai_chat_client import OpenAIChatClient, OpenAIChatError
from app.llm.factory import get_chat_llm_client, create_chat_client
from app.llm.structured_output import (
    generate_structured_response,
    extract_json_from_text,
    validate_with_pydantic,
    StructuredOutputError
)

__all__ = [
    "LLMClient",
    "OllamaChatClient",
    "OllamaChatError",
    "OpenAIChatClient",
    "OpenAIChatError",
    "get_chat_llm_client",
    "create_chat_client",
    "generate_structured_response",
    "extract_json_from_text",
    "validate_with_pydantic",
    "StructuredOutputError",
]
