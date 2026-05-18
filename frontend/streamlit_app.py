"""
FeedbackRadar Agentic — Frontend Streamlit v3
"""

import re
import time
import threading
import streamlit as st
import requests
from requests.exceptions import ConnectionError, Timeout

# ──────────────────────────────────────────────────────────────────────────────
# Page config (must be first Streamlit call)
# ──────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="FeedbackRadar",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────────────────────
# CSS
# ──────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
/* ── FoodGo brand palette ──────────────────────────────────────────────────
   Primary:   #FF6B00  (FoodGo orange)
   Light:     rgba(255,107,0,0.10)
   Warm bg:   #FFFCF9
   Sidebar:   #FFF4EC
────────────────────────────────────────────────────────────────────────── */

/* ── Hide default Streamlit header ── */
header[data-testid="stHeader"] { display: none; }

/* ── Page background: warm off-white ── */
.stApp {
    background-color: #FFFCF9;
}

/* ── Sidebar: warm cream with orange top border ── */
section[data-testid="stSidebar"] > div:first-child {
    background: #FFF4EC;
    border-right: 1px solid #FFD4B0;
}

/* ── Metric cards ── */
[data-testid="metric-container"] {
    background: #fff;
    border: 1px solid #FFD4B0;
    border-radius: 10px;
    padding: 16px 20px;
}

/* ── Sidebar nav buttons (base) ── */
section[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    text-align: left !important;
    justify-content: flex-start !important;
    padding: 10px 14px !important;
    border-radius: 8px !important;
    font-size: 0.93rem !important;
    font-weight: 500 !important;
    color: #374151 !important;
    margin-bottom: 2px !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,107,0,0.08) !important;
    color: #CC5500 !important;
    border: none !important;
    box-shadow: none !important;
}
/* ── Sidebar nav button: página activa ── */
section[data-testid="stSidebar"] [data-testid="baseButton-primary"] {
    background: rgba(255,107,0,0.13) !important;
    color: #FF6B00 !important;
    font-weight: 700 !important;
    border: none !important;
    box-shadow: none !important;
}
section[data-testid="stSidebar"] [data-testid="baseButton-primary"]:hover {
    background: rgba(255,107,0,0.20) !important;
    color: #CC5500 !important;
}

/* ── Hub cards ── */
div[data-testid="stVerticalBlockBorderWrapper"] {
    transition: box-shadow 0.2s, border-color 0.2s;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    box-shadow: 0 4px 16px rgba(255,107,0,0.18);
    border-color: #FF6B00 !important;
    cursor: pointer;
}

/* ── Dashboard cards ── */
.hub-card {
    background: white;
    border: 1.5px solid #FFD4B0;
    border-radius: 12px;
    padding: 28px 24px;
    text-align: center;
    transition: box-shadow 0.2s, border-color 0.2s;
    cursor: pointer;
    min-height: 140px;
}
.hub-card:hover {
    box-shadow: 0 4px 16px rgba(255,107,0,0.18);
    border-color: #FF6B00;
}
.hub-card-icon { font-size: 2.4rem; margin-bottom: 10px; }
.hub-card-title { font-size: 1.05rem; font-weight: 700; color: #1a1a2e; margin-bottom: 6px; }
.hub-card-desc  { font-size: 0.85rem; color: #666; }

/* ── Agent pipeline ── */
.pipeline-step {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 16px;
    border-radius: 8px;
    margin-bottom: 6px;
    background: #fafafa;
    font-size: 0.9rem;
}
.pipeline-step-done  { background: #e8f5e9; color: #2e7d32; }
.pipeline-step-active { background: #FFF0E0; color: #CC5500; font-weight: 600; }

/* ── Blockquote (evidence) ── */
blockquote {
    border-left: 3px solid #FF6B00;
    padding-left: 12px;
    color: #555;
    font-style: italic;
    margin: 4px 0 4px 8px;
}

/* ── Expander header ── */
[data-testid="stExpander"] summary {
    font-weight: 600;
    font-size: 0.95rem;
}

/* ── Primary buttons: orange ── */
button[kind="primary"], .stButton > button[kind="primary"] {
    background-color: #FF6B00 !important;
    border-color: #FF6B00 !important;
    color: white !important;
}
button[kind="primary"]:hover {
    background-color: #E05A00 !important;
    border-color: #E05A00 !important;
}

/* ── Chat evidence cards ── */
.chat-evidence {
    background: #FFF4EC;
    border-left: 3px solid #FF6B00;
    border-radius: 0 6px 6px 0;
    padding: 8px 12px;
    font-size: 0.82rem;
    color: #555;
    margin: 4px 0;
}
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────────────

PRIORITY_COLOR = {
    "Crítica": "#d32f2f",
    "Alta":    "#f57c00",
    "Media":   "#f9a825",
    "Baja":    "#388e3c",
}
PRIORITY_EMOJI = {"Crítica": "🔴", "Alta": "🟠", "Media": "🟡", "Baja": "🟢"}

SENTIMENT_COLOR = {
    "Negativo": "#d32f2f",
    "Mixto":    "#f57c00",
    "Positivo": "#388e3c",
}


_PRIORITY_RANK = {"crítica": 0, "critica": 0, "alta": 1, "media": 2, "baja": 3}

PAGES = [
    ("🏠", "Dashboard"),
    ("📤", "Subir CSV"),
    ("⚙️", "Ejecutar Análisis"),
    ("💡", "Insights"),
    ("💬", "Consultar"),
]

# ──────────────────────────────────────────────────────────────────────────────
# Session state defaults
# ──────────────────────────────────────────────────────────────────────────────

if "api_url" not in st.session_state:
    st.session_state.api_url = "http://localhost:8000"
if "upload_result" not in st.session_state:
    st.session_state.upload_result = None
if "upload_error" not in st.session_state:
    st.session_state.upload_error = None

# Página activa: query param tiene prioridad (nav links), si no, session_state
_valid_pages = [name for _, name in PAGES]
_qp = st.query_params.get("nav", "")
if _qp in _valid_pages:
    st.session_state.page = _qp
elif "page" not in st.session_state:
    st.session_state.page = "Dashboard"


def go_to(page: str):
    st.query_params["nav"] = page
    st.session_state.page = page
    st.rerun()


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def badge(text: str, color: str) -> str:
    return (
        f'<span style="background:{color};color:#fff;padding:3px 12px;'
        f'border-radius:12px;font-size:0.78rem;font-weight:700;'
        f'display:inline-block;line-height:1.7">{text}</span>'
    )

def priority_badge(priority: str) -> str:
    return badge(priority, PRIORITY_COLOR.get(priority, "#9e9e9e"))


def expander_label(priority: str, theme: str) -> str:
    return f"{PRIORITY_EMOJI.get(priority, '⚪')}  {theme}"

def _theme_sort_key(item: str):
    prio_match = re.search(r'prioridad:\s*(\w+)', item, re.IGNORECASE)
    prio = prio_match.group(1).lower() if prio_match else "baja"
    pct_match = re.search(r'([\d]+(?:[.,][\d]+)?)\s*%', item)
    pct = float(pct_match.group(1).replace(',', '.')) if pct_match else 0.0
    return (_PRIORITY_RANK.get(prio, 4), -pct)

def api_get(path: str, params: dict = None):
    try:
        r = requests.get(f"{st.session_state.api_url}{path}", params=params, timeout=10)
        r.raise_for_status()
        return r.json(), None
    except ConnectionError:
        return None, "No se puede conectar con el backend."
    except Timeout:
        return None, "El backend tardó demasiado en responder."
    except requests.HTTPError as e:
        return None, f"Error HTTP {e.response.status_code}: {e.response.text}"
    except Exception as e:
        return None, str(e)

def render_executive_summary(summary: dict):
    if not summary:
        st.info("No hay resumen ejecutivo disponible.")
        return
    sentiment  = summary.get("overall_sentiment", "")
    sent_color = SENTIMENT_COLOR.get(sentiment, "#9e9e9e")
    narrative  = summary.get("narrative", "")
    st.markdown(
        f"**Sentimiento general:** {badge(sentiment, sent_color)}",
        unsafe_allow_html=True,
    )
    if narrative:
        st.info(narrative)
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🔍 Top temas")
        for item in sorted(summary.get("top_themes", []), key=_theme_sort_key):
            st.markdown(f"- {item}")
        st.markdown("#### 🚨 Problemas urgentes")
        for item in summary.get("urgent_problems", []):
            st.markdown(f"- {item}")
    with col2:
        st.markdown("#### ✨ Features solicitadas")
        for item in summary.get("feature_requests", []):
            st.markdown(f"- {item}")
        st.markdown("#### 💼 Recomendaciones")
        for item in summary.get("product_recommendations", []):
            st.markdown(f"- {item}")
    st.divider()
    st.markdown("#### 💬 Ejemplos representativos")
    for example in summary.get("representative_examples", []):
        st.markdown(f"> {example}")


# ──────────────────────────────────────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        st.image("frontend/logo.png", use_container_width=True)
    st.markdown("## 📡 FeedbackRadar")
    st.caption("Copiloto de producto basado en agentes IA")
    st.divider()

    new_url = st.text_input(
        "URL del backend",
        value=st.session_state.api_url,
        help="URL base de la API FastAPI",
    ).rstrip("/")
    if new_url != st.session_state.api_url:
        st.session_state.api_url = new_url
        st.rerun()

    # ── Health check — compares against "ok" (what the backend actually returns) ──
    try:
        r = requests.get(f"{st.session_state.api_url}/health", timeout=3)
        if r.status_code == 200:
            hdata = r.json()
            mongo_ok = hdata.get("mongodb") == "ok"
            es_ok    = hdata.get("elasticsearch") == "ok"
            st.success("Backend conectado", icon="✅")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**MongoDB**  \n{'✅ OK' if mongo_ok else '❌ Error'}")
            with col2:
                st.markdown(f"**Elastic**  \n{'✅ OK' if es_ok else '❌ Error'}")
        else:
            st.error(f"Backend respondió {r.status_code}", icon="❌")
    except (ConnectionError, Timeout):
        st.error("Backend no disponible", icon="❌")

    st.divider()
    st.caption("NAVEGACIÓN")

    current = st.session_state.page
    for icon, name in PAGES:
        is_active = (name == current)
        if st.button(
            f"{icon}  {name}",
            key=f"nav_{name}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            go_to(name)


# ──────────────────────────────────────────────────────────────────────────────
# PAGE — Dashboard (hub)
# ──────────────────────────────────────────────────────────────────────────────

if st.session_state.page == "Dashboard":
    col_logo, col_title = st.columns([1, 5])
    with col_logo:
        st.image("frontend/logo.png", width=90)
    with col_title:
        st.title("Bienvenido a FeedbackRadar 📡")
    st.markdown(
        "Plataforma de análisis de feedback de usuarios basada en agentes IA. "
        "¿Qué quieres hacer hoy?"
    )
    st.write("")

    hub_items = [
        ("📤", "Subir CSV",         "Carga archivos CSV con feedback de usuarios en el sistema."),
        ("⚙️", "Ejecutar Análisis", "Lanza el pipeline de 7 agentes LangGraph sobre el feedback."),
        ("💡", "Insights",          "Explora los temas detectados y priorizados por los agentes."),
        ("💬", "Consultar",         "Pregunta en lenguaje natural sobre el feedback de tus clientes."),
    ]

    cols = st.columns(4, gap="large")
    for col, (icon, name, desc) in zip(cols, hub_items):
        with col:
            with st.container(border=True):
                st.markdown(f"### {icon} {name}")
                st.caption(desc)
                if st.button("Abrir →", key=f"hub_{name}", use_container_width=True):
                    go_to(name)


# ──────────────────────────────────────────────────────────────────────────────
# PAGE — Subir CSV
# ──────────────────────────────────────────────────────────────────────────────

elif st.session_state.page == "Subir CSV":
    st.title("📤 Subir Feedback CSV")

    tab_upload, tab_format = st.tabs(["Subir archivos", "Formato esperado"])

    with tab_format:
        st.markdown("""
#### Estructura del CSV

| Columna      | Tipo  | Descripción                     |
|--------------|-------|---------------------------------|
| `nombre`     | texto | Nombre o ID del usuario         |
| `fecha`      | fecha | Fecha de la reseña (YYYY-MM-DD) |
| `resena`     | texto | Texto del feedback              |
| `plataforma` | texto | App Store, Google Play, web…    |

**Ejemplo:**
```csv
nombre,fecha,resena,plataforma
Ana García,2024-01-15,La app va muy lenta,Google Play
Carlos López,2024-01-16,No puedo iniciar sesión,App Store
```
        """)

    with tab_upload:
        uploaded_files = st.file_uploader(
            "Selecciona uno o varios archivos CSV",
            type=["csv"],
            accept_multiple_files=True,
        )
        enable_embeddings = st.checkbox(
            "Generar embeddings e indexar en Elasticsearch",
            value=True,
            help="Requiere Ollama corriendo localmente.",
        )

        if st.button("⬆️  Subir archivos", type="primary", disabled=not uploaded_files):
            st.session_state.upload_result = None
            st.session_state.upload_error = None
            with st.spinner("Procesando archivos…"):
                try:
                    files_payload = [
                        ("files", (f.name, f.read(), "text/csv")) for f in uploaded_files
                    ]
                    r = requests.post(
                        f"{st.session_state.api_url}/feedback/upload",
                        files=files_payload,
                        params={"enable_embeddings": str(enable_embeddings).lower()},
                        timeout=60,
                    )
                    r.raise_for_status()
                    st.session_state.upload_result = r.json()
                except ConnectionError:
                    st.session_state.upload_error = "No se puede conectar con el backend."
                except requests.HTTPError as e:
                    st.session_state.upload_error = f"Error del servidor: {e.response.text}"
                except Exception as e:
                    st.session_state.upload_error = f"Error inesperado: {e}"

        # ── Renderizar resultado persistido (sobrevive cambios de pestaña) ──
        if st.session_state.upload_error:
            st.error(st.session_state.upload_error, icon="❌")

        elif st.session_state.upload_result:
            result = st.session_state.upload_result
            if result.get("success"):
                st.success(
                    f"✅  {result['inserted_rows']} registros cargados "
                    f"de {result['total_rows']} filas totales.",
                )
            else:
                st.warning("La subida terminó con advertencias.", icon="⚠️")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Archivos",      result.get("files_processed", 0))
            c2.metric("Filas válidas", result.get("valid_rows", 0))
            c3.metric("Insertadas",    result.get("inserted_rows", 0))
            c4.metric("Indexadas",     result.get("indexed_rows", 0))

            errors = result.get("errors", [])
            if errors:
                with st.expander(f"⚠️  Advertencias / errores ({len(errors)})"):
                    for e in errors:
                        st.warning(e)

            for res in result.get("results", []):
                with st.expander(f"📄  {res.get('source_file', '')}"):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Total filas", res.get("total_rows", 0))
                    c2.metric("Válidas",     res.get("valid_rows", 0))
                    c3.metric("Insertadas",  res.get("inserted_rows", 0))


# ──────────────────────────────────────────────────────────────────────────────
# PAGE — Ejecutar Análisis
# ──────────────────────────────────────────────────────────────────────────────

elif st.session_state.page == "Ejecutar Análisis":
    st.title("⚙️ Ejecutar Análisis")
    st.markdown("Lanza el **pipeline completo de 7 agentes** sobre el feedback almacenado en MongoDB y Elasticsearch.")

    # ── Agent pipeline visual ──
    with st.expander("Ver pipeline de agentes", expanded=False):
        agents = [
            ("1", "Theme Agent",          "Detecta y agrupa temas en el feedback"),
            ("2", "Evidence Agent",        "Busca evidencias semánticas por tema"),
            ("3", "Prioritization Agent",  "Prioriza temas por impacto y frecuencia"),
            ("4", "Recommendation Agent",  "Genera acciones de producto accionables"),
            ("5", "Persistence Agent",     "Guarda insights y acciones en MongoDB"),
            ("6", "Summary Agent",         "Produce el resumen ejecutivo final"),
        ]
        for num, name, desc in agents:
            st.markdown(
                f'<div class="pipeline-step">🤖 <strong>Agente {num} — {name}</strong>'
                f'&nbsp;·&nbsp; <span style="color:#555">{desc}</span></div>',
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Config form ──
    with st.form("analysis_form"):
        col1, col2 = st.columns(2)
        limit = col1.number_input(
            "Máximo de feedback a analizar",
            min_value=1, max_value=1000, value=100, step=10,
            help="Número máximo de reseñas que procesarán los agentes.",
        )
        days = col2.number_input(
            "Últimos N días (0 = todo)",
            min_value=0, max_value=365, value=0, step=1,
            help="Filtra el feedback por fecha. 0 = sin filtro de fecha.",
        )
        submitted = st.form_submit_button("▶️  Iniciar análisis", type="primary")

    if submitted:
        payload = {"limit": int(limit)}
        if days > 0:
            payload["days"] = int(days)

        # Clear previous result while running
        st.session_state.pop("analysis_result", None)
        st.session_state.pop("analysis_error", None)

        progress_bar    = st.progress(0, text="Preparando agentes…")
        result_holder: dict = {}
        _api_url = st.session_state.api_url  # capture before thread — session_state not safe in threads

        def _call_api():
            try:
                resp = requests.post(
                    f"{_api_url}/analysis/run",
                    json=payload,
                    timeout=180,
                )
                resp.raise_for_status()
                result_holder["data"] = resp.json()
            except Exception as exc:
                result_holder["error"] = str(exc)

        steps = [
            (10, "Agente 1 — Recuperando feedback de MongoDB…"),
            (25, "Agente 2 — Detectando temas con LLM…"),
            (42, "Agente 3 — Buscando evidencias semánticas…"),
            (58, "Agente 4 — Priorizando temas…"),
            (72, "Agente 5 — Generando recomendaciones…"),
            (86, "Agente 6 — Persistiendo insights y acciones…"),
            (94, "Generando resumen ejecutivo…"),
        ]

        thread = threading.Thread(target=_call_api)
        thread.start()
        step_idx = 0
        start    = time.time()

        while thread.is_alive():
            elapsed = time.time() - start
            if step_idx < len(steps) and elapsed > step_idx * 2.5:
                pct, msg = steps[step_idx]
                progress_bar.progress(pct, text=msg)
                step_idx += 1
            time.sleep(0.4)

        thread.join()
        progress_bar.progress(100, text="Pipeline completado ✅")
        elapsed = time.time() - start

        # Persist result so reruns don't wipe it
        if "error" in result_holder:
            st.session_state["analysis_error"] = result_holder["error"]
        else:
            result_holder["data"]["_elapsed"] = elapsed
            st.session_state["analysis_result"] = result_holder["data"]

    # ── Render persisted result (survives any subsequent rerun) ──
    if "analysis_error" in st.session_state:
        st.error(f"Error durante el análisis: {st.session_state['analysis_error']}", icon="❌")

    elif "analysis_result" in st.session_state:
        result  = st.session_state["analysis_result"]
        elapsed = result.get("_elapsed", 0)

        if result.get("success"):
            st.success(
                f"Análisis completado en **{result.get('execution_time_seconds', elapsed):.1f} s**",
                icon="✅",
            )
        else:
            st.warning("El análisis terminó con errores.", icon="⚠️")

        # ── Metrics ──
        jira_issues = result.get("jira_issues_created", [])
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Feedback analizado", result.get("feedback_analyzed", 0))
        c2.metric("Temas detectados",   result.get("themes_detected", 0))
        c3.metric("Insights creados",   result.get("insights_created", 0))
        c4.metric("Acciones creadas",   result.get("actions_created", 0))
        c5.metric("Tickets Jira",       len(jira_issues))

        errors = result.get("errors", [])
        if errors:
            with st.expander(f"⚠️  Errores durante el análisis ({len(errors)})"):
                for e in errors:
                    st.error(e)

        # ── Tabs ──
        tab_summary, tab_jira = st.tabs(["📊 Resumen ejecutivo", "🎫 Tickets Jira"])

        with tab_summary:
            exec_summary = result.get("executive_summary")
            if exec_summary:
                render_executive_summary(exec_summary)
            else:
                st.info("No se generó resumen ejecutivo en este análisis.")

        with tab_jira:
            if jira_issues:
                for issue in jira_issues:
                    key      = issue.get("key", "")
                    url      = issue.get("url", "#")
                    theme    = issue.get("theme", "")
                    priority = issue.get("priority", "")
                    reused   = issue.get("reused", False)
                    tag      = "🔁 Reutilizado" if reused else "✨ Nuevo"
                    st.markdown(
                        f"[**{key}**]({url}) &nbsp; "
                        f"{priority_badge(priority)} &nbsp; "
                        f"{theme} &nbsp; {tag}",
                        unsafe_allow_html=True,
                    )
            else:
                st.info("No se crearon tickets Jira en este análisis.")

        # ── Quick link ──
        st.divider()
        col_a, _ = st.columns([2, 8])
        if col_a.button("💡  Ver Insights", use_container_width=True):
            go_to("Insights")


# ──────────────────────────────────────────────────────────────────────────────
# PAGE — Insights
# ──────────────────────────────────────────────────────────────────────────────

elif st.session_state.page == "Consultar":
    st.title("💬 Consultar el Feedback")
    st.caption("Haz preguntas en lenguaje natural sobre el feedback de tus clientes")

    # Inicializar historial de chat
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Botón para limpiar la conversación
    col_title, col_clear = st.columns([8, 2])
    with col_clear:
        if st.button("Limpiar conversación", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()


    # Renderizar historial de mensajes
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                tools_called = msg.get("tools_called", [])
                iterations = msg.get("iterations", 1)
                if tools_called:
                    tool_names = ", ".join(f"`{t['tool']}`" for t in tools_called)
                    st.caption(f"Agente usó {iterations} iteración(es) · Tools: {tool_names}")
                if msg.get("evidence"):
                    with st.expander(f"Ver evidencias del feedback ({len(msg['evidence'])} fragmentos)", expanded=False):
                        for ev in msg["evidence"]:
                            score_pct = int(ev.get("score", 0) * 100)
                            platform = ev.get("platform", "")
                            text = ev.get("text", "")
                            st.markdown(
                                f'<div class="chat-evidence">'
                                f'<strong>{platform}</strong> &nbsp;·&nbsp; similitud {score_pct}%<br>'
                                f'"{text}"'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

    # Input del usuario
    if question := st.chat_input("Ej: ¿Cuáles son los principales problemas con el proceso de pago?"):
        # Mostrar mensaje del usuario
        with st.chat_message("user"):
            st.markdown(question)
        st.session_state.chat_history.append({"role": "user", "content": question})

        # Llamar al backend y mostrar respuesta
        with st.chat_message("assistant"):
            with st.spinner("Buscando en el feedback..."):
                try:
                    resp = requests.post(
                        f"{st.session_state.api_url}/chat/ask",
                        json={"question": question},
                        timeout=60,
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    answer = data.get("answer", "Sin respuesta.")
                    evidence = data.get("evidence", [])
                    tools_called = data.get("tools_called", [])
                    iterations = data.get("iterations", 1)

                    st.markdown(answer)

                    # Herramientas usadas por el agente
                    if tools_called:
                        tool_names = ", ".join(
                            f"`{t['tool']}`" for t in tools_called
                        )
                        st.caption(f"Agente usó {iterations} iteración(es) · Tools: {tool_names}")

                    if evidence:
                        with st.expander(f"Ver evidencias del feedback ({len(evidence)} fragmentos)", expanded=False):
                            for ev in evidence:
                                score_pct = int(ev.get("score", 0) * 100)
                                platform = ev.get("platform", "")
                                text = ev.get("text", "")
                                st.markdown(
                                    f'<div class="chat-evidence">'
                                    f'<strong>{platform}</strong> &nbsp;·&nbsp; similitud {score_pct}%<br>'
                                    f'"{text}"'
                                    f'</div>',
                                    unsafe_allow_html=True,
                                )

                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": answer,
                        "evidence": evidence,
                        "tools_called": tools_called,
                        "iterations": iterations,
                    })

                except ConnectionError:
                    err = "No se puede conectar con el backend."
                    st.error(err, icon="❌")
                    st.session_state.chat_history.append({"role": "assistant", "content": err, "evidence": []})
                except requests.HTTPError as e:
                    err = f"Error del servidor: {e.response.text}"
                    st.error(err, icon="❌")
                    st.session_state.chat_history.append({"role": "assistant", "content": err, "evidence": []})
                except Exception as e:
                    err = f"Error inesperado: {e}"
                    st.error(err, icon="❌")
                    st.session_state.chat_history.append({"role": "assistant", "content": err, "evidence": []})

    if not st.session_state.chat_history:
        st.markdown("""
        **Ejemplos de preguntas:**
        - ¿Cuáles son los principales problemas reportados por los clientes?
        - ¿Qué opinan los usuarios sobre el proceso de pago?
        - ¿Cuántos usuarios mencionan problemas de rendimiento?
        - ¿Qué features piden más los usuarios?
        - Resume el feedback de la plataforma App Store
        """)


elif st.session_state.page == "Insights":
    st.title("💡 Insights")
    st.caption("Temas detectados y priorizados a partir del feedback de usuarios")

    with st.expander("🔧 Filtros", expanded=True):
        col1, col2 = st.columns(2)
        limit = col1.slider("Máximo de resultados", 5, 200, 50)
        priority_filter = col2.selectbox(
            "Prioridad", ["Todas", "Crítica", "Alta", "Media", "Baja"]
        )

    data, err = api_get("/analysis/insights", {"limit": limit})

    if err:
        st.error(err, icon="❌")
    elif not data:
        st.info("No hay insights todavía. Ejecuta un análisis primero.", icon="ℹ️")
    else:
        if priority_filter != "Todas":
            data = [i for i in data if i.get("priority") == priority_filter]

        # ── Summary counts ──
        counts: dict = {}
        for i in data:
            p = i.get("priority", "—")
            counts[p] = counts.get(p, 0) + 1
        badge_html = "&nbsp;&nbsp;".join(
            f"{priority_badge(p)} <small style='color:#555'>×{n}</small>"
            for p, n in sorted(counts.items(), key=lambda x: _PRIORITY_RANK.get(x[0].lower(), 9))
        )
        st.markdown(
            f"**{len(data)} insights** &nbsp;·&nbsp; {badge_html}",
            unsafe_allow_html=True,
        )
        st.write("")

        for insight in data:
            priority = insight.get("priority", "")
            theme    = insight.get("theme", "")

            with st.expander(expander_label(priority, theme), expanded=False):
                st.markdown(priority_badge(priority), unsafe_allow_html=True)
                st.write("")
                st.markdown(insight.get("summary", ""))
                reasoning = insight.get("reasoning", "")
                if reasoning:
                    st.markdown(f"**Justificación:** {reasoning}")
                evidence = insight.get("evidence", [])
                if evidence:
                    st.caption(f"Evidencias ({len(evidence)}):")
                    for ev in evidence:
                        st.markdown(f'> "{ev}"')
                st.caption(
                    f"ID: `{insight.get('insight_id', '')}` · "
                    f"Análisis: `{insight.get('analysis_run_id', '')}`"
                )

