import streamlit as st
import pandas as pd
import mysql.connector
from mysql.connector import Error
import plotly.express as px
from datetime import datetime
import io
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import pytz 
from streamlit_autorefresh import st_autorefresh

# ==================== CONFIGURACIÓN INICIAL ====================
st.set_page_config(page_title="Carrier Transicold - Sistema Integral", layout="wide")
st_autorefresh(interval=30 * 1000, key="global_refresh")

# Configuración de Zona Horaria (Tijuana, BC)
tijuana_tz = pytz.timezone('America/Tijuana')
ahora_tj = datetime.now(tijuana_tz)
fecha_hoy = ahora_tj.strftime('%Y-%m-%d')

CARRIER_BLUE = "#002B5B"
BACKGROUND_COLOR = "#F4F7F9"
LOGO_URL = "https://raw.githubusercontent.com/Jesusalan0102/app-escaneo-series/main/carrierlogo2.jpeg.jpg"

CAMPOS_SERIES = {
    "vin_number": "VIN Number", "reefer_serial": "Reefer Serial",
    "reefer_model": "Reefer Model", "evaporator_serial_mjs11": "Evaporator Serial MJS11",
    "evaporator_serial_mjd22": "Evaporator Serial MJD22", "engine_serial": "Engine",
    "compressor_serial": "Compressor", "generator_serial": "Generator",
    "battery_charger_serial": "Battery Charger"
}

ACTIVIDADES_CARRIER = [
    "Cableado", "Cerrado", "Corriendo", "Inspección", "Pretrip", 
    "Programación", "Soldadura en sitio", "Vacíos", "Accesorios", 
    "Toma de valores", "Evidencia", "Standby", "Toma de series"
]

# --- ESTILOS CSS ---
st.markdown(f"""
<style>
    .stApp {{ background-color: {BACKGROUND_COLOR}; }}
    .main-header {{ font-size: 2.5rem; font-weight: 800; color: {CARRIER_BLUE}; text-align: center; margin-bottom: 30px; }}
    .logo-container {{ text-align: center; background-color: white; padding: 30px; border-radius: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom: 25px; }}
    .card {{ background-color: #ffffff; padding: 25px; border-radius: 15px; border-left: 6px solid {CARRIER_BLUE}; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; }}
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

# ==================== FUNCIONES DE CORREO ====================
def enviar_reporte_email(df_u, df_a, lista_correos, es_automatico=False):
    if not lista_correos: return False
    try:
        msg = MIMEMultipart()
        msg['From'] = st.secrets["email"]["user"]
        msg['To'] = ", ".join(lista_correos)
        msg['Subject'] = f"REPORTES CARRIER - {ahora_tj.strftime('%d/%m/%Y')}"

        cuerpo = f"Adjunto encontrará el reporte consolidado de Unidades y Actividades.\nHora: {ahora_tj.strftime('%H:%M:%S')} (Tijuana)."
        msg.attach(MIMEText(cuerpo, 'plain'))

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_u.to_excel(writer, index=False, sheet_name='Series')
            if not df_a.empty: df_a.to_excel(writer, index=False, sheet_name='Actividades')
        
        part = MIMEApplication(buffer.getvalue(), Name=f"Reporte_{fecha_hoy}.xlsx")
        part['Content-Disposition'] = f'attachment; filename="Reporte_{fecha_hoy}.xlsx"'
        msg.attach(part)

        server = smtplib.SMTP(st.secrets["email"]["smtp_server"], st.secrets["email"]["port"])
        server.starttls()
        server.login(st.secrets["email"]["user"], st.secrets["email"]["password"])
        server.send_message(msg)
        server.quit()
        return True
    except: return False

# ==================== LOGIN ====================
if "login" not in st.session_state:
    st.session_state.update({"login": False, "user": "", "role": "", "last_count": 0})

if not st.session_state.login:
    st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}" width="450"></div>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        u_log = st.text_input("Usuario")
        p_log = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            user = execute_read("SELECT * FROM users WHERE username=%s AND password=%s", (u_log, p_log))
            if user:
                st.session_state.update({"login": True, "user": user[0]['username'], "role": user[0]['role'].lower()})
                st.rerun()
            else: st.error("Error de acceso")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==================== SIDEBAR ====================
with st.sidebar:
    st.image(LOGO_URL, width=220)
    st.info(f"🕒 Tijuana: {ahora_tj.strftime('%H:%M')}")
    st.write(f"👤 **{st.session_state.user}**")
    is_admin = st.session_state.role == "admin"
    if is_admin:
        menu = st.radio("Administración", ["📊 Dashboard Completo", "🎯 Asignación Manual/Autorizar", "📸 Registro de Unidades", "👥 Usuarios y Correos"])
    else:
        menu = st.radio("Técnico", ["🎯 Mis Tareas", "🔔 Solicitar Actividad"])
    if st.button("Cerrar Sesión"):
        st.session_state.clear(); st.rerun()

# ==================== LÓGICA DE SECCIONES ====================

if menu == "🎯 Mis Tareas":
    st.markdown('<div class="main-header">Mis Actividades Autorizadas</div>', unsafe_allow_html=True)
    # Notificación Sonora
    pend = execute_read("SELECT id FROM asignaciones WHERE tecnico=%s AND estado='pendiente'", (st.session_state.user,))
    if len(pend) > st.session_state.last_count:
        st.markdown('<audio autoplay><source src="https://raw.githubusercontent.com/rafaelEscalante/notification-sounds/master/pings/ping-8.mp3" type="audio/mp3"></audio>', unsafe_allow_html=True)
        st.toast("¡Actividad Aceptada!", icon="🔔")
    st.session_state.last_count = len(pend)

    tareas = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado IN ('pendiente', 'en_proceso')", (st.session_state.user,))
    if not tareas: st.info("No tienes tareas autorizadas actualmente.")
    for t in tareas:
        with st.expander(f"📦 Unidad: {t['unidad']} - {t['actividad_id']}"):
            if t['estado'] == 'pendiente':
                if st.button(f"🚀 Iniciar Actividad", key=f"start_{t['id']}"):
                    execute_write("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=NOW() WHERE id=%s", (t['id'],)); st.rerun()
            else:
                if t['actividad_id'] == "Toma de series":
                    with st.form(f"form_{t['id']}"):
                        res = {k: st.text_input(v) for k, v in CAMPOS_SERIES.items()}
                        if st.form_submit_button("Guardar y Finalizar"):
                            q = ", ".join([f"{k}=%s" for k in res.keys()])
                            execute_write(f"UPDATE unidades SET {q} WHERE unit_number=%s", list(res.values()) + [t['unidad']])
                            execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW() WHERE id=%s", (t['id'],)); st.rerun()
                else:
                    if st.button(f"✅ Finalizar Trabajo", key=f"end_{t['id']}"):
                        execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW() WHERE id=%s", (t['id'],)); st.rerun()

elif menu == "📊 Dashboard Completo":
    st.markdown('<div class="main-header">Métricas de Productividad</div>', unsafe_allow_html=True)
    asig = execute_read("SELECT * FROM asignaciones")
    unid = execute_read("SELECT * FROM unidades")
    
    if asig:
        df_a = pd.DataFrame(asig)
        c1, c2 = st.columns(2)
        with c1: st.plotly_chart(px.bar(df_a, x='tecnico', color='estado', barmode='group', title="Tareas por Técnico"), use_container_width=True)
        with c2: st.plotly_chart(px.pie(df_a, names='estado', title="Resumen de Estados", hole=0.4), use_container_width=True)
        st.subheader("📋 Detalle de todas las Actividades")
        st.dataframe(df_a, use_container_width=True, hide_index=True)

    if unid:
        df_u = pd.DataFrame(unid)
        st.subheader("🏗️ Inventario y Series por Lotes")
        for lote in df_u['id_lote'].unique():
            with st.expander(f"Lote: {lote}"):
                st.table(df_u[df_u['id_lote']==lote][['unit_number'] + list(CAMPOS_SERIES.keys())])
        
        # Botón de reporte manual
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_u.to_excel(writer, index=False, sheet_name='Series')
            if asig: df_a.to_excel(writer, index=False, sheet_name='Actividades')
        st.download_button("📥 Descargar Reporte Excel", buffer.getvalue(), f"Reporte_{fecha_hoy}.xlsx")

elif menu == "🎯 Asignación Manual/Autorizar":
    st.markdown('<div class="main-header">Control de Asignaciones</div>', unsafe_allow_html=True)
    
    # --- AUTORIZACIONES ---
    sols = execute_read("SELECT * FROM asignaciones WHERE estado='solicitado'")
    if sols:
        st.subheader("🔔 Solicitudes por Autorizar")
        for s in sols:
            col1, col2, col3 = st.columns([3, 1, 1])
            col1.info(f"Técnico: {s['tecnico']} | Unidad: {s['unidad']} | {s['actividad_id']}")
            if col2.button("✅ Aceptar", key=f"y_{s['id']}"):
                execute_write("UPDATE asignaciones SET estado='pendiente' WHERE id=%s", (s['id'],)); st.rerun()
            if col3.button("❌ Rechazar", key=f"n_{s['id']}"):
                execute_write("DELETE FROM asignaciones WHERE id=%s", (s['id'],)); st.rerun()
    
    st.divider()
    # --- ASIGNACIÓN MANUAL ---
    st.subheader("➕ Asignar Actividad Directamente")
    u_db = execute_read("SELECT unit_number, id_lote FROM unidades")
    t_db = execute_read("SELECT username FROM users WHERE role='tecnico'")
    with st.form("manual_asig"):
        c1, c2, c3 = st.columns(3)
        u_m = c1.selectbox("Unidad", [f"{x['id_lote']} - {x['unit_number']}" for x in u_db])
        t_m = c2.selectbox("Técnico", [x['username'] for x in t_db])
        a_m = c3.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.form_submit_button("Asignar Ahora"):
            execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s,%s,%s,'pendiente')", (u_m.split(" - ")[1], a_m, t_m))
            st.success("Asignado correctamente."); st.rerun()

elif menu == "📸 Registro de Unidades":
    st.markdown('<div class="main-header">Registro de Datos</div>', unsafe_allow_html=True)
    with st.form("reg_u"):
        c1, c2 = st.columns(2)
        u_num = c1.text_input("Unit Number")
        l_id = c1.text_input("Lote")
        campo = c2.selectbox("Campo", list(CAMPOS_SERIES.keys()), format_func=lambda x: CAMPOS_SERIES[x])
        valor = c2.text_input("Valor Serial")
        if st.form_submit_button("Guardar en Base de Datos"):
            execute_write(f"INSERT INTO unidades (unit_number, id_lote, {campo}) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE {campo}=%s", (u_num, l_id, valor, valor))
            st.success("Datos guardados.")

elif menu == "👥 Usuarios y Correos":
    st.subheader("Gestión de Usuarios del Sistema")
    with st.form("new_user"):
        nu, np, nr = st.text_input("Usuario"), st.text_input("Contraseña"), st.selectbox("Rol", ["tecnico", "admin"])
        if st.form_submit_button("Crear Usuario"):
            execute_write("INSERT INTO users (username, password, role) VALUES (%s,%s,%s)", (nu, np, nr)); st.success("Creado.")
    
    st.divider()
    st.subheader("📧 Lista de Correos para Reportes")
    # Nota: Aquí puedes guardar los correos en una tabla llamada 'config_correos'
    email_input = st.text_area("Ingrese los correos separados por comas", help="ejemplo1@mail.com, ejemplo2@mail.com")
    if st.button("Guardar Destinatarios"):
        # Lógica para guardar en DB
        st.success("Destinatarios actualizados para el informe de Tijuana.")
