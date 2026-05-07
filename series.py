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
import time
import threading
import queue

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
CARRIER_SUCCESS = "#16a34a"
CARRIER_WARN = "#d97706"
CARRIER_DANGER = "#dc2626"

LOGO_URL = "https://raw.githubusercontent.com/Jesusalan0102/app-escaneo-series/main/carrierlogo.jpg"

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

# ==================== CSS BÁSICO ====================
st.markdown("""
<style>
header[data-testid="stHeader"] { display: none !important; }
footer { display: none !important; }
#MainMenu { display: none !important; }
.block-container { padding-top: 1.5rem !important; }
section[data-testid="stSidebar"] { width: 21rem !important; }
.main-header { font-size: 1.75rem; font-weight: 800; color: #002B5B; border-bottom: 3px solid #0057A8; padding-bottom: 12px; margin-bottom: 24px; }
.section-title { font-size: 0.92rem; font-weight: 700; color: #002B5B; border-left: 4px solid #0057A8; padding: 9px 14px; margin: 22px 0 14px 0; background: white; border-radius: 0 8px 8px 0; }
.kpi-wrap { background: white; border-radius: 16px; padding: 20px; text-align: center; box-shadow: 0 4px 20px rgba(0,43,91,0.08); border-top: 5px solid #0057A8; }
.kpi-num { font-size: 2.4rem; font-weight: 800; color: #002B5B; }
.kpi-lbl { font-size: 0.73rem; color: #6b7280; font-weight: 600; }
.login-card { background: white; padding: 36px 40px; border-radius: 20px; box-shadow: 0 12px 40px rgba(0,43,91,0.18); }
.time-badge { background: #002B5B; color: white; padding: 6px 16px; border-radius: 24px; font-size: 0.82rem; float: right; }
</style>
""", unsafe_allow_html=True)

# ==================== CONEXIÓN A BASE DE DATOS SIMPLIFICADA ====================

# Credenciales correctas (verificadas que funcionan)
DB_CONFIG = {
    "host": "bmffi0bgsqnener2omcu-mysql.services.clever-cloud.com",
    "database": "bmffi0bgsqnener2omcu",
    "user": "uo8vbdsnvm2ojwta",
    "password": "aXSKib5oxXDEwjlozeQP",
    "port": 3306,
    "connection_timeout": 30,
    "autocommit": True,
}

def get_db_connection():
    """Obtiene una conexión directa a la base de datos."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

def execute_query(query, params=None, fetch=True):
    """Ejecuta una consulta y retorna resultados."""
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
        return result if fetch else True
    except Exception as e:
        st.error(f"Error en consulta: {e}")
        return [] if fetch else False

# ==================== ESTADO DE SESIÓN ====================
if "login" not in st.session_state:
    st.session_state.login = False
if "user" not in st.session_state:
    st.session_state.user = ""
if "role" not in st.session_state:
    st.session_state.role = ""
if "menu_sel" not in st.session_state:
    st.session_state.menu_sel = None

# ==================== LOGIN ====================
if not st.session_state.login:
    st.markdown(f'<div style="text-align:center;padding:30px;"><img src="{LOGO_URL}" width="300"></div>', unsafe_allow_html=True)
    
    _, col_c, _ = st.columns([1, 2, 1])
    with col_c:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("<h3 style='text-align:center;color:#002B5B;'>Carrier Transicold</h3>", unsafe_allow_html=True)
        
        username = st.text_input("Usuario", key="login_user")
        password = st.text_input("Contraseña", type="password", key="login_pass")
        
        if st.button("Ingresar", use_container_width=True, type="primary"):
            if username and password:
                users = execute_query(
                    "SELECT * FROM users WHERE username=%s AND password=%s",
                    (username, password)
                )
                if users and len(users) > 0:
                    st.session_state.login = True
                    st.session_state.user = users[0]["username"]
                    st.session_state.role = users[0]["role"].lower()
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos")
            else:
                st.warning("⚠️ Ingresa usuario y contraseña")
        
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==================== SIDEBAR ====================
with st.sidebar:
    st.image(LOGO_URL, width=200)
    st.markdown("---")
    st.markdown(f"**👤 {st.session_state.user}**")
    st.markdown(f"*{'🛡 Admin' if st.session_state.role == 'admin' else '🔧 Técnico'}*")
    st.markdown("---")
    
    if st.session_state.role == "admin":
        menu_options = ["📊 Dashboard", "🎯 Asignaciones", "📦 Inventarios", "📸 Unidades", "👥 Usuarios"]
    else:
        menu_options = ["🎯 Mis Tareas", "🔔 Nueva Solicitud"]
    
    menu = st.radio("MENÚ", menu_options, key="menu")
    st.session_state.menu_sel = menu
    st.markdown("---")
    
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        for key in ["login", "user", "role", "menu_sel"]:
            st.session_state[key] = False if key == "login" else None
        st.rerun()

# ==================== DASHBOARD ====================
if menu == "📊 Dashboard":
    st.markdown(f'<div class="time-badge">🕒 {hora_actual}</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-header">📊 Panel de Control</div>', unsafe_allow_html=True)
    
    asignaciones = execute_query("SELECT * FROM asignaciones")
    unidades = execute_query("SELECT * FROM unidades")
    
    total_unidades = len(unidades)
    total_tareas = len(asignaciones)
    completadas = sum(1 for a in asignaciones if a.get("estado") == "completada") if asignaciones else 0
    en_proceso = sum(1 for a in asignaciones if a.get("estado") == "en_proceso") if asignaciones else 0
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="kpi-wrap"><div class="kpi-num">{total_unidades}</div><div class="kpi-lbl">Unidades</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="kpi-wrap"><div class="kpi-num">{total_tareas}</div><div class="kpi-lbl">Tareas</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="kpi-wrap"><div class="kpi-num">{completadas}</div><div class="kpi-lbl">Completadas</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="kpi-wrap"><div class="kpi-num">{en_proceso}</div><div class="kpi-lbl">En Proceso</div></div>', unsafe_allow_html=True)
    
    if asignaciones:
        st.markdown('<div class="section-title">📋 Últimas Actividades</div>', unsafe_allow_html=True)
        df = pd.DataFrame(asignaciones)
        st.dataframe(df[["unidad", "actividad_id", "tecnico", "estado"]].head(10), use_container_width=True)

# ==================== ASIGNACIONES (ADMIN) ====================
elif menu == "🎯 Asignaciones":
    st.markdown('<div class="main-header">🎯 Gestión de Asignaciones</div>', unsafe_allow_html=True)
    
    solicitudes = execute_query("SELECT * FROM asignaciones WHERE estado='solicitado'")
    
    if solicitudes:
        st.markdown(f'### 📨 Solicitudes Pendientes ({len(solicitudes)})')
        for s in solicitudes:
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.info(f"**{s['tecnico']}** solicita **{s['actividad_id']}** para unidad **{s['unidad']}**")
                with col2:
                    if st.button("✅ Aprobar", key=f"ap_{s['id']}"):
                        execute_query("UPDATE asignaciones SET estado='pendiente' WHERE id=%s", (s['id'],), fetch=False)
                        st.rerun()
                with col3:
                    if st.button("❌ Rechazar", key=f"re_{s['id']}"):
                        execute_query("DELETE FROM asignaciones WHERE id=%s", (s['id'],), fetch=False)
                        st.rerun()
                st.markdown("---")
    
    st.markdown("### ➕ Nueva Asignación Directa")
    unidades = execute_query("SELECT unit_number FROM unidades")
    tecnicos = execute_query("SELECT username FROM users WHERE role='tecnico'")
    
    with st.form("nueva_asignacion"):
        col1, col2, col3 = st.columns(3)
        unidad = col1.selectbox("Unidad", [u["unit_number"] for u in unidades] if unidades else [])
        tecnico = col2.selectbox("Técnico", [t["username"] for t in tecnicos] if tecnicos else [])
        actividad = col3.selectbox("Actividad", ACTIVIDADES_CARRIER)
        
        if st.form_submit_button("📋 Crear Asignación", type="primary"):
            if unidad and tecnico and actividad:
                execute_query(
                    "INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s,%s,%s,'pendiente')",
                    (unidad, actividad, tecnico), fetch=False
                )
                st.success("✅ Asignación creada")
                st.rerun()

# ==================== MIS TAREAS (TÉCNICO) ====================
elif menu == "🎯 Mis Tareas":
    st.markdown('<div class="main-header">🎯 Mis Tareas</div>', unsafe_allow_html=True)
    
    tareas = execute_query(
        "SELECT * FROM asignaciones WHERE tecnico=%s AND estado IN ('pendiente','en_proceso')",
        (st.session_state.user,)
    )
    
    if not tareas:
        st.info("✅ No tienes tareas pendientes")
    
    for tarea in tareas:
        with st.expander(f"📋 {tarea['actividad_id']} - Unidad {tarea['unidad']}"):
            if tarea["estado"] == "pendiente":
                if st.button("▶️ Iniciar", key=f"iniciar_{tarea['id']}"):
                    execute_query(
                        "UPDATE asignaciones SET estado='en_proceso', fecha_inicio=%s WHERE id=%s",
                        (datetime.now(tijuana_tz), tarea['id']), fetch=False
                    )
                    st.rerun()
            else:
                if tarea["actividad_id"].lower() == "toma de series":
                    with st.form(f"series_{tarea['id']}"):
                        st.markdown("### 📝 Registrar Series")
                        valores = {}
                        for campo, label in CAMPOS_SERIES.items():
                            valores[campo] = st.text_input(label)
                        
                        if st.form_submit_button("💾 Guardar Series", type="primary"):
                            set_q = ", ".join([f"{k}=%s" for k in valores.keys()])
                            execute_query(
                                f"UPDATE unidades SET {set_q} WHERE unit_number=%s",
                                list(valores.values()) + [tarea["unidad"]], fetch=False
                            )
                            execute_query(
                                "UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s",
                                (datetime.now(tijuana_tz), tarea['id']), fetch=False
                            )
                            st.success("✅ Series guardadas")
                            st.rerun()
                
                elif tarea["actividad_id"].lower() == "evidencia":
                    fotos = execute_query(
                        "SELECT COUNT(*) as total FROM evidencias WHERE unit_number=%s AND tecnico=%s",
                        (tarea["unidad"], st.session_state.user)
                    )
                    total_fotos = fotos[0]["total"] if fotos else 0
                    st.info(f"📸 Fotos guardadas: {total_fotos}/{MAX_FOTOS}")
                    
                    archivos = st.file_uploader(
                        "Selecciona fotos", 
                        accept_multiple_files=True, 
                        type=["jpg", "jpeg", "png"],
                        key=f"fotos_{tarea['id']}"
                    )
                    
                    if archivos and st.button("💾 Guardar Fotos", key=f"guardar_{tarea['id']}"):
                        for archivo in archivos[:MAX_FOTOS - total_fotos]:
                            execute_query(
                                "INSERT INTO evidencias (unit_number, nombre_archivo, contenido, tecnico) VALUES (%s,%s,%s,%s)",
                                (tarea["unidad"], archivo.name, archivo.read(), st.session_state.user), fetch=False
                            )
                        st.rerun()
                    
                    if st.button("✅ Finalizar Tarea", key=f"finalizar_{tarea['id']}"):
                        execute_query(
                            "UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s",
                            (datetime.now(tijuana_tz), tarea['id']), fetch=False
                        )
                        st.rerun()
                
                else:
                    if st.button("✅ Completar", key=f"completar_{tarea['id']}"):
                        execute_query(
                            "UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s",
                            (datetime.now(tijuana_tz), tarea['id']), fetch=False
                        )
                        st.rerun()

# ==================== NUEVA SOLICITUD ====================
elif menu == "🔔 Nueva Solicitud":
    st.markdown('<div class="main-header">🔔 Nueva Solicitud</div>', unsafe_allow_html=True)
    
    unidades = execute_query("SELECT unit_number FROM unidades")
    
    with st.form("nueva_solicitud"):
        unidad = st.selectbox("Unidad", [u["unit_number"] for u in unidades] if unidades else [])
        actividad = st.selectbox("Actividad", ACTIVIDADES_CARRIER)
        
        if st.form_submit_button("📤 Enviar Solicitud", type="primary"):
            if unidad and actividad:
                execute_query(
                    "INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s,%s,%s,'solicitado')",
                    (unidad, actividad, st.session_state.user), fetch=False
                )
                st.success("✅ Solicitud enviada al administrador")
                st.rerun()

# ==================== INVENTARIOS ====================
elif menu == "📦 Inventarios":
    st.markdown('<div class="main-header">📦 Inventarios</div>', unsafe_allow_html=True)
    
    # Crear tabla si no existe
    execute_query("""
        CREATE TABLE IF NOT EXISTS inventario (
            id INT AUTO_INCREMENT PRIMARY KEY,
            codigo VARCHAR(100),
            descripcion TEXT,
            cantidad INT,
            ubicacion VARCHAR(100)
        )
    """, fetch=False)
    
    inventario = execute_query("SELECT * FROM inventario ORDER BY id")
    
    if inventario:
        df_inv = pd.DataFrame(inventario)
        st.dataframe(df_inv, use_container_width=True, hide_index=True)
    else:
        st.info("📋 Inventario vacío")
    
    with st.expander("➕ Agregar Producto"):
        with st.form("nuevo_producto"):
            col1, col2 = st.columns(2)
            codigo = col1.text_input("Código")
            descripcion = col2.text_input("Descripción")
            cantidad = col1.number_input("Cantidad", min_value=0, step=1)
            ubicacion = col2.text_input("Ubicación")
            
            if st.form_submit_button("💾 Guardar"):
                if codigo:
                    execute_query(
                        "INSERT INTO inventario (codigo, descripcion, cantidad, ubicacion) VALUES (%s,%s,%s,%s)",
                        (codigo, descripcion, cantidad, ubicacion), fetch=False
                    )
                    st.rerun()

# ==================== UNIDADES ====================
elif menu == "📸 Unidades":
    st.markdown('<div class="main-header">📸 Registro de Unidades</div>', unsafe_allow_html=True)
    
    with st.form("nueva_unidad"):
        col1, col2 = st.columns(2)
        numero = col1.text_input("Número Económico")
        lote = col2.text_input("Lote")
        
        if st.form_submit_button("💾 Guardar Unidad", type="primary"):
            if numero:
                execute_query(
                    "INSERT INTO unidades (unit_number, id_lote) VALUES (%s,%s) ON DUPLICATE KEY UPDATE id_lote=%s",
                    (numero, lote, lote), fetch=False
                )
                st.success("✅ Unidad guardada")
                st.rerun()
    
    unidades = execute_query("SELECT * FROM unidades ORDER BY unit_number")
    if unidades:
        st.markdown("### 📋 Listado de Unidades")
        st.dataframe(pd.DataFrame(unidades), use_container_width=True, hide_index=True)

# ==================== USUARIOS ====================
elif menu == "👥 Usuarios":
    st.markdown('<div class="main-header">👥 Gestión de Usuarios</div>', unsafe_allow_html=True)
    
    usuarios = execute_query("SELECT username, role FROM users ORDER BY username")
    if usuarios:
        st.dataframe(pd.DataFrame(usuarios), use_container_width=True, hide_index=True)
    
    with st.expander("➕ Crear Nuevo Usuario"):
        with st.form("nuevo_usuario"):
            col1, col2, col3 = st.columns(3)
            username = col1.text_input("Usuario")
            password = col2.text_input("Contraseña", type="password")
            role = col3.selectbox("Rol", ["tecnico", "admin"])
            
            if st.form_submit_button("👤 Crear"):
                if username and password:
                    execute_query(
                        "INSERT INTO users (username, password, role) VALUES (%s,%s,%s)",
                        (username, password, role), fetch=False
                    )
                    st.success(f"✅ Usuario {username} creado")
                    st.rerun()