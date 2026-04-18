import streamlit as st
import pandas as pd
import mysql.connector
from mysql.connector import Error
import plotly.express as px
from datetime import datetime
import io
from streamlit_autorefresh import st_autorefresh

# ==================== CONFIGURACIÓN E INTERFAZ ====================
st.set_page_config(page_title="Carrier Transicold - Gestión de Flota", layout="wide")

# Autorefresh cada 30 segundos (mantiene viva la sesión y actualiza alarmas)
st_autorefresh(interval=30 * 1000, key="global_refresh")

CARRIER_BLUE = "#002B5B"
BACKGROUND_COLOR = "#F4F7F9"
LOGO_URL = "https://raw.githubusercontent.com/Jesusalan0102/app-escaneo-series/main/carrierlogo2.jpeg.jpg"

CAMPOS_SERIES = {
    "vin_number": "VIN NUMBER",
    "reefer_serial": "REEFER SERIAL",
    "reefer_model": "REEFER MODEL",
    "evaporator_serial_mjs11": "EVAPORATOR SERIAL MJS11",
    "evaporator_serial_mjd22": "EVAPORATOR SERIAL MJD22",
    "engine_serial": "ENGINE",
    "compressor_serial": "COMPRESSOR",
    "generator_serial": "GENERATOR",
    "battery_charger_serial": "BATTERY CHARGER"
}

ACTIVIDADES_CARRIER = [
    "Cableado", "Cerrado", "Corriendo", "Inspección", "Pretrip", 
    "Programación", "Soldadura en sitio", "Vacios", "Accesorios", 
    "toma de valores", "Evidencia", "standby", "toma de series"
]

# --- FUNCIÓN DE SONIDO ---
def play_notification_sound():
    audio_html = """
        <audio autoplay>
            <source src="https://raw.githubusercontent.com/rafaelEscalante/notification-sounds/master/pings/ping-8.mp3" type="audio/mp3">
        </audio>
    """
    st.markdown(audio_html, unsafe_allow_html=True)

# --- ESTILOS CSS ---
st.markdown(f"""
<style>
    .stApp {{ background-color: {BACKGROUND_COLOR}; }}
    .main-header {{ font-size: 2.2rem; font-weight: 800; color: {CARRIER_BLUE}; text-align: center; margin-bottom: 25px; }}
    .logo-container {{ text-align: center; background-color: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 20px; }}
    .card {{ background-color: #ffffff; padding: 20px; border-radius: 12px; border-left: 5px solid {CARRIER_BLUE}; box-shadow: 0 2px 5px rgba(0,0,0,0.05); margin-bottom: 15px; }}
    .task-card {{ background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #e1e8ed; margin-bottom: 10px; }}
</style>
""", unsafe_allow_html=True)

# ==================== FUNCIONES DE BASE DE DATOS ====================
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
        except Exception as e: return e
    return "Error de conexión"

# ==================== CONTROL DE ACCESO ====================
if "login" not in st.session_state:
    st.session_state.update({"login": False, "user": "", "role": ""})

if not st.session_state.login:
    st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}" width="300"></div>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        u_log = st.text_input("Usuario")
        p_log = st.text_input("Contraseña", type="password")
        if st.button("Iniciar Sesión"):
            user = execute_read("SELECT * FROM users WHERE username = %s AND password = %s", (u_log, p_log))
            if user:
                st.session_state.update({"login": True, "user": user[0]['username'], "role": user[0]['role'].lower()})
                st.rerun()
            else: st.error("Credenciales no válidas")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==================== BARRA LATERAL ====================
with st.sidebar:
    st.image(LOGO_URL, width=150)
    st.write(f"👤 **{st.session_state.user.upper()}** ({st.session_state.role})")
    st.divider()
    is_admin = st.session_state.role == "admin"
    if is_admin:
        menu = st.radio("Panel de Control", ["🎯 Asignación", "📊 Dashboard", "📸 Registro", "👥 Usuarios"])
    else:
        menu = st.radio("Panel Técnico", ["🎯 Mis Tareas", "🔔 Solicitar Unidad"])
    
    if st.button("Cerrar Sesión"):
        st.session_state.clear(); st.rerun()

# ==================== LÓGICA DE SECCIONES ====================

# --- VISTA TÉCNICO: MIS TAREAS ---
if menu == "🎯 Mis Tareas":
    st.markdown('<div class="main-header">MIS ACTIVIDADES</div>', unsafe_allow_html=True)
    
    # SISTEMA DE NOTIFICACIÓN: Tareas recién aceptadas por el admin
    recien_aceptadas = execute_read("SELECT id, unidad, actividad_id FROM asignaciones WHERE tecnico=%s AND estado='pendiente'", (st.session_state.user,))
    if recien_aceptadas:
        play_notification_sound()
        for r in recien_aceptadas:
            st.success(f"✅ **¡Solicitud Aceptada!** Unidad: {r['unidad']} - Tarea: {r['actividad_id']}")
            st.toast(f"Nueva tarea: {r['unidad']}", icon="🔔")

    tareas = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado NOT IN ('completada', 'solicitado')", (st.session_state.user,))
    if not tareas:
        st.info("No tienes tareas pendientes autorizadas.")
    else:
        for t in tareas:
            with st.expander(f"📦 UNIDAD: {t['unidad']} | {t['actividad_id'].upper()} ({t['estado']})"):
                if t['estado'] == 'pendiente':
                    if st.button(f"🚀 Comenzar Trabajo #{t['id']}", key=f"btn_s_{t['id']}"):
                        execute_write("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=NOW() WHERE id=%s", (t['id'],))
                        st.rerun()
                elif t['estado'] == 'en_proceso':
                    if t['actividad_id'] == "toma de series":
                        with st.form(f"form_ser_{t['id']}"):
                            campos = {k: st.text_input(v, key=f"f_{k}_{t['id']}") for k, v in CAMPOS_SERIES.items()}
                            if st.form_submit_button("Finalizar y Guardar Series"):
                                set_q = ", ".join([f"{k}=%s" for k in campos.keys()])
                                execute_write(f"UPDATE unidades SET {set_q} WHERE unit_number=%s", list(campos.values()) + [t['unidad']])
                                execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW() WHERE id=%s", (t['id'],))
                                st.rerun()
                    else:
                        if st.button(f"✅ Finalizar Actividad #{t['id']}", key=f"btn_f_{t['id']}"):
                            execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW() WHERE id=%s", (t['id'],))
                            st.rerun()

# --- VISTA TÉCNICO: SOLICITAR UNIDAD ---
elif menu == "🔔 Solicitar Unidad":
    st.markdown('<div class="main-header">SOLICITUD DE TRABAJO</div>', unsafe_allow_html=True)
    unidades_raw = execute_read("SELECT unit_number, id_lote FROM unidades")
    u_opciones = [f"{x['id_lote']} - {x['unit_number']}" for x in unidades_raw]
    
    with st.form("sol_tecnico"):
        u_sel = st.selectbox("Unidad a trabajar", u_opciones)
        a_sel = st.selectbox("Actividad específica", ACTIVIDADES_CARRIER)
        if st.form_submit_button("Enviar Solicitud al Administrador"):
            u_final = u_sel.split(" - ")[1]
            execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'solicitado')", (u_final, a_sel, st.session_state.user))
            st.success("Enviado. Recibirás una alerta cuando el administrador la autorice.")

# --- VISTA ADMIN: ASIGNACIÓN Y AUTORIZACIÓN ---
elif menu == "🎯 Asignación":
    st.markdown('<div class="main-header">GESTIÓN DE SOLICITUDES</div>', unsafe_allow_html=True)
    
    sols_pendientes = execute_read("SELECT * FROM asignaciones WHERE estado='solicitado'")
    if sols_pendientes:
        st.subheader("🔔 Solicitudes por Técnicos")
        for s in sols_pendientes:
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.markdown(f'<div class="card">👨‍🔧 <b>{s["tecnico"]}</b> solicita unidad <b>{s["unidad"]}</b> para <b>{s["actividad_id"]}</b></div>', unsafe_allow_html=True)
            if c2.button("✅ Autorizar", key=f"aut_{s['id']}"):
                execute_write("UPDATE asignaciones SET estado='pendiente' WHERE id=%s", (s['id'],)); st.rerun()
            if c3.button("❌ Rechazar", key=f"rec_{s['id']}"):
                execute_write("DELETE FROM asignaciones WHERE id=%s", (s['id'],)); st.rerun()
    else:
        st.write("No hay solicitudes nuevas de técnicos.")

    st.divider()
    with st.expander("➕ Asignación Directa (Manual)"):
        u_db = execute_read("SELECT unit_number, id_lote FROM unidades")
        t_db = execute_read("SELECT username FROM users WHERE role='tecnico'")
        col1, col2, col3 = st.columns(3)
        u_man = col1.selectbox("Unidad", [f"{x['id_lote']} - {x['unit_number']}" for x in u_db])
        t_man = col2.selectbox("Técnico", [x['username'] for x in t_db])
        a_man = col3.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.button("Asignar Tarea"):
            execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'pendiente')", (u_man.split(" - ")[1], a_man, t_man))
            st.rerun()

# --- VISTA ADMIN: DASHBOARD ---
elif menu == "📊 Dashboard":
    st.markdown('<div class="main-header">CONTROL DE PRODUCTIVIDAD</div>', unsafe_allow_html=True)
    asig = execute_read("SELECT * FROM asignaciones")
    unid = execute_read("SELECT * FROM unidades")
    
    if asig:
        df_a = pd.DataFrame(asig)
        # Gráficas
        c1, c2 = st.columns(2)
        with c1: st.plotly_chart(px.bar(df_a, x='tecnico', color='estado', barmode='group', title="Estado por Técnico"), use_container_width=True)
        with c2: st.plotly_chart(px.pie(df_a, names='estado', title="Resumen General de Tareas", hole=0.4), use_container_width=True)
        
        # NUEVO: Detalle de actividades por técnico
        st.subheader("📋 Detalle de Actividades Actuales")
        st.dataframe(df_a[['tecnico', 'unidad', 'actividad_id', 'estado', 'fecha_inicio']], use_container_width=True, hide_index=True)

    if unid:
        df_u = pd.DataFrame(unid)
        st.subheader("🏗️ Inventario por Lotes")
        for lote in df_u['id_lote'].unique():
            with st.expander(f"LOTE: {lote}"):
                st.table(df_u[df_u['id_lote']==lote][['unit_number'] + list(CAMPOS_SERIES.keys())])
        
        # Exportación
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_u.to_excel(writer, index=False, sheet_name='Series')
            if asig: df_a.to_excel(writer, index=False, sheet_name='Actividades')
        st.download_button("📥 Descargar Reporte Excel", buffer.getvalue(), f"Reporte_{datetime.now().strftime('%Y%m%d')}.xlsx")

# --- VISTA ADMIN: REGISTRO ---
elif menu == "📸 Registro":
    st.markdown('<div class="main-header">REGISTRO DE UNIDADES</div>', unsafe_allow_html=True)
    with st.form("reg_master"):
        c1, c2 = st.columns(2)
        u_i = c1.text_input("Número de Unidad")
        l_i = c1.text_input("ID Lote / Proyecto")
        c_i = c2.selectbox("Campo a registrar", list(CAMPOS_SERIES.keys()), format_func=lambda x: CAMPOS_SERIES[x])
        v_i = c2.text_input("Valor del Serial")
        if st.form_submit_button("Guardar"):
            execute_write(f"INSERT INTO unidades (unit_number, id_lote, {c_i}) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE id_lote=%s, {c_i}=%s", (u_i, l_i, v_i, l_i, v_i))
            st.success("Guardado en Base de Datos.")

# --- VISTA ADMIN: USUARIOS ---
elif menu == "👥 Usuarios":
    st.subheader("Control de Personal")
    with st.form("user_add"):
        nu, np, nr = st.text_input("Nombre de Usuario"), st.text_input("Password"), st.selectbox("Rol", ["tecnico", "admin"])
        if st.form_submit_button("Registrar Usuario"):
            execute_write("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (nu, np, nr))
            st.success("Personal registrado.")
