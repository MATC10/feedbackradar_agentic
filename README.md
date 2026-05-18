# FeedbackRadar Agentic

**FeedbackRadar Agentic** es un copiloto de producto basado en agentes que analiza feedback multicanal de clientes, detecta los principales problemas, los justifica con evidencia semantica real y genera un informe ejecutivo con recomendaciones priorizadas para tomar mejores decisiones de negocio.

---

## Stack tecnologico

| Capa | Tecnologia |
|------|-----------|
| Backend API | FastAPI + Uvicorn |
| Orquestacion de agentes | LangGraph |
| Chat LLM | Groq API (`llama-3.3-70b-versatile`) |
| Embeddings | Ollama local (`nomic-embed-text`) |
| MCP Tools internos | FastMCP |
| MCP Tools externos | `mcp` SDK + `mcp-atlassian` v0.21 |
| Integracion Jira | mcp-atlassian (servidor MCP externo via stdio) |
| Base de datos documental | MongoDB |
| Base de datos vectorial | Elasticsearch |
| Frontend demo | Streamlit |
| Infraestructura | Docker Compose |
| Validacion | Pydantic |

---

## Estado del proyecto

| Fase | Descripcion | Estado |
|------|-------------|--------|
| 1 | Estructura base del proyecto | Completada |
| 2 | Ingesta de CSVs y persistencia en MongoDB | Completada |
| 3 | Embeddings con Ollama e indexacion en Elasticsearch | Completada |
| 4 | MCP Tools con FastMCP | Completada |
| 5 | API REST con FastAPI | Completada |
| 6 | Agentes LangGraph + resumen ejecutivo | Completada |
| 7 | Frontend Streamlit | Completada |
| 8 | Integracion Jira via MCP (mcp-atlassian) | Completada |
| 9 | Gmail Collector con ingesta automatica a MongoDB + Elasticsearch | Completada |
| 10 | Deduplicacion de insights y temas (textual + semantica via LLM) | Completada |
| 11 | Chat agente conversacional con tool-calling (ReAct loop) | Completada |

---

## Arrancar el proyecto

### 1. Levantar servicios Docker

```bash
docker-compose up -d
docker-compose ps   # verificar que esten healthy
```

Servicios que levanta:
- **MongoDB** en `localhost:27017`
- **Elasticsearch** en `localhost:9200`
- **Ollama** en `localhost:11435` (para embeddings)

### 2. Descargar modelo de embeddings

```bash
docker exec -it feedbackradar_ollama ollama pull nomic-embed-text
```

### 3. Configurar entorno Python

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

pip install -r requirements.txt
copy .env.example .env
```

Editar `.env` con las claves necesarias (ver seccion Configuracion).

### 4. Arrancar la API

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

La API esta lista cuando los logs muestran:
```
[OK] MongoDB conectado
[OK] Elasticsearch conectado
Aplicacion iniciada correctamente
```

Documentacion interactiva: http://localhost:8000/docs

### 5. Arrancar el frontend Streamlit

```bash
venv\Scripts\streamlit run frontend\streamlit_app.py --server.port 8501
```

Frontend disponible en: http://localhost:8501

---

## Configuracion

Variables clave en `.env`:

```env
# LLM para agentes - Groq (rapido, recomendado)
CHAT_LLM_PROVIDER=openai
OPENAI_API_KEY=gsk_...
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL=llama-3.3-70b-versatile

# Embeddings - Ollama local (no requiere API key)
OLLAMA_BASE_URL=http://localhost:11435
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Bases de datos
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=feedbackradar
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_INDEX=feedback

# Jira MCP Integration (mcp-atlassian)
JIRA_MCP_ENABLED=true
JIRA_BASE_URL=https://yourcompany.atlassian.net
JIRA_USER_EMAIL=user@company.com
JIRA_API_TOKEN=your-jira-api-token
JIRA_PROJECT_KEY=KAN
JIRA_DEFAULT_ISSUE_TYPE=Task
JIRA_PRIORITY_CRITICA=Highest
JIRA_PRIORITY_ALTA=High
JIRA_DEDUP_DAYS=7
```

Para usar Ollama como chat LLM en lugar de Groq (mas lento, sin coste de API):
```env
CHAT_LLM_PROVIDER=ollama
OLLAMA_CHAT_MODEL=llama3.2
```

Para desactivar la integracion Jira:
```env
JIRA_MCP_ENABLED=false
```

---

## Endpoints de la API

### Feedback

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| `POST` | `/feedback/upload` | Subir uno o varios CSV de feedback |

**Ejemplo:**
```bash
curl -X POST "http://localhost:8000/feedback/upload" \
  -F "files=@data/raw/feedback.csv"
```

**Respuesta:**
```json
{
  "success": true,
  "total_rows": 100,
  "inserted_rows": 100,
  "indexed_rows": 100,
  "errors": []
}
```

### Analisis

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| `POST` | `/analysis/run` | Ejecutar workflow completo de analisis |
| `GET` | `/analysis/insights` | Listar insights generados |
| `GET` | `/analysis/actions` | Listar acciones generadas |

### Chat

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| `POST` | `/chat/ask` | Consulta en lenguaje natural sobre el feedback (agente ReAct con tool-calling) |

**Ejemplo:**
```bash
curl -X POST "http://localhost:8000/chat/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Compara los problemas de pago con los de rendimiento"}'
```

**Respuesta:**
```json
{
  "answer": "Los problemas de pago afectan a 18 clientes (18.2% del total), mientras que los de rendimiento afectan a 11 (11.1%)...",
  "evidence": [
    {"text": "El pago falla constantemente", "platform": "App", "score": 0.94},
    {"text": "La app va muy lenta", "platform": "Google Play", "score": 0.89}
  ],
  "tools_called": [
    {"tool": "get_feedback_stats", "args": {"theme": "pago"}},
    {"tool": "get_feedback_stats", "args": {"theme": "rendimiento"}},
    {"tool": "search_feedback", "args": {"query": "problemas pago rendimiento", "top_k": 8}}
  ],
  "iterations": 2
}
```

**Ejemplo de analisis:**
```bash
curl -X POST "http://localhost:8000/analysis/run" \
  -H "Content-Type: application/json" \
  -d '{"limit": 100}'
```

**Respuesta completa:**
```json
{
  "success": true,
  "feedback_analyzed": 100,
  "themes_detected": 5,
  "evidence_count": 50,
  "themes_prioritized": 5,
  "recommendations_generated": 5,
  "actions_created": 5,
  "insights_created": 5,
  "jira_issues_created": [
    {
      "theme": "Fallas en el proceso de pago",
      "key": "KAN-1",
      "url": "https://yourcompany.atlassian.net/browse/KAN-1",
      "priority": "Critica",
      "reused": false
    },
    {
      "theme": "Metodos de pago y opciones",
      "key": "KAN-2",
      "url": "https://yourcompany.atlassian.net/browse/KAN-2",
      "priority": "Alta",
      "reused": false
    }
  ],
  "executive_summary": {
    "narrative": "El principal foco de frustracion esta en el proceso de pago...",
    "overall_sentiment": "Negativo",
    "top_themes": [
      "Fallas en el proceso de pago - 18.2% de afectacion, prioridad: Critica",
      "Metodos de pago - 14.2% de afectacion, prioridad: Alta"
    ],
    "urgent_problems": ["..."],
    "feature_requests": ["..."],
    "representative_examples": ["..."],
    "product_recommendations": ["..."]
  },
  "errors": [],
  "execution_time_seconds": 36.0
}
```

### Sistema

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| `GET` | `/health` | Estado de MongoDB y Elasticsearch |

---

## RAG — Retrieval-Augmented Generation

FeedbackRadar utiliza un pipeline RAG para que el LLM nunca "invente" evidencias: toda conclusion
esta respaldada por fragmentos reales del feedback indexado.

### Como funciona el RAG

```
FASE 1 — INDEXACION (al subir feedback)
─────────────────────────────────────────────────────────────────
CSV / Gmail
    │
    ▼
IngestionService
    ├─► MongoDB          ← datos originales (texto, fecha, plataforma)
    │
    └─► OllamaEmbeddingService
            │  modelo: nomic-embed-text (768 dimensiones)
            ▼
        Elasticsearch  ← campo dense_vector con similitud coseno
            índice: feedback
            campos: feedback_id, text, platform, date, embedding

FASE 2 — RECUPERACION (al analizar o chatear)
─────────────────────────────────────────────────────────────────
Query en lenguaje natural
    │
    ▼
OllamaEmbeddingService.embed_text(query)
    │  → vector de 768 dimensiones
    ▼
ElasticsearchClient.semantic_search()
    │  → kNN aproximado (cosine), top_k candidatos × 2
    ▼
Lista de fragmentos de feedback reales con score de similitud

FASE 3 — GENERACION AUMENTADA
─────────────────────────────────────────────────────────────────
Fragmentos recuperados  +  contexto del analisis
    │
    ▼
LLM (Groq / llama-3.3-70b-versatile)
    │
    ▼
Insights, prioridades y recomendaciones fundamentadas en evidencia real
```

### Donde se aplica el RAG en el sistema

| Punto de uso | Agente / componente | Descripcion |
|---|---|---|
| Analisis de temas | Evidence Retrieval Agent (agente 2) | Para cada tema detectado, genera una query, recupera los 10 fragmentos mas similares y los pasa como evidencia a los agentes posteriores |
| Priorizacion | Prioritization Agent (agente 3) | Recibe las evidencias del agente 2 y las usa para justificar la prioridad asignada (Critica / Alta / Media / Baja) |
| Chat conversacional | `search_feedback` tool (chat_agent.py) | El LLM invoca esta tool en el loop ReAct para recuperar fragmentos relevantes antes de formular su respuesta |

### Detalle tecnico del indice vectorial

| Parametro | Valor |
|---|---|
| Modelo de embeddings | `nomic-embed-text` (Ollama local) |
| Dimension del vector | 768 |
| Metrica de similitud | Coseno |
| Motor de busqueda | Elasticsearch `dense_vector` + kNN nativo |
| Candidatos kNN | `top_k × 2` (HNSW aproximado) |
| Filtro opcional | Por plataforma (`platform_filter`) |

### Configuracion relevante

```env
# Servicio de embeddings (local, sin coste de API)
OLLAMA_BASE_URL=http://localhost:11435
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Indice vectorial
ELASTICSEARCH_URL=http://localhost:9200
ELASTICSEARCH_INDEX=feedback
```

> El modelo `nomic-embed-text` se descarga una sola vez con:
> `docker exec -it feedbackradar_ollama ollama pull nomic-embed-text`

---

## Agente conversacional (Chat)

El endpoint `/chat/ask` utiliza un agente ReAct con tool-calling nativo de Groq/OpenAI.
El LLM decide iterativamente que herramientas invocar hasta tener suficiente informacion para responder.

```
Pregunta del usuario
        |
        v
[LLM] Decide que tools invocar
        |
        v
[Tools] search_feedback / get_feedback_stats / get_recent_feedback / get_insights
        |
        v
[LLM] Analiza resultados — ¿necesita mas datos?
        |   |
      Si    No → Respuesta final fundamentada en datos reales
        |
        v
[Tools] Mas llamadas si es necesario (max 6 iteraciones)
```

**Tools disponibles para el agente:**

| Tool | Descripcion |
|------|-------------|
| `search_feedback` | Busqueda semantica de fragmentos de feedback por tema |
| `get_feedback_stats` | Estadisticas numericas de cuantos clientes mencionan un tema |
| `get_recent_feedback` | Feedback de los ultimos N dias |
| `get_insights` | Insights analizados previamente con prioridades y resumenes |

Esto permite responder preguntas comparativas como:
- "Compara los problemas de pago con los de rendimiento, ¿cual tiene mas impacto?"
- "¿Cuantas menciones de login hubo este mes?"
- "¿En que plataforma se concentra mas el problema de rendimiento?"

---

## Workflow de agentes

El analisis se ejecuta como un grafo secuencial de 7 agentes (LangGraph):

```
Feedback en MongoDB
        |
        v
[1] Theme Discovery Agent
    Detecta 3-7 temas recurrentes en el feedback usando LLM
        |
        v
[2] Evidence Retrieval Agent
    Busqueda semantica de evidencias reales por tema (Ollama + Elasticsearch)
        |
        v
[3] Prioritization Agent
    Asigna prioridad (Critica/Alta/Media/Baja) a cada tema con estadisticas + LLM
        |
        v
[4] Recommendation Agent
    Genera recomendacion accionable y titulo de accion por tema
        |
        v
[5] Persistence Agent
    Guarda insights y acciones en MongoDB via MCP tools
        |
        v
[6] Jira Action Agent
    Crea issues en Jira (via mcp-atlassian) para temas con prioridad Critica o Alta
    Deduplicacion: no crea duplicados para el mismo tema en los ultimos 7 dias
        |
        v
[7] Summary Agent
    Genera resumen ejecutivo: narrativa, sentimiento, top temas,
    problemas urgentes, features solicitadas, ejemplos textuales,
    recomendaciones de producto
        |
        v
AnalysisResponse (JSON con jira_issues_created)
```

**Tiempo de ejecucion**: ~30-40 segundos con Groq para 100 feedbacks (incluye llamadas Jira MCP).

---

## Formato de CSV de entrada

El endpoint `/feedback/upload` acepta CSV con estas columnas:

```csv
nombre,fecha,resena,plataforma
Juan Garcia,2024-01-15,El pago falla constantemente,App
Maria Lopez,2024-01-16,No encuentro mis facturas,Web
```

Columnas requeridas: texto del feedback y plataforma.  
La fecha admite multiples formatos (`DD/MM/YYYY`, `YYYY-MM-DD`, etc.).

---

## MCP Tools disponibles

### Tools propios (FastMCP — `app/mcp/server.py`)

El sistema expone 5 herramientas via FastMCP para agentes externos:

| Tool | Descripcion |
|------|-------------|
| `search_feedback` | Busqueda semantica de feedback por query |
| `get_feedback_stats` | Estadisticas de feedback relacionado con un tema |
| `get_recent_feedback` | Feedback de los ultimos N dias |
| `save_insight` | Guarda un insight en MongoDB |
| `create_action_item` | Crea una accion en MongoDB |

Arrancar el servidor MCP propio:
```bash
python -m app.mcp.server
```

### Servidor MCP externo: mcp-atlassian (Jira)

El agente Jira se conecta como **cliente MCP** al servidor `mcp-atlassian` via protocolo stdio.
No requiere configuracion adicional: el binario `mcp-atlassian` se instala con `pip install mcp-atlassian`
y el cliente (`app/mcp/jira_mcp_client.py`) lo lanza automaticamente como subproceso.

Tool utilizada:

| Tool MCP | Descripcion |
|----------|-------------|
| `jira_create_issue` | Crea una issue en el proyecto Jira configurado |

Parametros que se envian: `project_key`, `summary`, `issue_type`, `description` (Markdown),
`additional_fields` (JSON con `priority` y `labels`).

---

## Gmail Collector

FeedbackRadar incluye un colector de feedback desde Gmail que se activa automaticamente al arrancar la app. Cada minuto (configurable) busca emails nuevos, los escribe en CSV y los ingesta en MongoDB + Elasticsearch sin intervencion manual.

### Flujo completo

```
Al arrancar FastAPI (si GMAIL_MCP_POLLING_ENABLED=true):
    cada GMAIL_MCP_POLL_INTERVAL_SECONDS segundos:
        Gmail API → filtra por subject:notausuario
                  → escribe solo emails NUEVOS en data/raw/gmail_notausuario.csv
                    (deduplicacion via .ids)
                  → ingesta directa a MongoDB + Elasticsearch (embeddings Ollama)
```

### Configuracion en `.env`

```env
# Activar el poller
GMAIL_MCP_POLLING_ENABLED=true
GMAIL_MCP_POLL_INTERVAL_SECONDS=60

# Filtro de emails: busca en Gmail "subject:<valor>"
# Para revertir a otro filtro, cambiar este valor
GMAIL_MCP_SUBJECT_FILTER=notausuario

# Modo de acceso a Gmail
# true  = Gmail API directa (gmail.googleapis.com) — recomendado
# false = Gmail Remote MCP Server (gmailmcp.googleapis.com) — requiere app publicada en Google
GMAIL_USE_DIRECT_API=true

# CSV de auditoria (los emails nuevos tambien se ingestan automaticamente)
GMAIL_MCP_OUTPUT_CSV=data/raw/gmail_notausuario.csv

# Anthropic (requerido aunque GMAIL_USE_DIRECT_API=true)
ANTHROPIC_API_KEY=sk-ant-...
```

### Credenciales OAuth de Google

1. Crear cliente OAuth en Google Cloud Console → tipo **Web application**
2. Redirect URI: `http://localhost:8080`
3. Descargar JSON → guardar como `credentials_web.json` en la raiz del proyecto
4. Al arrancar la app por primera vez, se abre el navegador para autenticarse
5. El token se guarda en `token.json` y se refresca automaticamente

> `credentials.json` (Desktop App) se mantiene como fallback pero el Gmail Remote MCP Server requiere Web Application.

---

## Tests

```bash
# Ejecutar todos los tests
python -m pytest -v

# Solo un agente
python -m pytest tests/test_theme_agent.py -v
```

51 tests unitarios pasan. Usan mocks, no requieren servicios levantados.

---

## Estructura del proyecto

```
feedbackradar_agentic/
├── app/
│   ├── agents/
│   │   ├── graph.py               # Grafo LangGraph (7 nodos)
│   │   ├── state.py               # AgentState compartido
│   │   ├── theme_agent.py         # [1] Deteccion de temas
│   │   ├── evidence_agent.py      # [2] Recuperacion de evidencias
│   │   ├── prioritization_agent.py # [3] Priorizacion
│   │   ├── recommendation_agent.py # [4] Recomendaciones
│   │   ├── persistence_agent.py   # [5] Persistencia MongoDB
│   │   ├── jira_action_agent.py   # [6] Creacion de issues en Jira via MCP
│   │   ├── summary_agent.py       # [7] Resumen ejecutivo
│   │   └── chat_agent.py          # Agente conversacional ReAct con tool-calling
│   ├── api/             # Rutas FastAPI (feedback, analysis, chat)
│   ├── core/            # Configuracion (Pydantic Settings)
│   ├── databases/       # Clientes MongoDB y Elasticsearch + repositorios
│   ├── embeddings/      # Servicio de embeddings Ollama
│   ├── ingestion/       # Lectura y normalizacion de CSV
│   ├── integrations/    # Gmail MCP collector (Anthropic)
│   ├── llm/             # Clientes LLM (Groq/OpenAI-compatible, Ollama) + factory
│   ├── mcp/
│   │   ├── tools.py               # MCP tools propios (FastMCP)
│   │   ├── server.py              # Servidor MCP propio
│   │   └── jira_mcp_client.py     # Cliente MCP para mcp-atlassian (Jira)
│   ├── schemas/         # Modelos Pydantic (feedback, insight, action, analysis)
│   └── main.py          # Inicializacion de FastAPI y lifecycle
├── frontend/
│   └── streamlit_app.py # Frontend Streamlit (5 paginas: Dashboard, Subir CSV, Analisis, Insights, Consultar)
├── tests/               # Suite de tests pytest
├── data/raw/            # CSV de ejemplo
├── docker-compose.yml   # MongoDB + Elasticsearch + Ollama
├── .env.example         # Plantilla de configuracion
└── requirements.txt     # Dependencias Python
```
