import streamlit as st
import pandas as pd
import mysql.connector
import cv2
import numpy as np
import easyocr
import re

# ==================== CONFIGURACIÓN ====================
st.set_page_config(page_title="Carrier Transicold - Gestión", page_icon="📋", layout="wide")

CARRIER_BLUE = "#002B5B"
LOGO_URL = "https://raw.githubusercontent.com/Jesusalan0102/app-escaneo-series/main/carrierlogo2.jpeg.jpg"

st.markdown(f"""
<style>
.main-header {{ font-size: 2.4rem; font-weight: bold; color: {CARRIER_BLUE}; text-align: center; }}
.stButton>button {{ background-color: {CARRIER_BLUE}; color: white; border-radius: 8px; font-weight: bold; }}
.admin-box {{ padding: 15px; border: 2px solid {CARRIER_BLUE}; border-radius: 10px; background-color: #f8f9fa; }}
</style>
""", unsafe_allow_html=True)

# ==================== CONEXIÓN A BASE DE DATOS ====================
@st.cache_resource(show_spinner="Conectando...")
def get_db():
    try:
        # Credenciales directas de Clever Cloud
        return mysql.connector.connect(
            host="bmffi0bgsqnener2omcu-mysql.services.clever-cloud.com",
            port=3306,
            user="uo8vbdsnvm2ojwta",
            password="aXSKib5oxXDEwjlozeQP",
            database="bmffi0bgsqnener2omcu",
            autocommit=True
        )
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
        st.stop()

def get_cursor(dictionary=False):
    conn = get_db()
    try:
        conn.ping(reconnect=True, attempts=3, delay=2)
    except:
        st.stop()
    return conn.cursor(dictionary=dictionary)

# ==================== LOGIN ====================
if "login" not in st.session_state:
    st.session_state.update({"login": False, "user": "", "role": ""})

if not st.session_state.login:
    st.title("🔐 Acceso al Sistema")
    u = st.text_input("Usuario")
    p = st.text_input("Password", type="password")
    if st.button("Entrar", type="primary"):
        cur = get_cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE username=%s AND password=%s", (u, p))
        user = cur.fetchone()
        cur.close()
        if user:
            st.session_state.update({"login": True, "user": u, "role": user['role']})
            st.rerun()
        else:
            st.error("Credenciales incorrectas")
    st.stop()

# ==================== SIDEBAR ====================
with st.sidebar:
    st.image(LOGO_URL, width=150)
    st.markdown(f"**Usuario:** {st.session_state.user} ({st.session_state.role})")
    st.divider()
    
    # Notificación de actividades pendientes para el técnico
    st.subheader("📋 Actividades Asignadas")
    try:
        cur = get_cursor(dictionary=True)
        cur.execute("SELECT unidad, actividad_id FROM asignaciones WHERE tecnico=%s AND estado!='completada'", (st.session_state.user,))
        tareas_side = cur.fetchall()
        cur.close()
        if tareas_side:
            for t in tareas_side:
                st.write(f"● {t['unidad']} - {t['actividad_id']}")
        else:
            st.info("Sin tareas pendientes")
    except:
        pass

    st.divider()
    menu_options = ["📸 Registro de Series"]
    if st.session_state.role == "admin":
        menu_options.extend(["🎯 Asignar Tareas", "📊 Dashboard Admin"])
    else:
        menu_options.append("🛠️ Mis Tareas")
    
    menu = st.radio("Navegación", menu_options)
    if st.button("Cerrar Sesión"):
        st.session_state.login = False
        st.rerun()

# ==================== 1. REGISTRO DE SERIES (AMBOS) ====================
if menu == "📸 Registro de Series":
    st.markdown('<h1 class="main-header">REGISTRO DE UNIDADES</h1>', unsafe_allow_html=True)
    
    cur = get_cursor(dictionary=True)
    cur.execute("SELECT unit_number, vin_number FROM unidades")
    unidades_db = pd.DataFrame(cur.fetchall())
    cur.close()

    col1, col2 = st.columns(2)
    with col1:
        tipo = st.radio("Entrada", ["Existente", "+ Nueva"])
        u_final = st.text_input("Nuevo Unit Number") if tipo == "+ Nueva" else st.selectbox("Unit Number", unidades_db["unit_number"] if not unidades_db.empty else ["Vacío"])
    
    with col2:
        campo = st.selectbox("Campo", ["vin_number", "reefer", "engine_serial", "compressor_serial"])
        valor = st.text_input("Número de Serie")

    if st.button("💾 Guardar y Notificar", type="primary"):
        if u_final and valor:
            try:
                cur = get_cursor()
                # Lógica ON DUPLICATE para permitir múltiples series a un mismo Unit Number
                sql = f"INSERT INTO unidades (unit_number, {campo}) VALUES (%s, %s) ON DUPLICATE KEY UPDATE {campo}=%s"
                cur.execute(sql, (u_final, valor, valor))
                st.success(f"✅ ¡Guardado! {campo} registrado para unidad {u_final}")
                st.balloons()
                cur.close()
            except Exception as e:
                st.error(f"Error: {e}")

# ==================== 2. ASIGNACIÓN (SÓLO ADMIN) ====================
elif menu == "🎯 Asignar Tareas" and st.session_state.role == "admin":
    st.markdown('<h1 class="main-header">PANEL DE ADMINISTRADOR</h1>', unsafe_allow_html=True)
    
    st.markdown('<div class="admin-box">', unsafe_allow_html=True)
    # Solo unidades que ya tengan VIN pueden recibir tareas
    cur = get_cursor(dictionary=True)
    cur.execute("SELECT unit_number, vin_number FROM unidades WHERE vin_number IS NOT NULL")
    u_validas = pd.DataFrame(cur.fetchall())
    cur.execute("SELECT username FROM users WHERE role='tecnico'")
    tecnicos_db = pd.DataFrame(cur.fetchall())
    cur.close()

    if u_validas.empty:
        st.warning("⚠️ No hay unidades con VIN registrado. Regístrelas primero.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            u_opt = u_validas.apply(lambda x: f"{x['unit_number']} (VIN: {x['vin_number']})", axis=1)
            u_sel = st.selectbox("Unidad (Unit Number + VIN)", u_opt)
            tec_sel = st.selectbox("Asignar a Técnico", tecnicos_db["username"])
        
        with col2:
            # Lista exacta de 14 actividades
            act_lista = ["Cableado", "Cerrado", "Corriendo", "Inspeccion", "Pretrip", 
                         "Programación", "Soldadura en sitio", "Vacíos", "Accesorios", 
                         "Alarma", "toma de valores", "Evidencia", "lista para irse", "standby"]
            act_sel = st.selectbox("Actividad a realizar", act_lista)

        if st.button("📌 Confirmar Asignación"):
            u_id = u_sel.split(" ")[0]
            cur = get_cursor()
            cur.execute("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'pendiente')", (u_id, act_sel, tec_sel))
            st.success(f"Tarea '{act_sel}' asignada a {tec_sel}")
            cur.close()
    st.markdown('</div>', unsafe_allow_html=True)

# ==================== 3. MIS TAREAS (TÉCNICO) ====================
elif menu == "🛠️ Mis Tareas":
    st.subheader(f"Gestión de Tareas: {st.session_state.user}")
    cur = get_cursor(dictionary=True)
    cur.execute("SELECT * FROM asignaciones WHERE tecnico=%s AND estado!='completada'", (st.session_state.user,))
    tareas = cur.fetchall()
    cur.close()

    if not tareas:
        st.info("No tienes tareas pendientes")
    for t in tareas:
        with st.expander(f"📦 Unidad {t['unidad']} - {t['actividad_id']}"):
            if t['estado'] == 'pendiente':
                if st.button("▶️ Iniciar", key=f"s{t['id']}"):
                    cur = get_cursor()
                    cur.execute("UPDATE asignaciones SET estado='en_progreso', start_time=NOW() WHERE id=%s", (t['id'],))
                    st.rerun()
            elif t['estado'] == 'en_progreso':
                if st.button("✅ Terminar", key=f"f{t['id']}"):
                    cur = get_cursor()
                    cur.execute("UPDATE asignaciones SET estado='completada', end_time=NOW() WHERE id=%s", (t['id'],))
                    st.rerun()