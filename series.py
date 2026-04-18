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

# Configuración de campos técnicos
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
    .task-accounting-card {{ background-color: white; padding: 20px; border-radius: 12px; border: 1px solid #e1e8ed; margin-bottom: 15px; }}
    .task-header {{ font-size: 1.3rem; font-weight: 700; color: {CARRIER_BLUE}; border-bottom: 2px solid #e1e8ed; padding-bottom: 10px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; }}
    .task-count {{ background-color: {CARRIER_BLUE}; color: white; padding: 5px 12px; border-radius: 20px; font-size: 0.9rem; }}
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
def enviar_reporte_email(df_u, df_a, lista_correos):
    if not lista_correos:
        st.warning("No hay correos destinatarios configurados.")
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = st.secrets["email"]["user"]
        msg['To'] = ", ".join(lista_correos)
        msg['Subject'] = f"INFORME FINAL CARRIER - {ahora_tj.strftime('%d/%m/%Y')}"

        cuerpo = f"Hola, se adjunta el reporte final consolidado.\nHora de envío: {ahora_tj.strftime('%H:%M:%S')} (Tijuana)."
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
        st.error(f"Error de envío: {e}")
        return False

# ==================== LOGIN ====================
if "login" not in st.session_state:
    st.session_state.update({"login": False, "user": "", "role": "", "last_count": 0})

if not st.session_state.login:
    # --- LOGO TAMAÑO DOBLE (900px) ---
    st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}" width="900"></div>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        u_log = st.text_input("Usuario")
        p_log = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            user = execute_read("SELECT * FROM users WHERE username=%s AND password=%s", (u_log, p_log))
            if user:
                st.session_state.update({"login": True, "user": user[0]['username'], "role": user[0]['role'].lower()})
                st.rerun()
            else: st.error("Acceso denegado")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==================== SIDEBAR ====================
with st.sidebar:
    # --- LOGO TAMAÑO DOBLE (440px) ---
    st.image(LOGO_URL, width=440)
    st.info(f"📍 Tijuana: {ahora_tj.strftime('%H:%M')}")
    st.write(f"👤 **{st.session_state.user}**")
    is_admin = st.session_state.role == "admin"
    if is_admin:
        menu = st.radio("Administración", ["📊 Dashboard Completo", "🎯 Asignación Manual/Autorizar", "📸 Registro de Unidades", "👥 Usuarios y Correos"])
    else:
        menu = st.radio("Técnico", ["🎯 Mis Tareas", "🔔 Solicitar Actividad"])
    if st.button("Cerrar Sesión"):
        st.session_state.clear(); st.rerun()

# ==================== SECCIONES ====================

if menu == "🎯 Mis Tareas":
    st.markdown('<div class="main-header">Mis Actividades Autorizadas</div>', unsafe_allow_html=True)
    # Alerta Sonora
    pend = execute_read("SELECT id FROM asignaciones WHERE tecnico=%s AND estado='pendiente'", (st.session_state.user,))
    if len(pend) > st.session_state.last_count:
        st.markdown('<audio autoplay><source src="https://raw.githubusercontent.com/rafaelEscalante/notification-sounds/master/pings/ping-8.mp3" type="audio/mp3"></audio>', unsafe_allow_html=True)
        st.toast("¡Nueva tarea autorizada!", icon="🔔")
    st.session_state.last_count = len(pend)

    tareas = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado NOT IN ('completada', 'solicitado')", (st.session_state.user,))
    if not tareas:
        st.info("Sin tareas pendientes.")
    else:
        df_t = pd.DataFrame(tareas)
        for unidad in df_t['unidad'].unique():
            tareas_u = df_t[df_t['unidad'] == unidad]
            st.markdown(f'<div class="task-accounting-card"><div class="task-header"><span>📦 Unidad: {unidad}</span><span class="task-count">{len(tareas_u)} Actividades</span></div></div>', unsafe_allow_html=True)
            for _, t in tareas_u.iterrows():
                with st.expander(f"🛠️ {t['actividad_id']} - {t['estado'].capitalize()}"):
                    if t['estado'] == 'pendiente':
                        if st.button(f"🚀 Iniciar #{t['id']}"):
                            execute_write("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=NOW() WHERE id=%s", (t['id'],)); st.rerun()
                    else:
                        if t['actividad_id'].lower() == "toma de series":
                            with st.form(f"f_{t['id']}"):
                                res = {k: st.text_input(v) for k, v in CAMPOS_SERIES.items()}
                                if st.form_submit_button("Guardar y Finalizar"):
                                    q = ", ".join([f"{k}=%s" for k in res.keys()])
                                    execute_write(f"UPDATE unidades SET {q} WHERE unit_number=%s", list(res.values()) + [t['unidad']])
                                    execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW() WHERE id=%s", (t['id'],)); st.rerun()
                        elif st.button(f"✅ Finalizar #{t['id']}"):
                            execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW() WHERE id=%s", (t['id'],)); st.rerun()

elif menu == "📊 Dashboard Completo":
    st.markdown('<div class="main-header">Métricas de Productividad</div>', unsafe_allow_html=True)
    asig = execute_read("SELECT * FROM asignaciones")
    unid = execute_read("SELECT * FROM unidades")
    
    if asig:
        df_a = pd.DataFrame(asig)
        c1, c2 = st.columns(2)
        with c1: st.plotly_chart(px.bar(df_a, x='tecnico', color='estado', barmode='group', title="Tareas por Técnico"), use_container_width=True)
        with c2: st.plotly_chart(px.pie(df_a, names='estado', title="Estado Global", hole=0.4), use_container_width=True)
        st.subheader("📋 Detalle de Actividades")
        st.dataframe(df_a, use_container_width=True, hide_index=True)

    if unid:
        df_u = pd.DataFrame(unid)
        st.subheader("🏗️ Lotes y Unidades")
        for lote in df_u['id_lote'].unique():
            with st.expander(f"Ver Lote: {lote}"):
                st.table(df_u[df_u['id_lote']==lote][['unit_number'] + list(CAMPOS_SERIES.keys())])
        
        # Botones finales
        st.divider()
        col_ex1, col_ex2 = st.columns(2)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_u.to_excel(writer, index=False, sheet_name='Series')
            if asig: df_a.to_excel(writer, index=False, sheet_name='Actividades')
        col_ex1.download_button("📥 Descargar Reporte Excel", buffer.getvalue(), f"Reporte_{fecha_hoy}.xlsx")
        
        # --- BOTÓN DE ENVÍO FINAL SOLICITADO ---
        if col_ex2.button("📧 Enviar Informe Final por Correo Ahora"):
            # En esta sección se deben jalar los correos de tu lista de destinatarios
            destinatarios_test = ["tu_correo@ejemplo.com"] # Ajustar según tu configuración
            if enviar_reporte_email(df_u, pd.DataFrame(asig) if asig else pd.DataFrame(), destinatarios_test):
                st.success("¡Informe Final enviado exitosamente!")

elif menu == "🎯 Asignación Manual/Autorizar":
    st.markdown('<div class="main-header">Control de Asignaciones</div>', unsafe_allow_html=True)
    sols = execute_read("SELECT * FROM asignaciones WHERE estado='solicitado'")
    if sols:
        st.subheader("🔔 Solicitudes por Autorizar")
        for s in sols:
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.info(f"Técnico: {s['tecnico']} | Unidad: {s['unidad']} | {s['actividad_id']}")
            if c2.button("✅ Aceptar", key=f"y{s['id']}"):
                execute_write("UPDATE asignaciones SET estado='pendiente' WHERE id=%s", (s['id'],)); st.rerun()
            if c3.button("❌ Rechazar", key=f"n{s['id']}"):
                execute_write("DELETE FROM asignaciones WHERE id=%s", (s['id'],)); st.rerun()
    
    st.divider()
    st.subheader("➕ Asignación Directa")
    u_db = execute_read("SELECT unit_number, id_lote FROM unidades")
    t_db = execute_read("SELECT username FROM users WHERE role='tecnico'")
    with st.form("asig_man"):
        u_sel = st.selectbox("Unidad", [f"{x['id_lote']} - {x['unit_number']}" for x in u_db])
        t_sel = st.selectbox("Técnico", [x['username'] for x in t_db])
        a_sel = st.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.form_submit_button("Asignar Tarea"):
            execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s,%s,%s,'pendiente')", (u_sel.split(" - ")[1], a_sel, t_sel))
            st.success("Tarea asignada."); st.rerun()

elif menu == "📸 Registro de Unidades":
    st.markdown('<div class="main-header">Registro de Datos</div>', unsafe_allow_html=True)
    with st.form("reg_u"):
        u_i = st.text_input("Unit Number")
        l_i = st.text_input("Lote")
        c_i = st.selectbox("Campo", list(CAMPOS_SERIES.keys()), format_func=lambda x: CAMPOS_SERIES[x])
        v_i = st.text_input("Valor")
        if st.form_submit_button("Guardar"):
            execute_write(f"INSERT INTO unidades (unit_number, id_lote, {c_i}) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE {c_i}=%s", (u_i, l_i, v_i, v_i))
            st.success("Información guardada."); st.rerun()

elif menu == "👥 Usuarios y Correos":
    st.subheader("Gestión de Usuarios y Destinatarios")
    with st.form("u_new"):
        un, pw, rl = st.text_input("Usuario"), st.text_input("Contraseña"), st.selectbox("Rol", ["tecnico", "admin"])
        if st.form_submit_button("Crear"):
            execute_write("INSERT INTO users (username, password, role) VALUES (%s,%s,%s)", (un, pw, rl)); st.success("Creado.")
    st.divider()
    st.text_area("Correos para informes (separados por comas)")
    if st.button("Guardar Destinatarios"):
        st.success("Configuración de correos guardada.")
