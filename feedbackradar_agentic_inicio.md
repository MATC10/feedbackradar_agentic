# FeedbackRadar Agentic

## Documento base del proyecto

---

# 1. Resumen ejecutivo

**FeedbackRadar Agentic** es una solución basada en agentes que transforma feedback disperso de clientes en **insights accionables para equipos de producto y negocio**.

El sistema ingiere reseñas y comentarios procedentes de diferentes canales, como:

* Email
* Encuestas
* Reviews
* Formularios
* Otros canales futuros

A partir de esos datos, un workflow de agentes:

1. Detecta los principales problemas y oportunidades.
2. Recupera evidencias textuales reales.
3. Prioriza qué temas requieren atención.
4. Genera recomendaciones de producto.
5. Crea acciones concretas y las persiste en base de datos.

---

# 2. Problema real que resuelve

Las empresas reciben constantemente feedback de usuarios desde múltiples fuentes, pero ese feedback suele quedar:

* Desordenado
* Sin analizar
* Repartido en varios canales
* Sin priorización
* Sin una conexión clara con decisiones de producto

Esto provoca que:

* Se ignoren problemas importantes.
* Se tomen decisiones por intuición.
* No se detecten tendencias emergentes.
* El roadmap no esté suficientemente conectado con la voz real del cliente.

---

# 3. Propuesta de valor

> **FeedbackRadar Agentic convierte opiniones dispersas en decisiones de producto basadas en evidencia.**

No es solo un resumidor de comentarios. Es un sistema que:

* Analiza feedback multicanal.
* Usa agentes especializados.
* Consulta bases de datos mediante herramientas MCP.
* Recupera evidencia con búsqueda vectorial.
* Devuelve recomendaciones justificadas y accionables.

---

# 4. Público objetivo

El producto está pensado para:

* Product Managers
* Equipos de atención al cliente
* Startups
* Equipos de negocio
* Equipos de UX / Research
* Empresas que reciben mucho feedback de usuarios

---

# 5. Caso de uso principal

## Pregunta de negocio

> “Tenemos cientos de comentarios de usuarios. ¿Qué problemas están apareciendo, cuáles son más importantes y qué deberíamos priorizar?”

## Respuesta esperada del sistema

El sistema devuelve:

* Top problemas detectados.
* Número aproximado de menciones.
* Plataformas donde aparecen.
* Evidencias reales de usuarios.
* Nivel de prioridad.
* Recomendaciones de acción.

### Ejemplo

```markdown
Problema detectado: Fallos en el proceso de pago

Prioridad: Alta

Motivo:
- Aparece en múltiples plataformas.
- Bloquea una acción crítica del usuario.
- Se repite con frecuencia.

Evidencias:
- “La app se queda cargando cuando intento pagar.”
- “No consigo completar la compra desde el móvil.”
- “El pago falla incluso probando otra tarjeta.”

Acción recomendada:
- Revisar el checkout móvil.
- Analizar errores recientes en pasarela de pago.
- Priorizarlo como incidencia crítica de producto.
```

---

# 6. Casos de uso concretos

## 6.1. Detectar dolores principales del cliente

El sistema analiza el conjunto completo de feedback y encuentra temas recurrentes:

* Pagos fallidos
* Problemas de login
* Lentitud en móvil
* Dificultad para descargar facturas
* Falta de filtros
* Mala experiencia de navegación

---

## 6.2. Priorizar problemas

No solo agrupa temas: también decide cuáles requieren atención antes.

Criterios posibles:

* Frecuencia
* Presencia en múltiples canales
* Impacto funcional
* Tono negativo
* Aparición reciente

---

## 6.3. Recuperar evidencias

Para cada insight, el sistema muestra comentarios reales que lo sustentan.

Esto hace que la recomendación sea:

* Trazable
* Explicable
* Convincente para negocio

---

## 6.4. Generar acciones de producto

A partir de cada insight, se crea una acción sugerida:

```markdown
Acción:
Revisar el flujo de checkout móvil

Justificación:
El tema “pagos fallidos” aparece de manera recurrente y bloquea la conversión.

Estado:
Pendiente
```

---

## 6.5. Crear un informe ejecutivo

El sistema puede devolver un resumen tipo:

```markdown
Resumen ejecutivo:

El principal foco de frustración de los usuarios está relacionado con el proceso de pago, especialmente desde móvil. También se detectan problemas recurrentes con la localización de facturas y el rendimiento de la aplicación en ciertos flujos.

Se recomienda priorizar:
1. Checkout móvil
2. Acceso a facturas
3. Optimización del rendimiento
```

---

# 7. Decisiones de stack tecnológico

## Stack final

| Componente                          | Tecnología     |
| ----------------------------------- | -------------- |
| Lenguaje                            | Python         |
| Backend API                         | FastAPI        |
| Servidor ASGI                       | Uvicorn        |
| Orquestación de agentes             | LangGraph      |
| MCP                                 | FastMCP        |
| Embeddings                          | Ollama         |
| BBDD no vectorial                   | MongoDB        |
| BBDD vectorial / búsqueda semántica | Elasticsearch  |
| Validación de datos                 | Pydantic       |
| Frontend demo                       | Streamlit      |
| Infraestructura                     | Docker Compose |

---

# 8. Decisión sobre Pandas

**No se usará Pandas.**

Motivo:

Los datasets ya estarán preparados como CSVs con una estructura clara y homogénea. Por tanto, basta con procesarlos usando:

* `csv` de la librería estándar de Python
* `pydantic` para validar cada fila
* funciones propias de normalización

Esto reduce dependencias y simplifica el MVP.

---

# 9. Formato de los datasets

Los CSVs vendrán de distintas fuentes, pero compartirán la misma estructura lógica.

## Columnas previstas

| Campo        | Descripción                                          |
| ------------ | ---------------------------------------------------- |
| `nombre`     | Nombre de la persona que dejó la reseña              |
| `fecha`      | Fecha del comentario                                 |
| `reseña`     | Texto de feedback                                    |
| `plataforma` | Origen del feedback: Email, Encuestas, Reviews, etc. |

## Ejemplo

```csv
nombre,fecha,reseña,plataforma
Laura Gómez,2026-05-10,"No consigo completar el pago desde el móvil",Reviews
Carlos Ruiz,2026-05-11,"Me gustaría que hubiera más filtros",Encuestas
Ana Pérez,2026-05-12,"La factura no aparece en mi área privada",Email
```

---

# 10. Modelo interno de feedback

Aunque los CSV tengan columnas simples, internamente se normalizará cada fila a un formato estándar.

```json
{
  "feedback_id": "fb_001",
  "author_name": "Laura Gómez",
  "date": "2026-05-10",
  "text": "No consigo completar el pago desde el móvil",
  "platform": "Reviews",
  "source_file": "reviews.csv",
  "ingested_at": "2026-05-12T10:30:00"
}
```

---

# 11. Tratamiento del nombre de usuario

El nombre puede conservarse en MongoDB para mantener fidelidad al dataset, pero en la interfaz de demo conviene mostrarlo:

* Anonimizado
* Con iniciales
* O como “Usuario 001”

Ejemplo:

```text
Laura Gómez → L. G.
```

Esto permite una demo más profesional y cuidadosa.

---

# 12. Arquitectura general

```text
CSV de feedback
        ↓
Ingestor Python
        ↓
MongoDB
        ↓
Ollama genera embeddings
        ↓
Elasticsearch indexa feedback vectorizado
        ↓
FastAPI expone endpoints
        ↓
LangGraph coordina agentes
        ↓
FastMCP expone herramientas consultables por los agentes
        ↓
Streamlit muestra resultados al usuario
```

---

# 13. Arquitectura visual simplificada

```text
                    ┌───────────────────┐
                    │     Streamlit     │
                    │    Front demo     │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │      FastAPI      │
                    │   API Backend     │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │     LangGraph     │
                    │  Workflow Agents  │
                    └─────────┬─────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
┌────────▼────────┐ ┌────────▼────────┐ ┌────────▼────────┐
│   FastMCP Tools │ │    MongoDB      │ │ Elasticsearch   │
│ consultas/acciones│ datos persistidos│ búsqueda vectorial│
└────────┬────────┘ └─────────────────┘ └────────┬────────┘
         │                                         │
         └─────────────────┬───────────────────────┘
                           │
                    ┌──────▼──────┐
                    │    Ollama   │
                    │  Embeddings │
                    └─────────────┘
```

---

# 14. Pipeline de ingestión

## Flujo

```text
1. Leer CSV
2. Validar campos
3. Crear feedback_id
4. Guardar documento completo en MongoDB
5. Generar embedding de la reseña con Ollama
6. Indexar documento en Elasticsearch
```

---

## Ejemplo de documento en MongoDB

```json
{
  "feedback_id": "fb_001",
  "author_name": "Laura Gómez",
  "date": "2026-05-10",
  "text": "No consigo completar el pago desde el móvil",
  "platform": "Reviews",
  "source_file": "reviews.csv",
  "ingested_at": "2026-05-12T10:30:00"
}
```

---

## Ejemplo de documento en Elasticsearch

```json
{
  "feedback_id": "fb_001",
  "text": "No consigo completar el pago desde el móvil",
  "platform": "Reviews",
  "date": "2026-05-10",
  "embedding": [0.021, -0.345, 0.812]
}
```

---

# 15. Papel de cada base de datos

## MongoDB

Será la **base de datos operativa**.

Guardará:

* Feedback original
* Ejecuciones de análisis
* Insights detectados
* Acciones recomendadas
* Metadatos de la demo

### Colecciones propuestas

#### `feedback`

Comentarios ingestados.

#### `analysis_runs`

Cada ejecución del análisis.

#### `insights`

Hallazgos principales.

#### `actions`

Acciones recomendadas generadas por el sistema.

---

## Elasticsearch

Será la **base de búsqueda semántica**.

Permitirá:

* Recuperar feedback similar a un tema.
* Obtener evidencias representativas.
* Filtrar por plataforma.
* Filtrar por fecha.
* Localizar patrones semánticos.

---

# 16. Uso de Ollama

Ollama se usará para generar embeddings del texto de las reseñas.

## Entradas

```text
"No consigo completar el pago desde el móvil"
```

## Salida

```text
Vector numérico representando el significado del texto
```

Ese vector se indexa en Elasticsearch para realizar recuperación semántica.

---

# 17. Uso de RAG en el proyecto

FeedbackRadar Agentic usa una forma de **RAG aplicada a feedback**.

No se trata de consultar documentos largos, sino de:

1. Formular una búsqueda semántica sobre un tema.
2. Recuperar comentarios relevantes desde Elasticsearch.
3. Usarlos como evidencia en el razonamiento del agente.
4. Generar recomendaciones basadas en datos reales.

Ejemplo:

```text
Tema detectado:
"Pagos fallidos"

Consulta semántica:
"Usuarios que no pueden pagar o terminar una compra"

Resultado:
Comentarios reales relacionados con ese problema
```

---

# 18. Diseño de agentes con LangGraph

## Agentes principales

### 18.1. Theme Discovery Agent

Responsabilidad:

* Analizar el conjunto de feedback.
* Detectar los temas principales.
* Proponer etiquetas o categorías.

Ejemplo de salida:

```json
{
  "themes": [
    {
      "name": "Pagos fallidos",
      "description": "Usuarios que no consiguen completar el checkout."
    },
    {
      "name": "Acceso a facturas",
      "description": "Usuarios que no encuentran o no pueden descargar sus facturas."
    }
  ]
}
```

---

### 18.2. Evidence Retrieval Agent

Responsabilidad:

* Tomar cada tema detectado.
* Consultar Elasticsearch.
* Recuperar evidencias textuales representativas.

Ejemplo de salida:

```json
{
  "theme": "Pagos fallidos",
  "evidence": [
    "La app se queda cargando cuando intento pagar.",
    "No puedo terminar la compra desde el móvil."
  ]
}
```

---

### 18.3. Prioritization Agent

Responsabilidad:

* Determinar la criticidad de cada tema.
* Justificar el nivel de prioridad.

Criterios:

* Frecuencia
* Impacto
* Presencia en varias plataformas
* Tono negativo
* Carácter bloqueante del problema

Ejemplo:

```json
{
  "theme": "Pagos fallidos",
  "priority": "Alta",
  "reason": "Bloquea la conversión y aparece en múltiples fuentes de feedback."
}
```

---

### 18.4. Recommendation Agent

Responsabilidad:

* Crear una recomendación ejecutiva.
* Traducir el insight en una acción concreta.

Ejemplo:

```json
{
  "recommendation": "Priorizar una revisión del checkout móvil y analizar los errores de pago más recientes.",
  "action_item": "Investigar fallos en pagos móviles"
}
```

---

### 18.5. Persistence Agent

Responsabilidad:

* Guardar los resultados del análisis en MongoDB.
* Registrar insights y acciones.

---

# 19. Workflow de LangGraph

## Grafo de ejecución

```text
START
  ↓
discover_themes
  ↓
retrieve_evidence
  ↓
prioritize_themes
  ↓
generate_recommendations
  ↓
persist_results
  ↓
END
```

---

# 20. Uso de MCP

## Por qué se usa MCP

MCP no estará “de adorno”. Servirá para que los agentes interactúen con capacidades del sistema mediante herramientas bien definidas.

En lugar de que los agentes accedan directamente a toda la lógica, usarán tools expuestas a través de **FastMCP**.

---

# 21. MCP Tools propuestas

## 21.1. `search_feedback`

Busca feedback relacionado con un tema.

```python
search_feedback(query: str, platform: str | None = None, top_k: int = 5)
```

Uso:

* Recuperar evidencias semánticas.
* Buscar comentarios relacionados con una hipótesis.

---

## 21.2. `get_feedback_stats`

Obtiene estadísticas generales.

```python
get_feedback_stats(theme: str)
```

Uso:

* Contar menciones.
* Estimar peso del problema.
* Consultar distribución por plataformas.

---

## 21.3. `save_insight`

Guarda un insight generado.

```python
save_insight(theme: str, summary: str, priority: str, reasoning: str)
```

---

## 21.4. `create_action_item`

Crea una acción recomendada.

```python
create_action_item(title: str, description: str, priority: str)
```

---

## 21.5. `get_recent_feedback`

Recupera feedback reciente.

```python
get_recent_feedback(days: int = 7)
```

Uso opcional:

* Detectar señales recientes.
* Comparar feedback nuevo frente al histórico.

---

# 22. Endpoints de FastAPI

## 22.1. Ingestar feedback

```http
POST /feedback/upload
```

Recibe uno o varios CSVs.

---

## 22.2. Ejecutar análisis

```http
POST /analysis/run
```

Lanza el workflow de agentes.

---

## 22.3. Consultar último análisis

```http
GET /analysis/latest
```

Devuelve el informe más reciente.

---

## 22.4. Consultar insights

```http
GET /insights
```

---

## 22.5. Consultar acciones

```http
GET /actions
```

---

# 23. Ejemplo de respuesta del análisis

```json
{
  "executive_summary": "El principal problema detectado está relacionado con fallos en pagos y checkout móvil.",
  "top_themes": [
    {
      "theme": "Pagos fallidos",
      "priority": "Alta",
      "reason": "Bloquea la conversión y aparece en varios canales.",
      "evidence": [
        "No consigo completar el pago desde el móvil.",
        "La app se queda cargando al pagar."
      ],
      "recommendation": "Revisar el checkout móvil y priorizar el diagnóstico de errores de pago."
    },
    {
      "theme": "Acceso a facturas",
      "priority": "Media",
      "reason": "Genera fricción y tickets repetitivos, aunque no bloquea la compra.",
      "evidence": [
        "No encuentro dónde descargar la factura.",
        "La factura no aparece en mi área privada."
      ],
      "recommendation": "Mejorar la visibilidad del acceso a facturas."
    }
  ],
  "actions_created": [
    {
      "title": "Investigar fallos en pagos móviles",
      "priority": "Alta",
      "status": "Pendiente"
    }
  ]
}
```

---

# 24. Frontend en Streamlit

La UI será sencilla y orientada a demo.

## Pantallas mínimas

### Pantalla 1: Carga de datos

* Botón para subir CSVs.
* Indicador de ingestión correcta.

### Pantalla 2: Lanzar análisis

* Botón “Analizar feedback”.

### Pantalla 3: Resultados

* Resumen ejecutivo.
* Top problemas.
* Nivel de prioridad.
* Evidencias reales.
* Recomendaciones.
* Acciones creadas.

---

# 25. Demo ideal del hackathon

## Historia de demo

Una empresa ficticia recibe feedback de varios canales.
El equipo no sabe qué priorizar.

### Paso 1

Subimos los CSVs.

### Paso 2

Pulsamos “Analizar feedback”.

### Paso 3

El sistema genera:

* Temas principales
* Evidencias textuales
* Prioridades
* Recomendaciones
* Acciones

### Paso 4

Mostramos que los resultados quedan guardados.

---

# 26. Mensaje de venta al jurado

> “FeedbackRadar Agentic transforma feedback multicanal en decisiones de producto. Mediante agentes orquestados con LangGraph, herramientas MCP, búsqueda vectorial con Elasticsearch y persistencia en MongoDB, el sistema detecta dolores reales del cliente, recupera evidencias, prioriza problemas y genera acciones concretas.”

---

# 27. Alcance del MVP

## Incluido

* Ingesta de CSVs
* Persistencia en MongoDB
* Embeddings con Ollama
* Indexación vectorial en Elasticsearch
* Workflow de agentes con LangGraph
* Herramientas MCP funcionales
* API con FastAPI
* Front sencillo con Streamlit
* Visualización de insights y acciones

---

## Fuera de alcance

Para no sobrecomplicar, se deja fuera:

* Integración real con Gmail
* Integración real con Google Forms
* Conexión directa con plataformas externas
* Login y autenticación
* Dashboard complejo
* Análisis en tiempo real
* Predicción avanzada de churn
* Comparativas sofisticadas por periodo

---

# 28. Estructura de carpetas recomendada

```text
feedback-radar-agentic/
│
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── feedback_routes.py
│   │   ├── analysis_routes.py
│   │   ├── insights_routes.py
│   │   └── actions_routes.py
│   │
│   ├── ingestion/
│   │   ├── csv_reader.py
│   │   ├── normalizer.py
│   │   └── ingestion_service.py
│   │
│   ├── agents/
│   │   ├── graph.py
│   │   ├── theme_agent.py
│   │   ├── evidence_agent.py
│   │   ├── prioritization_agent.py
│   │   ├── recommendation_agent.py
│   │   └── persistence_agent.py
│   │
│   ├── mcp/
│   │   ├── server.py
│   │   └── tools.py
│   │
│   ├── databases/
│   │   ├── mongodb_client.py
│   │   ├── elasticsearch_client.py
│   │   └── repositories.py
│   │
│   ├── embeddings/
│   │   └── ollama_embeddings.py
│   │
│   ├── schemas/
│   │   ├── feedback_schema.py
│   │   ├── insight_schema.py
│   │   ├── action_schema.py
│   │   └── analysis_schema.py
│   │
│   └── services/
│       ├── analysis_service.py
│       └── anonymization_service.py
│
├── frontend/
│   └── streamlit_app.py
│
├── data/
│   └── raw/
│       ├── emails.csv
│       ├── encuestas.csv
│       └── reviews.csv
│
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

# 29. Plan de desarrollo recomendado

## Fase 1 — Base de datos e ingesta

* Crear estructura de proyecto.
* Levantar MongoDB y Elasticsearch.
* Leer CSVs sin Pandas.
* Guardar feedback en MongoDB.
* Generar embeddings con Ollama.
* Indexar en Elasticsearch.

## Fase 2 — API

* Crear FastAPI.
* Endpoint de upload.
* Endpoint de análisis.

## Fase 3 — MCP

* Crear servidor FastMCP.
* Implementar tools:

  * `search_feedback`
  * `get_feedback_stats`
  * `save_insight`
  * `create_action_item`

## Fase 4 — Agentes

* Definir estado común del workflow.
* Implementar grafo en LangGraph.
* Conectar agentes con MCP y BBDD.

## Fase 5 — Front

* Carga de CSV.
* Botón de análisis.
* Visualización de insights.

## Fase 6 — Demo

* Ensayar storytelling.
* Preparar un dataset con patrones claros.
* Tener resultados esperados controlados.

---

# 30. Reparto de trabajo sugerido para 4 personas

| Persona | Responsabilidad                                              |
| ------- | ------------------------------------------------------------ |
| 1       | Ingesta de CSVs, MongoDB, modelo de datos                    |
| 2       | Elasticsearch, embeddings con Ollama, recuperación semántica |
| 3       | LangGraph, agentes, lógica de priorización                   |
| 4       | FastAPI, MCP, Streamlit y coordinación de integración        |

---

# 31. Riesgos técnicos principales

## 31.1. Elasticsearch vectorial

Puede consumir tiempo configurar bien el índice y las consultas vectoriales.

**Mitigación:**
Montar primero una búsqueda vectorial mínima y dejar mejoras para el final.

---

## 31.2. Coordinación LangGraph + MCP

Hay que asegurarse de que el MCP tenga un papel real, pero sin convertirlo en un cuello de botella.

**Mitigación:**
Crear 3–4 tools simples y que los agentes las utilicen en puntos concretos.

---

## 31.3. Calidad de los insights

Si el dataset no tiene patrones suficientemente claros, el resultado puede parecer difuso.

**Mitigación:**
Preparar CSVs de demo con varios problemas repetidos y reconocibles.

---

## 31.4. Demasiado alcance

El mayor enemigo será querer añadir demasiadas funciones.

**Mitigación:**
Centrarse en:

* detectar temas,
* recuperar evidencias,
* priorizar,
* recomendar.

---

# 32. Qué debe estar funcionando sí o sí

Para considerar el MVP exitoso, al final debe poder hacerse esto:

1. Subir CSVs.
2. Ingestar el feedback.
3. Guardarlo en MongoDB.
4. Vectorizarlo con Ollama.
5. Indexarlo en Elasticsearch.
6. Ejecutar el workflow de agentes.
7. Recuperar evidencia real.
8. Generar insights priorizados.
9. Crear acciones.
10. Mostrarlo en pantalla.

---

# 33. Resultado final esperado

FeedbackRadar Agentic será una aplicación funcional que demuestra:

* IA aplicada a un problema real.
* Diseño agentic con LangGraph.
* Uso real de MCP.
* Persistencia no vectorial con MongoDB.
* Recuperación semántica con Elasticsearch.
* Embeddings locales con Ollama.
* Backend completo con FastAPI.
* Demo clara y potente.

---

# 34. Definición final del proyecto

> **FeedbackRadar Agentic es un copiloto de producto basado en agentes que analiza feedback multicanal, detecta los principales dolores del cliente, los justifica con evidencia semánticamente recuperada y genera acciones priorizadas para ayudar a tomar mejores decisiones de negocio.**
