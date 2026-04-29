import streamlit as st
import pandas as pd
import mysql.connector
import plotly.express as px
from datetime import datetime
import io
import pytz
import zipfile
import os

# ==================== CONFIGURACIÓN INICIAL ====================
st.set_page_config(
    page_title="Carrier Transicold - Panel de Control",
    layout="wide",
    initial_sidebar_state="expanded"
)
tijuana_tz  = pytz.timezone('America/Tijuana')
ahora_tj    = datetime.now(tijuana_tz)
fecha_hoy   = ahora_tj.strftime('%Y-%m-%d')
hora_actual = ahora_tj.strftime('%H:%M:%S')

CARRIER_BLUE   = "#002B5B"
CARRIER_ACCENT = "#0057A8"
LOGO_URL  = "https://raw.githubusercontent.com/Jesusalan0102/app-escaneo-series/main/carrierlogo2.jpeg.jpg"
SOUND_URL = "https://raw.githubusercontent.com/rafaelEscalante/notification-sounds/master/pings/ping-8.mp3"

CAMPOS_SERIES = {
    "vin_number":              "VIN Number",
    "reefer_serial":           "Serie del Reefer",
    "reefer_model":            "Modelo del Reefer",
    "evaporator_serial_mjs11": "Evaporador MJS11",
    "evaporator_serial_mjd22": "Evaporador MJD22",
    "engine_serial":           "Motor",
    "compressor_serial":       "Compresor",
    "generator_serial":        "Generador",
    "battery_charger_serial":  "Cargador de Batería",
}

ACTIVIDADES_CARRIER = [
    "Cableado", "Programación", "Soldadura", "Check de fugas",
    "Vacío", "Cerrado", "Pre-viaje", "Horas Corridas",
    "Standby", "GPS", "Corriendo", "Inspección",
    "Accesorios", "Toma de Valores", "Evidencia", "Toma de Series",

]

MAX_FOTOS = 100   # Límite máximo de fotos por tarea de Evidencia

# ==================== CSS ====================
st.markdown(f"""
<style>
/* ══════════════════════════════════════
   OCULTAR BRANDING DE STREAMLIT
   ══════════════════════════════════════ */

/* Header principal (menú hamburguesa + botón Deploy) */
header[data-testid="stHeader"] {{
    display: none !important;
}}

/* Footer "Made with Streamlit" */
footer {{
    display: none !important;
}}

/* Botón "Manage app" esquina inferior derecha */
#MainMenu {{
    display: none !important;
}}
.stDeployButton {{
    display: none !important;
}}
[data-testid="stToolbar"] {{
    display: none !important;
}}
[data-testid="manage-app-button"] {{
    display: none !important;
}}

/* Barra de estado / running indicator */
[data-testid="stStatusWidget"] {{
    display: none !important;
}}

/* Quitar padding superior que deja el header oculto */
.block-container {{
    padding-top: 1.5rem !important;
}}

/* ── Base ── */
.stApp {{ background-color: #F0F4F9; }}

/* ── Sidebar ── */
section[data-testid="stSidebar"] > div:first-child {{
    background: linear-gradient(180deg, {CARRIER_BLUE} 0%, #01418a 100%);
    padding-top: 1rem;
}}
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] div {{ color: #e8eef8 !important; }}
section[data-testid="stSidebar"] .stRadio > label {{ color: white !important; font-weight: 600; }}
section[data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,0.18) !important; }}
section[data-testid="stSidebar"] button {{
    background: rgba(255,255,255,0.12) !important;
    color: white !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
    border-radius: 8px !important;
}}
section[data-testid="stSidebar"] button:hover {{ background: rgba(255,255,255,0.22) !important; }}

/* ── Títulos ── */
.main-header {{
    font-size: 1.85rem; font-weight: 700; color: {CARRIER_BLUE};
    border-bottom: 3px solid {CARRIER_ACCENT};
    padding-bottom: 10px; margin-bottom: 22px;
}}
.section-title {{
    font-size: 1rem; font-weight: 600; color: {CARRIER_BLUE};
    border-left: 4px solid {CARRIER_ACCENT};
    padding: 8px 12px; margin: 20px 0 12px 0;
    background: white; border-radius: 0 6px 6px 0;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}}

/* ── KPI cards ── */
.kpi-wrap {{
    background: white; border-radius: 12px;
    padding: 18px 20px; text-align: center;
    box-shadow: 0 2px 10px rgba(0,43,91,0.09);
    border-top: 4px solid {CARRIER_ACCENT};
}}
.kpi-wrap.green  {{ border-top-color: #16a34a; }}
.kpi-wrap.amber  {{ border-top-color: #d97706; }}
.kpi-wrap.red    {{ border-top-color: #dc2626; }}
.kpi-wrap.purple {{ border-top-color: #7c3aed; }}
.kpi-num {{ font-size: 2.1rem; font-weight: 700; color: {CARRIER_BLUE}; line-height: 1.1; }}
.kpi-wrap.green  .kpi-num {{ color: #16a34a; }}
.kpi-wrap.amber  .kpi-num {{ color: #d97706; }}
.kpi-wrap.red    .kpi-num {{ color: #dc2626; }}
.kpi-wrap.purple .kpi-num {{ color: #7c3aed; }}
.kpi-lbl {{
    font-size: 0.78rem; color: #6b7280; font-weight: 500;
    text-transform: uppercase; letter-spacing: 0.4px; margin-top: 4px;
}}

/* ── Badge hora ── */
.time-badge {{
    background: {CARRIER_BLUE}; color: white;
    padding: 5px 14px; border-radius: 20px;
    font-size: 0.85rem; float: right; margin-top: 2px;
}}

/* ── Expanders ── */
div[data-testid="stExpander"] {{
    background: white; border-radius: 10px;
    box-shadow: 0 1px 5px rgba(0,0,0,0.07);
    border: 1px solid #e5eaf2; margin-bottom: 8px;
}}

/* ── Botones ── */
.stButton > button {{
    border-radius: 8px; font-weight: 600;
    transition: transform .15s, box-shadow .15s;
}}
.stButton > button:hover {{
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0,43,91,0.18);
}}

/* ── Uploader ── */
div[data-testid="stFileUploader"] {{
    background: white; border-radius: 10px;
    border: 2px dashed #c3cfe2; padding: 8px;
}}

/* ── Alerta de bloqueo ── */
.bloqueo-card {{
    background: #fef2f2; border: 1.5px solid #fca5a5;
    border-left: 5px solid #dc2626; border-radius: 10px;
    padding: 14px 18px; margin: 8px 0;
}}
.bloqueo-card p {{ margin: 0; color: #7f1d1d; font-size: .9rem; font-weight: 500; }}

/* ── Info de evidencia ── */
.evidencia-info {{
    background: #eff6ff; border: 1px solid #bfdbfe;
    border-left: 5px solid #3b82f6; border-radius: 10px;
    padding: 12px 18px; margin-bottom: 14px;
}}
.evidencia-info p {{ margin: 0; color: #1e40af; font-size: .88rem; }}

/* ── Fotos counter badge ── */
.fotos-badge {{
    display: inline-block; background: #f0fdf4;
    border: 1px solid #86efac; border-radius: 20px;
    padding: 4px 14px; font-size: .85rem;
    color: #166534; font-weight: 600; margin-top: 10px;
}}

/* ── Formularios ── */
div[data-testid="stForm"] {{
    background: white; border-radius: 12px;
    padding: 20px 24px;
    box-shadow: 0 2px 10px rgba(0,43,91,0.07);
    border: 1px solid #e5eaf2;
}}
</style>
""", unsafe_allow_html=True)


# ==================== BASE DE DATOS ====================
def _get_db_config():
    """
    Lee credenciales primero desde variables de entorno (Clever Cloud),
    y si no existen, cae a st.secrets (desarrollo local).
    """
    env_host = os.environ.get("STREAMLIT_SECRETS_DB_HOST")
    if env_host:
        return {
            "host":     env_host,
            "database": os.environ.get("STREAMLIT_SECRETS_DB_DATABASE"),
            "user":     os.environ.get("STREAMLIT_SECRETS_DB_USER"),
            "password": os.environ.get("STREAMLIT_SECRETS_DB_PASSWORD"),
            "port":     int(os.environ.get("STREAMLIT_SECRETS_DB_PORT", 3306)),
        }
    # Fallback para desarrollo local con secrets.toml
    try:
        return dict(st.secrets["db"])
    except Exception:
        return None

def get_db_connection():
    config = _get_db_config()
    if not config:
        st.error("Error de conexión: No se encontraron credenciales de base de datos.")
        return None
    try:
        return mysql.connector.connect(**config, autocommit=True)
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

def execute_read(query, params=None):
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(query, params or ())
            res = cur.fetchall()
            cur.close(); conn.close()
            return res
        except Exception as e:
            st.error(f"Error de consulta: {e}")
    return []

def execute_write(query, params=None):
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(query, params or ())
            cur.close(); conn.close()
            return True
        except Exception as e:
            st.error(f"Error en base de datos: {e}")
            return False
    return False


# ==================== ESTADO DE SESIÓN ====================
for k, v in {"login": False, "user": "", "role": "", "last_count": 0}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Recuperar sesión desde query params (sobrevive el autorefresh) ──
params = st.query_params
if not st.session_state.login and params.get("u") and params.get("r"):
    st.session_state["login"] = True
    st.session_state["user"]  = params["u"]
    st.session_state["role"]  = params["r"]

# ── Autorefresh inteligente: solo se dispara si el usuario NO está scrolleando ──
# Espera 5 segundos de inactividad de scroll antes de refrescar.
# No usa st_autorefresh ni ningún componente externo.
if st.session_state.get("login"):
    st.markdown("""
    <script>
    (function() {
        var REFRESH_MS   = 30000;  // Refresca cada 30 segundos
        var SCROLL_WAIT  = 5000;   // Espera 5s sin scroll antes de refrescar
        var refreshTimer = null;
        var userScrolling = false;
        var scrollEndTimer = null;

        function doRefresh() {
            if (!userScrolling) {
                window.location.reload();
            }
        }

        function scheduleRefresh() {
            clearTimeout(refreshTimer);
            refreshTimer = setTimeout(doRefresh, REFRESH_MS);
        }

        window.addEventListener('scroll', function() {
            userScrolling = true;
            clearTimeout(refreshTimer);        // Cancelar refresco mientras scrollea
            clearTimeout(scrollEndTimer);
            scrollEndTimer = setTimeout(function() {
                userScrolling = false;
                scheduleRefresh();             // Reprogramar al terminar scroll
            }, SCROLL_WAIT);
        }, { passive: true });

        scheduleRefresh();
    })();
    </script>
    """, unsafe_allow_html=True)


# ==================== LOGIN ====================
if not st.session_state.login:
    st.markdown(
        f'<div style="text-align:center;padding:40px 0 10px;">'
        f'<img src="{LOGO_URL}" width="520" style="border-radius:8px;"></div>',
        unsafe_allow_html=True,
    )
    _, col_c, _ = st.columns([1, 1.3, 1])
    with col_c:
        st.markdown(
            '<div style="background:white;padding:32px;border-radius:16px;'
            'box-shadow:0 6px 28px rgba(0,43,91,0.14);">',
            unsafe_allow_html=True,
        )
        with st.form("login_form"):
            st.markdown(
                f"<h3 style='text-align:center;color:{CARRIER_BLUE};margin-bottom:18px;'>"
                "🔐 Panel de Acceso</h3>",
                unsafe_allow_html=True,
            )
            u_log = st.text_input("👤 Usuario")
            p_log = st.text_input("🔑 Contraseña", type="password")
            if st.form_submit_button("Ingresar al Sistema", use_container_width=True, type="primary"):
                user = execute_read(
                    "SELECT * FROM users WHERE username=%s AND password=%s",
                    (u_log.strip(), p_log.strip()),
                )
                if user:
                    st.session_state.update({
                        "login": True,
                        "user":  user[0]["username"],
                        "role":  user[0]["role"].lower(),
                    })
                    # Guardar sesión en query params para que sobreviva el refresco
                    st.query_params["u"] = user[0]["username"]
                    st.query_params["r"] = user[0]["role"].lower()
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()


# ==================== SIDEBAR ====================
with st.sidebar:
    st.image(LOGO_URL, width=220)
    st.markdown(
        f"<p style='margin:4px 0;font-size:.88rem;'>🕒 <b>{hora_actual}</b> &nbsp;|&nbsp; {fecha_hoy}</p>",
        unsafe_allow_html=True,
    )
    st.markdown("---")
    role_label = "🛡 Administrador" if st.session_state.role == "admin" else "🔧 Técnico"
    st.markdown(
        f"<p style='margin:0;'>👤 <b>{st.session_state.user}</b></p>"
        f"<span style='background:rgba(255,255,255,.18);padding:2px 10px;"
        f"border-radius:20px;font-size:.8rem;'>{role_label}</span>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    if st.session_state.role == "admin":
        menu = st.radio(
            "MENÚ PRINCIPAL",
            ["📊 Dashboard Ejecutivo", "🎯 Control de Asignaciones",
             "📸 Registro de Unidades", "👥 Gestión de Usuarios"],
        )
    else:
        menu = st.radio("ÁREA DE TRABAJO", ["🎯 Mis Tareas", "🔔 Nueva Solicitud"])

    st.markdown("---")
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state["login"]      = False
        st.session_state["user"]       = ""
        st.session_state["role"]       = ""
        st.session_state["last_count"] = 0
        st.query_params.clear()
        st.rerun()


# ==================== DASHBOARD EJECUTIVO ====================
if menu == "📊 Dashboard Ejecutivo":
    st.markdown(
        f'<div class="time-badge">🕒 Tijuana: {hora_actual}</div>'
        f'<div class="main-header">📊 Panel de Rendimiento Operativo</div>',
        unsafe_allow_html=True,
    )

    asig = execute_read("SELECT * FROM asignaciones")
    unid = execute_read("SELECT * FROM unidades")
    df_a = pd.DataFrame(asig) if asig else pd.DataFrame()

    # ── KPIs ──
    total_u = len(unid)
    total_t = len(df_a)
    comp_t  = int((df_a["estado"] == "completada").sum()) if not df_a.empty else 0
    proc_t  = int((df_a["estado"] == "en_proceso").sum()) if not df_a.empty else 0
    pend_t  = int((df_a["estado"] == "pendiente").sum())  if not df_a.empty else 0
    pct_av  = round(comp_t / total_t * 100) if total_t else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    for col, val, lbl, cls in [
        (k1, total_u,       "Total Unidades",  ""),
        (k2, comp_t,        "Completadas",     "green"),
        (k3, proc_t,        "En Proceso",      "amber"),
        (k4, pend_t,        "Pendientes",      "red"),
        (k5, f"{pct_av}%",  "Avance Global",   "purple"),
    ]:
        with col:
            st.markdown(
                f'<div class="kpi-wrap {cls}">'
                f'<div class="kpi-num">{val}</div>'
                f'<div class="kpi-lbl">{lbl}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Estadísticas y gráficas ──
    if not df_a.empty:
        st.markdown('<div class="section-title">📈 Estadísticas por Técnico</div>', unsafe_allow_html=True)
        stats = df_a.groupby("tecnico").agg(
            Total      =("id",     "count"),
            Completadas=("estado", lambda x: (x == "completada").sum()),
            En_Curso   =("estado", lambda x: (x == "en_proceso").sum()),
            Pendientes =("estado", lambda x: (x == "pendiente").sum()),
        ).reset_index()
        stats["Rendimiento %"] = ((stats["Completadas"] / stats["Total"]) * 100).round(0).astype(int)
        st.dataframe(stats.sort_values("Total", ascending=False), use_container_width=True, hide_index=True)

        COLOR_MAP = {
            "completada": "#16a34a", "en_proceso": "#f59e0b",
            "pendiente":  "#dc2626", "solicitado": "#6b7280",
        }
        c1, c2 = st.columns([2, 1])
        with c1:
            fig_b = px.bar(
                df_a, x="tecnico", color="estado",
                title="Carga de Trabajo por Técnico",
                color_discrete_map=COLOR_MAP, template="plotly_white",
            )
            fig_b.update_layout(paper_bgcolor="white", plot_bgcolor="white")
            st.plotly_chart(fig_b, use_container_width=True)
        with c2:
            fig_p = px.pie(
                df_a, names="estado", title="Distribución Global",
                hole=0.52, color_discrete_map=COLOR_MAP, template="plotly_white",
            )
            fig_p.update_layout(paper_bgcolor="white")
            st.plotly_chart(fig_p, use_container_width=True)

    # ── Tabla estatus por unidad ──
 st.markdown('<div class="section-title">📋 Estatus de Proceso y Valores de Operación</div>', unsafe_allow_html=True)
    
    # Obtener datos base
    unid_raw = execute_read("SELECT * FROM unidades")
    # Obtener valores dinámicos registrados
    valores_raw = execute_read("SELECT unit_number, campo, valor FROM valores_registrados")

    if unid_raw:
        df_u = pd.DataFrame(unid_raw)
        
        # Unir valores dinámicos si existen
        if valores_raw:
            df_v = pd.DataFrame(valores_raw)
            # Pivotar: Convierte filas de parámetros en columnas individuales
            df_v_pivot = df_v.pivot(index='unit_number', columns='campo', values='valor').reset_index()
            # Unión (Join) con la tabla principal de unidades
            df_final = pd.merge(df_u, df_v_pivot, on='unit_number', how='left')
        else:
            df_final = df_u

        # Mostrar tabla unificada
        st.dataframe(df_final, use_container_width=True, hide_index=True)

    # ── Descarga de evidencias ──
    st.markdown('<div class="section-title">📂 Descarga de Evidencias por Unidad</div>', unsafe_allow_html=True)
    if unid:
        col_ev1, col_ev2 = st.columns([3, 1])
        with col_ev1:
            u_sel_ev = st.selectbox("Selecciona unidad:", [u["unit_number"] for u in unid], key="ev_sel")
        ev_archivos = execute_read(
            "SELECT nombre_archivo, contenido FROM evidencias WHERE unit_number=%s", (u_sel_ev,)
        )
        with col_ev2:
            st.metric("📸 Fotos", len(ev_archivos))
        if ev_archivos:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "a", zipfile.ZIP_DEFLATED, False) as zf:
                for ev in ev_archivos:
                    zf.writestr(ev["nombre_archivo"], ev["contenido"])
            st.download_button(
                f"📥 Descargar {len(ev_archivos)} fotos — Unidad {u_sel_ev}",
                buf.getvalue(), f"{u_sel_ev}_evidencia.zip", "application/zip",
                use_container_width=True,
            )
        else:
            st.info("Sin fotos cargadas para esta unidad.")

    # ── Reporte maestro Excel ──
    st.markdown('<div class="section-title">📥 Reportes y Descargas</div>', unsafe_allow_html=True)
    if unid:
        df_u = pd.DataFrame(unid)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_u.to_excel(writer, index=False, sheet_name="Series_Unidades")
            if not df_a.empty:
                df_a.to_excel(writer, index=False, sheet_name="Actividades")
        st.download_button(
            "📊 Descargar Reporte Maestro General (Excel)",
            buffer.getvalue(), f"Carrier_Reporte_{fecha_hoy}.xlsx",
            use_container_width=True, type="primary",
        )
        st.markdown("<br>", unsafe_allow_html=True)
        for lote in sorted(df_u["id_lote"].unique()):
            n = len(df_u[df_u["id_lote"] == lote])
            with st.expander(f"📦 Lote: {lote}  ({n} unidades)"):
                st.table(df_u[df_u["id_lote"] == lote][["unit_number"] + list(CAMPOS_SERIES.keys())])


# ==================== CONTROL DE ASIGNACIONES (Admin) ====================
elif menu == "🎯 Control de Asignaciones":
    st.markdown('<div class="main-header">🎯 Gestión de Órdenes de Trabajo</div>', unsafe_allow_html=True)

    sols = execute_read("SELECT * FROM asignaciones WHERE estado='solicitado'")

    # Alerta sonora cuando llegan nuevas solicitudes
    if len(sols) > st.session_state.last_count:
        st.markdown(
            f'<audio autoplay><source src="{SOUND_URL}" type="audio/mp3"></audio>',
            unsafe_allow_html=True,
        )
    st.session_state.last_count = len(sols)

    if not sols:
        st.success("✅ Sin solicitudes pendientes de aprobar.")
    else:
        st.markdown(
            f'<div class="section-title">🔔 Solicitudes Pendientes de Aprobación ({len(sols)})</div>',
            unsafe_allow_html=True,
        )
        for s in sols:
            # Verificar si ya existe completada o activa (otro técnico)
            dup_comp = execute_read(
                "SELECT tecnico FROM asignaciones "
                "WHERE unidad=%s AND actividad_id=%s AND estado='completada'",
                (s["unidad"], s["actividad_id"]),
            )
            dup_activa = execute_read(
                "SELECT tecnico, estado FROM asignaciones "
                "WHERE unidad=%s AND actividad_id=%s "
                "AND estado IN ('pendiente','en_proceso') AND id != %s",
                (s["unidad"], s["actividad_id"], s["id"]),
            )

            tiene_alerta = bool(dup_comp or dup_activa)

            with st.container():
                col_inf, col_ap, col_den = st.columns([4, 1, 1])
                with col_inf:
                    if tiene_alerta:
                        st.error(
                            f"🚨 **{s['tecnico']}** solicita **{s['actividad_id']}** — Unidad: **{s['unidad']}**"
                        )
                    else:
                        st.warning(
                            f"📋 **{s['tecnico']}** solicita **{s['actividad_id']}** — Unidad: **{s['unidad']}**"
                        )

                    # Alertas de seguridad detalladas
                    if dup_comp:
                        tecnicos_comp = ", ".join([d["tecnico"] for d in dup_comp])
                        st.markdown(
                            f'<div class="bloqueo-card"><p>'
                            f'⛔ ACTIVIDAD YA COMPLETADA — Completada anteriormente por: <b>{tecnicos_comp}</b>. '
                            f'Aprobar implica permitir una repetición de esta actividad.'
                            f'</p></div>',
                            unsafe_allow_html=True,
                        )
                    if dup_activa:
                        for da in dup_activa:
                            st.markdown(
                                f'<div class="bloqueo-card"><p>'
                                f'⚠️ TAREA DUPLICADA EN CURSO — <b>{da["tecnico"]}</b> ya tiene '
                                f'esta misma actividad en estado <b>{da["estado"]}</b>.'
                                f'</p></div>',
                                unsafe_allow_html=True,
                            )

                if col_ap.button("✅ Aprobar", key=f"ap_{s['id']}", use_container_width=True):
                    execute_write("UPDATE asignaciones SET estado='pendiente' WHERE id=%s", (s["id"],))
                    st.rerun()
                if col_den.button("❌ Rechazar", key=f"de_{s['id']}", use_container_width=True):
                    execute_write("DELETE FROM asignaciones WHERE id=%s", (s["id"],))
                    st.rerun()

            st.markdown("<hr style='margin:6px 0;border-color:#e5eaf2;'>", unsafe_allow_html=True)

    # Asignación manual
    st.markdown('<div class="section-title">➕ Asignación Directa</div>', unsafe_allow_html=True)
    u_db = execute_read("SELECT unit_number, id_lote FROM unidades")
    t_db = execute_read("SELECT username FROM users WHERE role='tecnico'")
    with st.form("manual_assign"):
        c1, c2, c3 = st.columns(3)
        u_sel = c1.selectbox("Unidad",    [f"{x['id_lote']} - {x['unit_number']}" for x in u_db])
        t_sel = c2.selectbox("Técnico",   [x["username"] for x in t_db])
        a_sel = c3.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.form_submit_button("📋 Crear Orden", use_container_width=True, type="primary"):
            execute_write(
                "INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) "
                "VALUES (%s,%s,%s,'pendiente')",
                (u_sel.split(" - ")[1], a_sel, t_sel),
            )
            st.success("✅ Orden creada correctamente.")
            st.rerun()


# ==================== MIS TAREAS (Técnico) ====================
elif menu == "🎯 Mis Tareas":
    st.markdown('<div class="main-header">🎯 Mis Actividades</div>', unsafe_allow_html=True)

    tareas = execute_read(
        "SELECT * FROM asignaciones WHERE tecnico=%s AND estado IN ('pendiente','en_proceso')",
        (st.session_state.user,),
    )

    if not tareas:
        st.info("✅ No tienes tareas asignadas en este momento.")

    for t in tareas:
        icono = "⏳" if t["estado"] == "pendiente" else "▶️"
        with st.expander(f"{icono} Unidad **{t['unidad']}** — {t['actividad_id']}"):

            # ── PENDIENTE: iniciar ──
            if t["estado"] == "pendiente":
                st.markdown(
                    "<p style='color:#d97706;font-weight:600;'>Estado: Pendiente de inicio</p>",
                    unsafe_allow_html=True,
                )
                if st.button("▶️ Iniciar Actividad", key=f"ini_{t['id']}",
                             use_container_width=True, type="primary"):
                    execute_write(
                        "UPDATE asignaciones SET estado='en_proceso', fecha_inicio=%s WHERE id=%s",
                        (datetime.now(tijuana_tz), t["id"]),
                    )
                    st.rerun()

            # ── EN PROCESO ──
            else:
                st.markdown(
                    "<p style='color:#16a34a;font-weight:600;'>▶️ Actividad en proceso</p>",
                    unsafe_allow_html=True,
                )

                # ── EVIDENCIA: solo subir archivos ──
                if t["actividad_id"].lower() == "evidencia":

                    # Conteo de fotos ya guardadas
                    fotos_prev = execute_read(
                        "SELECT COUNT(*) AS total FROM evidencias "
                        "WHERE unit_number=%s AND tecnico=%s",
                        (t["unidad"], st.session_state.user),
                    )
                    total_prev = fotos_prev[0]["total"] if fotos_prev else 0
                    restantes  = MAX_FOTOS - total_prev

                    st.markdown(
                        f'<div class="evidencia-info"><p>'
                        f'📋 Unidad: <b>{t["unidad"]}</b> &nbsp;|&nbsp; '
                        f'Técnico: <b>{st.session_state.user}</b><br>'
                        f'Límite: <b>{MAX_FOTOS} fotos</b> por tarea &nbsp;·&nbsp; '
                        f'Ya guardadas: <b>{total_prev}</b> &nbsp;·&nbsp; '
                        f'Disponibles: <b>{restantes}</b>'
                        f'</p></div>',
                        unsafe_allow_html=True,
                    )

                    if restantes <= 0:
                        st.warning(
                            f"⚠️ Ya alcanzaste el límite de {MAX_FOTOS} fotos para esta unidad. "
                            "Finaliza la actividad o contacta al administrador."
                        )
                    else:
                        archivos = st.file_uploader(
                            f"📁 Selecciona hasta {restantes} foto(s) — JPG, JPEG o PNG",
                            accept_multiple_files=True,
                            type=["jpg", "jpeg", "png"],
                            key=f"fup_{t['id']}",
                            help=f"Puedes subir varias fotos a la vez. Máximo {restantes} en esta carga.",
                        )

                        if archivos:
                            exceso = len(archivos) > restantes
                            if exceso:
                                st.warning(
                                    f"⚠️ Seleccionaste {len(archivos)} fotos pero solo "
                                    f"puedes subir {restantes} más. Se tomarán las primeras {restantes}."
                                )
                                archivos = archivos[:restantes]

                            # Previsualizacion en grid
                            st.markdown(
                                f'<div class="fotos-badge">📸 {len(archivos)} foto(s) lista(s) para guardar</div>',
                                unsafe_allow_html=True,
                            )
                            cols_prev = st.columns(min(len(archivos), 5))
                            for idx, arc in enumerate(archivos):
                                with cols_prev[idx % 5]:
                                    st.image(arc, use_container_width=True, caption=arc.name[:18])

                            st.markdown("<br>", unsafe_allow_html=True)
                            if st.button(
                                f"💾 Guardar {len(archivos)} foto(s)",
                                key=f"savef_{t['id']}",
                                use_container_width=True,
                                type="primary",
                            ):
                                barra = st.progress(0, text="Iniciando...")
                                errores = 0
                                for i, arc in enumerate(archivos):
                                    arc.seek(0)
                                    ok = execute_write(
                                        "INSERT INTO evidencias "
                                        "(unit_number, nombre_archivo, contenido, tecnico) "
                                        "VALUES (%s,%s,%s,%s)",
                                        (t["unidad"], arc.name, arc.read(), st.session_state.user),
                                    )
                                    if not ok:
                                        errores += 1
                                    barra.progress(
                                        (i + 1) / len(archivos),
                                        text=f"Guardando {i+1} de {len(archivos)}: {arc.name[:30]}",
                                    )
                                if errores == 0:
                                    st.success(f"✅ {len(archivos)} foto(s) guardada(s) correctamente.")
                                else:
                                    st.warning(f"⚠️ {len(archivos)-errores} guardadas, {errores} fallaron.")
                                st.rerun()

                    st.markdown("---")
                    col_fin1, col_fin2 = st.columns([3, 1])
                    with col_fin1:
                        st.markdown(
                            f"<p style='font-size:.85rem;color:#6b7280;margin:6px 0 0;'>"
                            f"Al finalizar se cerrará la tarea. Total guardadas: <b>{total_prev}</b></p>",
                            unsafe_allow_html=True,
                        )
                    with col_fin2:
                        if st.button("✅ Finalizar", key=f"finev_{t['id']}", use_container_width=True):
                            execute_write(
                                "UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s",
                                (datetime.now(tijuana_tz), t["id"]),
                            )
                            st.success("✅ Evidencia completada.")
                            st.rerun()

                # ── TOMA DE SERIES ──
                elif t["actividad_id"].lower() == "toma de series":# ── TOMA DE VALORES DINÁMICA ──
                elif t["actividad_id"].lower() == "toma de valores":
                    st.markdown('<div class="section-title">📝 Registro de Parámetros</div>', unsafe_allow_html=True)
                    
                    # Campos definidos previamente (puedes hardcodearlos o traerlos de una tabla de config)
                    campos_medicion = ["PSI Aceite", "Voltaje Bat", "Temperatura Salida", "Nivel Combustible"]
                    
                    with st.form(f"val_form_{t['id']}"):
                        c1, c2 = st.columns(2)
                        respuestas = {}
                        for i, campo in enumerate(campos_medicion):
                            target_col = c1 if i % 2 == 0 else c2
                            respuestas[campo] = target_col.text_input(campo, key=f"v_{t['id']}_{i}")
                        
                        if st.form_submit_button("💾 Finalizar y Guardar Valores", use_container_width=True, type="primary"):
                            for campo, valor in respuestas.items():
                                execute_write(
                                    "INSERT INTO valores_registrados (unit_number, campo, valor, tecnico) VALUES (%s, %s, %s, %s)",
                                    (t["unidad"], campo, valor, st.session_state.user)
                                )
                            execute_write(
                                "UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s",
                                (datetime.now(tijuana_tz), t["id"])
                            )
                            st.rerun()
                    with st.form(f"ser_{t['id']}"):
                        st.markdown(
                            "<p style='font-size:.9rem;color:#374151;margin-bottom:10px;'>"
                            "Ingresa los seriales de cada componente:</p>",
                            unsafe_allow_html=True,
                        )
                        items = list(CAMPOS_SERIES.items())
                        mid   = (len(items) + 1) // 2
                        col_a, col_b = st.columns(2)
                        res = {}
                        for i, (k, v) in enumerate(items):
                            target = col_a if i < mid else col_b
                            res[k] = target.text_input(v, key=f"s_{t['id']}_{k}")
                        if st.form_submit_button("💾 Guardar Series",
                                                  use_container_width=True, type="primary"):
                            set_q = ", ".join([f"{k}=%s" for k in res])
                            execute_write(
                                f"UPDATE unidades SET {set_q} WHERE unit_number=%s",
                                list(res.values()) + [t["unidad"]],
                            )
                            execute_write(
                                "UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s",
                                (datetime.now(tijuana_tz), t["id"]),
                            )
                            st.rerun()

                # ── ACTIVIDAD GENÉRICA ──
                else:
                    if st.button("✅ Terminar Actividad", key=f"fin_{t['id']}",
                                 use_container_width=True, type="primary"):
                        execute_write(
                            "UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s",
                            (datetime.now(tijuana_tz), t["id"]),
                        )
                        st.rerun()


# ==================== NUEVA SOLICITUD (Técnico) ====================
elif menu == "🔔 Nueva Solicitud":
    st.markdown('<div class="main-header">🔔 Solicitar Actividad</div>', unsafe_allow_html=True)

    u_db = execute_read("SELECT unit_number, id_lote FROM unidades")

    with st.form("sol_f"):
        u_sel = st.selectbox("Unidad",    [f"{x['id_lote']} - {x['unit_number']}" for x in u_db])
        a_sel = st.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.form_submit_button("📤 Enviar Solicitud", use_container_width=True, type="primary"):
            unidad_sel = u_sel.split(" - ")[1]

            # ── VALIDACIÓN 1: ya tiene esta tarea activa (pendiente, solicitada o en proceso) ──
            activa = execute_read(
                "SELECT id, estado FROM asignaciones "
                "WHERE tecnico=%s AND unidad=%s AND actividad_id=%s "
                "AND estado IN ('solicitado','pendiente','en_proceso')",
                (st.session_state.user, unidad_sel, a_sel),
            )
            if activa:
                estado_act = activa[0]["estado"]
                etiquetas  = {
                    "solicitado": "esperando aprobación del administrador",
                    "pendiente":  "pendiente de iniciar",
                    "en_proceso": "actualmente en proceso",
                }
                st.error(
                    f"🚫 Ya tienes esta actividad registrada para la unidad **{unidad_sel}** "
                    f"({etiquetas.get(estado_act, estado_act)}). "
                    f"No puedes solicitarla de nuevo hasta que sea completada o cancelada por el administrador."
                )

            else:
                # ── VALIDACIÓN 2: ya fue completada por alguien ──
                completada = execute_read(
                    "SELECT tecnico FROM asignaciones "
                    "WHERE unidad=%s AND actividad_id=%s AND estado='completada'",
                    (unidad_sel, a_sel),
                )
                if completada:
                    st.warning(
                        f"⚠️ La actividad **{a_sel}** en la unidad **{unidad_sel}** "
                        f"ya fue completada por **{completada[0]['tecnico']}**. "
                        "Tu solicitud se enviará al administrador para autorización especial."
                    )
                    # Se inserta igualmente pero el admin verá la alerta de duplicado al aprobar
                    execute_write(
                        "INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) "
                        "VALUES (%s,%s,%s,'solicitado')",
                        (unidad_sel, a_sel, st.session_state.user),
                    )
                    st.toast("📨 Solicitud enviada — requiere autorización especial del administrador")
                    st.rerun()
                else:
                    # ── Solicitud limpia ──
                    execute_write(
                        "INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) "
                        "VALUES (%s,%s,%s,'solicitado')",
                        (unidad_sel, a_sel, st.session_state.user),
                    )
                    st.toast("✅ Solicitud enviada correctamente")
                    st.rerun()

    # ── Historial de solicitudes del técnico ──
    st.markdown('<div class="section-title">📋 Mis Solicitudes Recientes</div>', unsafe_allow_html=True)
    historial = execute_read(
        "SELECT unidad, actividad_id, estado, fecha_inicio, fecha_fin "
        "FROM asignaciones WHERE tecnico=%s ORDER BY id DESC LIMIT 20",
        (st.session_state.user,),
    )
    if historial:
        ESTADO_BADGE = {
            "solicitado":  ("🟡", "#fef9c3", "#854d0e"),
            "pendiente":   ("🟠", "#fff7ed", "#9a3412"),
            "en_proceso":  ("🔵", "#eff6ff", "#1e40af"),
            "completada":  ("🟢", "#f0fdf4", "#166534"),
        }
        for h in historial:
            icono, bg, color = ESTADO_BADGE.get(h["estado"], ("⚪", "#f9fafb", "#374151"))
            st.markdown(
                f'<div style="background:{bg};border-radius:8px;padding:10px 16px;'
                f'margin-bottom:6px;border-left:4px solid {color};">'
                f'<span style="font-weight:600;color:{color};">{icono} {h["estado"].upper()}</span>'
                f' &nbsp;·&nbsp; <b>{h["unidad"]}</b> — {h["actividad_id"]}'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("Sin solicitudes registradas.")
# ==================== INVENTARIOS (Admin) ====================
elif menu == "📦 Inventarios":
    st.markdown('<div class="main-header">📦 Inventario de Refacciones y Equipos</div>', unsafe_allow_html=True)
    
    # Carga inicial desde DB
    res_inv = execute_read("SELECT * FROM inventarios")
    df_inv = pd.DataFrame(res_inv) if res_inv else pd.DataFrame(columns=["ID", "Item", "Cantidad", "Ubicacion"])

    st.info("💡 Puedes editar celdas, agregar filas al final o eliminar seleccionando y presionando Suprimir.")
    
    # Editor dinámico
    df_editado = st.data_editor(
        df_inv, 
        num_rows="dynamic", 
        use_container_width=True, 
        key="editor_inv",
        hide_index=True
    )

    if st.button("💾 Guardar Cambios en Inventario", type="primary", use_container_width=True):
        execute_write("DELETE FROM inventarios")
        for _, row in df_editado.iterrows():
            if row.get('Item'): # Evitar guardar filas vacías
                execute_write(
                    "INSERT INTO inventarios (item, cantidad, ubicacion) VALUES (%s, %s, %s)",
                    (row.get('Item'), row.get('Cantidad'), row.get('Ubicacion'))
                )
        st.success("✅ Inventario sincronizado.")
        st.rerun()

# ==================== REGISTRO DE UNIDADES (Admin) ====================
elif menu == "📸 Registro de Unidades":
    st.markdown('<div class="main-header">📸 Registro Maestro de Unidades</div>', unsafe_allow_html=True)
    with st.form("reg_u"):
        col1, col2 = st.columns(2)
        u_num  = col1.text_input("Número Económico")
        l_num  = col1.text_input("Número de Lote")
        campo  = col2.selectbox("Campo a Registrar", ["Ninguno"] + list(CAMPOS_SERIES.keys()))
        valor  = col2.text_input("Valor del Serial")
        if st.form_submit_button("💾 Guardar Registro", use_container_width=True, type="primary"):
            if campo != "Ninguno":
                execute_write(
                    f"INSERT INTO unidades (unit_number, id_lote, {campo}) VALUES (%s,%s,%s) "
                    f"ON DUPLICATE KEY UPDATE id_lote=%s, {campo}=%s",
                    (u_num, l_num, valor, l_num, valor),
                )
            else:
                execute_write(
                    "INSERT INTO unidades (unit_number, id_lote) VALUES (%s,%s) "
                    "ON DUPLICATE KEY UPDATE id_lote=%s",
                    (u_num, l_num, l_num),
                )
            st.success("✅ Registro guardado correctamente")
            st.rerun()


# ==================== GESTIÓN DE USUARIOS (Admin) ====================
elif menu == "👥 Gestión de Usuarios":
    st.markdown('<div class="main-header">👥 Usuarios del Sistema</div>', unsafe_allow_html=True)

    # Lista de usuarios existentes
    usuarios = execute_read("SELECT username, role FROM users ORDER BY role, username")
    if usuarios:
        st.markdown('<div class="section-title">👥 Usuarios Registrados</div>', unsafe_allow_html=True)
        df_users = pd.DataFrame(usuarios)
        df_users.columns = ["Usuario", "Rol"]
        st.dataframe(df_users, use_container_width=True, hide_index=True)

    # Formulario nuevo usuario
    st.markdown('<div class="section-title">➕ Crear Nuevo Usuario</div>', unsafe_allow_html=True)
    with st.form("u_f"):
        c1, c2, c3 = st.columns(3)
        n_u = c1.text_input("Nombre de Usuario")
        n_p = c2.text_input("Contraseña", type="password")
        n_r = c3.selectbox("Rol", ["tecnico", "admin"])
        if st.form_submit_button("👤 Crear Usuario", use_container_width=True, type="primary"):
            if n_u and n_p:
                execute_write(
                    "INSERT INTO users (username, password, role) VALUES (%s,%s,%s)",
                    (n_u, n_p, n_r),
                )
                st.success(f"✅ Usuario **{n_u}** creado correctamente.")
                st.rerun()
            else:
                st.warning("⚠️ Completa todos los campos antes de guardar.")
