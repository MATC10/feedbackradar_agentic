"""
app/api/chat_routes.py

Endpoint para consultas en lenguaje natural sobre el feedback de clientes.
Delega en el ChatAgent (tool-calling ReAct loop) para respuestas fundamentadas.
"""

import logging
from typing import List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.agents.chat_agent import run_chat_agent

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000, description="Pregunta sobre el feedback de clientes")


class EvidenceItem(BaseModel):
    text: str
    platform: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    evidence: List[EvidenceItem]
    tools_called: List[dict]
    iterations: int


@router.post(
    "/ask",
    response_model=ChatResponse,
    summary="Consultar sobre el feedback de clientes",
    description="Responde preguntas en lenguaje natural usando un agente con tool-calling sobre el feedback almacenado."
)
async def ask(request: ChatRequest) -> ChatResponse:
    logger.info(f"Chat request: '{request.question[:80]}'")

    result = await run_chat_agent(request.question.strip())

    evidence = [
        EvidenceItem(
            text=e.get("text", ""),
            platform=e.get("platform", ""),
            score=float(e.get("score") or 0.0),
        )
        for e in result.evidence
        if e.get("text")
    ]

    return ChatResponse(
        answer=result.answer,
        evidence=evidence,
        tools_called=result.tools_called,
        iterations=result.iterations,
    )
