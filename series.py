import streamlit as st
import pandas as pd
import mysql.connector
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io
import pytz
import zipfile
import os
import json
import time
import threading
import queue
import base64 as _b64
import pathlib as _pl

# ==================== CONFIGURACIÓN INICIAL ====================
st.set_page_config(
    page_title="Carrier Transicold – Sistema Operativo",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="❄️",
)

tijuana_tz = pytz.timezone('America/Tijuana')
ahora_tj = datetime.now(tijuana_tz)
fecha_hoy = ahora_tj.strftime('%Y-%m-%d')
hora_actual = ahora_tj.strftime('%H:%M:%S')

CARRIER_BLUE    = "#002B5B"
CARRIER_ACCENT  = "#0057A8"
CARRIER_LIGHT   = "#E8F0FB"
CARRIER_SUCCESS = "#16a34a"
CARRIER_WARN    = "#d97706"
CARRIER_DANGER  = "#dc2626"

LOGO_URL = "https://raw.githubusercontent.com/Jesusalan0102/app-escaneo-series/main/carrierlogo.jpg"
_logo_path = _pl.Path(__file__).parent / "carrierlogo.jpg"
if _logo_path.exists():
    _logo_b64 = _b64.b64encode(_logo_path.read_bytes()).decode()
    LOGO_DATA_URI = f"data:image/jpeg;base64,{_logo_b64}"
else:
    LOGO_DATA_URI = LOGO_URL

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

MAX_FOTOS = 100

# ==================== CSS PREMIUM (COMPLETO) ====================
st.markdown(f"""
<style>
/* ══ OCULTAR BRANDING STREAMLIT ══ */
header[data-testid="stHeader"] {{ display: none !important; }}
footer {{ display: none !important; }}
#MainMenu {{ display: none !important; }}
.stDeployButton {{ display: none !important; }}
[data-testid="stToolbar"] {{ display: none !important; }}
[data-testid="manage-app-button"] {{ display: none !important; }}
[data-testid="stStatusWidget"] {{ display: none !important; }}
.block-container {{ padding-top: 1.5rem !important; }}

/* ══ FORZAR SIDEBAR SIEMPRE ABIERTO ══ */
section[data-testid="stSidebar"] {{
    transform: none !important;
    visibility: visible !important;
    width: 21rem !important;
    min-width: 21rem !important;
    display: block !important;
    transition: transform 0.28s ease !important;
}}
button[data-testid="baseButton-header"],
[data-testid="stSidebarCollapsedControl"] {{
    display: none !important;
}}

/* ══ BASE ══ */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
*, *::before, *::after {{ box-sizing: border-box; }}
.stApp {{
    background: linear-gradient(135deg, #EEF2F9 0%, #F5F7FB 60%, #EAF0FB 100%) !important;
    font-family: 'Inter', sans-serif !important;
}}

/* ══ SIDEBAR PREMIUM ══ */
section[data-testid="stSidebar"] > div:first-child {{
    background: linear-gradient(180deg, {CARRIER_BLUE} 0%, #01418a 60%, #0056b3 100%) !important;
    border-right: 1px solid rgba(255,255,255,0.08);
    padding-top: 0.5rem;
}}
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span {{ color: #e0eaff !important; }}
section[data-testid="stSidebar"] .stRadio > label {{
    color: white !important; font-weight: 600; font-size: 0.72rem; letter-spacing: 1.5px;
}}
section[data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,0.15) !important; }}
section[data-testid="stSidebar"] button {{
    background: rgba(255,255,255,0.1) !important;
    color: white !important;
    border-radius: 10px !important;
}}

/* ══ HEADER ══ */
.main-header {{
    font-size: 1.75rem; font-weight: 800; color: {CARRIER_BLUE};
    border-bottom: 3px solid {CARRIER_ACCENT};
    padding-bottom: 12px; margin-bottom: 24px;
    display: flex; align-items: center; gap: 12px;
}}
.section-title {{
    font-size: 0.92rem; font-weight: 700; color: {CARRIER_BLUE};
    border-left: 4px solid {CARRIER_ACCENT};
    padding: 9px 14px; margin: 22px 0 14px 0;
    background: white; border-radius: 0 8px 8px 0;
    box-shadow: 0 2px 8px rgba(0,43,91,0.07);
}}

/* ══ KPI CARDS ══ */
.kpi-wrap {{
    background: white; border-radius: 16px;
    padding: 20px 22px 18px; text-align: center;
    box-shadow: 0 4px 20px rgba(0,43,91,0.08);
    border-top: 5px solid {CARRIER_ACCENT};
    transition: transform 0.2s;
}}
.kpi-wrap:hover {{ transform: translateY(-3px); }}
.kpi-wrap.green  {{ border-top-color: {CARRIER_SUCCESS}; }}
.kpi-wrap.amber  {{ border-top-color: {CARRIER_WARN}; }}
.kpi-wrap.red    {{ border-top-color: {CARRIER_DANGER}; }}
.kpi-wrap.purple {{ border-top-color: #7c3aed; }}
.kpi-num {{
    font-size: 2.4rem; font-weight: 800; color: {CARRIER_BLUE};
    line-height: 1.1;
}}
.kpi-lbl {{
    font-size: 0.73rem; color: #6b7280; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.6px; margin-top: 6px;
}}

/* ══ TIME BADGE ══ */
.time-badge {{
    background: {CARRIER_BLUE}; color: white;
    padding: 6px 16px; border-radius: 24px;
    font-size: 0.82rem; font-weight: 600; float: right;
    margin-top: 2px;
}}

/* ══ EXPANDERS ══ */
div[data-testid="stExpander"] {{
    background: white; border-radius: 12px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06);
    border: 1px solid #e2e8f2; margin-bottom: 10px;
}}

/* ══ BUTTONS ══ */
.stButton > button {{
    border-radius: 10px; font-weight: 600;
    transition: all 0.2s ease;
}}

/* ══ FORMS ══ */
div[data-testid="stForm"] {{
    background: white; border-radius: 14px;
    padding: 22px 26px;
    box-shadow: 0 3px 14px rgba(0,43,91,0.07);
    border: 1px solid #e2e8f2;
}}

/* ══ ALERT CARDS ══ */
.bloqueo-card {{
    background: #fef2f2; border: 1.5px solid #fca5a5;
    border-left: 5px solid {CARRIER_DANGER}; border-radius: 10px;
    padding: 14px 18px; margin: 8px 0;
}}
.evidencia-info {{
    background: #eff6ff; border: 1px solid #bfdbfe;
    border-left: 5px solid #3b82f6; border-radius: 10px;
    padding: 12px 18px; margin-bottom: 14px;
}}
.fotos-badge {{
    display: inline-block; background: #f0fdf4;
    border: 1px solid #86efac; border-radius: 20px;
    padding: 4px 14px; font-size: .85rem;
    color: #166534; font-weight: 600; margin-top: 10px;
}}
.inv-info-bar {{
    background: linear-gradient(90deg, {CARRIER_BLUE} 0%, {CARRIER_ACCENT} 100%);
    color: white; padding: 14px 20px; border-radius: 12px;
    margin-bottom: 16px;
}}
.tv-field-badge {{
    background: {CARRIER_LIGHT}; border: 1px solid #c3d4f0;
    border-radius: 8px; padding: 6px 12px;
    font-size: 0.82rem; color: {CARRIER_BLUE}; font-weight: 600;
    display: inline-block; margin-bottom: 8px;
}}
.login-card {{
    background: white; padding: 36px 40px; border-radius: 20px;
    box-shadow: 0 12px 40px rgba(0,43,91,0.18);
}}
.user-chip {{
    background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.22);
    border-radius: 50px; padding: 6px 14px;
    color: white !important; font-size: 0.82rem; font-weight: 500;
    display: inline-block; margin-top: 4px;
}}
[data-testid="stDataFrame"] {{
    border-radius: 10px; overflow: hidden;
    box-shadow: 0 2px 10px rgba(0,43,91,0.06);
}}

/* ══ RESPONSIVE ══ */
@media (max-width: 768px) {{
    .main-header {{ font-size: 1.2rem; }}
    .kpi-num {{ font-size: 1.6rem; }}
    .login-card {{ padding: 20px 16px; }}
}}
</style>
""", unsafe_allow_html=True)

# ==================== BASE DE DATOS (CON HILOS Y CACHÉ) ====================
def _get_db_config():
    import os
    # Credenciales directas (funciona en todos lados)
    config = {
        "host": "bmffi0bgsqnener2omcu-mysql.services.clever-cloud.com",
        "database": "bmffi0bgsqnener2omcu",
        "user": "uo8vbdsnvm2ojwta",
        "password": "aXSKib5oxXDEwjlozeQP",
        "port": 3306,
        "connection_timeout": 30,
        "autocommit": True,
        "use_pure": True,
    }
    # Si existen variables de entorno, usarlas (Streamlit Cloud)
    env_host = os.environ.get("STREAMLIT_SECRETS_DB_HOST")
    if env_host:
        return {
            "host": env_host,
            "database": os.environ.get("STREAMLIT_SECRETS_DB_DATABASE"),
            "user": os.environ.get("STREAMLIT_SECRETS_DB_USER"),
            "password": os.environ.get("STREAMLIT_SECRETS_DB_PASSWORD"),
            "port": int(os.environ.get("STREAMLIT_SECRETS_DB_PORT", 3306)),
            "connection_timeout": 30,
            "autocommit": True,
            "use_pure": True,
        }
    return config

_db_lock = threading.RLock()
_db_conn_holder = [None]
_wq = queue.Queue()
_wq_ready = threading.Event()

def _open_conn():
    config = _get_db_config()
    if not config:
        return None
    for intento in range(5):
        try:
            conn = mysql.connector.connect(**config)
            conn.ping(reconnect=True, attempts=1, delay=1)
            return conn
        except Exception:
            if intento == 4:
                return None
            time.sleep(1.5 ** (intento + 1))
    return None

def _get_conn():
    with _db_lock:
        conn = _db_conn_holder[0]
        try:
            if conn and conn.is_connected():
                conn.ping(reconnect=True, attempts=2, delay=1)
                return conn
        except Exception:
            conn = None
        conn = _open_conn()
        _db_conn_holder[0] = conn
        return conn

def _write_worker():
    _wq_ready.set()
    while True:
        item = _wq.get()
        if item is None:
            break
        query, params, ev, box = item
        ok = False
        for _ in range(3):
            conn = _get_conn()
            if conn is None:
                time.sleep(1)
                continue
            try:
                with _db_lock:
                    cur = conn.cursor()
                    cur.execute(query, params or ())
                    cur.close()
                ok = True
                break
            except Exception:
                time.sleep(0.8)
        box.append(ok)
        if ev:
            ev.set()
        _wq.task_done()

_wt = threading.Thread(target=_write_worker, daemon=True)
_wt.start()
_wq_ready.wait(timeout=3)

@st.cache_data(ttl=45, show_spinner=False)
def _cached_read(query: str, params: tuple):
    conn = _get_conn()
    if conn is None:
        return []
    try:
        with _db_lock:
            cur = conn.cursor(dictionary=True)
            cur.execute(query, params)
            res = cur.fetchall()
            cur.close()
        return res
    except Exception:
        return []

def execute_read(query, params=None):
    return _cached_read(query, tuple(params) if params else ())

def _invalidate_cache():
    _cached_read.clear()

def execute_write(query, params=None, wait=True):
    ev = threading.Event() if wait else None
    box = []
    _wq.put((query, params, ev, box))
    if wait and ev:
        ev.wait(timeout=6)
        ok = bool(box and box[0])
    else:
        ok = True
    if ok:
        _invalidate_cache()
    return ok

def init_extra_tables():
    queries = [
        """CREATE TABLE IF NOT EXISTS inventario_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            tabla_nombre VARCHAR(120) DEFAULT 'Principal',
            fila_idx INT NOT NULL,
            col_nombre VARCHAR(120) NOT NULL,
            valor TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS inventario_columnas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            tabla_nombre VARCHAR(120) DEFAULT 'Principal',
            col_nombre VARCHAR(120) NOT NULL,
            col_orden INT DEFAULT 0
        )""",
        """CREATE TABLE IF NOT EXISTS toma_valores_campos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            campo_nombre VARCHAR(200) NOT NULL,
            campo_orden INT DEFAULT 0
        )""",
        """CREATE TABLE IF NOT EXISTS toma_valores_datos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            asignacion_id INT NOT NULL,
            campo_nombre VARCHAR(200) NOT NULL,
            valor TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE,
            password VARCHAR(255),
            role VARCHAR(20)
        )""",
        """CREATE TABLE IF NOT EXISTS unidades (
            unit_number VARCHAR(50) PRIMARY KEY,
            id_lote VARCHAR(50),
            vin_number VARCHAR(50),
            reefer_serial VARCHAR(100),
            reefer_model VARCHAR(100),
            evaporator_serial_mjs11 VARCHAR(100),
            evaporator_serial_mjd22 VARCHAR(100),
            engine_serial VARCHAR(100),
            compressor_serial VARCHAR(100),
            generator_serial VARCHAR(100),
            battery_charger_serial VARCHAR(100)
        )""",
        """CREATE TABLE IF NOT EXISTS asignaciones (
            id INT AUTO_INCREMENT PRIMARY KEY,
            unidad VARCHAR(50),
            actividad_id VARCHAR(50),
            tecnico VARCHAR(50),
            estado VARCHAR(20),
            fecha_inicio TIMESTAMP NULL,
            fecha_fin TIMESTAMP NULL,
            ticket_id INT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS evidencias (
            id INT AUTO_INCREMENT PRIMARY KEY,
            unit_number VARCHAR(50),
            nombre_archivo VARCHAR(255),
            contenido LONGBLOB,
            tecnico VARCHAR(50),
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS tickets (
            id INT AUTO_INCREMENT PRIMARY KEY,
            ticket_num INT NOT NULL UNIQUE,
            unit_number VARCHAR(50) NOT NULL,
            vin_number VARCHAR(50),
            descripcion TEXT,
            atendido BOOLEAN DEFAULT FALSE,
            reporte_enviado BOOLEAN DEFAULT FALSE,
            creado_por VARCHAR(50),
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_atencion TIMESTAMP NULL,
            fecha_reporte TIMESTAMP NULL
        )""",
        """CREATE TABLE IF NOT EXISTS comentarios_actividades (
            id INT AUTO_INCREMENT PRIMARY KEY,
            asignacion_id INT NOT NULL,
            tecnico VARCHAR(50),
            comentario TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
    ]
    for q in queries:
        execute_write(q)
    # Asegurar columna ticket_id en asignaciones
    try:
        execute_write("ALTER TABLE asignaciones ADD COLUMN ticket_id INT NULL", wait=False)
    except:
        pass

threading.Thread(target=init_extra_tables, daemon=True).start()

# ==================== ESTADO DE SESIÓN ====================
defaults = {
    "login": False, "user": "", "role": "", "last_count": 0, "menu_sel": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

params = st.query_params
if not st.session_state.login and params.get("u") and params.get("r"):
    st.session_state.update({"login": True, "user": params["u"], "role": params["r"]})
if params.get("m") and st.session_state.menu_sel is None:
    st.session_state.menu_sel = params["m"]

# ==================== LOGIN ====================
if not st.session_state.login:
    if "_login_u" not in st.session_state:
        st.session_state._login_u = ""
    if "_login_p" not in st.session_state:
        st.session_state._login_p = ""
    if "_login_err" not in st.session_state:
        st.session_state._login_err = ""

    st.markdown(f'<div style="text-align:center;padding:30px 0 16px;"><img src="{LOGO_DATA_URI}" width="340" style="border-radius:12px;"></div>', unsafe_allow_html=True)
    _, col_c, _ = st.columns([1, 2, 1])
    with col_c:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align:center;color:{CARRIER_BLUE};'>Carrier Transicold</h3><p style='text-align:center;color:#6b7280;'>Sistema Operativo — Panel de Acceso</p>", unsafe_allow_html=True)

        u_log = st.text_input("Usuario", key="_login_u", placeholder="Ingresa tu usuario")
        p_log = st.text_input("Contraseña", key="_login_p", type="password", placeholder="Ingresa tu contraseña")

        if st.session_state._login_err:
            st.error(st.session_state._login_err)

        if st.button("Ingresar al Sistema", use_container_width=True, type="primary"):
            st.session_state._login_err = ""
            _u = st.session_state._login_u.strip()
            _p = st.session_state._login_p.strip()
            if not _u or not _p:
                st.session_state._login_err = "⚠️ Ingresa usuario y contraseña."
                st.rerun()
            else:
                with st.spinner("Verificando..."):
                    def direct_read(q, p):
                        config = _get_db_config()
                        if not config:
                            return None
                        conn = None
                        try:
                            conn = mysql.connector.connect(**config)
                            cur = conn.cursor(dictionary=True)
                            cur.execute(q, p)
                            res = cur.fetchall()
                            cur.close()
                            return res if res is not None else []
                        except Exception:
                            return None
                        finally:
                            if conn and conn.is_connected():
                                conn.close()
                    user = direct_read("SELECT * FROM users WHERE username=%s AND password=%s", (_u, _p))
                if user is None:
                    st.session_state._login_err = "❌ No se pudo conectar a la base de datos."
                    st.rerun()
                elif len(user) == 0:
                    st.session_state._login_err = "❌ Credenciales incorrectas."
                    st.rerun()
                else:
                    st.session_state.update({"login": True, "user": user[0]["username"], "role": user[0]["role"].lower()})
                    st.query_params["u"] = user[0]["username"]
                    st.query_params["r"] = user[0]["role"].lower()
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==================== ACTUALIZACIÓN EN VIVO (SOLO SI LOGUEADO) ====================
if st.session_state.login:
    _sols_count = len(execute_read("SELECT id FROM asignaciones WHERE estado='solicitado'"))
    st.markdown(f"""
    <script>
    (function() {{
        if (window.__CT_ENGINE_STARTED__) return;
        window.__CT_ENGINE_STARTED__ = true;
        window.__CT_LAST_COUNT__ = {_sols_count};
        function tickClock() {{
            var now = new Date();
            var t = now.toLocaleTimeString("es-MX", {{ timeZone: "America/Tijuana", hour:"2-digit", minute:"2-digit", second:"2-digit" }});
            var dt = now.toLocaleDateString("es-MX", {{ timeZone: "America/Tijuana", year:"numeric", month:"2-digit", day:"2-digit" }});
            var sb = document.getElementById('__sb_clock__');
            if(sb) sb.innerHTML = '🕒 <b>' + t + '</b> &nbsp;·&nbsp; ' + dt;
        }}
        tickClock();
        setInterval(tickClock, 1000);
    }})();
    </script>
    """, unsafe_allow_html=True)
    st.markdown(f'<span id="__ct_sol_count__" data-count="{_sols_count}" style="display:none"></span>', unsafe_allow_html=True)

# ==================== SIDEBAR ====================
with st.sidebar:
    st.image(LOGO_DATA_URI, width=210)
    st.markdown(f"<p id='__sb_clock__' style='margin:8px 0 2px;font-size:.82rem;color:#c3d4f0;'>🕒 <b>{hora_actual}</b> &nbsp;·&nbsp; {fecha_hoy}</p>", unsafe_allow_html=True)
    st.markdown("---")
    role_label = "🛡 Administrador" if st.session_state.role == "admin" else "🔧 Técnico"
    st.markdown(f"<p style='margin:0 0 4px;font-size:.95rem;font-weight:700;'>👤 {st.session_state.user}</p><span class='user-chip'>{role_label}</span>", unsafe_allow_html=True)
    st.markdown("---")

    if st.session_state.role == "admin":
        _opts = ["📊 Dashboard Ejecutivo", "🎯 Control de Asignaciones", "🎫 Tickets", "📦 Inventarios", "📸 Registro de Unidades", "👥 Gestión de Usuarios"]
    else:
        _opts = ["🎯 Mis Tareas", "🔔 Nueva Solicitud"]

    _saved = st.session_state.menu_sel
    _idx = _opts.index(_saved) if _saved in _opts else 0
    def _on_menu():
        st.session_state.menu_sel = st.session_state._menu_key
        st.query_params["m"] = st.session_state._menu_key
    menu = st.radio("MENÚ PRINCIPAL" if st.session_state.role == "admin" else "ÁREA DE TRABAJO", _opts, index=_idx, key="_menu_key", on_change=_on_menu)
    st.session_state.menu_sel = menu
    st.query_params["m"] = menu
    st.markdown("---")
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        for k in ["login", "user", "role", "last_count"]:
            st.session_state[k] = False if k == "login" else "" if k != "last_count" else 0
        st.query_params.clear()
        st.rerun()

# ==================== FUNCIONES AUXILIARES ====================
def get_next_ticket_num():
    res = execute_read("SELECT MAX(ticket_num) as max_num FROM tickets")
    if res and res[0]["max_num"]:
        return res[0]["max_num"] + 1
    return 1

# ==================== DASHBOARD EJECUTIVO ====================
if menu == "📊 Dashboard Ejecutivo":
    st.markdown(f'<div class="time-badge">🕒 Tijuana: {hora_actual}</div><div class="main-header">📊 Panel de Rendimiento Operativo</div>', unsafe_allow_html=True)

    asig = execute_read("SELECT * FROM asignaciones")
    unid = execute_read("SELECT * FROM unidades")
    df_a = pd.DataFrame(asig) if asig else pd.DataFrame()

    total_u = len(unid)
    total_t = len(df_a)
    comp_t = int((df_a["estado"] == "completada").sum()) if not df_a.empty else 0
    proc_t = int((df_a["estado"] == "en_proceso").sum()) if not df_a.empty else 0
    pend_t = int((df_a["estado"] == "pendiente").sum()) if not df_a.empty else 0
    pct_av = round(comp_t / total_t * 100) if total_t else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    for col, val, lbl, cls in [
        (k1, total_u, "Total Unidades", ""),
        (k2, comp_t, "Completadas", "green"),
        (k3, proc_t, "En Proceso", "amber"),
        (k4, pend_t, "Pendientes", "red"),
        (k5, f"{pct_av}%", "Avance Global", "purple"),
    ]:
        with col:
            st.markdown(f'<div class="kpi-wrap {cls}"><div class="kpi-num">{val}</div><div class="kpi-lbl">{lbl}</div></div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    if not df_a.empty:
        st.markdown('<div class="section-title">📈 Estadísticas por Técnico</div>', unsafe_allow_html=True)
        stats = df_a.groupby("tecnico").agg(
            Total=("id", "count"),
            Completadas=("estado", lambda x: (x == "completada").sum()),
            En_Curso=("estado", lambda x: (x == "en_proceso").sum()),
            Pendientes=("estado", lambda x: (x == "pendiente").sum())
        ).reset_index()
        stats["Rendimiento %"] = ((stats["Completadas"] / stats["Total"]) * 100).round(0).astype(int)
        st.dataframe(stats.sort_values("Total", ascending=False), use_container_width=True, hide_index=True)

        COLOR_MAP = {"completada": CARRIER_SUCCESS, "en_proceso": CARRIER_WARN, "pendiente": CARRIER_DANGER, "solicitado": "#6b7280"}
        c1, c2 = st.columns([2, 1])
        with c1:
            fig_b = px.bar(df_a, x="tecnico", color="estado", title="Carga de Trabajo por Técnico", color_discrete_map=COLOR_MAP, template="plotly_white")
            fig_b.update_layout(paper_bgcolor="white", plot_bgcolor="white", title_font=dict(color=CARRIER_BLUE, size=15), font=dict(family="Inter"))
            st.plotly_chart(fig_b, use_container_width=True)
        with c2:
            fig_p = px.pie(df_a, names="estado", title="Distribución Global", hole=0.55, color_discrete_map=COLOR_MAP, template="plotly_white")
            fig_p.update_layout(paper_bgcolor="white", title_font=dict(color=CARRIER_BLUE, size=15))
            st.plotly_chart(fig_p, use_container_width=True)

    st.markdown('<div class="section-title">📋 Estatus de Proceso por Unidad</div>', unsafe_allow_html=True)
    if unid:
        completadas_raw = execute_read("SELECT unidad, actividad_id FROM asignaciones WHERE estado='completada'")
        completed_set = {(r["unidad"], r["actividad_id"]) for r in completadas_raw}
        status_data = []
        for u in unid:
            row = {"LOTE": u["id_lote"], "#Económico": u["unit_number"]}
            for act in ACTIVIDADES_CARRIER:
                row[act] = "✔" if (u["unit_number"], act) in completed_set else "–"
            status_data.append(row)
        st.dataframe(pd.DataFrame(status_data), use_container_width=True, hide_index=True, height=340)

    st.markdown('<div class="section-title">📂 Descarga de Evidencias por Unidad</div>', unsafe_allow_html=True)
    if unid:
        col_ev1, col_ev2 = st.columns([3, 1])
        with col_ev1:
            u_sel_ev = st.selectbox("Selecciona unidad:", [u["unit_number"] for u in unid], key="ev_sel")
        ev_archivos = execute_read("SELECT nombre_archivo, contenido FROM evidencias WHERE unit_number=%s", (u_sel_ev,))
        with col_ev2:
            st.metric("📸 Fotos", len(ev_archivos))
        if ev_archivos:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "a", zipfile.ZIP_DEFLATED, False) as zf:
                for ev in ev_archivos:
                    zf.writestr(ev["nombre_archivo"], ev["contenido"])
            st.download_button(f"📥 Descargar {len(ev_archivos)} fotos — Unidad {u_sel_ev}", buf.getvalue(), f"{u_sel_ev}_evidencia.zip", "application/zip", use_container_width=True)
        else:
            st.info("Sin fotos cargadas para esta unidad.")

    st.markdown('<div class="section-title">📥 Reportes y Descargas</div>', unsafe_allow_html=True)
    if unid:
        df_u = pd.DataFrame(unid)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_u.to_excel(writer, index=False, sheet_name="Series_Unidades")
            if not df_a.empty:
                df_a.to_excel(writer, index=False, sheet_name="Actividades")
        st.download_button("📊 Descargar Reporte Maestro General (Excel)", buffer.getvalue(), f"Carrier_Reporte_{fecha_hoy}.xlsx", use_container_width=True, type="primary")
        st.markdown("<br>", unsafe_allow_html=True)
        for lote in sorted(df_u["id_lote"].unique()):
            n = len(df_u[df_u["id_lote"] == lote])
            with st.expander(f"📦 Lote: {lote}  ({n} unidades)"):
                st.table(df_u[df_u["id_lote"] == lote][["unit_number"] + list(CAMPOS_SERIES.keys())])

# ==================== INVENTARIOS ====================
elif menu == "📦 Inventarios":
    st.markdown(f'<div class="time-badge">🕒 {hora_actual}</div><div class="main-header">📦 Gestión de Inventarios</div>', unsafe_allow_html=True)

    def get_inv_columnas():
        rows = execute_read("SELECT col_nombre, col_orden FROM inventario_columnas WHERE tabla_nombre='Principal' ORDER BY col_orden ASC")
        return [r["col_nombre"] for r in rows] if rows else []

    def save_inv_columnas(columnas):
        execute_write("DELETE FROM inventario_columnas WHERE tabla_nombre='Principal'")
        for i, c in enumerate(columnas):
            execute_write("INSERT INTO inventario_columnas (tabla_nombre, col_nombre, col_orden) VALUES (%s,%s,%s)", ("Principal", c, i))

    def get_inv_data(columnas):
        if not columnas:
            return pd.DataFrame()
        rows = execute_read("SELECT fila_idx, col_nombre, valor FROM inventario_data WHERE tabla_nombre='Principal' ORDER BY fila_idx ASC, col_nombre ASC")
        if not rows:
            return pd.DataFrame(columns=columnas)
        data_dict = {}
        for r in rows:
            fi = r["fila_idx"]
            if fi not in data_dict:
                data_dict[fi] = {c: "" for c in columnas}
            if r["col_nombre"] in columnas:
                data_dict[fi][r["col_nombre"]] = r["valor"] or ""
        return pd.DataFrame([data_dict[k] for k in sorted(data_dict.keys())], columns=columnas)

    def save_inv_data(df):
        execute_write("DELETE FROM inventario_data WHERE tabla_nombre='Principal'")
        for i, row in df.iterrows():
            for col in df.columns:
                execute_write("INSERT INTO inventario_data (tabla_nombre, fila_idx, col_nombre, valor) VALUES (%s,%s,%s,%s)", ("Principal", i, col, str(row[col])))

    columnas = get_inv_columnas()
    if not columnas:
        columnas = ["Código", "Descripción", "Cantidad", "Unidad", "Ubicación", "Estado"]
        save_inv_columnas(columnas)

    df_inv = get_inv_data(columnas)

    st.markdown(f'<div class="inv-info-bar">🗄 Inventario Principal &nbsp;·&nbsp; {len(df_inv)} registros &nbsp;·&nbsp; {len(columnas)} columnas</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📋 Tabla de Inventario", "⚙️ Configurar Columnas"])

    with tab1:
        col_add, col_del, col_save = st.columns([1, 1, 2])
        with col_add:
            if st.button("➕ Agregar Fila", use_container_width=True):
                nueva_fila = pd.DataFrame([{c: "" for c in columnas}])
                df_inv = pd.concat([df_inv, nueva_fila], ignore_index=True)
                save_inv_data(df_inv)
                st.success("✅ Fila agregada.")
                st.rerun()
        with col_del:
            if len(df_inv) > 0:
                fila_del = st.number_input("Eliminar fila #", min_value=1, max_value=max(len(df_inv), 1), value=1, step=1, key="fila_del_n")
                if st.button("🗑 Eliminar Fila", use_container_width=True):
                    df_inv = df_inv.drop(index=fila_del - 1).reset_index(drop=True)
                    save_inv_data(df_inv)
                    st.success(f"✅ Fila {fila_del} eliminada.")
                    st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)

        if df_inv.empty:
            st.info("📋 La tabla está vacía. Agrega filas con el botón de arriba.")
        else:
            df_editado = st.data_editor(df_inv, use_container_width=True, num_rows="dynamic", hide_index=False, key="inv_editor")
            if st.button("💾 Guardar Cambios del Inventario", use_container_width=True, type="primary"):
                save_inv_data(df_editado)
                st.success("✅ Inventario guardado correctamente.")
                st.rerun()
            buf_inv = io.BytesIO()
            with pd.ExcelWriter(buf_inv, engine="openpyxl") as w:
                df_inv.to_excel(w, index=False, sheet_name="Inventario")
            st.download_button("📥 Exportar Inventario a Excel", buf_inv.getvalue(), f"Inventario_Carrier_{fecha_hoy}.xlsx", use_container_width=True)

    with tab2:
        st.markdown('<div class="section-title">⚙️ Administrar Columnas</div>', unsafe_allow_html=True)
        with st.form("add_col_form"):
            nueva_col = st.text_input("Nombre de nueva columna")
            if st.form_submit_button("➕ Agregar Columna", type="primary"):
                if nueva_col and nueva_col not in columnas:
                    columnas.append(nueva_col)
                    save_inv_columnas(columnas)
                    if not df_inv.empty:
                        df_inv[nueva_col] = ""
                        save_inv_data(df_inv)
                    st.success(f'✅ Columna "{nueva_col}" agregada.')
                    st.rerun()
                elif nueva_col in columnas:
                    st.warning("⚠️ Esa columna ya existe.")
                else:
                    st.warning("⚠️ Escribe un nombre válido.")

        st.markdown('<div class="section-title">📋 Columnas Actuales</div>', unsafe_allow_html=True)
        if columnas:
            for i, col in enumerate(columnas):
                c1, c2, c3 = st.columns([3, 2, 1])
                with c1:
                    st.markdown(f"`{i+1}.` **{col}**")
                with c2:
                    nuevo_nombre = st.text_input("Renombrar", value=col, key=f"ren_col_{i}", label_visibility="collapsed")
                with c3:
                    if st.button("✏️", key=f"ren_btn_{i}", help="Aplicar nuevo nombre"):
                        if nuevo_nombre and nuevo_nombre != col:
                            if not df_inv.empty and col in df_inv.columns:
                                df_inv = df_inv.rename(columns={col: nuevo_nombre})
                                save_inv_data(df_inv)
                            columnas[i] = nuevo_nombre
                            save_inv_columnas(columnas)
                            st.success(f'✅ Renombrado a "{nuevo_nombre}".')
                            st.rerun()
                col_d1, col_d2 = st.columns([5, 1])
                with col_d2:
                    if len(columnas) > 1:
                        if st.button("🗑", key=f"del_col_{i}", help=f'Eliminar columna "{col}"'):
                            columnas.pop(i)
                            save_inv_columnas(columnas)
                            if not df_inv.empty and col in df_inv.columns:
                                df_inv = df_inv.drop(columns=[col])
                                save_inv_data(df_inv)
                            st.success(f'✅ Columna "{col}" eliminada.')
                            st.rerun()
                st.markdown("<hr style='margin:4px 0;border-color:#f0f0f0;'>", unsafe_allow_html=True)
        else:
            st.info("No hay columnas definidas.")

# ==================== CONTROL DE ASIGNACIONES (ADMIN) ====================
elif menu == "🎯 Control de Asignaciones":
    st.markdown('<div class="main-header">🎯 Gestión de Órdenes de Trabajo</div>', unsafe_allow_html=True)

    sols = execute_read("SELECT * FROM asignaciones WHERE estado='solicitado'")

    if len(sols) > st.session_state.last_count:
        st.markdown(f'<audio autoplay><source src="{SOUND_URL}" type="audio/mp3"></audio>', unsafe_allow_html=True)
    st.session_state.last_count = len(sols)

    if not sols:
        st.success("✅ Sin solicitudes pendientes de aprobar.")
    else:
        st.markdown(f'<div class="section-title">🔔 Solicitudes Pendientes de Aprobación ({len(sols)})</div>', unsafe_allow_html=True)
        for s in sols:
            dup_comp = execute_read("SELECT tecnico FROM asignaciones WHERE unidad=%s AND actividad_id=%s AND estado='completada'", (s["unidad"], s["actividad_id"]))
            dup_activa = execute_read("SELECT tecnico, estado FROM asignaciones WHERE unidad=%s AND actividad_id=%s AND estado IN ('pendiente','en_proceso') AND id != %s", (s["unidad"], s["actividad_id"], s["id"]))
            tiene_alerta = bool(dup_comp or dup_activa)

            with st.container():
                col_inf, col_ap, col_den = st.columns([4, 1, 1])
                with col_inf:
                    if tiene_alerta:
                        st.error(f"🚨 **{s['tecnico']}** solicita **{s['actividad_id']}** — Unidad: **{s['unidad']}**")
                    else:
                        st.warning(f"📋 **{s['tecnico']}** solicita **{s['actividad_id']}** — Unidad: **{s['unidad']}**")
                    if dup_comp:
                        tecnicos_comp = ", ".join([d["tecnico"] for d in dup_comp])
                        st.markdown(f'<div class="bloqueo-card"><p>⛔ ACTIVIDAD YA COMPLETADA — Por: <b>{tecnicos_comp}</b>. Aprobar permite una repetición.</p></div>', unsafe_allow_html=True)
                    if dup_activa:
                        for da in dup_activa:
                            st.markdown(f'<div class="bloqueo-card"><p>⚠️ TAREA DUPLICADA — <b>{da["tecnico"]}</b> ya tiene esta actividad en estado <b>{da["estado"]}</b>.</p></div>', unsafe_allow_html=True)
                if col_ap.button("✅ Aprobar", key=f"ap_{s['id']}", use_container_width=True):
                    execute_write("UPDATE asignaciones SET estado='pendiente' WHERE id=%s", (s["id"],))
                    st.rerun()
                if col_den.button("❌ Rechazar", key=f"de_{s['id']}", use_container_width=True):
                    execute_write("DELETE FROM asignaciones WHERE id=%s", (s["id"],))
                    st.rerun()
            st.markdown("<hr style='margin:6px 0;border-color:#e5eaf2;'>", unsafe_allow_html=True)

    st.markdown('<div class="section-title">➕ Asignación Directa</div>', unsafe_allow_html=True)
    u_db = execute_read("SELECT unit_number, id_lote FROM unidades")
    t_db = execute_read("SELECT username FROM users WHERE role='tecnico'")
    with st.form("manual_assign"):
        c1, c2, c3 = st.columns(3)
        u_sel = c1.selectbox("Unidad", [f"{x['id_lote']} - {x['unit_number']}" for x in u_db])
        t_sel = c2.selectbox("Técnico", [x["username"] for x in t_db])
        a_sel = c3.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.form_submit_button("📋 Crear Orden", use_container_width=True, type="primary"):
            execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s,%s,%s,'pendiente')", (u_sel.split(" - ")[1], a_sel, t_sel))
            st.success("✅ Orden creada correctamente.")
            st.rerun()

# ==================== MIS TAREAS (TÉCNICO) ====================
elif menu == "🎯 Mis Tareas":
    st.markdown('<div class="main-header">🎯 Mis Actividades</div>', unsafe_allow_html=True)

    tareas = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado IN ('pendiente','en_proceso')", (st.session_state.user,))

    if not tareas:
        st.info("✅ No tienes tareas asignadas en este momento.")

    for t in tareas:
        icono = "⏳" if t["estado"] == "pendiente" else "▶️"
        es_ticket = t["actividad_id"].startswith("Ticket #") if t["actividad_id"] else False
        with st.expander(f"{icono} Unidad **{t['unidad']}** — {t['actividad_id']}"):
            if t["estado"] == "pendiente":
                st.markdown("<p style='color:#d97706;font-weight:600;'>Estado: Pendiente de inicio</p>", unsafe_allow_html=True)
                if st.button("▶️ Iniciar Actividad", key=f"ini_{t['id']}", use_container_width=True, type="primary"):
                    execute_write("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=%s WHERE id=%s", (datetime.now(tijuana_tz), t["id"]))
                    st.rerun()
            else:
                st.markdown("<p style='color:#16a34a;font-weight:600;'>▶️ Actividad en proceso</p>", unsafe_allow_html=True)

                # Sección de comentario (para todas las actividades)
                comentario = st.text_area("Comentario / Reporte", key=f"coment_{t['id']}", help="Agrega observaciones sobre esta actividad")

                if t["actividad_id"].lower() == "evidencia":
                    fotos_prev = execute_read("SELECT COUNT(*) AS total FROM evidencias WHERE unit_number=%s AND tecnico=%s", (t["unidad"], st.session_state.user))
                    total_prev = fotos_prev[0]["total"] if fotos_prev else 0
                    restantes = MAX_FOTOS - total_prev
                    st.markdown(f'<div class="evidencia-info"><p>📋 Unidad: <b>{t["unidad"]}</b> | Guardadas: <b>{total_prev}</b> | Disponibles: <b>{restantes}</b></p></div>', unsafe_allow_html=True)
                    if restantes > 0:
                        archivos = st.file_uploader(f"📁 Selecciona hasta {restantes} foto(s)", accept_multiple_files=True, type=["jpg", "jpeg", "png"], key=f"fup_{t['id']}")
                        if archivos:
                            if len(archivos) > restantes:
                                archivos = archivos[:restantes]
                            st.markdown(f'<div class="fotos-badge">📸 {len(archivos)} foto(s)</div>', unsafe_allow_html=True)
                            if st.button(f"💾 Guardar {len(archivos)} foto(s)", key=f"savef_{t['id']}", use_container_width=True):
                                for arc in archivos:
                                    arc.seek(0)
                                    execute_write("INSERT INTO evidencias (unit_number, nombre_archivo, contenido, tecnico) VALUES (%s,%s,%s,%s)", (t["unidad"], arc.name, arc.read(), st.session_state.user))
                                st.rerun()
                    if st.button("✅ Finalizar Actividad", key=f"fin_ev_{t['id']}", use_container_width=True):
                        if comentario:
                            execute_write("INSERT INTO comentarios_actividades (asignacion_id, tecnico, comentario) VALUES (%s,%s,%s)", (t['id'], st.session_state.user, comentario))
                        execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t["id"]))
                        if es_ticket and t.get("ticket_id"):
                            execute_write("UPDATE tickets SET atendido=TRUE, fecha_atencion=%s WHERE id=%s", (datetime.now(tijuana_tz), t['ticket_id']))
                        st.success("✅ Actividad completada.")
                        st.rerun()

                elif t["actividad_id"].lower() == "toma de valores":
                    st.markdown('<div class="tv-field-badge">📊 Registro de Valores del Equipo</div>', unsafe_allow_html=True)
                    campos_tv = execute_read("SELECT campo_nombre, campo_orden FROM toma_valores_campos ORDER BY campo_orden ASC")
                    campos_lista = [c["campo_nombre"] for c in campos_tv]
                    if not campos_lista:
                        st.info("⚙️ No hay campos configurados. Agrégalos en la sección de abajo.")
                    else:
                        datos_previos = execute_read("SELECT campo_nombre, valor FROM toma_valores_datos WHERE asignacion_id=%s", (t["id"],))
                        datos_dict = {d["campo_nombre"]: d["valor"] or "" for d in datos_previos}
                        with st.form(f"tv_{t['id']}"):
                            mid = (len(campos_lista) + 1) // 2
                            col_a, col_b = st.columns(2)
                            valores = {}
                            for i, campo in enumerate(campos_lista):
                                target = col_a if i < mid else col_b
                                valores[campo] = target.text_input(campo, value=datos_dict.get(campo, ""), key=f"tv_{t['id']}_{i}")
                            if st.form_submit_button("💾 Guardar Valores y Finalizar", type="primary"):
                                execute_write("DELETE FROM toma_valores_datos WHERE asignacion_id=%s", (t["id"],))
                                for campo, valor in valores.items():
                                    execute_write("INSERT INTO toma_valores_datos (asignacion_id, campo_nombre, valor) VALUES (%s,%s,%s)", (t["id"], campo, valor))
                                if comentario:
                                    execute_write("INSERT INTO comentarios_actividades (asignacion_id, tecnico, comentario) VALUES (%s,%s,%s)", (t['id'], st.session_state.user, comentario))
                                execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t["id"]))
                                if es_ticket and t.get("ticket_id"):
                                    execute_write("UPDATE tickets SET atendido=TRUE, fecha_atencion=%s WHERE id=%s", (datetime.now(tijuana_tz), t['ticket_id']))
                                st.success("✅ Valores guardados y tarea completada.")
                                st.rerun()
                    with st.expander("⚙️ Configurar campos de Toma de Valores"):
                        col_cf1, col_cf2 = st.columns([3, 1])
                        with col_cf1:
                            nuevo_campo_tv = st.text_input("Nombre del nuevo campo", key=f"ncampo_{t['id']}")
                        with col_cf2:
                            st.markdown("<br>", unsafe_allow_html=True)
                            if st.button("➕ Agregar", key=f"addcampo_{t['id']}"):
                                if nuevo_campo_tv:
                                    orden = len(campos_lista)
                                    execute_write("INSERT INTO toma_valores_campos (campo_nombre, campo_orden) VALUES (%s,%s)", (nuevo_campo_tv, orden))
                                    st.success(f'✅ Campo "{nuevo_campo_tv}" agregado.')
                                    st.rerun()
                        if campos_lista:
                            st.markdown("**Campos actuales:**")
                            for i, c in enumerate(campos_lista):
                                cc1, cc2 = st.columns([5, 1])
                                cc1.markdown(f"`{i+1}.` {c}")
                                if cc2.button("🗑", key=f"delcampo_{t['id']}_{i}"):
                                    execute_write("DELETE FROM toma_valores_campos WHERE campo_nombre=%s", (c,))
                                    st.rerun()

                elif t["actividad_id"].lower() == "toma de series":
                    with st.form(f"ser_{t['id']}"):
                        st.markdown("<p style='font-size:.9rem;color:#374151;margin-bottom:10px;'>Ingresa los seriales de cada componente:</p>", unsafe_allow_html=True)
                        items = list(CAMPOS_SERIES.items())
                        mid = (len(items) + 1) // 2
                        col_a, col_b = st.columns(2)
                        res = {}
                        for i, (k, v) in enumerate(items):
                            target = col_a if i < mid else col_b
                            res[k] = target.text_input(v, key=f"s_{t['id']}_{k}")
                        if st.form_submit_button("💾 Guardar Series y Finalizar", use_container_width=True, type="primary"):
                            set_q = ", ".join([f"{k}=%s" for k in res])
                            execute_write(f"UPDATE unidades SET {set_q} WHERE unit_number=%s", list(res.values()) + [t["unidad"]])
                            if comentario:
                                execute_write("INSERT INTO comentarios_actividades (asignacion_id, tecnico, comentario) VALUES (%s,%s,%s)", (t['id'], st.session_state.user, comentario))
                            execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t["id"]))
                            if es_ticket and t.get("ticket_id"):
                                execute_write("UPDATE tickets SET atendido=TRUE, fecha_atencion=%s WHERE id=%s", (datetime.now(tijuana_tz), t['ticket_id']))
                            st.success("✅ Series guardadas.")
                            st.rerun()

                else:
                    # Actividad genérica
                    if st.button("✅ Terminar Actividad", key=f"fin_{t['id']}", use_container_width=True, type="primary"):
                        if comentario:
                            execute_write("INSERT INTO comentarios_actividades (asignacion_id, tecnico, comentario) VALUES (%s,%s,%s)", (t['id'], st.session_state.user, comentario))
                        execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t["id"]))
                        if es_ticket and t.get("ticket_id"):
                            execute_write("UPDATE tickets SET atendido=TRUE, fecha_atencion=%s WHERE id=%s", (datetime.now(tijuana_tz), t['ticket_id']))
                        st.success("✅ Actividad completada.")
                        st.rerun()

# ==================== NUEVA SOLICITUD ====================
elif menu == "🔔 Nueva Solicitud":
    st.markdown('<div class="main-header">🔔 Solicitar Actividad</div>', unsafe_allow_html=True)
    u_db = execute_read("SELECT unit_number, id_lote FROM unidades")
    with st.form("sol_f"):
        u_sel = st.selectbox("Unidad", [f"{x['id_lote']} - {x['unit_number']}" for x in u_db])
        a_sel = st.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.form_submit_button("📤 Enviar Solicitud", use_container_width=True, type="primary"):
            unidad_sel = u_sel.split(" - ")[1]
            activa = execute_read("SELECT id, estado FROM asignaciones WHERE tecnico=%s AND unidad=%s AND actividad_id=%s AND estado IN ('solicitado','pendiente','en_proceso')", (st.session_state.user, unidad_sel, a_sel))
            if activa:
                st.error("🚫 Ya tienes esta actividad registrada.")
            else:
                completada = execute_read("SELECT tecnico FROM asignaciones WHERE unidad=%s AND actividad_id=%s AND estado='completada'", (unidad_sel, a_sel))
                if completada:
                    st.warning(f"⚠️ Actividad ya completada por {completada[0]['tecnico']}. Requiere autorización.")
                execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s,%s,%s,'solicitado')", (unidad_sel, a_sel, st.session_state.user))
                st.toast("✅ Solicitud enviada correctamente")
                st.rerun()

# ==================== TICKETS (SOLO ADMIN) ====================
elif menu == "🎫 Tickets":
    st.markdown('<div class="main-header">🎫 Gestión de Tickets</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📋 Listado de Tickets", "➕ Crear nuevo ticket"])

    with tab1:
        tickets = execute_read("SELECT t.*, a.id as asignacion_id, a.tecnico FROM tickets t LEFT JOIN asignaciones a ON t.id = a.ticket_id ORDER BY t.ticket_num DESC")
        if tickets:
            for t in tickets:
                # Determinar estado del semáforo
                if not t["atendido"]:
                    estado_color = "🔴 No atendido"
                    clase = "ticket-rojo"
                elif t["atendido"] and not t["reporte_enviado"]:
                    estado_color = "🟡 Atendido (sin reporte)"
                    clase = "ticket-ambar"
                else:
                    estado_color = "🟢 Completado"
                    clase = "ticket-verde"
                with st.container():
                    st.markdown(f'<div style="background:#f8f9fa; border-left: 6px solid {CARRIER_ACCENT}; padding:12px; border-radius:10px; margin-bottom:12px;">', unsafe_allow_html=True)
                    col1, col2, col3 = st.columns([1, 3, 1])
                    with col1:
                        st.markdown(f"## #{t['ticket_num']}")
                        st.markdown(f"**{estado_color}**")
                    with col2:
                        st.markdown(f"**Unidad:** {t['unit_number']} | **VIN:** {t.get('vin_number', 'N/D')}")
                        st.markdown(f"**Descripción:** {t['descripcion']}")
                        st.markdown(f"*Creado por: {t['creado_por']} | {t['fecha_creacion']}*")
                        if t.get("tecnico"):
                            st.markdown(f"*Asignado a: {t['tecnico']}*")
                    with col3:
                        if t["atendido"] and not t["reporte_enviado"]:
                            if st.button("📤 Marcar reporte enviado", key=f"reporte_{t['id']}"):
                                execute_write("UPDATE tickets SET reporte_enviado=TRUE, fecha_reporte=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                                st.rerun()
                        if not t["atendido"]:
                            st.caption("⏳ Esperando atención del técnico")
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No hay tickets registrados.")

    with tab2:
        unidades = execute_read("SELECT unit_number, vin_number FROM unidades")
        tecnicos = execute_read("SELECT username FROM users WHERE role='tecnico'")
        with st.form("nuevo_ticket"):
            st.markdown("### Crear nuevo ticket")
            unidad_opciones = {f"{u['unit_number']} - {u.get('vin_number', 'sin VIN')}": u['unit_number'] for u in unidades}
            unidad_label = st.selectbox("Unidad (SAP)", list(unidad_opciones.keys()))
            unidad_seleccionada = unidad_opciones[unidad_label]
            vin_auto = next((u.get("vin_number") for u in unidades if u["unit_number"] == unidad_seleccionada), "")
            vin = st.text_input("VIN Number", value=vin_auto)
            descripcion = st.text_area("Descripción del problema / solicitud")
            tecnico_asignado = st.selectbox("Asignar a técnico", [t["username"] for t in tecnicos] if tecnicos else [])
            if st.form_submit_button("📌 Crear ticket y asignar", type="primary"):
                if unidad_seleccionada and descripcion and tecnico_asignado:
                    next_num = get_next_ticket_num()
                    execute_write("INSERT INTO tickets (ticket_num, unit_number, vin_number, descripcion, creado_por) VALUES (%s,%s,%s,%s,%s)", (next_num, unidad_seleccionada, vin, descripcion, st.session_state.user))
                    ticket_id = execute_read("SELECT id FROM tickets WHERE ticket_num=%s", (next_num,))[0]["id"]
                    actividad_ticket = f"Ticket #{next_num}"
                    execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado, ticket_id) VALUES (%s,%s,%s,'pendiente',%s)", (unidad_seleccionada, actividad_ticket, tecnico_asignado, ticket_id))
                    st.success(f"✅ Ticket #{next_num} creado y asignado a {tecnico_asignado}")
                    st.rerun()
                else:
                    st.warning("Completa todos los campos")

# ==================== REGISTRO DE UNIDADES ====================
elif menu == "📸 Registro de Unidades":
    st.markdown('<div class="main-header">📸 Registro Maestro de Unidades</div>', unsafe_allow_html=True)
    with st.form("reg_u"):
        col1, col2 = st.columns(2)
        u_num = col1.text_input("Número Económico")
        l_num = col1.text_input("Número de Lote")
        campo = col2.selectbox("Campo a Registrar", ["Ninguno"] + list(CAMPOS_SERIES.keys()))
        valor = col2.text_input("Valor del Serial")
        if st.form_submit_button("💾 Guardar Registro", use_container_width=True, type="primary"):
            if campo != "Ninguno":
                execute_write(f"INSERT INTO unidades (unit_number, id_lote, {campo}) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE id_lote=%s, {campo}=%s", (u_num, l_num, valor, l_num, valor))
            else:
                execute_write("INSERT INTO unidades (unit_number, id_lote) VALUES (%s,%s) ON DUPLICATE KEY UPDATE id_lote=%s", (u_num, l_num, l_num))
            st.success("✅ Registro guardado correctamente")
            st.rerun()

# ==================== GESTIÓN DE USUARIOS ====================
elif menu == "👥 Gestión de Usuarios":
    st.markdown('<div class="main-header">👥 Usuarios del Sistema</div>', unsafe_allow_html=True)
    usuarios = execute_read("SELECT username, role FROM users ORDER BY role, username")
    if usuarios:
        st.markdown('<div class="section-title">👥 Usuarios Registrados</div>', unsafe_allow_html=True)
        df_users = pd.DataFrame(usuarios)
        df_users.columns = ["Usuario", "Rol"]
        st.dataframe(df_users, use_container_width=True, hide_index=True)

    st.markdown('<div class="section-title">➕ Crear Nuevo Usuario</div>', unsafe_allow_html=True)
    with st.form("u_f"):
        c1, c2, c3 = st.columns(3)
        n_u = c1.text_input("Nombre de Usuario")
        n_p = c2.text_input("Contraseña", type="password")
        n_r = c3.selectbox("Rol", ["tecnico", "admin"])
        if st.form_submit_button("👤 Crear Usuario", use_container_width=True, type="primary"):
            if n_u and n_p:
                execute_write("INSERT INTO users (username, password, role) VALUES (%s,%s,%s)", (n_u, n_p, n_r))
                st.success(f"✅ Usuario **{n_u}** creado correctamente.")
                st.rerun()
            else:
                st.warning("⚠️ Completa todos los campos antes de guardar.")