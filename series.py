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

# ==================== CSS PREMIUM ====================
st.markdown(f"""
<style>
header[data-testid="stHeader"] {{ display: none !important; }}
footer {{ display: none !important; }}
#MainMenu {{ display: none !important; }}
.stDeployButton {{ display: none !important; }}
[data-testid="stToolbar"] {{ display: none !important; }}
.block-container {{ padding-top: 1.5rem !important; }}
section[data-testid="stSidebar"] {{ width: 21rem !important; }}
.main-header {{ font-size: 1.75rem; font-weight: 800; color: {CARRIER_BLUE}; border-bottom: 3px solid {CARRIER_ACCENT}; padding-bottom: 12px; margin-bottom: 24px; }}
.section-title {{ font-size: 0.92rem; font-weight: 700; color: {CARRIER_BLUE}; border-left: 4px solid {CARRIER_ACCENT}; padding: 9px 14px; margin: 22px 0 14px 0; background: white; border-radius: 0 8px 8px 0; }}
.kpi-wrap {{ background: white; border-radius: 16px; padding: 20px; text-align: center; box-shadow: 0 4px 20px rgba(0,43,91,0.08); border-top: 5px solid {CARRIER_ACCENT}; }}
.kpi-num {{ font-size: 2.4rem; font-weight: 800; color: {CARRIER_BLUE}; }}
.kpi-lbl {{ font-size: 0.73rem; color: #6b7280; font-weight: 600; }}
.time-badge {{ background: {CARRIER_BLUE}; color: white; padding: 6px 16px; border-radius: 24px; float: right; }}
.login-card {{ background: white; padding: 36px 40px; border-radius: 20px; box-shadow: 0 12px 40px rgba(0,43,91,0.18); }}
.evidencia-info {{ background: #eff6ff; border-left: 5px solid #3b82f6; padding: 12px 18px; border-radius: 10px; margin-bottom: 14px; }}
.fotos-badge {{ background: #f0fdf4; border: 1px solid #86efac; border-radius: 20px; padding: 4px 14px; display: inline-block; }}
.tv-field-badge {{ background: {CARRIER_LIGHT}; border: 1px solid #c3d4f0; border-radius: 8px; padding: 6px 12px; display: inline-block; }}
.inv-info-bar {{ background: linear-gradient(90deg, {CARRIER_BLUE}, {CARRIER_ACCENT}); color: white; padding: 14px 20px; border-radius: 12px; margin-bottom: 16px; }}
.bloqueo-card {{ background: #fef2f2; border-left: 5px solid {CARRIER_DANGER}; border-radius: 10px; padding: 14px 18px; margin: 8px 0; }}
.user-chip {{ background: rgba(255,255,255,0.12); border-radius: 50px; padding: 6px 14px; color: white; display: inline-block; }}
</style>
""", unsafe_allow_html=True)

# ==================== CONEXIÓN DIRECTA A TIDB CLOUD (CON REINTENTOS) ====================
DB_CONFIG = {
    "host": "gateway01.us-east-1.prod.aws.tidbcloud.com",
    "port": 4000,
    "user": "4BgYs96t9XXhCMS.root",
    "password": "YZcSUhQ5H7Gx9vLk",
    "database": "carrier_db",
    "connection_timeout": 30,
    "autocommit": True,
    "use_pure": True,
}

def get_db_connection(max_retries=3):
    for i in range(max_retries):
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            return conn
        except Exception as e:
            if i == max_retries - 1:
                st.error(f"❌ Error de conexión: {e}")
                return None
            time.sleep(1.5 ** (i+1))
    return None

def execute_query(query, params=None, fetch=True):
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
        st.error(f"Error en consulta: {e}")
        return [] if fetch else False

# ==================== INICIALIZAR TABLAS FALTANTES ====================
def init_tables():
    queries = [
        """CREATE TABLE IF NOT EXISTS actividades (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nombre VARCHAR(100) NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS unidades (
            id INT AUTO_INCREMENT PRIMARY KEY,
            unit_number VARCHAR(50) UNIQUE,
            id_lote VARCHAR(100),
            vin_number VARCHAR(50),
            engine_serial VARCHAR(50),
            compressor_serial VARCHAR(50),
            fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
            reefer_serial VARCHAR(255),
            reefer_model VARCHAR(255),
            evaporator_serial_mjs11 VARCHAR(255),
            evaporator_serial_mjd22 VARCHAR(255),
            generator_serial VARCHAR(255),
            battery_charger_serial VARCHAR(255)
        )""",
        """CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE,
            password VARCHAR(100),
            role ENUM('admin','tecnico') DEFAULT 'tecnico'
        )""",
        """CREATE TABLE IF NOT EXISTS asignaciones (
            id INT AUTO_INCREMENT PRIMARY KEY,
            unidad VARCHAR(50),
            actividad_id VARCHAR(100),
            tecnico VARCHAR(100),
            estado VARCHAR(20) DEFAULT 'pendiente',
            fecha_asignacion DATETIME DEFAULT CURRENT_TIMESTAMP,
            fecha_inicio DATETIME,
            fecha_fin DATETIME,
            ticket_id INT
        )""",
        """CREATE TABLE IF NOT EXISTS evidencias (
            id INT AUTO_INCREMENT PRIMARY KEY,
            unit_number VARCHAR(50),
            nombre_archivo VARCHAR(255),
            contenido LONGBLOB,
            tecnico VARCHAR(100),
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            KEY idx_unit_number (unit_number)
        )""",
        """CREATE TABLE IF NOT EXISTS comentarios_actividades (
            id INT AUTO_INCREMENT PRIMARY KEY,
            asignacion_id INT NOT NULL,
            tecnico VARCHAR(50),
            comentario TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS config_sistema (
            clave VARCHAR(50) PRIMARY KEY,
            valor TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS inventario_columnas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            tabla_nombre VARCHAR(120) DEFAULT 'Principal',
            col_nombre VARCHAR(120) NOT NULL,
            col_orden INT DEFAULT 0
        )""",
        """CREATE TABLE IF NOT EXISTS inventario_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            tabla_nombre VARCHAR(120) DEFAULT 'Principal',
            fila_idx INT NOT NULL,
            col_nombre VARCHAR(120) NOT NULL,
            valor TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
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
            fecha_atencion TIMESTAMP,
            fecha_reporte TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS valores_registrados (
            id INT AUTO_INCREMENT PRIMARY KEY,
            unit_number VARCHAR(100),
            campo VARCHAR(100),
            valor VARCHAR(255),
            tecnico VARCHAR(100),
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
    ]
    for q in queries:
        execute_query(q, fetch=False)
    
    # Insertar actividades si no existen
    actividades = execute_query("SELECT COUNT(*) as total FROM actividades")
    if actividades and actividades[0]["total"] == 0:
        for i, nombre in enumerate(ACTIVIDADES_CARRIER, 1):
            execute_query("INSERT INTO actividades (id, nombre) VALUES (%s, %s) ON DUPLICATE KEY UPDATE nombre=%s", (i, nombre, nombre), fetch=False)
    
    # Insertar configuración si no existe
    config = execute_query("SELECT * FROM config_sistema WHERE clave='correos_reporte'")
    if not config:
        execute_query("INSERT INTO config_sistema (clave, valor) VALUES ('correos_reporte', 'ejemplo@correo.com')", fetch=False)
    
    # Insertar campos de toma de valores si no existen
    campos_tv = execute_query("SELECT COUNT(*) as total FROM toma_valores_campos")
    if campos_tv and campos_tv[0]["total"] == 0:
        campos = [
            ('Presión de Succión (PSI)', 0), ('Presión de Descarga (PSI)', 1),
            ('Temperatura Set Point (°C)', 2), ('Temperatura de Retorno (°C)', 3),
            ('Temperatura de Suministro (°C)', 4), ('Voltaje Batería (V)', 5),
            ('Corriente (A)', 6), ('RPM Motor', 7), ('Horas de Motor', 8),
            ('Temperatura Ambiente (°C)', 9)
        ]
        for campo, orden in campos:
            execute_query("INSERT INTO toma_valores_campos (campo_nombre, campo_orden) VALUES (%s, %s)", (campo, orden), fetch=False)
    
    # Insertar columnas de inventario si no existen
    inv_cols = execute_query("SELECT COUNT(*) as total FROM inventario_columnas")
    if inv_cols and inv_cols[0]["total"] == 0:
        columnas = ['Código', 'Descripción', 'Cantidad', 'Unidad', 'Ubicación', 'Estado']
        for i, col in enumerate(columnas):
            execute_query("INSERT INTO inventario_columnas (tabla_nombre, col_nombre, col_orden) VALUES (%s, %s, %s)", ('Principal', col, i), fetch=False)

init_tables()

# ==================== ESTADO DE SESIÓN ====================
if "login" not in st.session_state:
    st.session_state.login = False
if "user" not in st.session_state:
    st.session_state.user = ""
if "role" not in st.session_state:
    st.session_state.role = ""
if "menu_sel" not in st.session_state:
    st.session_state.menu_sel = None
if "last_count" not in st.session_state:
    st.session_state.last_count = 0

# ==================== LOGIN ====================
if not st.session_state.login:
    st.markdown(f'<div style="text-align:center;padding:30px;"><img src="{LOGO_DATA_URI}" width="340"></div>', unsafe_allow_html=True)
    _, col_c, _ = st.columns([1,2,1])
    with col_c:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("<h3 style='text-align:center;color:#002B5B;'>Carrier Transicold</h3>", unsafe_allow_html=True)
        username = st.text_input("Usuario", key="login_user")
        password = st.text_input("Contraseña", type="password", key="login_pass")
        if st.button("Ingresar", use_container_width=True, type="primary"):
            if username and password:
                user = execute_query("SELECT * FROM users WHERE username = %s AND password = %s", (username.strip(), password.strip()))
                if user:
                    st.session_state.login = True
                    st.session_state.user = user[0]["username"]
                    st.session_state.role = user[0]["role"].lower()
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas")
            else:
                st.warning("Ingresa usuario y contraseña")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==================== SIDEBAR ====================
with st.sidebar:
    st.image(LOGO_DATA_URI, width=200)
    st.markdown(f"<p style='margin-top:10px'><b>👤 {st.session_state.user}</b><br><span style='font-size:0.8rem'>{'🛡 Administrador' if st.session_state.role == 'admin' else '🔧 Técnico'}</span></p>", unsafe_allow_html=True)
    st.markdown("---")
    if st.session_state.role == "admin":
        menu_options = ["📊 Dashboard Ejecutivo", "🎯 Control de Asignaciones", "🎫 Tickets", "📦 Inventarios", "📸 Registro de Unidades", "👥 Gestión de Usuarios"]
    else:
        menu_options = ["🎯 Mis Tareas", "🔔 Nueva Solicitud"]
    menu = st.radio("MENÚ", menu_options, key="menu")
    st.session_state.menu_sel = menu
    st.markdown("---")
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        for k in ["login", "user", "role", "menu_sel"]:
            st.session_state[k] = False if k == "login" else None
        st.rerun()

# ==================== FUNCIONES AUXILIARES ====================
def get_next_ticket_num():
    res = execute_query("SELECT MAX(ticket_num) as max_num FROM tickets")
    if res and res[0]["max_num"]:
        return res[0]["max_num"] + 1
    return 1

# ==================== DASHBOARD EJECUTIVO ====================
if menu == "📊 Dashboard Ejecutivo" and st.session_state.role == "admin":
    st.markdown(f'<div class="time-badge">🕒 {hora_actual}</div><div class="main-header">📊 Panel de Rendimiento Operativo</div>', unsafe_allow_html=True)
    asig = execute_query("SELECT * FROM asignaciones")
    unid = execute_query("SELECT * FROM unidades")
    df_a = pd.DataFrame(asig) if asig else pd.DataFrame()
    total_u = len(unid)
    total_t = len(df_a)
    comp_t = int((df_a["estado"] == "completada").sum()) if not df_a.empty else 0
    proc_t = int((df_a["estado"] == "en_proceso").sum()) if not df_a.empty else 0
    pend_t = int((df_a["estado"] == "pendiente").sum()) if not df_a.empty else 0
    pct_av = round(comp_t / total_t * 100) if total_t else 0
    col1, col2, col3, col4, col5 = st.columns(5)
    for col, val, lbl, cls in [
        (col1, total_u, "Total Unidades", ""),
        (col2, comp_t, "Completadas", "green"),
        (col3, proc_t, "En Proceso", "amber"),
        (col4, pend_t, "Pendientes", "red"),
        (col5, f"{pct_av}%", "Avance Global", "purple"),
    ]:
        with col:
            st.markdown(f'<div class="kpi-wrap {cls}"><div class="kpi-num">{val}</div><div class="kpi-lbl">{lbl}</div></div>', unsafe_allow_html=True)
    st.markdown("<br>")
    if not df_a.empty:
        st.markdown('<div class="section-title">📈 Estadísticas por Técnico</div>', unsafe_allow_html=True)
        stats = df_a.groupby("tecnico").agg(
            Total=("id","count"),
            Completadas=("estado", lambda x: (x=="completada").sum()),
            En_Curso=("estado", lambda x: (x=="en_proceso").sum()),
            Pendientes=("estado", lambda x: (x=="pendiente").sum())
        ).reset_index()
        stats["Rendimiento %"] = ((stats["Completadas"] / stats["Total"]) * 100).round(0).astype(int)
        st.dataframe(stats.sort_values("Total", ascending=False), use_container_width=True, hide_index=True)
        COLOR_MAP = {"completada": CARRIER_SUCCESS, "en_proceso": CARRIER_WARN, "pendiente": CARRIER_DANGER, "solicitado": "#6b7280"}
        c1, c2 = st.columns(2)
        with c1:
            fig_b = px.bar(df_a, x="tecnico", color="estado", title="Carga de Trabajo por Técnico", color_discrete_map=COLOR_MAP, template="plotly_white")
            fig_b.update_layout(paper_bgcolor="white", plot_bgcolor="white")
            st.plotly_chart(fig_b, use_container_width=True)
        with c2:
            fig_p = px.pie(df_a, names="estado", title="Distribución Global", hole=0.55, color_discrete_map=COLOR_MAP, template="plotly_white")
            fig_p.update_layout(paper_bgcolor="white")
            st.plotly_chart(fig_p, use_container_width=True)
    st.markdown('<div class="section-title">📋 Estatus de Proceso por Unidad</div>', unsafe_allow_html=True)
    if unid:
        completadas_raw = execute_query("SELECT unidad, actividad_id FROM asignaciones WHERE estado='completada'")
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
        col_ev1, col_ev2 = st.columns([3,1])
        with col_ev1:
            u_sel_ev = st.selectbox("Selecciona unidad:", [u["unit_number"] for u in unid], key="ev_sel")
        ev_archivos = execute_query("SELECT nombre_archivo, contenido FROM evidencias WHERE unit_number=%s", (u_sel_ev,))
        with col_ev2:
            st.metric("📸 Fotos", len(ev_archivos))
        if ev_archivos:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as zf:
                for ev in ev_archivos:
                    zf.writestr(ev["nombre_archivo"], ev["contenido"])
            st.download_button(f"📥 Descargar {len(ev_archivos)} fotos — Unidad {u_sel_ev}", buf.getvalue(), f"{u_sel_ev}_evidencia.zip", use_container_width=True)
        else:
            st.info("Sin fotos cargadas")
    st.markdown('<div class="section-title">📥 Reportes y Descargas</div>', unsafe_allow_html=True)
    if unid:
        df_u = pd.DataFrame(unid)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_u.to_excel(writer, index=False, sheet_name="Series_Unidades")
            if not df_a.empty:
                df_a.to_excel(writer, index=False, sheet_name="Actividades")
        st.download_button("📊 Descargar Reporte Maestro (Excel)", buffer.getvalue(), f"Carrier_Reporte_{fecha_hoy}.xlsx", use_container_width=True, type="primary")

# ==================== CONTROL DE ASIGNACIONES ====================
elif menu == "🎯 Control de Asignaciones" and st.session_state.role == "admin":
    st.markdown('<div class="main-header">🎯 Gestión de Órdenes de Trabajo</div>', unsafe_allow_html=True)
    solicitudes = execute_query("SELECT * FROM asignaciones WHERE estado='solicitado'")
    if solicitudes:
        st.markdown(f"### 📨 Solicitudes pendientes ({len(solicitudes)})")
        for s in solicitudes:
            with st.container():
                col1, col2, col3 = st.columns([4,1,1])
                col1.warning(f"**{s['tecnico']}** solicita **{s['actividad_id']}** para unidad **{s['unidad']}**")
                if col2.button("✅ Aprobar", key=f"ap_{s['id']}"):
                    execute_query("UPDATE asignaciones SET estado='pendiente' WHERE id=%s", (s['id'],), fetch=False)
                    st.rerun()
                if col3.button("❌ Rechazar", key=f"re_{s['id']}"):
                    execute_query("DELETE FROM asignaciones WHERE id=%s", (s['id'],), fetch=False)
                    st.rerun()
                st.markdown("---")
    else:
        st.success("No hay solicitudes pendientes")
    st.markdown("### ➕ Asignación directa")
    unidades = execute_query("SELECT unit_number FROM unidades")
    tecnicos = execute_query("SELECT username FROM users WHERE role='tecnico'")
    with st.form("asignacion_directa"):
        c1, c2, c3 = st.columns(3)
        unidad = c1.selectbox("Unidad", [u["unit_number"] for u in unidades] if unidades else [])
        tecnico = c2.selectbox("Técnico", [t["username"] for t in tecnicos] if tecnicos else [])
        actividad = c3.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.form_submit_button("📋 Crear orden", type="primary"):
            if unidad and tecnico and actividad:
                execute_query("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s,%s,%s,'pendiente')", (unidad, actividad, tecnico), fetch=False)
                st.success("Orden creada")
                st.rerun()

# ==================== MIS TAREAS ====================
elif menu == "🎯 Mis Tareas" and st.session_state.role == "tecnico":
    st.markdown('<div class="main-header">🎯 Mis Actividades</div>', unsafe_allow_html=True)
    tareas = execute_query("SELECT * FROM asignaciones WHERE tecnico=%s AND estado IN ('pendiente','en_proceso')", (st.session_state.user,))
    if not tareas:
        st.info("No tienes tareas pendientes")
    for t in tareas:
        es_ticket = t["actividad_id"].startswith("Ticket #") if t["actividad_id"] else False
        with st.expander(f"{'⏳' if t['estado']=='pendiente' else '▶️'} Unidad {t['unidad']} - {t['actividad_id']}"):
            if t["estado"] == "pendiente":
                if st.button("Iniciar", key=f"ini_{t['id']}"):
                    execute_query("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']), fetch=False)
                    st.rerun()
            else:
                comentario = st.text_area("Comentario / Reporte", key=f"coment_{t['id']}")
                if t["actividad_id"].lower() == "evidencia":
                    fotos = execute_query("SELECT COUNT(*) as total FROM evidencias WHERE unit_number=%s AND tecnico=%s", (t["unidad"], st.session_state.user))
                    total_fotos = fotos[0]["total"] if fotos else 0
                    st.info(f"📸 Fotos guardadas: {total_fotos}/{MAX_FOTOS}")
                    archivos = st.file_uploader("Selecciona fotos", accept_multiple_files=True, type=["jpg","jpeg","png"], key=f"fotos_{t['id']}")
                    if archivos and st.button("Guardar fotos", key=f"guardar_{t['id']}"):
                        for arc in archivos[:MAX_FOTOS - total_fotos]:
                            execute_query("INSERT INTO evidencias (unit_number, nombre_archivo, contenido, tecnico) VALUES (%s,%s,%s,%s)", (t["unidad"], arc.name, arc.read(), st.session_state.user), fetch=False)
                        st.rerun()
                    if st.button("✅ Finalizar", key=f"fin_ev_{t['id']}"):
                        if comentario:
                            execute_query("INSERT INTO comentarios_actividades (asignacion_id, tecnico, comentario) VALUES (%s,%s,%s)", (t['id'], st.session_state.user, comentario), fetch=False)
                        execute_query("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']), fetch=False)
                        if es_ticket and t.get("ticket_id"):
                            execute_query("UPDATE tickets SET atendido=TRUE, fecha_atencion=%s WHERE id=%s", (datetime.now(tijuana_tz), t['ticket_id']), fetch=False)
                        st.success("Actividad completada")
                        st.rerun()
                elif t["actividad_id"].lower() == "toma de valores":
                    st.markdown('<div class="tv-field-badge">📊 Registro de Valores del Equipo</div>', unsafe_allow_html=True)
                    campos = execute_query("SELECT campo_nombre FROM toma_valores_campos ORDER BY campo_orden ASC")
                    if not campos:
                        st.info("No hay campos configurados. Contacta al administrador.")
                    else:
                        datos_previos = execute_query("SELECT campo_nombre, valor FROM toma_valores_datos WHERE asignacion_id=%s", (t['id'],))
                        prev_dict = {d["campo_nombre"]: d["valor"] or "" for d in datos_previos}
                        with st.form(f"tv_{t['id']}"):
                            valores = {}
                            for c in campos:
                                valores[c["campo_nombre"]] = st.text_input(c["campo_nombre"], value=prev_dict.get(c["campo_nombre"], ""))
                            if st.form_submit_button("Guardar valores y finalizar", type="primary"):
                                execute_query("DELETE FROM toma_valores_datos WHERE asignacion_id=%s", (t['id'],), fetch=False)
                                for campo, valor in valores.items():
                                    execute_query("INSERT INTO toma_valores_datos (asignacion_id, campo_nombre, valor) VALUES (%s,%s,%s)", (t['id'], campo, valor), fetch=False)
                                if comentario:
                                    execute_query("INSERT INTO comentarios_actividades (asignacion_id, tecnico, comentario) VALUES (%s,%s,%s)", (t['id'], st.session_state.user, comentario), fetch=False)
                                execute_query("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']), fetch=False)
                                if es_ticket and t.get("ticket_id"):
                                    execute_query("UPDATE tickets SET atendido=TRUE, fecha_atencion=%s WHERE id=%s", (datetime.now(tijuana_tz), t['ticket_id']), fetch=False)
                                st.success("Valores guardados")
                                st.rerun()
                elif t["actividad_id"].lower() == "toma de series":
                    with st.form(f"series_{t['id']}"):
                        st.markdown("Ingresa los seriales de cada componente:")
                        valores = {}
                        for campo, label in CAMPOS_SERIES.items():
                            valores[campo] = st.text_input(label)
                        if st.form_submit_button("Guardar series y finalizar", type="primary"):
                            set_q = ", ".join([f"{k}=%s" for k in valores.keys()])
                            execute_query(f"UPDATE unidades SET {set_q} WHERE unit_number=%s", list(valores.values()) + [t["unidad"]], fetch=False)
                            if comentario:
                                execute_query("INSERT INTO comentarios_actividades (asignacion_id, tecnico, comentario) VALUES (%s,%s,%s)", (t['id'], st.session_state.user, comentario), fetch=False)
                            execute_query("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']), fetch=False)
                            if es_ticket and t.get("ticket_id"):
                                execute_query("UPDATE tickets SET atendido=TRUE, fecha_atencion=%s WHERE id=%s", (datetime.now(tijuana_tz), t['ticket_id']), fetch=False)
                            st.success("Series guardadas")
                            st.rerun()
                else:
                    if st.button("✅ Completar", key=f"fin_{t['id']}", type="primary"):
                        if comentario:
                            execute_query("INSERT INTO comentarios_actividades (asignacion_id, tecnico, comentario) VALUES (%s,%s,%s)", (t['id'], st.session_state.user, comentario), fetch=False)
                        execute_query("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']), fetch=False)
                        if es_ticket and t.get("ticket_id"):
                            execute_query("UPDATE tickets SET atendido=TRUE, fecha_atencion=%s WHERE id=%s", (datetime.now(tijuana_tz), t['ticket_id']), fetch=False)
                        st.success("Actividad completada")
                        st.rerun()

# ==================== NUEVA SOLICITUD ====================
elif menu == "🔔 Nueva Solicitud" and st.session_state.role == "tecnico":
    st.markdown('<div class="main-header">🔔 Solicitar Actividad</div>', unsafe_allow_html=True)
    unidades = execute_query("SELECT unit_number FROM unidades")
    with st.form("nueva_solicitud"):
        unidad = st.selectbox("Unidad", [u["unit_number"] for u in unidades] if unidades else [])
        actividad = st.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.form_submit_button("Enviar solicitud", type="primary"):
            if unidad and actividad:
                existente = execute_query("SELECT id FROM asignaciones WHERE tecnico=%s AND unidad=%s AND actividad_id=%s AND estado IN ('solicitado','pendiente','en_proceso')", (st.session_state.user, unidad, actividad))
                if existente:
                    st.error("Ya tienes esta actividad pendiente o en curso")
                else:
                    execute_query("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s,%s,%s,'solicitado')", (unidad, actividad, st.session_state.user), fetch=False)
                    st.success("Solicitud enviada")
                    st.rerun()

# ==================== TICKETS ====================
elif menu == "🎫 Tickets" and st.session_state.role == "admin":
    st.markdown('<div class="main-header">🎫 Gestión de Tickets</div>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["📋 Listado de Tickets", "➕ Crear nuevo ticket"])
    with tab1:
        tickets = execute_query("SELECT t.*, a.id as asignacion_id, a.tecnico FROM tickets t LEFT JOIN asignaciones a ON t.id = a.ticket_id ORDER BY t.ticket_num DESC")
        if tickets:
            for t in tickets:
                if not t["atendido"]:
                    estado_color = "🔴 No atendido"
                elif t["atendido"] and not t["reporte_enviado"]:
                    estado_color = "🟡 Atendido (sin reporte)"
                else:
                    estado_color = "🟢 Completado"
                with st.container():
                    st.markdown(f'<div style="background:#f8f9fa; border-left: 6px solid {CARRIER_ACCENT}; padding:12px; border-radius:10px; margin-bottom:12px;">', unsafe_allow_html=True)
                    col1, col2, col3 = st.columns([1,3,1])
                    col1.markdown(f"## #{t['ticket_num']}")
                    col1.markdown(f"**{estado_color}**")
                    col2.markdown(f"**Unidad:** {t['unit_number']} | **VIN:** {t.get('vin_number','N/D')}")
                    col2.markdown(f"**Descripción:** {t['descripcion']}")
                    col2.markdown(f"*Creado por: {t['creado_por']} | {t['fecha_creacion']}*")
                    if t.get("tecnico"):
                        col2.markdown(f"*Asignado a: {t['tecnico']}*")
                    with col3:
                        if t["atendido"] and not t["reporte_enviado"]:
                            if st.button("📤 Marcar reporte enviado", key=f"reporte_{t['id']}"):
                                execute_query("UPDATE tickets SET reporte_enviado=TRUE, fecha_reporte=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']), fetch=False)
                                st.rerun()
                        if not t["atendido"]:
                            st.caption("⏳ Esperando atención")
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No hay tickets")
    with tab2:
        unidades = execute_query("SELECT unit_number, vin_number FROM unidades")
        tecnicos = execute_query("SELECT username FROM users WHERE role='tecnico'")
        with st.form("nuevo_ticket"):
            st.markdown("### Crear nuevo ticket")
            unidad_opciones = {f"{u['unit_number']} - {u.get('vin_number','sin VIN')}": u['unit_number'] for u in unidades}
            unidad_label = st.selectbox("Unidad (SAP)", list(unidad_opciones.keys()))
            unidad_seleccionada = unidad_opciones[unidad_label]
            vin_auto = next((u.get("vin_number") for u in unidades if u["unit_number"] == unidad_seleccionada), "")
            vin = st.text_input("VIN Number", value=vin_auto)
            descripcion = st.text_area("Descripción del problema / solicitud")
            tecnico_asignado = st.selectbox("Asignar a técnico", [t["username"] for t in tecnicos] if tecnicos else [])
            if st.form_submit_button("📌 Crear ticket y asignar", type="primary"):
                if unidad_seleccionada and descripcion and tecnico_asignado:
                    next_num = get_next_ticket_num()
                    execute_query("INSERT INTO tickets (ticket_num, unit_number, vin_number, descripcion, creado_por) VALUES (%s,%s,%s,%s,%s)", (next_num, unidad_seleccionada, vin, descripcion, st.session_state.user), fetch=False)
                    ticket = execute_query("SELECT id FROM tickets WHERE ticket_num=%s", (next_num,))
                    if ticket:
                        execute_query("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado, ticket_id) VALUES (%s,%s,%s,'pendiente',%s)", (unidad_seleccionada, f"Ticket #{next_num}", tecnico_asignado, ticket[0]['id']), fetch=False)
                    st.success(f"✅ Ticket #{next_num} creado y asignado a {tecnico_asignado}")
                    st.rerun()
                else:
                    st.warning("Completa todos los campos")

# ==================== INVENTARIOS ====================
elif menu == "📦 Inventarios" and st.session_state.role == "admin":
    st.markdown(f'<div class="time-badge">🕒 {hora_actual}</div><div class="main-header">📦 Gestión de Inventarios</div>', unsafe_allow_html=True)
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
    st.markdown(f'<div class="inv-info-bar">🗄 Inventario Principal · {len(df_inv)} registros · {len(columnas)} columnas</div>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["📋 Tabla de Inventario", "⚙️ Configurar Columnas"])
    with tab1:
        col_add, col_del, _ = st.columns([1,1,2])
        with col_add:
            if st.button("➕ Agregar Fila", use_container_width=True):
                nueva_fila = pd.DataFrame([{c: "" for c in columnas}])
                df_inv = pd.concat([df_inv, nueva_fila], ignore_index=True)
                save_inv_data(df_inv)
                st.rerun()
        with col_del:
            if len(df_inv) > 0:
                fila_del = st.number_input("Eliminar fila #", min_value=1, max_value=len(df_inv), value=1, step=1, key="fila_del")
                if st.button("🗑 Eliminar Fila", use_container_width=True):
                    df_inv = df_inv.drop(index=fila_del-1).reset_index(drop=True)
                    save_inv_data(df_inv)
                    st.rerun()
        if df_inv.empty:
            st.info("📋 Tabla vacía. Agrega filas.")
        else:
            df_editado = st.data_editor(df_inv, use_container_width=True, num_rows="dynamic", hide_index=False, key="inv_editor")
            if st.button("💾 Guardar Cambios", use_container_width=True, type="primary"):
                save_inv_data(df_editado)
                st.success("Inventario guardado")
                st.rerun()
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                df_inv.to_excel(writer, index=False, sheet_name="Inventario")
            st.download_button("📥 Exportar a Excel", buf.getvalue(), f"Inventario_{fecha_hoy}.xlsx", use_container_width=True)
    with tab2:
        with st.form("add_col_form"):
            nueva_col = st.text_input("Nombre de nueva columna")
            if st.form_submit_button("➕ Agregar Columna"):
                if nueva_col and nueva_col not in columnas:
                    columnas.append(nueva_col)
                    save_inv_columnas(columnas)
                    if not df_inv.empty:
                        df_inv[nueva_col] = ""
                        save_inv_data(df_inv)
                    st.rerun()
                elif nueva_col in columnas:
                    st.warning("Ya existe")
                else:
                    st.warning("Escribe un nombre válido")
        st.markdown("### Columnas actuales")
        if columnas:
            for i, col in enumerate(columnas):
                with st.container():
                    c1, c2, c3 = st.columns([3,2,1])
                    c1.markdown(f"`{i+1}.` **{col}**")
                    nuevo_nom = c2.text_input("Renombrar", value=col, key=f"ren_{i}", label_visibility="collapsed")
                    if c3.button("✏️", key=f"renb_{i}"):
                        if nuevo_nom and nuevo_nom != col:
                            if not df_inv.empty and col in df_inv.columns:
                                df_inv = df_inv.rename(columns={col: nuevo_nom})
                                save_inv_data(df_inv)
                            columnas[i] = nuevo_nom
                            save_inv_columnas(columnas)
                            st.rerun()
                    if len(columnas) > 1 and c3.button("🗑", key=f"del_{i}"):
                        columnas.pop(i)
                        save_inv_columnas(columnas)
                        if not df_inv.empty and col in df_inv.columns:
                            df_inv = df_inv.drop(columns=[col])
                            save_inv_data(df_inv)
                        st.rerun()
                    st.markdown("<hr>", unsafe_allow_html=True)
        else:
            st.info("No hay columnas")

# ==================== REGISTRO DE UNIDADES ====================
elif menu == "📸 Registro de Unidades" and st.session_state.role == "admin":
    st.markdown('<div class="main-header">📸 Registro Maestro de Unidades</div>', unsafe_allow_html=True)
    with st.form("reg_u"):
        col1, col2 = st.columns(2)
        u_num = col1.text_input("Número Económico (SAP)")
        l_num = col1.text_input("Número de Lote")
        campo = col2.selectbox("Campo a Registrar", ["Ninguno"] + list(CAMPOS_SERIES.keys()))
        valor = col2.text_input("Valor del Serial")
        if st.form_submit_button("💾 Guardar Registro", use_container_width=True, type="primary"):
            if u_num:
                if campo != "Ninguno":
                    execute_query(f"INSERT INTO unidades (unit_number, id_lote, {campo}) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE id_lote=%s, {campo}=%s", (u_num, l_num, valor, l_num, valor), fetch=False)
                else:
                    execute_query("INSERT INTO unidades (unit_number, id_lote) VALUES (%s,%s) ON DUPLICATE KEY UPDATE id_lote=%s", (u_num, l_num, l_num), fetch=False)
                st.success("Registro guardado")
                st.rerun()
    st.markdown("### Unidades existentes")
    unidades = execute_query("SELECT * FROM unidades ORDER BY unit_number")
    if unidades:
        df_units = pd.DataFrame(unidades)
        st.dataframe(df_units, use_container_width=True, hide_index=True)

# ==================== GESTIÓN DE USUARIOS ====================
elif menu == "👥 Gestión de Usuarios" and st.session_state.role == "admin":
    st.markdown('<div class="main-header">👥 Usuarios del Sistema</div>', unsafe_allow_html=True)
    usuarios = execute_query("SELECT username, role FROM users ORDER BY username")
    if usuarios:
        st.dataframe(pd.DataFrame(usuarios), use_container_width=True, hide_index=True)
    with st.expander("➕ Crear nuevo usuario"):
        with st.form("new_user"):
            c1, c2, c3 = st.columns(3)
            u = c1.text_input("Usuario")
            p = c2.text_input("Contraseña", type="password")
            r = c3.selectbox("Rol", ["tecnico", "admin"])
            if st.form_submit_button("Crear", type="primary"):
                if u and p:
                    execute_query("INSERT INTO users (username, password, role) VALUES (%s,%s,%s)", (u, p, r), fetch=False)
                    st.success(f"Usuario {u} creado")
                    st.rerun()