import streamlit as st
import pandas as pd
import pymysql
import pymysql.cursors
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io
import pytz
import zipfile
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

CARRIER_BLUE    = "#002B5B"
CARRIER_ACCENT  = "#0057A8"
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

# ==================== CSS ====================
st.markdown(f"""
<style>
header[data-testid="stHeader"] {{ display: none !important; }}
footer {{ display: none !important; }}
#MainMenu {{ display: none !important; }}
.block-container {{ padding-top: 1.5rem !important; }}
section[data-testid="stSidebar"] {{ width: 21rem !important; }}
.main-header {{ font-size: 1.75rem; font-weight: 800; color: {CARRIER_BLUE}; border-bottom: 3px solid {CARRIER_ACCENT}; margin-bottom: 24px; }}
.section-title {{ font-size: 0.92rem; font-weight: 700; color: {CARRIER_BLUE}; border-left: 4px solid {CARRIER_ACCENT}; background: white; padding: 9px 14px; margin: 22px 0 14px 0; border-radius: 0 8px 8px 0; }}
.kpi-wrap {{ background: white; border-radius: 16px; padding: 20px; text-align: center; box-shadow: 0 4px 20px rgba(0,43,91,0.08); border-top: 5px solid {CARRIER_ACCENT}; }}
.kpi-num {{ font-size: 2.4rem; font-weight: 800; color: {CARRIER_BLUE}; }}
.kpi-lbl {{ font-size: 0.73rem; color: #6b7280; font-weight: 600; text-transform: uppercase; }}
.time-badge {{ background: {CARRIER_BLUE}; color: white; padding: 6px 16px; border-radius: 24px; float: right; }}
.login-card {{ background: white; padding: 36px 40px; border-radius: 20px; box-shadow: 0 12px 40px rgba(0,43,91,0.18); }}
.evidencia-info {{ background: #eff6ff; border-left: 5px solid #3b82f6; padding: 12px 18px; border-radius: 10px; margin-bottom: 14px; }}
.fotos-badge {{ background: #f0fdf4; border: 1px solid #86efac; border-radius: 20px; padding: 4px 14px; display: inline-block; }}
.tv-field-badge {{ background: #e8f0fb; border: 1px solid #c3d4f0; border-radius: 8px; padding: 6px 12px; display: inline-block; }}
.inv-info-bar {{ background: linear-gradient(90deg, {CARRIER_BLUE}, {CARRIER_ACCENT}); color: white; padding: 14px 20px; border-radius: 12px; margin-bottom: 16px; }}
.bloqueo-card {{ background: #fef2f2; border-left: 5px solid {CARRIER_DANGER}; border-radius: 10px; padding: 14px 18px; margin: 8px 0; }}
.user-chip {{ background: rgba(255,255,255,0.12); border-radius: 50px; padding: 6px 14px; color: white; display: inline-block; }}
</style>
""", unsafe_allow_html=True)

# ==================== CONEXIÓN DIRECTA A TIDB CLOUD ====================
DB_CONFIG = {
    "host": "gateway01.us-east-1.prod.aws.tidbcloud.com",
    "port": 4000,
    "user": "4BgYs96t9XXhCMS.root",
    "password": "YZcSUhQ5H7Gx9vLk",
    "database": "carrier_db",
    "connect_timeout": 30,
    "autocommit": True,
    "ssl": True,
    "cursorclass": pymysql.cursors.DictCursor,
}

def get_connection():
    try:
        conn = pymysql.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        st.error(f"Error de conexión: {type(e).__name__}: {e}")
        return None

def query(sql, params=None, fetch=True):
    conn = get_connection()
    if not conn:
        return [] if fetch else False
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            if fetch:
                res = cur.fetchall()
            else:
                res = True
        conn.close()
        return res
    except Exception as e:
        st.error(f"Error SQL: {e}")
        conn.close()
        return [] if fetch else False

# ==================== INICIALIZAR TABLAS Y USUARIO ADMIN ====================
def init_db():
    # Crear tabla users si no existe
    query("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE,
            password VARCHAR(100),
            role ENUM('admin','tecnico') DEFAULT 'tecnico'
        )
    """, fetch=False)
    # Verificar si existe al menos un admin, si no, crearlo
    admin = query("SELECT * FROM users WHERE role='admin' LIMIT 1")
    if not admin:
        query("INSERT INTO users (username, password, role) VALUES ('Ing Sepulveda', 'peluche123', 'admin')", fetch=False)
        query("INSERT INTO users (username, password, role) VALUES ('Admin', 'admin123', 'admin')", fetch=False)
    
    # Otras tablas (crear si no existen)
    query("""
        CREATE TABLE IF NOT EXISTS unidades (
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
        )
    """, fetch=False)
    query("""
        CREATE TABLE IF NOT EXISTS asignaciones (
            id INT AUTO_INCREMENT PRIMARY KEY,
            unidad VARCHAR(50),
            actividad_id VARCHAR(100),
            tecnico VARCHAR(100),
            estado VARCHAR(20) DEFAULT 'pendiente',
            fecha_asignacion DATETIME DEFAULT CURRENT_TIMESTAMP,
            fecha_inicio DATETIME,
            fecha_fin DATETIME,
            ticket_id INT
        )
    """, fetch=False)
    query("""
        CREATE TABLE IF NOT EXISTS evidencias (
            id INT AUTO_INCREMENT PRIMARY KEY,
            unit_number VARCHAR(50),
            nombre_archivo VARCHAR(255),
            contenido LONGBLOB,
            tecnico VARCHAR(100),
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """, fetch=False)
    query("""
        CREATE TABLE IF NOT EXISTS comentarios_actividades (
            id INT AUTO_INCREMENT PRIMARY KEY,
            asignacion_id INT NOT NULL,
            tecnico VARCHAR(50),
            comentario TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """, fetch=False)
    query("""
        CREATE TABLE IF NOT EXISTS inventario_columnas (
            id INT AUTO_INCREMENT PRIMARY KEY,
            tabla_nombre VARCHAR(120) DEFAULT 'Principal',
            col_nombre VARCHAR(120) NOT NULL,
            col_orden INT DEFAULT 0
        )
    """, fetch=False)
    query("""
        CREATE TABLE IF NOT EXISTS inventario_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            tabla_nombre VARCHAR(120) DEFAULT 'Principal',
            fila_idx INT NOT NULL,
            col_nombre VARCHAR(120) NOT NULL,
            valor TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    """, fetch=False)
    query("""
        CREATE TABLE IF NOT EXISTS toma_valores_campos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            campo_nombre VARCHAR(200) NOT NULL,
            campo_orden INT DEFAULT 0
        )
    """, fetch=False)
    query("""
        CREATE TABLE IF NOT EXISTS toma_valores_datos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            asignacion_id INT NOT NULL,
            campo_nombre VARCHAR(200) NOT NULL,
            valor TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    """, fetch=False)
    query("""
        CREATE TABLE IF NOT EXISTS tickets (
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
        )
    """, fetch=False)
    # Insertar columnas de inventario si no existen
    cols = query("SELECT * FROM inventario_columnas LIMIT 1")
    if not cols:
        for i, col in enumerate(['Código', 'Descripción', 'Cantidad', 'Unidad', 'Ubicación', 'Estado']):
            query("INSERT INTO inventario_columnas (tabla_nombre, col_nombre, col_orden) VALUES (%s, %s, %s)", ('Principal', col, i), fetch=False)
    # Insertar campos de toma de valores si no existen
    campos = query("SELECT * FROM toma_valores_campos LIMIT 1")
    if not campos:
        defaults = [
            ('Presión de Succión (PSI)',0), ('Presión de Descarga (PSI)',1),
            ('Temperatura Set Point (°C)',2), ('Temperatura de Retorno (°C)',3),
            ('Temperatura de Suministro (°C)',4), ('Voltaje Batería (V)',5),
            ('Corriente (A)',6), ('RPM Motor',7), ('Horas de Motor',8),
            ('Temperatura Ambiente (°C)',9)
        ]
        for nom, ord in defaults:
            query("INSERT INTO toma_valores_campos (campo_nombre, campo_orden) VALUES (%s, %s)", (nom, ord), fetch=False)

init_db()

# ==================== ESTADO DE SESIÓN ====================
if 'login' not in st.session_state: st.session_state.login = False
if 'user' not in st.session_state: st.session_state.user = ''
if 'role' not in st.session_state: st.session_state.role = ''
if 'menu_sel' not in st.session_state: st.session_state.menu_sel = None
if 'last_count' not in st.session_state: st.session_state.last_count = 0

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
                u = username.strip()
                p = password.strip()
                user = query("SELECT * FROM users WHERE username = %s AND password = %s", (u, p))
                if user:
                    st.session_state.login = True
                    st.session_state.user = user[0]['username']
                    st.session_state.role = user[0]['role'].lower()
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
    st.markdown(f"<p><b>👤 {st.session_state.user}</b><br><span class='user-chip'>{'🛡 Administrador' if st.session_state.role == 'admin' else '🔧 Técnico'}</span></p>", unsafe_allow_html=True)
    st.markdown("---")
    if st.session_state.role == 'admin':
        opts = ["📊 Dashboard Ejecutivo", "🎯 Control de Asignaciones", "🎫 Tickets", "📦 Inventarios", "📸 Registro de Unidades", "👥 Gestión de Usuarios"]
    else:
        opts = ["🎯 Mis Tareas", "🔔 Nueva Solicitud"]
    menu = st.radio("MENÚ", opts, key="menu")
    st.session_state.menu_sel = menu
    st.markdown("---")
    if st.button("Cerrar Sesión", use_container_width=True):
        st.session_state.login = False
        st.session_state.user = ''
        st.session_state.role = ''
        st.session_state.menu_sel = None
        st.rerun()

# ==================== FUNCIONES AUXILIARES ====================
def get_next_ticket_num():
    res = query("SELECT MAX(ticket_num) as max_num FROM tickets")
    if res and res[0]['max_num']:
        return res[0]['max_num'] + 1
    return 1

# ==================== DASHBOARD EJECUTIVO (ADMIN) ====================
if menu == "📊 Dashboard Ejecutivo":
    st.markdown(f'<div class="time-badge">🕒 {hora_actual}</div><div class="main-header">📊 Panel de Rendimiento Operativo</div>', unsafe_allow_html=True)
    asig = query("SELECT * FROM asignaciones")
    unid = query("SELECT * FROM unidades")
    df_a = pd.DataFrame(asig) if asig else pd.DataFrame()
    total_u = len(unid)
    total_t = len(df_a)
    comp_t = int((df_a["estado"] == "completada").sum()) if not df_a.empty else 0
    proc_t = int((df_a["estado"] == "en_proceso").sum()) if not df_a.empty else 0
    pend_t = int((df_a["estado"] == "pendiente").sum()) if not df_a.empty else 0
    pct_av = round(comp_t / total_t * 100) if total_t else 0
    cols = st.columns(5)
    for i, (val, lbl, cls) in enumerate([(total_u,"Total Unidades",""), (comp_t,"Completadas","green"), (proc_t,"En Proceso","amber"), (pend_t,"Pendientes","red"), (f"{pct_av}%","Avance Global","purple")]):
        with cols[i]:
            st.markdown(f'<div class="kpi-wrap {cls}"><div class="kpi-num">{val}</div><div class="kpi-lbl">{lbl}</div></div>', unsafe_allow_html=True)
    st.markdown("<br>")
    if not df_a.empty:
        st.markdown('<div class="section-title">📈 Estadísticas por Técnico</div>', unsafe_allow_html=True)
        stats = df_a.groupby("tecnico").agg(Total=("id","count"), Completadas=("estado",lambda x: (x=="completada").sum()), En_Curso=("estado",lambda x: (x=="en_proceso").sum()), Pendientes=("estado",lambda x: (x=="pendiente").sum())).reset_index()
        stats["Rendimiento %"] = ((stats["Completadas"] / stats["Total"]) * 100).round(0).astype(int)
        st.dataframe(stats, use_container_width=True, hide_index=True)
        COLOR_MAP = {"completada":CARRIER_SUCCESS, "en_proceso":CARRIER_WARN, "pendiente":CARRIER_DANGER}
        fig = px.bar(df_a, x="tecnico", color="estado", title="Carga por Técnico", color_discrete_map=COLOR_MAP)
        st.plotly_chart(fig, use_container_width=True)
    st.markdown('<div class="section-title">📋 Estatus de Actividades por Unidad</div>', unsafe_allow_html=True)
    if unid:
        completadas = query("SELECT unidad, actividad_id FROM asignaciones WHERE estado='completada'")
        completadas_set = {(r['unidad'], r['actividad_id']) for r in completadas}
        data = []
        for u in unid:
            row = {"LOTE": u.get('id_lote',''), "UNIDAD": u['unit_number']}
            for act in ACTIVIDADES_CARRIER:
                row[act] = "✔" if (u['unit_number'], act) in completadas_set else "—"
            data.append(row)
        st.dataframe(pd.DataFrame(data), use_container_width=True, height=340)
    st.markdown('<div class="section-title">📂 Descarga de Evidencias</div>', unsafe_allow_html=True)
    if unid:
        unidad_sel = st.selectbox("Selecciona unidad:", [u['unit_number'] for u in unid])
        evs = query("SELECT nombre_archivo, contenido FROM evidencias WHERE unit_number=%s", (unidad_sel,))
        if evs:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as zf:
                for ev in evs:
                    zf.writestr(ev['nombre_archivo'], ev['contenido'])
            st.download_button(f"📥 Descargar {len(evs)} fotos", buf.getvalue(), f"{unidad_sel}_evidencias.zip", use_container_width=True)
        else:
            st.info("Sin fotos")

# ==================== CONTROL DE ASIGNACIONES (ADMIN) ====================
elif menu == "🎯 Control de Asignaciones":
    st.markdown('<div class="main-header">🎯 Gestión de Órdenes de Trabajo</div>', unsafe_allow_html=True)
    sols = query("SELECT * FROM asignaciones WHERE estado='solicitado'")
    if sols:
        for s in sols:
            with st.container():
                col1, col2, col3 = st.columns([4,1,1])
                col1.warning(f"**{s['tecnico']}** solicita **{s['actividad_id']}** para unidad **{s['unidad']}**")
                if col2.button("✅ Aprobar", key=f"ap_{s['id']}"):
                    query("UPDATE asignaciones SET estado='pendiente' WHERE id=%s", (s['id'],), fetch=False)
                    st.rerun()
                if col3.button("❌ Rechazar", key=f"re_{s['id']}"):
                    query("DELETE FROM asignaciones WHERE id=%s", (s['id'],), fetch=False)
                    st.rerun()
                st.markdown("---")
    else:
        st.success("No hay solicitudes pendientes")
    st.markdown("### ➕ Asignación directa")
    unidades = query("SELECT unit_number FROM unidades")
    tecnicos = query("SELECT username FROM users WHERE role='tecnico'")
    with st.form("new_assignment"):
        c1,c2,c3 = st.columns(3)
        unidad = c1.selectbox("Unidad", [u['unit_number'] for u in unidades] if unidades else [])
        tecnico = c2.selectbox("Técnico", [t['username'] for t in tecnicos] if tecnicos else [])
        actividad = c3.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.form_submit_button("Crear orden"):
            if unidad and tecnico and actividad:
                query("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s,%s,%s,'pendiente')", (unidad, actividad, tecnico), fetch=False)
                st.success("Orden creada")
                st.rerun()

# ==================== MIS TAREAS (TÉCNICO) ====================
elif menu == "🎯 Mis Tareas":
    st.markdown('<div class="main-header">🎯 Mis Actividades</div>', unsafe_allow_html=True)
    tareas = query("SELECT * FROM asignaciones WHERE tecnico=%s AND estado IN ('pendiente','en_proceso')", (st.session_state.user,))
    if not tareas:
        st.info("No tienes tareas pendientes")
    for t in tareas:
        with st.expander(f"{'⏳' if t['estado']=='pendiente' else '▶️'} Unidad {t['unidad']} - {t['actividad_id']}"):
            if t['estado'] == 'pendiente':
                if st.button("Iniciar", key=f"ini_{t['id']}"):
                    query("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']), fetch=False)
                    st.rerun()
            else:
                comentario = st.text_area("Comentario / Reporte", key=f"coment_{t['id']}")
                if t['actividad_id'].lower() == 'evidencia':
                    fotos = query("SELECT COUNT(*) as total FROM evidencias WHERE unit_number=%s AND tecnico=%s", (t['unidad'], st.session_state.user))
                    total_fotos = fotos[0]['total'] if fotos else 0
                    st.info(f"📸 Fotos guardadas: {total_fotos}/{MAX_FOTOS}")
                    archivos = st.file_uploader("Subir fotos", accept_multiple_files=True, type=['jpg','jpeg','png'], key=f"fotos_{t['id']}")
                    if archivos and st.button("Guardar fotos", key=f"save_{t['id']}"):
                        for arc in archivos[:MAX_FOTOS-total_fotos]:
                            query("INSERT INTO evidencias (unit_number, nombre_archivo, contenido, tecnico) VALUES (%s,%s,%s,%s)", (t['unidad'], arc.name, arc.read(), st.session_state.user), fetch=False)
                        st.rerun()
                    if st.button("✅ Finalizar", key=f"fin_{t['id']}"):
                        if comentario:
                            query("INSERT INTO comentarios_actividades (asignacion_id, tecnico, comentario) VALUES (%s,%s,%s)", (t['id'], st.session_state.user, comentario), fetch=False)
                        query("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']), fetch=False)
                        if t.get('ticket_id'):
                            query("UPDATE tickets SET atendido=TRUE, fecha_atencion=%s WHERE id=%s", (datetime.now(tijuana_tz), t['ticket_id']), fetch=False)
                        st.success("Completada")
                        st.rerun()
                elif t['actividad_id'].lower() == 'toma de valores':
                    campos = query("SELECT campo_nombre FROM toma_valores_campos ORDER BY campo_orden ASC")
                    if campos:
                        prev = query("SELECT campo_nombre, valor FROM toma_valores_datos WHERE asignacion_id=%s", (t['id'],))
                        prev_dict = {p['campo_nombre']: p['valor'] for p in prev}
                        with st.form(f"tv_{t['id']}"):
                            vals = {}
                            for c in campos:
                                vals[c['campo_nombre']] = st.text_input(c['campo_nombre'], value=prev_dict.get(c['campo_nombre'], ''))
                            if st.form_submit_button("Guardar y finalizar"):
                                query("DELETE FROM toma_valores_datos WHERE asignacion_id=%s", (t['id'],), fetch=False)
                                for campo, valor in vals.items():
                                    query("INSERT INTO toma_valores_datos (asignacion_id, campo_nombre, valor) VALUES (%s,%s,%s)", (t['id'], campo, valor), fetch=False)
                                if comentario:
                                    query("INSERT INTO comentarios_actividades (asignacion_id, tecnico, comentario) VALUES (%s,%s,%s)", (t['id'], st.session_state.user, comentario), fetch=False)
                                query("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']), fetch=False)
                                if t.get('ticket_id'):
                                    query("UPDATE tickets SET atendido=TRUE, fecha_atencion=%s WHERE id=%s", (datetime.now(tijuana_tz), t['ticket_id']), fetch=False)
                                st.success("Completada")
                                st.rerun()
                elif t['actividad_id'].lower() == 'toma de series':
                    with st.form(f"series_{t['id']}"):
                        valores = {}
                        for campo, label in CAMPOS_SERIES.items():
                            valores[campo] = st.text_input(label)
                        if st.form_submit_button("Guardar y finalizar"):
                            set_q = ", ".join([f"{k}=%s" for k in valores.keys()])
                            query(f"UPDATE unidades SET {set_q} WHERE unit_number=%s", list(valores.values()) + [t['unidad']], fetch=False)
                            if comentario:
                                query("INSERT INTO comentarios_actividades (asignacion_id, tecnico, comentario) VALUES (%s,%s,%s)", (t['id'], st.session_state.user, comentario), fetch=False)
                            query("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']), fetch=False)
                            if t.get('ticket_id'):
                                query("UPDATE tickets SET atendido=TRUE, fecha_atencion=%s WHERE id=%s", (datetime.now(tijuana_tz), t['ticket_id']), fetch=False)
                            st.success("Series guardadas")
                            st.rerun()
                else:
                    if st.button("✅ Completar", key=f"fin_{t['id']}"):
                        if comentario:
                            query("INSERT INTO comentarios_actividades (asignacion_id, tecnico, comentario) VALUES (%s,%s,%s)", (t['id'], st.session_state.user, comentario), fetch=False)
                        query("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']), fetch=False)
                        if t.get('ticket_id'):
                            query("UPDATE tickets SET atendido=TRUE, fecha_atencion=%s WHERE id=%s", (datetime.now(tijuana_tz), t['ticket_id']), fetch=False)
                        st.success("Completada")
                        st.rerun()

# ==================== NUEVA SOLICITUD ====================
elif menu == "🔔 Nueva Solicitud":
    st.markdown('<div class="main-header">🔔 Solicitar Actividad</div>', unsafe_allow_html=True)
    unidades = query("SELECT unit_number FROM unidades")
    with st.form("nueva_solicitud"):
        unidad = st.selectbox("Unidad", [u['unit_number'] for u in unidades] if unidades else [])
        actividad = st.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.form_submit_button("Enviar solicitud"):
            if unidad and actividad:
                existente = query("SELECT id FROM asignaciones WHERE tecnico=%s AND unidad=%s AND actividad_id=%s AND estado IN ('solicitado','pendiente','en_proceso')", (st.session_state.user, unidad, actividad))
                if existente:
                    st.error("Ya tienes esta actividad pendiente o en curso")
                else:
                    query("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s,%s,%s,'solicitado')", (unidad, actividad, st.session_state.user), fetch=False)
                    st.success("Solicitud enviada")
                    st.rerun()

# ==================== TICKETS (ADMIN) ====================
elif menu == "🎫 Tickets":
    st.markdown('<div class="main-header">🎫 Gestión de Tickets</div>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["📋 Lista", "➕ Nuevo"])
    with tab1:
        tickets = query("SELECT t.*, a.tecnico FROM tickets t LEFT JOIN asignaciones a ON t.id = a.ticket_id ORDER BY t.ticket_num DESC")
        if tickets:
            for t in tickets:
                if not t['atendido']: estado = "🔴 No atendido"
                elif t['atendido'] and not t['reporte_enviado']: estado = "🟡 Atendido (sin reporte)"
                else: estado = "🟢 Completado"
                st.markdown(f"<div style='border-left:6px solid {CARRIER_ACCENT}; padding:10px; margin-bottom:10px; background:#f8f9fa;'>", unsafe_allow_html=True)
                col1, col2 = st.columns([1,3])
                col1.markdown(f"## #{t['ticket_num']}")
                col1.markdown(f"**{estado}**")
                col2.markdown(f"**Unidad:** {t['unit_number']} | **VIN:** {t.get('vin_number','N/D')}")
                col2.markdown(f"**Descripción:** {t['descripcion']}")
                col2.markdown(f"*Creado: {t['creado_por']} | {t['fecha_creacion']}*")
                if t['tecnico']:
                    col2.markdown(f"*Asignado a: {t['tecnico']}*")
                if t['atendido'] and not t['reporte_enviado']:
                    if st.button("📤 Marcar reporte enviado", key=f"rep_{t['id']}"):
                        query("UPDATE tickets SET reporte_enviado=TRUE, fecha_reporte=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']), fetch=False)
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("No hay tickets")
    with tab2:
        unidades = query("SELECT unit_number, vin_number FROM unidades")
        tecnicos = query("SELECT username FROM users WHERE role='tecnico'")
        with st.form("new_ticket"):
            opciones = {f"{u['unit_number']} - {u.get('vin_number','sin VIN')}": u['unit_number'] for u in unidades}
            unidad_label = st.selectbox("Unidad", list(opciones.keys()))
            unidad_sel = opciones[unidad_label]
            vin_auto = next((u['vin_number'] for u in unidades if u['unit_number']==unidad_sel), '')
            vin = st.text_input("VIN", value=vin_auto)
            desc = st.text_area("Descripción")
            tecnico = st.selectbox("Asignar a técnico", [t['username'] for t in tecnicos] if tecnicos else [])
            if st.form_submit_button("Crear ticket"):
                if unidad_sel and desc and tecnico:
                    num = get_next_ticket_num()
                    query("INSERT INTO tickets (ticket_num, unit_number, vin_number, descripcion, creado_por) VALUES (%s,%s,%s,%s,%s)", (num, unidad_sel, vin, desc, st.session_state.user), fetch=False)
                    ticket = query("SELECT id FROM tickets WHERE ticket_num=%s", (num,))
                    if ticket:
                        query("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado, ticket_id) VALUES (%s,%s,%s,'pendiente',%s)", (unidad_sel, f"Ticket #{num}", tecnico, ticket[0]['id']), fetch=False)
                    st.success(f"Ticket #{num} creado")
                    st.rerun()
                else:
                    st.warning("Completa todos los campos")

# ==================== INVENTARIOS ====================
elif menu == "📦 Inventarios":
    st.markdown(f'<div class="time-badge">🕒 {hora_actual}</div><div class="main-header">📦 Gestión de Inventarios</div>', unsafe_allow_html=True)
    columnas = query("SELECT col_nombre FROM inventario_columnas WHERE tabla_nombre='Principal' ORDER BY col_orden ASC")
    if columnas:
        cols = [c['col_nombre'] for c in columnas]
    else:
        cols = ["Código", "Descripción", "Cantidad", "Unidad", "Ubicación", "Estado"]
    data = query("SELECT fila_idx, col_nombre, valor FROM inventario_data WHERE tabla_nombre='Principal' ORDER BY fila_idx ASC, col_nombre ASC")
    if data:
        rows = {}
        for d in data:
            rows.setdefault(d['fila_idx'], {}).update({d['col_nombre']: d['valor']})
        df = pd.DataFrame([rows[k] for k in sorted(rows.keys())], columns=cols)
    else:
        df = pd.DataFrame(columns=cols)
    st.markdown(f'<div class="inv-info-bar">🗄 Inventario · {len(df)} registros · {len(cols)} columnas</div>', unsafe_allow_html=True)
    if st.button("➕ Agregar fila"):
        nueva = pd.DataFrame([{c: '' for c in cols}])
        df = pd.concat([df, nueva], ignore_index=True)
        query("DELETE FROM inventario_data WHERE tabla_nombre='Principal'", fetch=False)
        for i, row in df.iterrows():
            for col in cols:
                query("INSERT INTO inventario_data (tabla_nombre, fila_idx, col_nombre, valor) VALUES (%s,%s,%s,%s)", ('Principal', i, col, str(row[col])), fetch=False)
        st.rerun()
    if not df.empty:
        edited = st.data_editor(df, use_container_width=True, num_rows="dynamic", key="inv_edit")
        if st.button("💾 Guardar cambios"):
            query("DELETE FROM inventario_data WHERE tabla_nombre='Principal'", fetch=False)
            for i, row in edited.iterrows():
                for col in cols:
                    query("INSERT INTO inventario_data (tabla_nombre, fila_idx, col_nombre, valor) VALUES (%s,%s,%s,%s)", ('Principal', i, col, str(row[col])), fetch=False)
            st.success("Guardado")
            st.rerun()
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            edited.to_excel(w, index=False, sheet_name="Inventario")
        st.download_button("📥 Exportar a Excel", buf.getvalue(), f"Inventario_{fecha_hoy}.xlsx", use_container_width=True)

# ==================== REGISTRO DE UNIDADES ====================
elif menu == "📸 Registro de Unidades":
    st.markdown('<div class="main-header">📸 Registro de Unidades</div>', unsafe_allow_html=True)
    with st.form("reg_unidad"):
        c1, c2 = st.columns(2)
        unit = c1.text_input("Número Económico")
        lote = c1.text_input("Lote")
        campo = c2.selectbox("Campo a registrar", ["Ninguno"] + list(CAMPOS_SERIES.keys()))
        valor = c2.text_input("Valor")
        if st.form_submit_button("Guardar"):
            if unit:
                if campo != "Ninguno":
                    query(f"INSERT INTO unidades (unit_number, id_lote, {campo}) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE id_lote=%s, {campo}=%s", (unit, lote, valor, lote, valor), fetch=False)
                else:
                    query("INSERT INTO unidades (unit_number, id_lote) VALUES (%s,%s) ON DUPLICATE KEY UPDATE id_lote=%s", (unit, lote, lote), fetch=False)
                st.success("Guardado")
                st.rerun()
    st.markdown("### Unidades existentes")
    unis = query("SELECT * FROM unidades ORDER BY unit_number")
    if unis:
        st.dataframe(pd.DataFrame(unis), use_container_width=True, hide_index=True)

# ==================== GESTIÓN DE USUARIOS ====================
elif menu == "👥 Gestión de Usuarios":
    st.markdown('<div class="main-header">👥 Usuarios del Sistema</div>', unsafe_allow_html=True)
    users = query("SELECT username, role FROM users ORDER BY username")
    if users:
        st.dataframe(pd.DataFrame(users), use_container_width=True, hide_index=True)
    with st.expander("➕ Crear nuevo usuario"):
        with st.form("new_user"):
            c1, c2, c3 = st.columns(3)
            u = c1.text_input("Usuario")
            p = c2.text_input("Contraseña", type="password")
            r = c3.selectbox("Rol", ["tecnico", "admin"])
            if st.form_submit_button("Crear"):
                if u and p:
                    try:
                        query("INSERT INTO users (username, password, role) VALUES (%s,%s,%s)", (u, p, r), fetch=False)
                        st.success(f"Usuario {u} creado")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")