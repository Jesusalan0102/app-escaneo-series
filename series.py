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
st.set_page_config(page_title="Carrier Transicold - Sistema de Gestión", layout="wide")
st_autorefresh(interval=30 * 1000, key="global_refresh")

# Configuración de Zona Horaria (Tijuana, BC)
tijuana_tz = pytz.timezone('America/Tijuana')
ahora_tj = datetime.now(tijuana_tz)
fecha_hoy = ahora_tj.strftime('%Y-%m-%d')

# Lista de destinatarios
DESTINATARIOS = [
    "gerente@ejemplo.com", 
    "supervisor@ejemplo.com", 
    "admin@ejemplo.com"
]

CARRIER_BLUE = "#002B5B"
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

# ==================== FUNCIONES DE CORREO Y ENVÍO AUTOMÁTICO ====================

def enviar_reporte_email(df_u, df_a, es_automatico=False):
    try:
        msg = MIMEMultipart()
        msg['From'] = st.secrets["email"]["user"]
        msg['To'] = ", ".join(DESTINATARIOS)
        tipo = "AUTOMÁTICO" if es_automatico else "MANUAL"
        msg['Subject'] = f"INFORME {tipo} CARRIER - {ahora_tj.strftime('%d/%m/%Y')}"

        cuerpo = f"Saludos. Se adjunta el reporte de actividades y series.\nGenerado a las: {ahora_tj.strftime('%H:%M:%S')} (Hora Tijuana)."
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
    except Exception as e:
        return False

# Lógica de disparo automático (A partir de las 18:00 hrs)
def verificar_envio_automatico(df_u, df_a):
    if ahora_tj.hour >= 18:
        # Consultar si ya se envió hoy para no saturar correos
        enviado = execute_read("SELECT id FROM registro_envios WHERE fecha = %s", (fecha_hoy,))
        if not enviado:
            if enviar_reporte_email(df_u, df_a, es_automatico=True):
                execute_write("INSERT INTO registro_envios (fecha, hora_envio) VALUES (%s, %s)", (fecha_hoy, ahora_tj.strftime('%H:%M:%S')))
                st.toast("Reporte diario enviado automáticamente.", icon="📧")

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

# ==================== SESIÓN Y LOGIN ====================
if "login" not in st.session_state:
    st.session_state.update({"login": False, "user": "", "role": "", "last_count": 0})

if not st.session_state.login:
    st.markdown(f'<div style="text-align:center; background:white; padding:20px; border-radius:15px; box-shadow:0 4px 10px rgba(0,0,0,0.1); margin-bottom:20px;"><img src="{LOGO_URL}" width="300"></div>', unsafe_allow_html=True)
    with st.container():
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("Entrar"):
            user = execute_read("SELECT * FROM users WHERE username=%s AND password=%s", (u, p))
            if user:
                st.session_state.update({"login": True, "user": user[0]['username'], "role": user[0]['role'].lower()})
                st.rerun()
            else: st.error("Acceso denegado")
    st.stop()

# ==================== NAVEGACIÓN ====================
with st.sidebar:
    st.image(LOGO_URL, width=150)
    st.info(f"📍 Tijuana: {ahora_tj.strftime('%H:%M')}")
    st.write(f"👤 **{st.session_state.user}**")
    is_admin = st.session_state.role == "admin"
    menu = st.radio("Menú", ["📸 Registro", "🎯 Asignación", "📊 Dashboard", "👥 Usuarios"]) if is_admin else st.radio("Menú", ["🎯 Mis Tareas", "🔔 Solicitar"])
    if st.button("Salir"):
        st.session_state.clear(); st.rerun()

# ==================== SECCIONES ====================

if menu == "🎯 Mis Tareas":
    st.subheader("Tareas del Técnico")
    # Alerta Sonora
    pend = execute_read("SELECT id FROM asignaciones WHERE tecnico=%s AND estado='pendiente'", (st.session_state.user,))
    if len(pend) > st.session_state.last_count:
        st.markdown('<audio autoplay><source src="https://raw.githubusercontent.com/rafaelEscalante/notification-sounds/master/pings/ping-8.mp3" type="audio/mp3"></audio>', unsafe_allow_html=True)
        st.success("¡Nueva actividad autorizada!")
    st.session_state.last_count = len(pend)

    tareas = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado IN ('pendiente', 'en_proceso')", (st.session_state.user,))
    for t in tareas:
        with st.expander(f"Unidad {t['unidad']} - {t['actividad_id']}"):
            if t['estado'] == 'pendiente':
                if st.button(f"Iniciar #{t['id']}"):
                    execute_write("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=NOW() WHERE id=%s", (t['id'],)); st.rerun()
            else:
                if t['actividad_id'] == "Toma de series":
                    with st.form(f"f_{t['id']}"):
                        res = {k: st.text_input(v) for k, v in CAMPOS_SERIES.items()}
                        if st.form_submit_button("Finalizar"):
                            q = ", ".join([f"{k}=%s" for k in res.keys()])
                            execute_write(f"UPDATE unidades SET {q} WHERE unit_number=%s", list(res.values()) + [t['unidad']])
                            execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW() WHERE id=%s", (t['id'],)); st.rerun()
                elif st.button(f"Finalizar #{t['id']}"):
                    execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW() WHERE id=%s", (t['id'],)); st.rerun()

elif menu == "📊 Dashboard":
    st.title("Estadísticas y Reportes")
    asig = execute_read("SELECT * FROM asignaciones")
    unid = execute_read("SELECT * FROM unidades")
    df_u = pd.DataFrame(unid)
    df_a = pd.DataFrame(asig)

    # Disparo de envío automático al entrar al dashboard
    verificar_envio_automatico(df_u, df_a)

    if not df_a.empty:
        c1, c2 = st.columns(2)
        c1.plotly_chart(px.bar(df_a, x='tecnico', color='estado', title="Avance por Técnico"), use_container_width=True)
        c2.plotly_chart(px.pie(df_a, names='estado', title="Estado Global"), use_container_width=True)
    
    st.subheader("Control de Lotes")
    for lote in df_u['id_lote'].unique():
        with st.expander(f"Lote: {lote}"):
            st.dataframe(df_u[df_u['id_lote']==lote], hide_index=True)
    
    if st.button("📧 Enviar Informe Manual Ahora"):
        if enviar_reporte_email(df_u, df_a): st.success("Enviado a destinatarios.")

elif menu == "🎯 Asignación":
    st.subheader("Autorizaciones")
    sols = execute_read("SELECT * FROM asignaciones WHERE estado='solicitado'")
    for s in sols:
        col1, col2, col3 = st.columns([3,1,1])
        col1.warning(f"{s['tecnico']} solicita {s['unidad']} para {s['actividad_id']}")
        if col2.button("Aprobar", key=f"y{s['id']}"):
            execute_write("UPDATE asignaciones SET estado='pendiente' WHERE id=%s", (s['id'],)); st.rerun()
        if col3.button("Negar", key=f"n{s['id']}"):
            execute_write("DELETE FROM asignaciones WHERE id=%s", (s['id'],)); st.rerun()

elif menu == "📸 Registro":
    with st.form("reg"):
        u, l = st.text_input("Unidad"), st.text_input("Lote")
        c = st.selectbox("Campo", list(CAMPOS_SERIES.keys()), format_func=lambda x: CAMPOS_SERIES[x])
        v = st.text_input("Valor")
        if st.form_submit_button("Guardar"):
            execute_write(f"INSERT INTO unidades (unit_number, id_lote, {c}) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE {c}=%s", (u,l,v,v))
            st.success("Actualizado")

elif menu == "👥 Usuarios":
    with st.form("us"):
        un, pw, rl = st.text_input("User"), st.text_input("Pass"), st.selectbox("Rol", ["tecnico", "admin"])
        if st.form_submit_button("Crear"):
            execute_write("INSERT INTO users (username, password, role) VALUES (%s,%s,%s)", (un,pw,rl))
            st.success("Creado")
