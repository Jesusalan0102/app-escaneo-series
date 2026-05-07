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

CARRIER_BLUE = "#002B5B"
CARRIER_ACCENT = "#0057A8"
CARRIER_LIGHT = "#E8F0FB"
CARRIER_SUCCESS = "#16a34a"
CARRIER_WARN = "#d97706"
CARRIER_DANGER = "#dc2626"

LOGO_URL = "https://raw.githubusercontent.com/Jesusalan0102/app-escaneo-series/main/carrierlogo.jpg"
_logo_path = _pl.Path(__file__).parent / "carrierlogo.jpg"
if _logo_path.exists():
    _logo_b64 = _b64.b64encode(_logo_path.read_bytes()).decode()
    LOGO_DATA_URI = f"data:image/jpeg;base64,{_logo_b64}"
else:
    LOGO_DATA_URI = LOGO_URL

SOUND_URL = "https://raw.githubusercontent.com/rafaelEscalante/notification-sounds/master/pings/ping-8.mp3"

CAMPOS_SERIES = {
    "vin_number": "VIN Number",
    "reefer_serial": "Serie del Reefer",
    "reefer_model": "Modelo del Reefer",
    "evaporator_serial_mjs11": "Evaporador MJS11",
    "evaporator_serial_mjd22": "Evaporador MJD22",
    "engine_serial": "Motor",
    "compressor_serial": "Compresor",
    "generator_serial": "Generador",
    "battery_charger_serial": "Cargador de Batería",
}

ACTIVIDADES_CARRIER = [
    "Cableado", "Programación", "Soldadura", "Check de fugas",
    "Vacío", "Cerrado", "Pre-viaje", "Horas Corridas",
    "Standby", "GPS", "Corriendo", "Inspección",
    "Accesorios", "Toma de Valores", "Evidencia", "Toma de Series",
]

MAX_FOTOS = 100

# ==================== CSS PREMIUM COMPLETO ====================
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
section[data-testid="stSidebar"] span {{ color: #e0eaff !important; font-family: 'Inter', sans-serif; }}
section[data-testid="stSidebar"] .stRadio > label {{
    color: white !important; font-weight: 600; font-size: 0.72rem; letter-spacing: 1.5px;
}}
section[data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p {{
    color: #d0ddf5 !important; font-size: 0.9rem; font-weight: 500; padding: 2px 0;
}}
section[data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,0.15) !important; }}
section[data-testid="stSidebar"] button {{
    background: rgba(255,255,255,0.1) !important;
    color: white !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: all 0.2s ease !important;
}}
section[data-testid="stSidebar"] button:hover {{
    background: rgba(255,255,255,0.22) !important;
    border-color: rgba(255,255,255,0.4) !important;
    transform: translateX(2px) !important;
}}

/* ══ HEADER ══ */
.main-header {{
    font-size: 1.75rem; font-weight: 800; color: {CARRIER_BLUE};
    border-bottom: 3px solid {CARRIER_ACCENT};
    padding-bottom: 12px; margin-bottom: 24px;
    display: flex; align-items: center; gap: 12px;
    font-family: 'Inter', sans-serif;
}}
.section-title {{
    font-size: 0.92rem; font-weight: 700; color: {CARRIER_BLUE};
    border-left: 4px solid {CARRIER_ACCENT};
    padding: 9px 14px; margin: 22px 0 14px 0;
    background: white; border-radius: 0 8px 8px 0;
    box-shadow: 0 2px 8px rgba(0,43,91,0.07);
    font-family: 'Inter', sans-serif; letter-spacing: 0.2px;
}}

/* ══ KPI CARDS ══ */
.kpi-wrap {{
    background: white; border-radius: 16px;
    padding: 20px 22px 18px; text-align: center;
    box-shadow: 0 4px 20px rgba(0,43,91,0.08);
    border-top: 5px solid {CARRIER_ACCENT};
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    position: relative; overflow: hidden;
}}
.kpi-wrap::after {{
    content: ''; position: absolute; top: 0; right: 0;
    width: 60px; height: 60px; background: rgba(0,87,168,0.04);
    border-radius: 0 0 0 60px;
}}
.kpi-wrap:hover {{ transform: translateY(-3px); box-shadow: 0 8px 28px rgba(0,43,91,0.14); }}
.kpi-wrap.green {{ border-top-color: {CARRIER_SUCCESS}; }}
.kpi-wrap.amber {{ border-top-color: {CARRIER_WARN}; }}
.kpi-wrap.red {{ border-top-color: {CARRIER_DANGER}; }}
.kpi-wrap.purple {{ border-top-color: #7c3aed; }}
.kpi-num {{
    font-size: 2.4rem; font-weight: 800; color: {CARRIER_BLUE};
    line-height: 1.1; font-family: 'Inter', sans-serif;
}}
.kpi-wrap.green .kpi-num {{ color: {CARRIER_SUCCESS}; }}
.kpi-wrap.amber .kpi-num {{ color: {CARRIER_WARN}; }}
.kpi-wrap.red .kpi-num {{ color: {CARRIER_DANGER}; }}
.kpi-wrap.purple .kpi-num {{ color: #7c3aed; }}
.kpi-lbl {{
    font-size: 0.73rem; color: #6b7280; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.6px; margin-top: 6px;
}}

/* ══ TIME BADGE ══ */
.time-badge {{
    background: {CARRIER_BLUE}; color: white;
    padding: 6px 16px; border-radius: 24px;
    font-size: 0.82rem; font-weight: 600; float: right;
    margin-top: 2px; box-shadow: 0 2px 8px rgba(0,43,91,0.25);
}}

/* ══ EXPANDERS ══ */
div[data-testid="stExpander"] {{
    background: white; border-radius: 12px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.06);
    border: 1px solid #e2e8f2; margin-bottom: 10px;
    transition: box-shadow 0.2s ease;
}}
div[data-testid="stExpander"]:hover {{ box-shadow: 0 4px 18px rgba(0,43,91,0.1); }}

/* ══ BUTTONS ══ */
.stButton > button {{
    border-radius: 10px; font-weight: 600; font-family: 'Inter', sans-serif;
    transition: all 0.2s ease; letter-spacing: 0.2px;
}}
.stButton > button:hover {{
    transform: translateY(-2px); box-shadow: 0 6px 16px rgba(0,43,91,0.2);
}}

/* ══ FILE UPLOADER ══ */
div[data-testid="stFileUploader"] {{
    background: white; border-radius: 12px;
    border: 2px dashed #b0c4de; padding: 10px;
    transition: border-color 0.2s;
}}
div[data-testid="stFileUploader"]:hover {{ border-color: {CARRIER_ACCENT}; }}

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
.bloqueo-card p {{ margin: 0; color: #7f1d1d; font-size: .88rem; font-weight: 500; }}
.evidencia-info {{
    background: #eff6ff; border: 1px solid #bfdbfe;
    border-left: 5px solid #3b82f6; border-radius: 10px;
    padding: 12px 18px; margin-bottom: 14px;
}}
.evidencia-info p {{ margin: 0; color: #1e40af; font-size: .88rem; }}

/* ══ BADGES ══ */
.fotos-badge {{
    display: inline-block; background: #f0fdf4;
    border: 1px solid #86efac; border-radius: 20px;
    padding: 4px 14px; font-size: .85rem;
    color: #166534; font-weight: 600; margin-top: 10px;
}}

/* ══ INVENTARIO ══ */
.inv-info-bar {{
    background: linear-gradient(90deg, {CARRIER_BLUE} 0%, {CARRIER_ACCENT} 100%);
    color: white; padding: 14px 20px; border-radius: 12px;
    font-weight: 600; margin-bottom: 16px;
    display: flex; align-items: center; gap: 10px;
}}

/* ══ TOMA DE VALORES ══ */
.tv-field-badge {{
    background: {CARRIER_LIGHT}; border: 1px solid #c3d4f0;
    border-radius: 8px; padding: 6px 12px;
    font-size: 0.82rem; color: {CARRIER_BLUE}; font-weight: 600;
    display: inline-block; margin-bottom: 8px;
}}

/* ══ LOGIN ══ */
.login-card {{
    background: white; padding: 36px 40px; border-radius: 20px;
    box-shadow: 0 12px 40px rgba(0,43,91,0.18); border: 1px solid #e2e8f2;
}}

/* ══ SIDEBAR USER CHIP ══ */
.user-chip {{
    background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.22);
    border-radius: 50px; padding: 6px 14px;
    color: white !important; font-size: 0.82rem; font-weight: 500;
    display: inline-block; margin-top: 4px;
}}

/* ══ DATAFRAME ══ */
[data-testid="stDataFrame"] {{
    border-radius: 10px; overflow: hidden;
    box-shadow: 0 2px 10px rgba(0,43,91,0.06);
}}

/* ══ METRIC ══ */
[data-testid="stMetric"] {{
    background: white; border-radius: 12px;
    padding: 14px 18px; border: 1px solid #e2e8f2;
    box-shadow: 0 2px 8px rgba(0,43,91,0.05);
}}

/* ══ SIDEBAR MENU HOVER ══ */
section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label {{
    padding: 8px 12px !important; border-radius: 8px !important;
    margin: 2px 0 !important; transition: background 0.15s !important;
}}
section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label:hover {{
    background: rgba(255,255,255,0.1) !important;
}}

/* ══ RESPONSIVE / ANDROID WEBVIEW ══ */
html {{
    -webkit-text-size-adjust: 100%;
    touch-action: manipulation;
    -webkit-tap-highlight-color: transparent;
    scroll-behavior: smooth;
}}

button, .stButton > button,
[role="radio"], [role="button"],
.stSelectbox, .stTextInput input,
.stMultiselect, .stFileUploader label {{
    min-height: 48px !important;
    touch-action: manipulation !important;
    -webkit-tap-highlight-color: transparent !important;
    cursor: pointer !important;
}}

.stTextInput input, .stSelectbox select,
.stTextArea textarea {{
    font-size: 16px !important;
    border-radius: 10px !important;
}}

.main .block-container {{
    -webkit-overflow-scrolling: touch;
    overflow-y: auto;
}}
section[data-testid="stSidebar"] {{
    -webkit-overflow-scrolling: touch;
}}

.stButton > button[kind="primary"] {{
    min-height: 52px !important;
    font-size: 1rem !important;
    letter-spacing: 0.3px !important;
}}
.stButton > button:active {{
    transform: scale(0.97) !important;
    transition: transform 0.08s ease !important;
}}

section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label {{
    min-height: 48px !important;
    display: flex !important;
    align-items: center !important;
}}

@media (max-width: 768px) {{
    .main-header {{ font-size: 1.2rem; }}
    .kpi-num {{ font-size: 1.6rem; }}
    .login-card {{ padding: 20px 16px; }}
    .block-container {{ padding: 1rem 0.75rem !important; }}
    section[data-testid="stSidebar"] {{
        width: 85vw !important;
        min-width: 85vw !important;
        max-width: 320px !important;
    }}
    [data-testid="column"] {{
        min-width: 45% !important;
    }}
}}

/* ══ BOTÓN FLOTANTE HAMBURGUESA ══ */
#sidebar-fab {{
    position: fixed; top: 14px; left: 14px;
    z-index: 99999; width: 46px; height: 46px;
    border-radius: 50%;
    background: linear-gradient(135deg, {CARRIER_BLUE} 0%, #0057A8 100%);
    border: 2px solid rgba(255,255,255,0.3);
    box-shadow: 0 4px 16px rgba(0,43,91,0.45);
    cursor: pointer; display: flex;
    align-items: center; justify-content: center;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}}
#sidebar-fab:hover {{ transform: scale(1.08); box-shadow: 0 6px 22px rgba(0,43,91,0.55); }}
#sidebar-fab svg {{
    width: 22px; height: 22px; fill: none;
    stroke: white; stroke-width: 2.2; stroke-linecap: round;
}}
@media (min-width: 992px) {{ #sidebar-fab {{ display: none; }} }}

/* ══ INDICADOR DE ACTUALIZACIÓN EN VIVO ══ */
#live-indicator {{
    position: fixed; bottom: 18px; right: 18px;
    z-index: 99998; display: flex; align-items: center; gap: 8px;
    background: rgba(255,255,255,0.95);
    border: 1px solid #e2e8f2;
    border-radius: 24px; padding: 6px 14px;
    box-shadow: 0 4px 16px rgba(0,43,91,0.12);
    font-family: 'Inter', sans-serif;
    font-size: 0.75rem; font-weight: 600;
    color: {CARRIER_BLUE};
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: opacity 0.3s ease;
    pointer-events: none;
}}
#live-dot {{
    width: 8px; height: 8px; border-radius: 50%;
    background: {CARRIER_SUCCESS};
    box-shadow: 0 0 0 0 rgba(22, 163, 74, 0.4);
    animation: live-pulse 2s infinite;
}}
@keyframes live-pulse {{
    0%   {{ box-shadow: 0 0 0 0 rgba(22,163,74,0.4); }}
    70%  {{ box-shadow: 0 0 0 8px rgba(22,163,74,0); }}
    100% {{ box-shadow: 0 0 0 0 rgba(22,163,74,0); }}
}}
#live-label {{ letter-spacing: 0.3px; }}

/* ══ TOAST DE ACTUALIZACIÓN ══ */
#update-toast {{
    position: fixed; bottom: 60px; right: 18px;
    z-index: 99997; display: none;
    background: {CARRIER_BLUE}; color: white;
    border-radius: 12px; padding: 10px 18px;
    font-family: 'Inter', sans-serif;
    font-size: 0.8rem; font-weight: 600;
    box-shadow: 0 6px 20px rgba(0,43,91,0.3);
    animation: slideUp 0.3s ease;
}}
@keyframes slideUp {{
    from {{ transform: translateY(10px); opacity: 0; }}
    to   {{ transform: translateY(0);    opacity: 1; }}
}}
</style>
""", unsafe_allow_html=True)

# ==================== JAVASCRIPT PARA ACTUALIZACIÓN EN VIVO Y SIDEBAR ====================
st.markdown("""
<script>
(function() {
    var meta = document.querySelector('meta[name="viewport"]');
    if (!meta) {
        meta = document.createElement('meta');
        meta.name = 'viewport';
        document.head.appendChild(meta);
    }
    meta.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no';

    function addTouchClick(el) {
        if (el._ctTouchFixed) return;
        el._ctTouchFixed = true;
        el.addEventListener('touchend', function(e) {
            e.preventDefault();
            el.click();
        }, { passive: false });
    }
    var obs = new MutationObserver(function(mutations) {
        mutations.forEach(function(m) {
            m.addedNodes.forEach(function(node) {
                if (!node.querySelectorAll) return;
                node.querySelectorAll('button, [role="button"]').forEach(addTouchClick);
            });
        });
        document.querySelectorAll('button, [role="button"]').forEach(addTouchClick);
    });
    obs.observe(document.body || document.documentElement, { childList: true, subtree: true });
    setTimeout(function() {
        document.querySelectorAll('button, [role="button"]').forEach(addTouchClick);
    }, 800);

    var lastTap = 0;
    document.addEventListener('touchend', function(e) {
        var now = Date.now();
        if (now - lastTap < 300) e.preventDefault();
        lastTap = now;
    }, { passive: false });
})();
</script>

<div id="sidebar-fab" onclick="toggleSidebar()" title="Menú" style="display:none">
  <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <line x1="3" y1="6"  x2="21" y2="6"/>
    <line x1="3" y1="12" x2="21" y2="12"/>
    <line x1="3" y1="18" x2="21" y2="18"/>
  </svg>
</div>

<div id="live-indicator">
    <div id="live-dot"></div>
    <span id="live-label">En vivo</span>
</div>

<div id="update-toast">🔄 Datos actualizados</div>

<script>
(function() {
    function clearSidebarStorage() {
        try {
            Object.keys(localStorage).forEach(function(k) {
                if (/sidebar/i.test(k)) localStorage.removeItem(k);
            });
        } catch(e) {}
    }
    clearSidebarStorage();

    function forceSidebarOpen(n) {
        var sb = document.querySelector('section[data-testid="stSidebar"]');
        if (!sb) {
            if (n > 0) setTimeout(function() { forceSidebarOpen(n - 1); }, 400);
            return;
        }
        sb.style.setProperty('transform',  'none',    'important');
        sb.style.setProperty('visibility', 'visible', 'important');
        sb.style.setProperty('width',      '21rem',   'important');
        sb.style.setProperty('min-width',  '21rem',   'important');
        sb.style.setProperty('display',    'block',   'important');
        ['button[data-testid="baseButton-header"]',
         '[data-testid="stSidebarCollapsedControl"] button'].forEach(function(sel) {
            var btn = document.querySelector(sel);
            if (btn) btn.style.display = 'none';
        });
    }
    setTimeout(function() { forceSidebarOpen(12); }, 500);

    var sidebarOpen = true;
    window.toggleSidebar = function() {
        var sb = document.querySelector('section[data-testid="stSidebar"]');
        if (!sb) return;
        if (sidebarOpen) {
            sb.style.setProperty('transform', 'translateX(-110%)', 'important');
        } else {
            sb.style.setProperty('transform',  'none',    'important');
            sb.style.setProperty('visibility', 'visible', 'important');
            sb.style.setProperty('width',      '21rem',   'important');
        }
        sidebarOpen = !sidebarOpen;
    };

    function updateFabVisibility() {
        var fab = document.getElementById('sidebar-fab');
        if (!fab) return;
        fab.style.display = window.innerWidth < 992 ? 'flex' : 'none';
    }
    window.addEventListener('resize', updateFabVisibility);
    setTimeout(updateFabVisibility, 800);
})();
</script>
""", unsafe_allow_html=True)

# ==================== CONEXIÓN A BASE DE DATOS (SIMPLIFICADA Y ROBUSTA) ====================
# Credenciales correctas (verificadas que funcionan local y en la nube)
DB_CONFIG = {
    "host": "bmffi0bgsqnener2omcu-mysql.services.clever-cloud.com",
    "database": "bmffi0bgsqnener2omcu",
    "user": "uo8vbdsnvm2ojwta",
    "password": "aXSKib5oxXDEwjlozeQP",
    "port": 3306,
    "connect_timeout": 30,
    "use_pure": True,
}

def get_db_connection():
    """Obtiene una conexión directa a la base de datos."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        # No mostrar error aquí para que no se vea en cada intento
        return None

def execute_query(query, params=None, fetch=True):
    """Ejecuta una consulta y retorna resultados o booleano."""
    conn = get_db_connection()
    if conn is None:
        return [] if fetch else False
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        if fetch:
            result = cursor.fetchall()
        else:
            result = True
        cursor.close()
        conn.close()
        return result
    except Exception as e:
        print(f"Error en consulta: {e}")
        return [] if fetch else False

# ==================== ESTADO DE SESIÓN ====================
defaults = {
    "login": False,
    "user": "",
    "role": "",
    "last_count": 0,
    "menu_sel": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Recuperar sesión desde query params
params = st.query_params
if not st.session_state.login and params.get("u") and params.get("r"):
    st.session_state.update({"login": True, "user": params["u"], "role": params["r"]})
if params.get("m") and st.session_state.get("menu_sel") is None:
    st.session_state["menu_sel"] = params["m"]

# Restaurar sesión desde localStorage (para APK)
if not st.session_state.login:
    st.markdown("""
    <script>
    (function() {
        var u = null, r = null, m = null;
        try {
            u = localStorage.getItem('ct_user');
            r = localStorage.getItem('ct_role');
            m = localStorage.getItem('ct_menu');
        } catch(e) { return; }
        if (u && r) {
            var sp = new URLSearchParams(window.location.search);
            if (!sp.get('u')) {
                sp.set('u', u);
                sp.set('r', r);
                if (m) sp.set('m', m);
                window.location.search = sp.toString();
            }
        }
    })();
    </script>
    """, unsafe_allow_html=True)

# ==================== LOGIN ====================
if not st.session_state.login:
    if "_login_u" not in st.session_state:
        st.session_state["_login_u"] = ""
    if "_login_p" not in st.session_state:
        st.session_state["_login_p"] = ""
    if "_login_err" not in st.session_state:
        st.session_state["_login_err"] = ""

    st.markdown(f'<div style="text-align:center;padding:30px 0 16px;"><img src="{LOGO_DATA_URI}" width="340" style="border-radius:12px;box-shadow:0 8px 32px rgba(0,43,91,0.18);max-width:90vw;"></div>', unsafe_allow_html=True)
    _, col_c, _ = st.columns([1, 2, 1])
    with col_c:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align:center;color:{CARRIER_BLUE};margin-bottom:4px;font-family:Inter,sans-serif;font-weight:800;font-size:1.3rem;'>Carrier Transicold</h3><p style='text-align:center;color:#6b7280;margin-bottom:20px;font-size:0.85rem;'>Sistema Operativo — Panel de Acceso</p>", unsafe_allow_html=True)

        u_log = st.text_input("Usuario", key="_login_u", placeholder="Ingresa tu usuario")
        p_log = st.text_input("Contraseña", key="_login_p", type="password", placeholder="Ingresa tu contraseña")

        if st.session_state["_login_err"]:
            st.error(st.session_state["_login_err"])

        if st.button("Ingresar al Sistema", use_container_width=True, type="primary", key="_login_btn"):
            st.session_state["_login_err"] = ""
            _u = st.session_state.get("_login_u", "").strip()
            _p = st.session_state.get("_login_p", "").strip()
            if not _u or not _p:
                st.session_state["_login_err"] = "⚠️ Ingresa usuario y contraseña."
                st.rerun()
            else:
                with st.spinner("Verificando credenciales..."):
                    users = execute_query("SELECT * FROM users WHERE username=%s AND password=%s", (_u, _p))
                if users is None or len(users) == 0:
                    st.session_state["_login_err"] = "❌ Credenciales incorrectas o error de conexión."
                    st.rerun()
                else:
                    st.session_state.update({"login": True, "user": users[0]["username"], "role": users[0]["role"].lower(), "_login_err": ""})
                    st.query_params["u"] = users[0]["username"]
                    st.query_params["r"] = users[0]["role"].lower()
                    st.rerun()

        st.markdown(f"<p style='text-align:center;margin-top:14px;font-size:0.75rem;color:#9ca3af;'>© {fecha_hoy[:4]} Carrier Transicold</p>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==================== MOTOR DE ACTUALIZACIÓN EN VIVO (solo logueado) ====================
if st.session_state.get("login"):
    # Conteo de solicitudes pendientes para el polling
    solicitudes_pendientes = execute_query("SELECT COUNT(*) as total FROM asignaciones WHERE estado='solicitado'")
    sols_count = solicitudes_pendientes[0]["total"] if solicitudes_pendientes else 0

    st.markdown(f"""
    <script>
    (function () {{
        try {{
            var _u = new URLSearchParams(window.location.search).get('u');
            var _r = new URLSearchParams(window.location.search).get('r');
            var _m = new URLSearchParams(window.location.search).get('m');
            if (_u) localStorage.setItem('ct_user', _u);
            if (_r) localStorage.setItem('ct_role', _r);
            if (_m) localStorage.setItem('ct_menu', _m);
        }} catch(e) {{}}

        if (window.__CT_ENGINE_STARTED__) return;
        window.__CT_ENGINE_STARTED__ = true;
        window.__CT_LAST_COUNT__ = {sols_count};

        var TZ = 'America/Tijuana';
        function fmtTime(d) {{
            try {{
                return d.toLocaleTimeString("es-MX", {{ timeZone: TZ, hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }});
            }} catch(e) {{
                var p = function(n){{ return String(n).padStart(2,'0'); }};
                return p(d.getUTCHours())+":"+p(d.getUTCMinutes())+":"+p(d.getUTCSeconds());
            }}
        }}
        function fmtDate(d) {{
            try {{
                var s = d.toLocaleDateString("es-MX", {{ timeZone: TZ, year:"numeric", month:"2-digit", day:"2-digit" }});
                var p = s.split("/");
                return (p.length===3) ? p[2]+"-"+p[1]+"-"+p[0] : s;
            }} catch(e) {{ return d.toISOString().slice(0,10); }}
        }}
        function tickClock() {{
            var now = new Date();
            var t = fmtTime(now);
            var dt = fmtDate(now);
            var sb = document.getElementById('__sb_clock__');
            var hd = document.getElementById('__hd_clock__');
            if (sb) sb.innerHTML = '&#x1F552; <b>' + t + '</b> &nbsp;&middot;&nbsp; ' + dt;
            if (hd) hd.textContent = String.fromCodePoint(0x1F552) + ' Tijuana: ' + t;
        }}
        tickClock();
        setInterval(tickClock, 1000);

        var dot = document.getElementById('live-dot');
        function pingHeartbeat() {{
            fetch('/_stcore/health', {{ cache: 'no-store' }})
                .then(function(r) {{ if (dot) dot.style.background = r.ok ? '#16a34a' : '#dc2626'; }})
                .catch(function() {{ if (dot) dot.style.background = '#dc2626'; }});
        }}
        setInterval(pingHeartbeat, 25000);
        pingHeartbeat();

        function showToast(msg) {{
            var toast = document.getElementById('update-toast');
            if (!toast) return;
            toast.textContent = msg;
            toast.style.display = 'block';
            setTimeout(function() {{ toast.style.display = 'none'; }}, 3200);
        }}

        function getCurrentCount() {{
            var el = document.getElementById('__ct_sol_count__');
            if (!el) return null;
            return parseInt(el.getAttribute('data-count') || '0', 10);
        }}

        function triggerSilentRefresh() {{
            var btn = document.querySelector('button[title="Actualización silenciosa"]');
            if (btn) btn.click();
        }}

        function pollData() {{
            var current = getCurrentCount();
            if (current === null) return;
            if (current !== window.__CT_LAST_COUNT__) {{
                window.__CT_LAST_COUNT__ = current;
                var delta = current - (window.__CT_LAST_COUNT__ || 0);
                if (delta > 0) {{
                    showToast('🔔 ' + current + ' solicitud(es) nueva(s)');
                    try {{ var audio = new Audio('{SOUND_URL}'); audio.play().catch(function(){{}}); }} catch(e) {{}}
                }} else {{
                    showToast('🔄 Datos actualizados');
                }}
                triggerSilentRefresh();
            }}
        }}
        setInterval(pollData, 30000);
    }})();
    </script>
    """, unsafe_allow_html=True)

    st.markdown(f'<span id="__ct_sol_count__" data-count="{sols_count}" style="display:none"></span>', unsafe_allow_html=True)

    st.markdown("""
    <style>
    div[data-testid="stButton"]:has(button[data-testid="baseButton-secondary"][title="Actualización silenciosa"]) {
        position: fixed !important;
        bottom: -200px !important;
        left: -200px !important;
        width: 1px !important;
        height: 1px !important;
        overflow: hidden !important;
        pointer-events: none !important;
        opacity: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    if st.button("↺", key="__ct_refresh_trigger__", help="Actualización silenciosa"):
        st.rerun()

# ==================== SIDEBAR ====================
with st.sidebar:
    st.image(LOGO_DATA_URI, width=210)
    st.markdown(f"<p id='__sb_clock__' style='margin:8px 0 2px;font-size:.82rem;color:#c3d4f0;padding-left:4px;'>🕒 <b>{hora_actual}</b> &nbsp;·&nbsp; {fecha_hoy}</p>", unsafe_allow_html=True)
    st.markdown("---")
    role_label = "🛡 Administrador" if st.session_state.role == "admin" else "🔧 Técnico"
    st.markdown(f"<p style='margin:0 0 4px;font-size:.95rem;font-weight:700;'>👤 {st.session_state.user}</p><span class='user-chip'>{role_label}</span>", unsafe_allow_html=True)
    st.markdown("---")

    ADMIN_OPTS = ["📊 Dashboard Ejecutivo", "🎯 Control de Asignaciones", "📦 Inventarios", "📸 Registro de Unidades", "👥 Gestión de Usuarios"]
    TECH_OPTS = ["🎯 Mis Tareas", "🔔 Nueva Solicitud"]
    opts = ADMIN_OPTS if st.session_state.role == "admin" else TECH_OPTS
    saved = st.session_state.get("menu_sel")
    idx = opts.index(saved) if saved in opts else 0

    def on_menu():
        st.session_state["menu_sel"] = st.session_state["_menu_key"]
        st.query_params["m"] = st.session_state["_menu_key"]

    menu = st.radio("MENÚ PRINCIPAL" if st.session_state.role == "admin" else "ÁREA DE TRABAJO", opts, index=idx, key="_menu_key", on_change=on_menu)
    st.session_state["menu_sel"] = menu
    st.query_params["m"] = menu
    st.markdown("---")
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        for k in ["login", "user", "role", "last_count", "menu_sel"]:
            st.session_state[k] = False if k == "login" else "" if k != "last_count" else 0
        st.markdown("""<script>try { localStorage.removeItem('ct_user'); localStorage.removeItem('ct_role'); localStorage.removeItem('ct_menu'); } catch(e) {}</script>""", unsafe_allow_html=True)
        st.query_params.clear()
        st.rerun()

# ==================== DASHBOARD EJECUTIVO ====================
if menu == "📊 Dashboard Ejecutivo":
    st.markdown(f'<div id="__hd_clock__" class="time-badge">🕒 Tijuana: {hora_actual}</div><div class="main-header">📊 Panel de Rendimiento Operativo</div>', unsafe_allow_html=True)

    asig = execute_query("SELECT * FROM asignaciones")
    unid = execute_query("SELECT * FROM unidades")
    df_a = pd.DataFrame(asig) if asig else pd.DataFrame()
    unid_df = pd.DataFrame(unid) if unid else pd.DataFrame()

    total_u = len(unid)
    total_t = len(df_a)
    comp_t = int((df_a["estado"] == "completada").sum()) if not df_a.empty else 0
    proc_t = int((df_a["estado"] == "en_proceso").sum()) if not df_a.empty else 0
    pend_t = int((df_a["estado"] == "pendiente").sum()) if not df_a.empty else 0
    pct_av = round(comp_t / total_t * 100) if total_t else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    for col, val, lbl, cls in [(k1, total_u, "Total Unidades", ""), (k2, comp_t, "Completadas", "green"), (k3, proc_t, "En Proceso", "amber"), (k4, pend_t, "Pendientes", "red"), (k5, f"{pct_av}%", "Avance Global", "purple")]:
        with col:
            st.markdown(f'<div class="kpi-wrap {cls}"><div class="kpi-num">{val}</div><div class="kpi-lbl">{lbl}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if not df_a.empty:
        st.markdown('<div class="section-title">📈 Estadísticas por Técnico</div>', unsafe_allow_html=True)
        stats = df_a.groupby("tecnico").agg(Total=("id", "count"), Completadas=("estado", lambda x: (x == "completada").sum()), En_Curso=("estado", lambda x: (x == "en_proceso").sum()), Pendientes=("estado", lambda x: (x == "pendiente").sum())).reset_index()
        stats["Rendimiento %"] = ((stats["Completadas"] / stats["Total"]) * 100).round(0).astype(int)
        st.dataframe(stats.sort_values("Total", ascending=False), use_container_width=True, hide_index=True)

        COLOR_MAP = {"completada": CARRIER_SUCCESS, "en_proceso": CARRIER_WARN, "pendiente": CARRIER_DANGER, "solicitado": "#6b7280"}
        c1, c2 = st.columns([2, 1])
        with c1:
            fig_b = px.bar(df_a, x="tecnico", color="estado", title="Carga de Trabajo por Técnico", color_discrete_map=COLOR_MAP, template="plotly_white")
            fig_b.update_layout(paper_bgcolor="white", plot_bgcolor="white", title_font=dict(color=CARRIER_BLUE, size=15, family="Inter"), font=dict(family="Inter"), legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig_b, use_container_width=True)
        with c2:
            fig_p = px.pie(df_a, names="estado", title="Distribución Global", hole=0.55, color_discrete_map=COLOR_MAP, template="plotly_white")
            fig_p.update_layout(paper_bgcolor="white", title_font=dict(color=CARRIER_BLUE, size=15, family="Inter"), font=dict(family="Inter"))
            st.plotly_chart(fig_p, use_container_width=True)

    st.markdown('<div class="section-title">📋 Estatus de Proceso por Unidad</div>', unsafe_allow_html=True)
    if not unid_df.empty:
        completadas_raw = execute_query("SELECT unidad, actividad_id FROM asignaciones WHERE estado='completada'")
        completed_set = {(r["unidad"], r["actividad_id"]) for r in completadas_raw} if completadas_raw else set()
        status_data = []
        for _, u in unid_df.iterrows():
            row = {"LOTE": u["id_lote"], "#Económico": u["unit_number"]}
            for act in ACTIVIDADES_CARRIER:
                row[act] = "✔" if (u["unit_number"], act) in completed_set else "–"
            status_data.append(row)
        st.dataframe(pd.DataFrame(status_data), use_container_width=True, hide_index=True, height=340)

    st.markdown('<div class="section-title">📂 Descarga de Evidencias por Unidad</div>', unsafe_allow_html=True)
    if not unid_df.empty:
        col_ev1, col_ev2 = st.columns([3, 1])
        with col_ev1:
            u_sel_ev = st.selectbox("Selecciona unidad:", unid_df["unit_number"].tolist(), key="ev_sel")
        ev_archivos = execute_query("SELECT nombre_archivo, contenido FROM evidencias WHERE unit_number=%s", (u_sel_ev,))
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
    if not unid_df.empty:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            unid_df.to_excel(writer, index=False, sheet_name="Series_Unidades")
            if not df_a.empty:
                df_a.to_excel(writer, index=False, sheet_name="Actividades")
        st.download_button("📊 Descargar Reporte Maestro General (Excel)", buffer.getvalue(), f"Carrier_Reporte_{fecha_hoy}.xlsx", use_container_width=True, type="primary")
        st.markdown("<br>", unsafe_allow_html=True)
        for lote in sorted(unid_df["id_lote"].unique()):
            n = len(unid_df[unid_df["id_lote"] == lote])
            with st.expander(f"📦 Lote: {lote}  ({n} unidades)"):
                st.table(unid_df[unid_df["id_lote"] == lote][["unit_number"] + list(CAMPOS_SERIES.keys())])

# ==================== INVENTARIOS ====================
elif menu == "📦 Inventarios":
    st.markdown(f'<div class="time-badge">🕒 {hora_actual}</div><div class="main-header">📦 Gestión de Inventarios</div>', unsafe_allow_html=True)

    # Asegurar tablas de inventario
    execute_query("""
        CREATE TABLE IF NOT EXISTS inventario_columnas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            tabla_nombre VARCHAR(120) DEFAULT 'Principal',
            col_nombre VARCHAR(120) NOT NULL,
            col_orden INT DEFAULT 0
        )
    """, fetch=False)
    execute_query("""
        CREATE TABLE IF NOT EXISTS inventario_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            tabla_nombre VARCHAR(120) DEFAULT 'Principal',
            fila_idx INT NOT NULL,
            col_nombre VARCHAR(120) NOT NULL,
            valor TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    """, fetch=False)

    def get_inv_columnas():
        rows = execute_query("SELECT col_nombre, col_orden FROM inventario_columnas WHERE tabla_nombre='Principal' ORDER BY col_orden ASC")
        return [r["col_nombre"] for r in rows] if rows else []

    def save_inv_columnas(columnas):
        execute_query("DELETE FROM inventario_columnas WHERE tabla_nombre='Principal'", fetch=False)
        for i, c in enumerate(columnas):
            execute_query("INSERT INTO inventario_columnas (tabla_nombre, col_nombre, col_orden) VALUES (%s,%s,%s)", ("Principal", c, i), fetch=False)

    def get_inv_data(columnas):
        if not columnas:
            return pd.DataFrame()
        rows = execute_query("SELECT fila_idx, col_nombre, valor FROM inventario_data WHERE tabla_nombre='Principal' ORDER BY fila_idx ASC, col_nombre ASC")
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
        execute_query("DELETE FROM inventario_data WHERE tabla_nombre='Principal'", fetch=False)
        for i, row in df.iterrows():
            for col in df.columns:
                execute_query("INSERT INTO inventario_data (tabla_nombre, fila_idx, col_nombre, valor) VALUES (%s,%s,%s,%s)", ("Principal", i, col, str(row[col])), fetch=False)

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

# ==================== CONTROL DE ASIGNACIONES (Admin) ====================
elif menu == "🎯 Control de Asignaciones":
    st.markdown('<div class="main-header">🎯 Gestión de Órdenes de Trabajo</div>', unsafe_allow_html=True)

    sols = execute_query("SELECT * FROM asignaciones WHERE estado='solicitado'")

    if len(sols) > st.session_state.last_count:
        st.markdown(f'<audio autoplay><source src="{SOUND_URL}" type="audio/mp3"></audio>', unsafe_allow_html=True)
    st.session_state.last_count = len(sols)

    if not sols:
        st.success("✅ Sin solicitudes pendientes de aprobar.")
    else:
        st.markdown(f'<div class="section-title">🔔 Solicitudes Pendientes de Aprobación ({len(sols)})</div>', unsafe_allow_html=True)
        for s in sols:
            dup_comp = execute_query("SELECT tecnico FROM asignaciones WHERE unidad=%s AND actividad_id=%s AND estado='completada'", (s["unidad"], s["actividad_id"]))
            dup_activa = execute_query("SELECT tecnico, estado FROM asignaciones WHERE unidad=%s AND actividad_id=%s AND estado IN ('pendiente','en_proceso') AND id != %s", (s["unidad"], s["actividad_id"], s["id"]))
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
                    execute_query("UPDATE asignaciones SET estado='pendiente' WHERE id=%s", (s["id"],), fetch=False)
                    st.rerun()
                if col_den.button("❌ Rechazar", key=f"de_{s['id']}", use_container_width=True):
                    execute_query("DELETE FROM asignaciones WHERE id=%s", (s["id"],), fetch=False)
                    st.rerun()
            st.markdown("<hr style='margin:6px 0;border-color:#e5eaf2;'>", unsafe_allow_html=True)

    st.markdown('<div class="section-title">➕ Asignación Directa</div>', unsafe_allow_html=True)
    u_db = execute_query("SELECT unit_number, id_lote FROM unidades")
    t_db = execute_query("SELECT username FROM users WHERE role='tecnico'")
    with st.form("manual_assign"):
        c1, c2, c3 = st.columns(3)
        u_sel = c1.selectbox("Unidad", [f"{x['id_lote']} - {x['unit_number']}" for x in u_db] if u_db else [])
        t_sel = c2.selectbox("Técnico", [x["username"] for x in t_db] if t_db else [])
        a_sel = c3.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.form_submit_button("📋 Crear Orden", use_container_width=True, type="primary"):
            if u_sel and t_sel:
                execute_query("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s,%s,%s,'pendiente')", (u_sel.split(" - ")[1], a_sel, t_sel), fetch=False)
                st.success("✅ Orden creada correctamente.")
                st.rerun()

# ==================== MIS TAREAS (Técnico) ====================
elif menu == "🎯 Mis Tareas":
    st.markdown('<div class="main-header">🎯 Mis Actividades</div>', unsafe_allow_html=True)

    tareas = execute_query("SELECT * FROM asignaciones WHERE tecnico=%s AND estado IN ('pendiente','en_proceso')", (st.session_state.user,))

    if not tareas:
        st.info("✅ No tienes tareas asignadas en este momento.")

    for t in tareas:
        icono = "⏳" if t["estado"] == "pendiente" else "▶️"
        with st.expander(f"{icono} Unidad **{t['unidad']}** — {t['actividad_id']}"):

            if t["estado"] == "pendiente":
                st.markdown("<p style='color:#d97706;font-weight:600;'>Estado: Pendiente de inicio</p>", unsafe_allow_html=True)
                if st.button("▶️ Iniciar Actividad", key=f"ini_{t['id']}", use_container_width=True, type="primary"):
                    execute_query("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=%s WHERE id=%s", (datetime.now(tijuana_tz), t["id"]), fetch=False)
                    st.rerun()
            else:
                st.markdown("<p style='color:#16a34a;font-weight:600;'>▶️ Actividad en proceso</p>", unsafe_allow_html=True)

                if t["actividad_id"].lower() == "evidencia":
                    fotos_prev = execute_query("SELECT COUNT(*) AS total FROM evidencias WHERE unit_number=%s AND tecnico=%s", (t["unidad"], st.session_state.user))
                    total_prev = fotos_prev[0]["total"] if fotos_prev else 0
                    restantes = MAX_FOTOS - total_prev

                    st.markdown(f'<div class="evidencia-info"><p>📋 Unidad: <b>{t["unidad"]}</b> &nbsp;|&nbsp; Técnico: <b>{st.session_state.user}</b><br>Límite: <b>{MAX_FOTOS} fotos</b> &nbsp;·&nbsp; Guardadas: <b>{total_prev}</b> &nbsp;·&nbsp; Disponibles: <b>{restantes}</b></p></div>', unsafe_allow_html=True)

                    if restantes <= 0:
                        st.warning(f"⚠️ Ya alcanzaste el límite de {MAX_FOTOS} fotos.")
                    else:
                        archivos = st.file_uploader(f"📁 Selecciona hasta {restantes} foto(s)", accept_multiple_files=True, type=["jpg", "jpeg", "png"], key=f"fup_{t['id']}", help=f"Máximo {restantes} en esta carga.")
                        if archivos:
                            if len(archivos) > restantes:
                                st.warning(f"⚠️ Se tomarán las primeras {restantes}.")
                                archivos = archivos[:restantes]
                            st.markdown(f'<div class="fotos-badge">📸 {len(archivos)} foto(s) lista(s)</div>', unsafe_allow_html=True)
                            cols_prev = st.columns(min(len(archivos), 5))
                            for idx, arc in enumerate(archivos):
                                with cols_prev[idx % 5]:
                                    st.image(arc, use_container_width=True, caption=arc.name[:18])
                            st.markdown("<br>", unsafe_allow_html=True)
                            if st.button(f"💾 Guardar {len(archivos)} foto(s)", key=f"savef_{t['id']}", use_container_width=True, type="primary"):
                                barra = st.progress(0, text="Iniciando...")
                                errores = 0
                                for i, arc in enumerate(archivos):
                                    arc.seek(0)
                                    ok = execute_query("INSERT INTO evidencias (unit_number, nombre_archivo, contenido, tecnico) VALUES (%s,%s,%s,%s)", (t["unidad"], arc.name, arc.read(), st.session_state.user), fetch=False)
                                    if not ok:
                                        errores += 1
                                    barra.progress((i + 1) / len(archivos), text=f"Guardando {i+1} de {len(archivos)}: {arc.name[:30]}")
                                if errores == 0:
                                    st.success(f"✅ {len(archivos)} foto(s) guardada(s) correctamente.")
                                else:
                                    st.warning(f"⚠️ {len(archivos)-errores} guardadas, {errores} fallaron.")
                                st.rerun()

                    st.markdown("---")
                    col_fin1, col_fin2 = st.columns([3, 1])
                    with col_fin1:
                        st.markdown(f"<p style='font-size:.85rem;color:#6b7280;margin:6px 0 0;'>Al finalizar se cerrará la tarea. Total guardadas: <b>{total_prev}</b></p>", unsafe_allow_html=True)
                    with col_fin2:
                        if st.button("✅ Finalizar", key=f"finev_{t['id']}", use_container_width=True):
                            execute_query("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t["id"]), fetch=False)
                            st.success("✅ Evidencia completada.")
                            st.rerun()

                elif t["actividad_id"].lower() == "toma de valores":
                    st.markdown('<div class="tv-field-badge">📊 Registro de Valores del Equipo</div>', unsafe_allow_html=True)
                    # Asegurar tablas de toma de valores
                    execute_query("""
                        CREATE TABLE IF NOT EXISTS toma_valores_campos (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            campo_nombre VARCHAR(200) NOT NULL,
                            campo_orden INT DEFAULT 0
                        )
                    """, fetch=False)
                    execute_query("""
                        CREATE TABLE IF NOT EXISTS toma_valores_datos (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            asignacion_id INT NOT NULL,
                            campo_nombre VARCHAR(200) NOT NULL,
                            valor TEXT,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                        )
                    """, fetch=False)

                    campos_tv = execute_query("SELECT campo_nombre, campo_orden FROM toma_valores_campos ORDER BY campo_orden ASC")
                    campos_lista = [c["campo_nombre"] for c in campos_tv] if campos_tv else []

                    if not campos_lista:
                        st.info("⚙️ No hay campos configurados. Agrégalos en la sección de abajo.")
                    else:
                        datos_previos = execute_query("SELECT campo_nombre, valor FROM toma_valores_datos WHERE asignacion_id=%s", (t["id"],))
                        datos_dict = {d["campo_nombre"]: d["valor"] or "" for d in datos_previos} if datos_previos else {}

                        with st.form(f"tv_{t['id']}"):
                            st.markdown("<p style='font-size:.9rem;color:#374151;margin-bottom:12px;'>Ingresa los valores medidos para cada campo:</p>", unsafe_allow_html=True)
                            mid = (len(campos_lista) + 1) // 2
                            col_a, col_b = st.columns(2)
                            valores_ingresados = {}
                            for i, campo in enumerate(campos_lista):
                                target = col_a if i < mid else col_b
                                valores_ingresados[campo] = target.text_input(campo, value=datos_dict.get(campo, ""), key=f"tv_{t['id']}_{i}")
                            if st.form_submit_button("💾 Guardar Valores", use_container_width=True, type="primary"):
                                execute_query("DELETE FROM toma_valores_datos WHERE asignacion_id=%s", (t["id"],), fetch=False)
                                for campo, valor in valores_ingresados.items():
                                    execute_query("INSERT INTO toma_valores_datos (asignacion_id, campo_nombre, valor) VALUES (%s,%s,%s)", (t["id"], campo, valor), fetch=False)
                                execute_query("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t["id"]), fetch=False)
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
                                    execute_query("INSERT INTO toma_valores_campos (campo_nombre, campo_orden) VALUES (%s,%s)", (nuevo_campo_tv, orden), fetch=False)
                                    st.success(f'✅ Campo "{nuevo_campo_tv}" agregado.')
                                    st.rerun()
                        if campos_lista:
                            st.markdown("**Campos actuales:**")
                            for i, c in enumerate(campos_lista):
                                cc1, cc2 = st.columns([5, 1])
                                cc1.markdown(f"`{i+1}.` {c}")
                                if cc2.button("🗑", key=f"delcampo_{t['id']}_{i}"):
                                    execute_query("DELETE FROM toma_valores_campos WHERE campo_nombre=%s", (c,), fetch=False)
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
                        if st.form_submit_button("💾 Guardar Series", use_container_width=True, type="primary"):
                            set_q = ", ".join([f"{k}=%s" for k in res])
                            execute_query(f"UPDATE unidades SET {set_q} WHERE unit_number=%s", list(res.values()) + [t["unidad"]], fetch=False)
                            execute_query("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t["id"]), fetch=False)
                            st.success("✅ Series guardadas y tarea completada.")
                            st.rerun()

                else:
                    if st.button("✅ Terminar Actividad", key=f"fin_{t['id']}", use_container_width=True, type="primary"):
                        execute_query("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t["id"]), fetch=False)
                        st.rerun()

# ==================== NUEVA SOLICITUD (Técnico) ====================
elif menu == "🔔 Nueva Solicitud":
    st.markdown('<div class="main-header">🔔 Solicitar Actividad</div>', unsafe_allow_html=True)

    u_db = execute_query("SELECT unit_number, id_lote FROM unidades")

    with st.form("sol_f"):
        u_sel = st.selectbox("Unidad", [f"{x['id_lote']} - {x['unit_number']}" for x in u_db] if u_db else [])
        a_sel = st.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.form_submit_button("📤 Enviar Solicitud", use_container_width=True, type="primary"):
            if u_sel:
                unidad_sel = u_sel.split(" - ")[1]
                activa = execute_query("SELECT id, estado FROM asignaciones WHERE tecnico=%s AND unidad=%s AND actividad_id=%s AND estado IN ('solicitado','pendiente','en_proceso')", (st.session_state.user, unidad_sel, a_sel))
                if activa:
                    estado_act = activa[0]["estado"]
                    etiquetas = {"solicitado": "esperando aprobación", "pendiente": "pendiente de iniciar", "en_proceso": "en proceso"}
                    st.error(f"🚫 Ya tienes esta actividad registrada para la unidad **{unidad_sel}** ({etiquetas.get(estado_act, estado_act)}).")
                else:
                    completada = execute_query("SELECT tecnico FROM asignaciones WHERE unidad=%s AND actividad_id=%s AND estado='completada'", (unidad_sel, a_sel))
                    if completada:
                        st.warning(f"⚠️ La actividad **{a_sel}** en la unidad **{unidad_sel}** ya fue completada por **{completada[0]['tecnico']}**. Solicitud requiere autorización especial.")
                    execute_query("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s,%s,%s,'solicitado')", (unidad_sel, a_sel, st.session_state.user), fetch=False)
                    st.toast("✅ Solicitud enviada correctamente")
                    st.rerun()

    st.markdown('<div class="section-title">📋 Mis Solicitudes Recientes</div>', unsafe_allow_html=True)
    historial = execute_query("SELECT unidad, actividad_id, estado, fecha_inicio, fecha_fin FROM asignaciones WHERE tecnico=%s ORDER BY id DESC LIMIT 20", (st.session_state.user,))
    if historial:
        ESTADO_BADGE = {"solicitado": ("🟡", "#fef9c3", "#854d0e"), "pendiente": ("🟠", "#fff7ed", "#9a3412"), "en_proceso": ("🔵", "#eff6ff", "#1e40af"), "completada": ("🟢", "#f0fdf4", "#166534")}
        for h in historial:
            icono, bg, color = ESTADO_BADGE.get(h["estado"], ("⚪", "#f9fafb", "#374151"))
            st.markdown(f'<div style="background:{bg};border-radius:8px;padding:10px 16px;margin-bottom:6px;border-left:4px solid {color};"><span style="font-weight:700;color:{color};">{icono} {h["estado"].upper()}</span> &nbsp;·&nbsp; <b>{h["unidad"]}</b> — {h["actividad_id"]}</div>', unsafe_allow_html=True)
    else:
        st.info("Sin solicitudes registradas.")

# ==================== REGISTRO DE UNIDADES (Admin) ====================
elif menu == "📸 Registro de Unidades":
    st.markdown('<div class="main-header">📸 Registro Maestro de Unidades</div>', unsafe_allow_html=True)
    with st.form("reg_u"):
        col1, col2 = st.columns(2)
        u_num = col1.text_input("Número Económico")
        l_num = col1.text_input("Número de Lote")
        campo = col2.selectbox("Campo a Registrar", ["Ninguno"] + list(CAMPOS_SERIES.keys()))
        valor = col2.text_input("Valor del Serial")
        if st.form_submit_button("💾 Guardar Registro", use_container_width=True, type="primary"):
            if u_num:
                if campo != "Ninguno":
                    execute_query(f"INSERT INTO unidades (unit_number, id_lote, {campo}) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE id_lote=%s, {campo}=%s", (u_num, l_num, valor, l_num, valor), fetch=False)
                else:
                    execute_query("INSERT INTO unidades (unit_number, id_lote) VALUES (%s,%s) ON DUPLICATE KEY UPDATE id_lote=%s", (u_num, l_num, l_num), fetch=False)
                st.success("✅ Registro guardado correctamente")
                st.rerun()

# ==================== GESTIÓN DE USUARIOS (Admin) ====================
elif menu == "👥 Gestión de Usuarios":
    st.markdown('<div class="main-header">👥 Usuarios del Sistema</div>', unsafe_allow_html=True)

    usuarios = execute_query("SELECT username, role FROM users ORDER BY role, username")
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
                execute_query("INSERT INTO users (username, password, role) VALUES (%s,%s,%s)", (n_u, n_p, n_r), fetch=False)
                st.success(f"✅ Usuario **{n_u}** creado correctamente.")
                st.rerun()
            else:
                st.warning("⚠️ Completa todos los campos antes de guardar.")