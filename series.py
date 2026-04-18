import streamlit as st
import pandas as pd
import mysql.connector
from mysql.connector import Error
import plotly.express as px
from datetime import datetime
import io
import pytz 
from streamlit_autorefresh import st_autorefresh

# ==================== CONFIGURACIÓN INICIAL ====================
st.set_page_config(page_title="Carrier Transicold - Panel de Control", layout="wide")
# Auto-refresco cada 30 segundos para detectar nuevas tareas/solicitudes
st_autorefresh(interval=30 * 1000, key="global_refresh")

tijuana_tz = pytz.timezone('America/Tijuana')
ahora_tj = datetime.now(tijuana_tz)
fecha_hoy = ahora_tj.strftime('%Y-%m-%d')

CARRIER_BLUE = "#002B5B"
LOGO_URL = "https://raw.githubusercontent.com/Jesusalan0102/app-escaneo-series/main/carrierlogo2.jpeg.jpg"
# URL de sonido de notificación (Ping profesional)
SOUND_URL = "https://raw.githubusercontent.com/rafaelEscalante/notification-sounds/master/pings/ping-8.mp3"

CAMPOS_SERIES = {
    "vin_number": "VIN Number", "reefer_serial": "Serie del Reefer",
    "reefer_model": "Modelo del Reefer", "evaporator_serial_mjs11": "Evaporador MJS11",
    "evaporator_serial_mjd22": "Evaporador MJD22", "engine_serial": "Motor",
    "compressor_serial": "Compresor", "generator_serial": "Generador",
    "battery_charger_serial": "Cargador de Batería"
}

ACTIVIDADES_CARRIER = [
    "Cableado", "Cerrado", "Corriendo", "Inspección", "Pretrip", 
    "Programación", "Soldadura en Sitio", "Vacíos", "Accesorios", 
    "Toma de Valores", "Evidencia", "Standby", "Toma de Series"
]

# --- ESTILOS CSS ---
st.markdown(f"""
<style>
    .stApp {{ background-color: white; }}
    .main-header {{ font-size: 2.2rem; font-weight: 700; color: {CARRIER_BLUE}; border-bottom: 3px solid {CARRIER_BLUE}; padding-bottom: 10px; margin-bottom: 30px; }}
    .logo-container {{ text-align: center; padding: 20px; margin-bottom: 10px; }}
    .section-title {{ font-size: 1.4rem; font-weight: 600; color: #333; margin-top: 20px; border-left: 5px solid {CARRIER_BLUE}; padding-left: 15px; margin-bottom: 15px; }}
</style>
""", unsafe_allow_html=True)

# ==================== BASE DE DATOS ====================
def get_db_connection():
    try: return mysql.connector.connect(**st.secrets["db"], autocommit=True)
    except: return None

def execute_read(query, params=None):
    conn = get_db_connection()
    if conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, params or ())
        res = cur.fetchall()
        cur.close(); conn.close()
        return res
    return []

def execute_write(query, params=None):
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(query, params or ())
            cur.close(); conn.close()
            return True
        except: return False
    return False

# ==================== LÓGICA DE ALARMAS ====================
def activar_alarma(mensaje):
    """Reproduce un sonido y muestra un mensaje emergente"""
    st.markdown(f'<audio autoplay><source src="{SOUND_URL}" type="audio/mp3"></audio>', unsafe_allow_html=True)
    st.toast(mensaje, icon="🔔")

# ==================== LOGIN ====================
if "login" not in st.session_state:
    st.session_state.update({"login": False, "user": "", "role": "", "last_count": 0})

if not st.session_state.login:
    st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}" width="900"></div>', unsafe_allow_html=True)
    with st.container():
        col_l, col_c, col_r = st.columns([1,2,1])
        with col_c:
            u_log = st.text_input("Usuario")
            p_log = st.text_input("Contraseña", type="password")
            if st.button("Acceder al Sistema", use_container_width=True):
                user = execute_read("SELECT * FROM users WHERE username=%s AND password=%s", (u_log.strip(), p_log.strip()))
                if user:
                    st.session_state.update({"login": True, "user": user[0]['username'], "role": user[0]['role'].lower()})
                    st.rerun()
                else: st.error("Credenciales Incorrectas")
    st.stop()

# ==================== SIDEBAR ====================
with st.sidebar:
    st.image(LOGO_URL, width=440)
    st.markdown("---")
    st.write(f"👤 **{st.session_state.user}**")
    st.write(f"📍 Tijuana, B.C.")
    st.markdown("---")
    is_admin = st.session_state.role == "admin"
    if is_admin:
        menu = st.radio("MENÚ PRINCIPAL", ["📊 Dashboard Ejecutivo", "🎯 Control de Asignaciones", "📸 Registro de Unidades", "👥 Gestión de Usuarios"])
    else:
        menu = st.radio("ÁREA DE TRABAJO", ["🎯 Mis Tareas", "🔔 Nueva Solicitud"])
    
    st.markdown("---")
    if st.button("Cerrar Sesión", use_container_width=True):
        st.session_state.clear(); st.rerun()

# ==================== SECCIONES ====================

if menu == "📊 Dashboard Ejecutivo":
    st.markdown('<div class="main-header">Resumen de Actividades por Técnico</div>', unsafe_allow_html=True)
    
    asig = execute_read("SELECT * FROM asignaciones")
    if asig:
        df_a = pd.DataFrame(asig)
        stats = df_a.groupby('tecnico').agg(
            Total=('id', 'count'),
            Completadas=('estado', lambda x: (x == 'completada').sum()),
            En_Curso=('estado', lambda x: (x == 'en_proceso').sum()),
            Pendientes=('estado', lambda x: (x == 'pendiente').sum())
        ).reset_index()
        stats['Avance'] = stats['Completadas'] / stats['Total']

        st.dataframe(
            stats.sort_values(by='Total', ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config={
                "tecnico": "Nombre del Técnico",
                "Total": st.column_config.NumberColumn("Total Asignado", format="%d 📋"),
                "Completadas": "Completadas ✅",
                "En_Curso": "En Curso ⚙️",
                "Pendientes": "Pendientes ⏳",
                "Avance": st.column_config.ProgressColumn("Avance Finalizado", format="%.0f%%", min_value=0.0, max_value=1.0)
            }
        )
        # Gráficas y Detalle (igual que antes...)
        # ... [Código de gráficas omitido por brevedad, se mantiene igual]

elif menu == "🎯 Control de Asignaciones":
    st.markdown('<div class="main-header">Gestión de Órdenes de Trabajo</div>', unsafe_allow_html=True)
    
    # ALARMA PARA ADMIN: Si hay nuevas solicitudes "solicitado"
    sols = execute_read("SELECT * FROM asignaciones WHERE estado='solicitado'")
    if len(sols) > st.session_state.last_count:
        activar_alarma(f"Tienes {len(sols)} nuevas solicitudes de técnicos por aprobar.")
    st.session_state.last_count = len(sols)

    if sols:
        st.markdown('<div class="section-title">Solicitudes Pendientes de Aprobación</div>', unsafe_allow_html=True)
        for s in sols:
            c1, c2, c3 = st.columns([4, 1, 1])
            c1.info(f"**{s['tecnico']}** solicita **{s['actividad_id']}** en Unidad **{s['unidad']}**")
            if c2.button("Aprobar", key=f"y{s['id']}", use_container_width=True):
                execute_write("UPDATE asignaciones SET estado='pendiente' WHERE id=%s", (s['id'],))
                st.success("Tarea aprobada y enviada al técnico."); st.rerun()
            if c3.button("Denegar", key=f"n{s['id']}", use_container_width=True):
                execute_write("DELETE FROM asignaciones WHERE id=%s", (s['id'],)); st.rerun()

elif menu == "🎯 Mis Tareas":
    st.markdown('<div class="main-header">Mis Actividades Asignadas</div>', unsafe_allow_html=True)
    
    # ALARMA PARA TÉCNICO: Si hay nuevas tareas en estado "pendiente"
    pendientes = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado='pendiente'", (st.session_state.user,))
    if len(pendientes) > st.session_state.last_count:
        activar_alarma("¡Se te ha asignado una nueva tarea!")
    st.session_state.last_count = len(pendientes)

    if not pendientes:
        st.info("No tienes tareas pendientes nuevas.")
    
    tareas_activas = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado IN ('pendiente', 'en_proceso')", (st.session_state.user,))
    for t in tareas_activas:
        with st.expander(f"📦 Unidad: {t['unidad']} - {t['actividad_id']} ({t['estado'].replace('_', ' ').capitalize()})"):
            if t['estado'] == 'pendiente':
                if st.button(f"Iniciar Trabajo", key=f"st_{t['id']}", use_container_width=True):
                    execute_write("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=NOW() WHERE id=%s", (t['id'],)); st.rerun()
            else:
                if t['actividad_id'].lower() == "toma de series":
                    with st.form(f"f_{t['id']}"):
                        res = {k: st.text_input(v) for k, v in CAMPOS_SERIES.items()}
                        if st.form_submit_button("Finalizar y Guardar Datos"):
                            q = ", ".join([f"{k}=%s" for k in res.keys()])
                            execute_write(f"UPDATE unidades SET {q} WHERE unit_number=%s", list(res.values()) + [t['unidad']])
                            execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW() WHERE id=%s", (t['id'],))
                            st.toast("Series registradas y tarea finalizada.", icon="✅"); st.rerun()
                elif st.button(f"Concluir Trabajo", key=f"fi_{t['id']}", use_container_width=True):
                    execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW() WHERE id=%s", (t['id'],))
                    st.toast("Tarea completada con éxito.", icon="✅"); st.rerun()

elif menu == "📸 Registro de Unidades":
    st.markdown('<div class="main-header">Registro de Datos Técnicos</div>', unsafe_allow_html=True)
    with st.form("reg_u"):
        c1, c2 = st.columns(2)
        unit = c1.text_input("Número de Unidad")
        lote = c1.text_input("Identificador de Lote")
        campo = c2.selectbox("Campo a Registrar", list(CAMPOS_SERIES.keys()), format_func=lambda x: CAMPOS_SERIES[x])
        valor = c2.text_input("Valor de la Serie")
        if st.form_submit_button("Guardar en Base de Datos", use_container_width=True):
            if execute_write(f"INSERT INTO unidades (unit_number, id_lote, {campo}) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE {campo}=%s", (unit, lote, valor, valor)):
                st.toast(f"Registro de unidad {unit} exitoso.", icon="✅")

elif menu == "🔔 Nueva Solicitud":
    st.markdown('<div class="main-header">Solicitar Autorización de Actividad</div>', unsafe_allow_html=True)
    u_db = execute_read("SELECT unit_number, id_lote FROM unidades")
    with st.form("sol_form"):
        u_s = st.selectbox("Unidad", [f"{x['id_lote']} - {x['unit_number']}" for x in u_db])
        a_s = st.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.form_submit_button("Enviar Solicitud al Administrador", use_container_width=True):
            execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'solicitado')", (u_s.split(" - ")[1], a_s, st.session_state.user))
            st.toast("Solicitud enviada. Espera la aprobación.", icon="📨"); st.rerun()
