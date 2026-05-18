# Estado Actual del Proyecto

**Fecha**: 2026-05-14  
**Estado**: PROYECTO TERMINADO — BACKEND + FRONTEND + JIRA MCP + GMAIL COLLECTOR + CHAT AGENTE OPERATIVOS

---

## Resultado de validacion E2E (ultima ejecucion)

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
    {"theme": "Fallas en el proceso de pago", "key": "KAN-1", "url": "https://tu_url_jira.atlassian.net/browse/KAN-1", "priority": "Critica", "reused": false},
    {"theme": "Metodos de pago y opciones de personalizacion", "key": "KAN-2", "url": "https://tu_url_jira.atlassian.net/browse/KAN-2", "priority": "Alta", "reused": false}
  ],
  "executive_summary": {
    "narrative": "...",
    "overall_sentiment": "Negativo",
    "top_themes": ["Fallas en el proceso de pago - 18.2% de afectacion, prioridad: Critica", "..."],
    "urgent_problems": ["..."],
    "feature_requests": ["..."],
    "representative_examples": ["..."],
    "product_recommendations": ["..."]
  },
  "errors": [],
  "execution_time_seconds": 36.0
}
```

Tiempo de ejecucion con Groq: **~30-40 segundos** para 100 feedbacks (incluye llamadas MCP a Jira).

---

## Como arrancar

```bash
# 1. Servicios Docker (MongoDB, Elasticsearch, Ollama para embeddings)
docker-compose up -d

# 2. FastAPI en puerto 8000
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 3. Frontend Streamlit en puerto 8501
venv\Scripts\streamlit run frontend\streamlit_app.py --server.port 8501
```

> El entorno virtual `venv/` esta creado en la raiz del proyecto con todas las
> dependencias de `requirements.txt` instaladas.

---

## Proveedor LLM activo: Groq

| Variable | Valor |
|----------|-------|
| `CHAT_LLM_PROVIDER` | `openai` |
| `OPENAI_BASE_URL` | `https://api.groq.com/openai/v1` |
| `OPENAI_MODEL` | `llama-3.3-70b-versatile` |

Los embeddings siguen usando Ollama local con `nomic-embed-text`.

Para volver a Ollama como LLM de chat: `CHAT_LLM_PROVIDER=ollama`

---

## Workflow implementado (7 agentes de analisis)

```
[1] Theme Discovery    → detecta 3-7 temas con LLM
[2] Evidence Retrieval → busqueda semantica via Ollama + Elasticsearch (top_k=10)
[3] Prioritization     → asigna Critica/Alta/Media/Baja con stats de keywords + LLM
[4] Recommendation     → genera recomendacion accionable por tema
[5] Persistence        → guarda insights y acciones en MongoDB via MCP tools
[6] Jira Action        → crea issues en Jira via mcp-atlassian (MCP externo stdio)
                         solo temas Critica/Alta, con deduplicacion de 7 dias
[7] Summary            → resumen ejecutivo completo con LLM
```

## Agente conversacional (chat_agent.py)

Agente ReAct con tool-calling nativo (Groq/OpenAI function calling). Loop de hasta 6 iteraciones.

```
Pregunta usuario → LLM decide tools → ejecuta tools → LLM sintetiza → Respuesta
```

**Tools disponibles:**

| Tool | Descripcion |
|------|-------------|
| `search_feedback` | Busqueda semantica de fragmentos de feedback |
| `get_feedback_stats` | Estadisticas numericas por tema (ideal para comparaciones) |
| `get_recent_feedback` | Feedback de los ultimos N dias |
| `get_insights` | Insights y prioridades del ultimo analisis |

**Endpoint:** `POST /chat/ask` — devuelve `answer`, `evidence`, `tools_called`, `iterations`

**Pagina frontend:** "Consultar" (5a pagina del Streamlit) con historial de chat, evidencias expandibles e indicador de tools usadas por el agente.

---

## Endpoints disponibles

| Metodo | Ruta | Estado |
|--------|------|--------|
| `GET` | `/health` | Operativo |
| `POST` | `/feedback/upload` | Operativo |
| `POST` | `/analysis/run` | Operativo |
| `GET` | `/analysis/insights` | Operativo |
| `GET` | `/analysis/actions` | Operativo |
| `POST` | `/chat/ask` | Operativo |
| `GET` | `/feedback/stats` | TODO (devuelve stub) |

---

## Campos del resumen ejecutivo (`executive_summary`)

El campo `executive_summary` en la respuesta de `/analysis/run` contiene:

| Campo | Tipo | Descripcion |
|-------|------|-------------|
| `narrative` | string | Parrafo narrativo de 2-3 frases con datos concretos |
| `overall_sentiment` | string | `Negativo`, `Mixto` o `Positivo` |
| `top_themes` | lista | Top 5 temas recurrentes con frecuencia estimada |
| `urgent_problems` | lista | Problemas criticos que requieren atencion inmediata |
| `feature_requests` | lista | Features o mejoras solicitadas por usuarios |
| `representative_examples` | lista | 3-5 citas textuales reales del feedback |
| `product_recommendations` | lista | Recomendaciones accionables para el equipo de producto |

---

## Cambios aplicados durante el desarrollo

### 1. Correccion de encoding Windows (logs con emojis)

**Problema**: Los emojis en logs (`✅`, `❌`, `🔧`) causaban `UnicodeEncodeError` en la consola
Windows. El error se confundia con un fallo de conexion a MongoDB.

**Archivos**: [app/main.py](app/main.py), [app/databases/mongodb_client.py](app/databases/mongodb_client.py)  
**Solucion**: Emojis reemplazados por `[OK]` / `[ERROR]`

---

### 2. Bug: `insights_created` siempre devolia 0

**Problema**: El agente de persistencia guardaba los IDs de insights en `state["metadata"]["insights_created"]`,
un campo fuera del `TypedDict` de LangGraph que no se propagaba correctamente.

**Archivos**: [app/agents/state.py](app/agents/state.py), [app/agents/persistence_agent.py](app/agents/persistence_agent.py), [app/agents/graph.py](app/agents/graph.py)  
**Solucion**: Campo `insights_created: List[str]` anadido al `AgentState` y al estado inicial.
El agente ahora escribe directamente en `state["insights_created"]`.

---

### 3. Migracion de LLM: Ollama CPU → Groq API

**Problema**: Ollama corriendo en CPU local tardaba ~50s por llamada LLM (9 min por workflow completo).

**Archivos**: [.env](.env), [app/llm/openai_chat_client.py](app/llm/openai_chat_client.py)  
**Solucion**:
- `.env` actualizado con Groq: `CHAT_LLM_PROVIDER=openai`, key de Groq, URL y modelo
- `OpenAIChatClient` modificado para que los headers personalizados sean opcionales
  (antes se enviaban siempre `provider`/`origin`/`origin-detail` aunque estuvieran vacios,
  causando rechazo por parte de la API de Groq)

---

### 4. Nuevo agente: Summary Agent (6o agente del workflow)

**Motivacion**: El workflow detectaba temas y generaba acciones, pero no producia un informe
ejecutivo legible. Se anadio un sexto agente que sintetiza todos los resultados.

**Archivos nuevos**: [app/agents/summary_agent.py](app/agents/summary_agent.py)  
**Archivos modificados**: [app/agents/state.py](app/agents/state.py), [app/agents/graph.py](app/agents/graph.py),
[app/agents/\_\_init\_\_.py](app/agents/__init__.py), [app/api/analysis_routes.py](app/api/analysis_routes.py)

**Cambios en el estado**:
- `executive_summary: str` cambiado a `executive_summary: Dict[str, Any]`
- Inicializado como `{}` en `create_initial_state`

**Salida del agente**: JSON estructurado con 7 campos (narrative, overall_sentiment, top_themes,
urgent_problems, feature_requests, representative_examples, product_recommendations).

---

## Frontend Streamlit (Completado, v5)

**Archivo**: `frontend/streamlit_app.py`  
**URL**: http://localhost:8501

### Paginas disponibles

| Pagina | Descripcion |
|--------|-------------|
| Dashboard | Hub con 4 tarjetas para navegar a Subir CSV, Ejecutar Analisis, Insights y Consultar |
| Subir CSV | Upload multi-fichero con tab de formato esperado, toggle de embeddings, metricas por archivo |
| Ejecutar Analisis | Pipeline de 7 agentes visualizado, formulario limit/days, barra de progreso animada, resultados en tabs (Resumen ejecutivo / Tickets Jira) con acceso rapido a Insights |
| Insights | Lista filtrable por prioridad, deduplicada (un tema por nombre), conteo de badges, evidencias expandibles |
| Consultar | Chat con el agente ReAct: historial de mensajes, evidencias expandibles bajo cada respuesta, caption con tools usadas e iteraciones del agente, boton de limpiar conversacion |

> La pagina Acciones fue eliminada: las acciones se gestionan directamente en Jira.

### Diseno

- Navegacion lateral con **enlaces HTML puros** (`<a href="?nav=X">`), sin radio buttons ni st.button; pagina activa destacada en azul via CSS
- La pagina activa se determina del query param `?nav=` en la URL; `go_to()` actualiza query param y session state
- Badges de color por prioridad (Critica rojo, Alta naranja, Media amarillo, Baja verde)
- Los badges HTML se renderizan DENTRO de los expanders; los titulos de expander usan emoji + texto plano
- Health check del backend con comparacion correcta (`== "ok"`) contra la respuesta real de `/health`
- URL del backend configurable desde el sidebar, almacenada en `st.session_state`
- Resultados del analisis persistidos en `st.session_state["analysis_result"]` — sobreviven reruns de Streamlit
- Barra de progreso simulada sincronizada con los 7 agentes (~30-40 s con Groq + Jira)
- Tickets Jira con enlace clickable, badge de prioridad y etiqueta Nuevo / Reutilizado

### Bugs corregidos

| Bug | Causa | Solucion |
|-----|-------|----------|
| MongoDB/Elastic mostraban "Sin conexion" estando activos | `/health` devuelve `"ok"` pero el codigo comparaba con `"connected"` | Cambiado a `== "ok"` |
| HTML crudo visible en titulos de expanders | `st.expander()` no renderiza HTML en su label | Titulos usan emoji + texto plano; badges HTML van dentro del expander |
| Resultados del analisis desaparecian al pulsar cualquier boton | Variables locales se resetean en cada rerun de Streamlit | Resultado guardado en `st.session_state["analysis_result"]` |
| `st.session_state has no attribute api_url` al ejecutar analisis | `st.session_state` no es accesible desde hilos secundarios | URL capturada en variable local antes de crear el thread |
| Nav lateral se expandia/colapsaba al clicar | `st.button` tiene estado visual activo/pulsado | Reemplazado por enlaces HTML con query params |

---

## Integracion Jira MCP (Fase 8 — Completada)

**Servidor externo**: `mcp-atlassian` v0.21.1 (ejecutado como subproceso stdio)  
**Cliente**: `app/mcp/jira_mcp_client.py` (Python MCP SDK v1.27)  
**Agente**: `app/agents/jira_action_agent.py` (7o agente del grafo)

### Variables de entorno necesarias

| Variable | Descripcion |
|----------|-------------|
| `JIRA_MCP_ENABLED` | `true` para activar, `false` para omitir el agente |
| `JIRA_BASE_URL` | URL base de Jira Cloud (ej: `https://empresa.atlassian.net`) |
| `JIRA_USER_EMAIL` | Email de la cuenta Atlassian |
| `JIRA_API_TOKEN` | Token generado en `id.atlassian.com > Security > API tokens` |
| `JIRA_PROJECT_KEY` | Clave del proyecto (ej: `KAN`) |
| `JIRA_DEFAULT_ISSUE_TYPE` | Tipo de issue (por defecto: `Task`) |
| `JIRA_PRIORITY_CRITICA` | Prioridad Jira para temas Critica (por defecto: `Highest`) |
| `JIRA_PRIORITY_ALTA` | Prioridad Jira para temas Alta (por defecto: `High`) |
| `JIRA_DEDUP_DAYS` | Dias de ventana anti-duplicados (por defecto: `7`) |

### Criterio de creacion de tickets

- Solo temas con prioridad `Critica` o `Alta`
- Solo si existe recomendacion asociada
- Deduplicacion nivel 1: mismo `action_id` ya procesado → skip
- Deduplicacion nivel 2: mismo tema con ticket creado en los ultimos N dias → reutiliza clave
  - La comparacion usa `theme_name_normalized` (minusculas, sin tildes, solo alfanumerico)
  - Tolera variaciones del LLM: "Problemas de Pago" y "problemas de pago" se tratan como el mismo tema

### Campos del ticket Jira creado

- **summary**: `[FeedbackRadar] {titulo de la recomendacion}`
- **issue_type**: `Task` (configurable)
- **priority**: `Highest` / `High` segun mapeo
- **labels**: `feedbackradar`, `automated`
- **description**: Markdown con tema, descripcion, recomendacion, evidencias y metadatos

---

## Gmail Collector (Fase 9 — Completada)

### Como funciona

El poller se activa al arrancar la app si `GMAIL_MCP_POLLING_ENABLED=true`. Cada `GMAIL_MCP_POLL_INTERVAL_SECONDS` segundos ejecuta el ciclo completo:

```
Gmail API (gmail.googleapis.com)
    → filtra emails: subject:notausuario  (configurable con GMAIL_MCP_SUBJECT_FILTER)
    → escribe solo los NUEVOS en data/raw/gmail_notausuario.csv
      (deduplicacion via gmail_notausuario.csv.ids)
    → llama a IngestionService con los emails nuevos
        → MongoDB  (datos originales)
        → Elasticsearch  (datos + embeddings via Ollama/nomic-embed-text)
```

### Variables de entorno necesarias

| Variable | Valor actual | Descripcion |
|----------|-------------|-------------|
| `GMAIL_MCP_POLLING_ENABLED` | `true` | Activa el poller al arrancar |
| `GMAIL_MCP_POLL_INTERVAL_SECONDS` | `60` | Intervalo entre ciclos |
| `GMAIL_MCP_SUBJECT_FILTER` | `notausuario` | Filtro de asunto Gmail (`subject:<valor>`) |
| `GMAIL_MCP_OUTPUT_CSV` | `data/raw/gmail_notausuario.csv` | CSV de auditoria |
| `GMAIL_USE_DIRECT_API` | `true` | `true` = Gmail API directa; `false` = MCP server Google |
| `ANTHROPIC_API_KEY` | configurada | Requerida aunque `GMAIL_USE_DIRECT_API=true` |

### Credenciales OAuth

Requiere `credentials_web.json` en la raiz del proyecto (tipo **Web Application** de Google Cloud Console, redirect URI `http://localhost:8080`). El token se guarda en `token.json` y se refresca automaticamente.

> `credentials.json` (Desktop App) se mantiene como fallback pero **no funciona** con el Gmail Remote MCP Server.

### Revertir a MCP Server de Google

Cambiar en `.env`:
```env
GMAIL_USE_DIRECT_API=false
```
El codigo MCP original se preserva en `_fetch_via_mcp()` dentro de `anthropic_gmail_client.py`.

---

## Mejoras de deduplicacion de insights (implementadas)

### Problema
Cada ejecucion del analisis creaba insights nuevos para los mismos temas sin comprobar si ya existian.
El LLM genera nombres ligeramente distintos cada vez ("Rendimiento y velocidad", "Lentitud y cargas",
"Problemas de rendimiento") que el sistema trataba como temas distintos. Resultado: 91 insights
acumulados para ~10 temas reales.

### Soluciones implementadas

**1. Deduplicacion en lectura — `GET /analysis/insights`**  
El endpoint llama a `InsightRepository.find_latest_per_theme()` que:
- Trae todos los insights ordenados del mas reciente al mas antiguo
- Agrupa por `_normalize_theme(theme)` (minusculas, sin tildes, solo alfanumerico)
- Devuelve solo el insight mas reciente por tema normalizado
- El historico en MongoDB se preserva intacto

**2. Deduplicacion en escritura — `ActionRepository.find_recent_jira_by_theme()`**  
Usa el campo `theme_name_normalized` para comparar temas al buscar tickets Jira existentes.
`update_jira_fields()` guarda tanto `theme_name` (original) como `theme_name_normalized` (para busqueda).

**3. Contexto de temas existentes en el Theme Agent**  
Antes de llamar al LLM, `discover_themes()` consulta `InsightRepository.find_latest_per_theme()`
e inyecta los nombres de temas existentes en el prompt:
> "Si detectas un tema igual o muy similar a alguno de los anteriores, usa EXACTAMENTE el mismo nombre."

Esto hace que el LLM reutilice nombres estables en lugar de inventar variantes.

**4. Limpieza inicial de la BD**  
Se ejecuto un script de limpieza en dos pasadas (dedup textual + dedup semantico via LLM)
que redujo los insights de **91 a 11** temas unicos. Los 11 temas actuales son:

| Tema | Prioridad |
|------|-----------|
| Dificultad para descargar la factura | Critica |
| Diseño y funcionalidad de la aplicacion | Alta |
| Estimacion de tiempos de entrega y comunicacion | Baja |
| Experiencia de checkout | Critica |
| Experiencia general y satisfaccion | Baja |
| Login y autenticacion | Alta |
| Mejoras y Sugerencias | Baja |
| Problemas de pago y comprobacion | Critica |
| Problemas en dispositivo movil | Critica |
| Rendimiento y velocidad | Alta |
| Variedad de opciones y calidad del servicio | Alta |

---

## Prioridades pendientes

| Item | Prioridad |
|------|-----------|
| Implementar `GET /feedback/stats` real | Baja |

> Proyecto terminado. No hay pendientes criticos.
