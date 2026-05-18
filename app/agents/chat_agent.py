"""
app/agents/chat_agent.py

Agente conversacional con tool-calling para consultas sobre feedback de clientes.
Loop ReAct: el LLM decide qué herramientas invocar iterativamente hasta tener
suficiente información para responder con datos reales.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from openai import AsyncOpenAI, BadRequestError

from app.core.config import settings
from app.mcp.agent_client import call_mcp_tool
from app.databases.repositories import InsightRepository

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 6

SYSTEM_PROMPT = """Eres un analista experto de feedback de clientes para un equipo de producto interno.
Tu rol es responder preguntas con análisis profundos y accionables, no solo estadísticas superficiales.

HERRAMIENTAS Y CUÁNDO USARLAS:
- search_feedback: úsala SIEMPRE para obtener fragmentos reales de opiniones. Lee el texto de cada resultado y analiza tú mismo el tono, sentimiento y contenido. Es tu principal fuente de insights cualitativos.
- get_feedback_stats: úsala para datos cuantitativos (cuántos mencionan un tema). Recuerda que cuenta apariciones de palabras, NO distingue positivo de negativo.
- get_recent_feedback: úsala cuando pregunten por tendencias recientes o feedback nuevo.
- get_insights: úsala para ver qué temas ya han sido analizados por el sistema.

CÓMO ANALIZAR SENTIMIENTO:
Cuando uses search_feedback, lee los textos devueltos y clasifícalos tú mismo:
- ¿El comentario expresa satisfacción, queja, sugerencia o neutro?
- ¿Qué palabras o frases concretas indican la opinión del cliente?
- Agrupa los resultados: cuántos son positivos, cuántos negativos, cuántos neutros.
- Extrae citas textuales representativas para apoyar tu análisis.

ESTRATEGIA PARA COMPARATIVAS (A vs B):
1. Llama a search_feedback para A → analiza sentimiento de los resultados
2. Llama a search_feedback para B → analiza sentimiento de los resultados
3. Llama a get_feedback_stats para A y B → datos cuantitativos de frecuencia
4. Sintetiza: compara tono, frecuencia y temas concretos que mencionan

FORMATO DE RESPUESTA:
- Empieza con la conclusión principal (qué responde directamente la pregunta)
- Luego apoya con datos: porcentajes, conteos y citas textuales reales
- Identifica patrones: qué aspectos concretos mencionan (rapidez, precio, trato, etc.)
- Si hay diferencias claras de sentimiento, explícalas con ejemplos del feedback real
- Sé específico: evita respuestas genéricas como "hay opiniones positivas y negativas"

REGLAS:
- Responde siempre en español
- No inventes datos ni citas que no estén en los resultados de las herramientas
- Si los datos son insuficientes, di exactamente qué información falta y por qué
- NUNCA menciones las herramientas, su nombre ni cómo obtienes los datos. El cliente solo quiere la respuesta, no el proceso. Nunca digas frases como "voy a usar search_feedback", "según la herramienta", "necesito consultar", "utilizando get_feedback_stats", etc."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_feedback",
            "description": "Búsqueda semántica de fragmentos de feedback de clientes. Úsala para encontrar opiniones relacionadas con un tema concreto.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Consulta en lenguaje natural para buscar feedback relacionado"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Número máximo de resultados (default: 8)",
                        "default": 8
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_feedback_stats",
            "description": "Obtiene estadísticas numéricas de cuántos clientes mencionan un tema: total de feedback, cuántos lo mencionan, etc. Ideal para comparaciones.",
            "parameters": {
                "type": "object",
                "properties": {
                    "theme": {
                        "type": "string",
                        "description": "Tema a buscar (ej: 'pago', 'rendimiento', 'login', 'factura')"
                    }
                },
                "required": ["theme"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_feedback",
            "description": "Obtiene el feedback más reciente de los últimos N días.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Número de días hacia atrás (default: 30)",
                        "default": 30
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_insights",
            "description": "Obtiene los insights analizados previamente: temas detectados por los agentes, sus prioridades y resúmenes del último análisis.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]


async def _execute_tool(name: str, args: dict) -> Any:
    """Ejecuta una herramienta via MCP server y devuelve el resultado serializable."""
    try:
        if name == "search_feedback":
            result = await call_mcp_tool(
                "search_feedback_tool",
                {"query": args["query"], "top_k": args.get("top_k", 8)},
            )
            items = result.get("results", [])
            return {
                "success": result.get("success"),
                "count": len(items),
                "results": [
                    {
                        "text": r.get("text", ""),
                        "platform": r.get("platform", ""),
                        "score": round(float(r.get("score") or 0), 3),
                    }
                    for r in items if r.get("text")
                ],
            }

        elif name == "get_feedback_stats":
            return await call_mcp_tool("get_feedback_stats_tool", {"theme": args["theme"]})

        elif name == "get_recent_feedback":
            result = await call_mcp_tool(
                "get_recent_feedback_tool",
                {"days": args.get("days", 30)},
            )
            feedbacks = result.get("feedbacks", [])
            return {
                "success": result.get("success"),
                "count": result.get("count", 0),
                "feedbacks": [
                    {"text": f.get("text", ""), "platform": f.get("platform", "")}
                    for f in feedbacks[:20] if f.get("text")
                ],
            }

        elif name == "get_insights":
            # get_insights no está expuesto en el MCP server; accede a MongoDB directamente
            insights = await InsightRepository.find_latest_per_theme()
            return [
                {
                    "theme": i.get("theme", ""),
                    "priority": i.get("priority", ""),
                    "summary": i.get("summary", ""),
                    "reasoning": i.get("reasoning", ""),
                }
                for i in insights
            ]

        else:
            return {"error": f"Herramienta desconocida: {name}"}

    except Exception as e:
        logger.error(f"Error ejecutando tool '{name}': {e}", exc_info=True)
        return {"error": str(e)}


@dataclass
class ChatAgentResult:
    answer: str
    tools_called: list = field(default_factory=list)
    evidence: list = field(default_factory=list)
    iterations: int = 0


async def run_chat_agent(question: str) -> ChatAgentResult:
    """
    Ejecuta el agente conversacional con tool-calling (loop ReAct).

    1. El LLM recibe la pregunta y las herramientas disponibles
    2. Decide qué herramientas invocar y con qué argumentos
    3. Se ejecutan las herramientas y los resultados se añaden al contexto
    4. El LLM sintetiza una respuesta final usando los datos reales
    5. Se repite hasta obtener respuesta o alcanzar MAX_ITERATIONS
    """
    logger.info(f"Chat agent iniciado: '{question[:80]}'")

    client = AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        timeout=60.0,
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    tools_called = []
    evidence = []
    iterations = 0

    for i in range(MAX_ITERATIONS):
        iterations = i + 1
        logger.info(f"Chat agent iteración {iterations}/{MAX_ITERATIONS}")

        try:
            response = await client.chat.completions.create(
                model=settings.openai_model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                parallel_tool_calls=False,
            )
        except BadRequestError as e:
            error_body = getattr(e, "body", {}) or {}
            if isinstance(error_body, dict) and error_body.get("code") == "tool_use_failed":
                logger.warning(
                    f"Iteración {iterations}: tool_use_failed (el modelo generó un tool call "
                    f"en formato incorrecto). Reintentando sin herramientas."
                )
                fallback_messages = messages + [{
                    "role": "user",
                    "content": (
                        "Responde a la pregunta original con la información disponible. "
                        "Si no tienes datos suficientes, indícalo claramente."
                    ),
                }]
                fallback = await client.chat.completions.create(
                    model=settings.openai_model,
                    messages=fallback_messages,
                )
                return ChatAgentResult(
                    answer=fallback.choices[0].message.content or "No se pudo generar respuesta.",
                    tools_called=tools_called,
                    evidence=evidence,
                    iterations=iterations,
                )
            raise

        msg = response.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))

        # Sin tool_calls → el LLM tiene suficiente información para responder
        if not msg.tool_calls:
            logger.info(f"Chat agent completado en {iterations} iteración(es), tools: {[t['tool'] for t in tools_called]}")
            return ChatAgentResult(
                answer=msg.content or "Sin respuesta.",
                tools_called=tools_called,
                evidence=evidence,
                iterations=iterations,
            )

        # Ejecutar cada tool call y añadir resultado al historial
        for tool_call in msg.tool_calls:
            name = tool_call.function.name
            try:
                args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                args = {}

            logger.info(f"  Tool call: {name}({args})")
            result = await _execute_tool(name, args)
            tools_called.append({"tool": name, "args": args})

            # Recoger evidencias de búsquedas semánticas para mostrar en el frontend
            if name == "search_feedback" and isinstance(result, dict):
                for r in result.get("results", []):
                    if r.get("text"):
                        evidence.append(r)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False),
            })

    # Límite alcanzado: forzar respuesta final sin más tool calls
    logger.warning("Chat agent alcanzó el límite de iteraciones, forzando respuesta final")
    messages.append({
        "role": "user",
        "content": "Con los datos que has recopilado, responde la pregunta original de forma concisa.",
    })
    final = await client.chat.completions.create(
        model=settings.openai_model,
        messages=messages,
    )
    return ChatAgentResult(
        answer=final.choices[0].message.content or "No se pudo generar respuesta.",
        tools_called=tools_called,
        evidence=evidence,
        iterations=iterations,
    )
