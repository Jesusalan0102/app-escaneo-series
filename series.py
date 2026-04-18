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
st_autorefresh(interval=30 * 1000, key="global_refresh")

# Configuración de Zona Horaria Tijuana
tijuana_tz = pytz.timezone('America/Tijuana')
ahora_tj = datetime.now(tijuana_tz)
fecha_hoy = ahora_tj.strftime('%Y-%m-%d')
hora_actual = ahora_tj.strftime('%H:%M:%S')

CARRIER_BLUE = "#002B5B"
LOGO_URL = "https://raw.githubusercontent.com/Jesusalan0102/app-escaneo-series/main/carrierlogo2.jpeg.jpg"
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
    .section-title {{ font-size: 1.4rem; font-weight: 600; color: #333; margin-top: 20px; border-left: 5px solid {CARRIER_BLUE}; padding-left: 15px; margin-bottom: 15px; }}
    .time-display {{ font-size: 1.1rem; color: #666; font-weight: 600; text-align: right; margin-bottom: 10px; }}
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

# ==================== INICIALIZACIÓN ====================
if "login" not in st.session_state:
    st.session_state.update({"login": False, "user": "", "role": "", "last_count": 0})

# ==================== LOGIN ====================
if not st.session_state.login:
    st.markdown(f'<div style="text-align: center;"><img src="{LOGO_URL}" width="700"></div>', unsafe_allow_html=True)
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
    st.markdown(f"🕒 **Hora Tijuana:** {hora_actual}")
    st.markdown("---")
    st.write(f"👤 **{st.session_state.user}**")
    st.write(f"📍 Tijuana, B.C.")
    st.markdown("---")
    if st.session_state.role == "admin":
        menu = st.radio("MENÚ PRINCIPAL", ["📊 Dashboard Ejecutivo", "🎯 Control de Asignaciones", "📸 Registro de Unidades", "👥 Gestión de Usuarios"])
    else:
        menu = st.radio("ÁREA DE TRABAJO", ["🎯 Mis Tareas", "🔔 Nueva Solicitud"])
    
    if st.button("Cerrar Sesión", use_container_width=True):
        st.session_state.clear(); st.rerun()

# ==================== SECCIONES ====================

if menu == "📊 Dashboard Ejecutivo":
    st.markdown(f'<div class="time-display">Tijuana, B.C. | {fecha_hoy} | {hora_actual}</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-header">Análisis de Operaciones y Rendimiento</div>', unsafe_allow_html=True)
    
    asig = execute_read("SELECT * FROM asignaciones")
    if asig:
        df_a = pd.DataFrame(asig)
        
        # --- CÁLCULO DE PRODUCTIVIDAD (AVANCE CORREGIDO) ---
        stats = df_a.groupby('tecnico').agg(
            Total=('id', 'count'),
            Completadas=('estado', lambda x: (x == 'completada').sum()),
            En_Curso=('estado', lambda x: (x == 'en_proceso').sum()),
            Pendientes=('estado', lambda x: (x == 'pendiente').sum())
        ).reset_index()

        # Cálculo de porcentaje real para la barra de progreso (0.0 a 1.0)
        stats['Avance'] = (stats['Completadas'] / stats['Total']).astype(float)

        st.markdown('<div class="section-title">Productividad por Técnico</div>', unsafe_allow_html=True)
        st.dataframe(
            stats.sort_values(by='Total', ascending=False),
            use_container_width=True, hide_index=True,
            column_config={
                "tecnico": "Nombre del Técnico",
                "Total": st.column_config.NumberColumn("Asignadas", format="%d 📋"),
                "Completadas": "Hechas ✅",
                "En_Curso": "En Curso ⚙️",
                "Pendientes": "Pendientes ⏳",
                "Avance": st.column_config.ProgressColumn(
                    "Avance Finalizado", 
                    format="%.0f%%", 
                    min_value=0.0, 
                    max_value=1.0
                )
            }
        )
        
        c1, c2 = st.columns([2, 1])
        with c1:
            st.plotly_chart(px.bar(df_a, x='tecnico', color='estado', title="Distribución de Tareas",
                                   color_discrete_map={'completada': '#2ECC71', 'en_proceso': '#3498DB', 'pendiente': '#F1C40F'}), use_container_width=True)
        with c2:
            st.plotly_chart(px.pie(df_a, names='estado', title="Estado Operativo", hole=0.5), use_container_width=True)

    unid = execute_read("SELECT * FROM unidades")
    if unid:
        df_u = pd.DataFrame(unid)
        st.markdown('<div class="section-title">Inventario de Unidades por Lote</div>', unsafe_allow_html=True)
        for lote in df_u['id_lote'].unique():
            with st.expander(f"📦 Lote: {lote}"):
                st.table(df_u[df_u['id_lote']==lote][['unit_number'] + list(CAMPOS_SERIES.keys())])

elif menu == "🎯 Control de Asignaciones":
    st.markdown('<div class="main-header">Gestión de Órdenes de Trabajo</div>', unsafe_allow_html=True)
    sols = execute_read("SELECT * FROM asignaciones WHERE estado='solicitado'")
    
    # Notificación Admin
    if len(sols) > st.session_state.last_count:
        st.markdown(f'<audio autoplay><source src="{SOUND_URL}" type="audio/mp3"></audio>', unsafe_allow_html=True)
        st.toast("Nueva solicitud recibida", icon="🔔")
    st.session_state.last_count = len(sols)

    if sols:
        st.markdown('<div class="section-title">Solicitudes Pendientes</div>', unsafe_allow_html=True)
        for s in sols:
            c1, c2, c3 = st.columns([4, 1, 1])
            c1.info(f"**{s['tecnico']}** solicita **{s['actividad_id']}** - Unidad: **{s['unidad']}**")
            if c2.button("Aprobar", key=f"y{s['id']}", use_container_width=True):
                execute_write("UPDATE asignaciones SET estado='pendiente' WHERE id=%s", (s['id'],)); st.rerun()
            if c3.button("Denegar", key=f"n{s['id']}", use_container_width=True):
                execute_write("DELETE FROM asignaciones WHERE id=%s", (s['id'],)); st.rerun()

elif menu == "🎯 Mis Tareas":
    st.markdown('<div class="main-header">Mis Actividades Asignadas</div>', unsafe_allow_html=True)
    pend = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado='pendiente'", (st.session_state.user,))
    
    # Notificación Técnico
    if len(pend) > st.session_state.last_count:
        st.markdown(f'<audio autoplay><source src="{SOUND_URL}" type="audio/mp3"></audio>', unsafe_allow_html=True)
        st.toast("Nueva tarea asignada", icon="🛠️")
    st.session_state.last_count = len(pend)

    tareas = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado IN ('pendiente', 'en_proceso')", (st.session_state.user,))
    if not tareas: st.info("Sin tareas activas.")
    else:
        for t in tareas:
            with st.expander(f"📦 Unidad: {t['unidad']} - {t['actividad_id']}"):
                if t['estado'] == 'pendiente':
                    if st.button("Iniciar Trabajo", key=f"st_{t['id']}", use_container_width=True):
                        # Se registra la fecha y hora de inicio de Tijuana
                        st_time = datetime.now(tijuana_tz).strftime('%Y-%m-%d %H:%M:%S')
                        execute_write("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=%s WHERE id=%s", (st_time, t['id'])); st.rerun()
                else:
                    if t['actividad_id'].lower() == "toma de series":
                        with st.form(f"f_{t['id']}"):
                            res = {k: st.text_input(v) for k, v in CAMPOS_SERIES.items()}
                            if st.form_submit_button("Guardar Datos y Finalizar"):
                                fn_time = datetime.now(tijuana_tz).strftime('%Y-%m-%d %H:%M:%S')
                                q = ", ".join([f"{k}=%s" for k in res.keys()])
                                execute_write(f"UPDATE unidades SET {q} WHERE unit_number=%s", list(res.values()) + [t['unidad']])
                                execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (fn_time, t['id'])); st.rerun()
                    elif st.button("Concluir Trabajo", key=f"fi_{t['id']}", use_container_width=True):
                        fn_time = datetime.now(tijuana_tz).strftime('%Y-%m-%d %H:%M:%S')
                        execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (fn_time, t['id'])); st.rerun()
