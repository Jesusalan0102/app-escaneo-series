import streamlit as st
import pandas as pd
import mysql.connector
import cv2
import numpy as np
import easyocr
import re

# ==================== CONFIG ====================
st.set_page_config(page_title="Carrier Transicold - Gestión", page_icon="📋", layout="wide")

CARRIER_BLUE = "#002B5B"
LOGO_URL = "https://raw.githubusercontent.com/Jesusalan0102/app-escaneo-series/main/carrierlogo2.jpeg.jpg"

st.markdown(f"""
<style>
.main-header {{ font-size: 2.4rem; font-weight: bold; color: {CARRIER_BLUE}; text-align: center; }}
.stButton>button {{ background-color: {CARRIER_BLUE}; color: white; border-radius: 8px; font-weight: bold; }}
.sidebar-task {{ padding: 10px; border-bottom: 1px solid #eee; font-size: 0.9rem; }}
</style>
""", unsafe_allow_html=True)

# ==================== DATABASE ====================
@st.cache_resource(show_spinner="Conectando a BD...")
def get_db():
    try:
        conn = mysql.connector.connect(
            **st.secrets["db"],
            autocommit=True,
            connection_timeout=120
        )
        return conn
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
        st.stop()

def get_cursor(dictionary=False):
    conn = get_db()
    try:
        conn.ping(reconnect=True, attempts=3, delay=5)
    except:
        st.error("❌ Error de reconexión")
        st.stop()
    return conn.cursor(dictionary=dictionary)

@st.cache_data(ttl=10)
def get_unidades():
    try:
        cur = get_cursor(dictionary=True)
        cur.execute("SELECT * FROM unidades ORDER BY unit_number DESC")
        res = cur.fetchall()
        cur.close()
        return pd.DataFrame(res)
    except:
        return pd.DataFrame()

# ==================== LOGIN ====================
if "login" not in st.session_state:
    st.session_state.login = False
    st.session_state.user = ""
    st.session_state.role = ""

if not st.session_state.login:
    col_logo, col_title = st.columns([1, 3])
    with col_logo: st.image(LOGO_URL, width=200)
    st.title("🔐 Acceso al Sistema")
    u = st.text_input("Usuario")
    p = st.text_input("Password", type="password")

    if st.button("Entrar", type="primary"):
        cur = get_cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE username=%s AND password=%s", (u, p))
        user = cur.fetchone()
        cur.close()
        if user:
            st.session_state.login = True
            st.session_state.user = u
            st.session_state.role = user.get("role", "tecnico")
            st.rerun()
        else:
            st.error("❌ Credenciales incorrectas")
    st.stop()

# ==================== SIDEBAR (TAREAS ASIGNADAS) ====================
with st.sidebar:
    st.image(LOGO_URL, width=150)
    st.markdown(f"**Usuario:** {st.session_state.user} ({st.session_state.role})")
    st.divider()
    
    st.subheader("📋 Mis Actividades")
    try:
        cur = get_cursor(dictionary=True)
        cur.execute("SELECT unidad, actividad_id, estado FROM asignaciones WHERE tecnico = %s AND estado != 'completada'", (st.session_state.user,))
        tareas_side = cur.fetchall()
        cur.close()
        
        if not tareas_side:
            st.info("No hay tareas pendientes")
        for t in tareas_side:
            color = "orange" if t['estado'] == 'en_progreso' else "gray"
            st.markdown(f"""
            <div class="sidebar-task">
                <b style="color:{color}">●</b> {t['unidad']}<br>
                <small>{t['actividad_id']}</small>
            </div>
            """, unsafe_allow_html=True)
    except:
        st.error("Error al cargar sidebar")

    st.divider()
    menu_options = ["📸 Ingreso Series", "📝 Gestionar Tareas"]
    if st.session_state.role == "admin":
        menu_options.append("⚙️ Panel Admin")
        menu_options.append("📊 Dashboard")
    
    menu = st.radio("Navegación", menu_options)
    
    if st.button("Cerrar Sesión"):
        st.session_state.login = False
        st.rerun()

# ==================== INGRESO SERIES ====================
if menu == "📸 Ingreso Series":
    st.markdown('<h1 class="main-header">CARRIER TRANSICOLD</h1>', unsafe_allow_html=True)
    st.subheader("Ingreso de Componentes por Unidad")

    # Selección de Unidad
    df_u = get_unidades()
    lista_u = df_u["unit_number"].astype(str).tolist() if not df_u.empty else []
    lista_u.insert(0, "+ Nueva Unidad")
    
    sel_u = st.selectbox("Seleccione Unit Number", lista_u)
    
    if sel_u == "+ Nueva Unidad":
        unit_final = st.text_input("Ingrese Nuevo Unit Number")
    else:
        unit_final = sel_u

    # Configuración de Campos
    mapa_campos = {
        "VIN": "vin_number",
        "REEFER": "reefer",
        "ENGINE": "engine_serial",
        "COMPRESSOR": "compressor_serial"
    }
    campo_label = st.selectbox("Componente a registrar", list(mapa_campos.keys()))
    campo_db = mapa_campos[campo_label]

    # OCR / Carga
    uploaded = st.file_uploader("Escanear Placa", type=["jpg", "png", "jpeg"])
    valor_final = st.text_input("Número de Serie / Valor", key="val_input")

    if st.button("💾 Guardar en Base de Datos", type="primary"):
        if not unit_final or not valor_final:
            st.warning("⚠️ Complete el Unit Number y el Valor")
        else:
            try:
                cur = get_cursor()
                # Lógica: Si existe el unit_number, actualiza solo el campo elegido. Si no existe, lo crea.
                sql = f"""
                    INSERT INTO unidades (unit_number, {campo_db}) 
                    VALUES (%s, %s) 
                    ON DUPLICATE KEY UPDATE {campo_db} = %s
                """
                cur.execute(sql, (unit_final, valor_final, valor_final))
                cur.close()
                
                st.success(f"✅ ¡Guardado con éxito! Se ha registrado el {campo_label} para la unidad {unit_final}.")
                st.balloons()
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Error: {e}")

# ==================== GESTIONAR TAREAS (TÉCNICO) ====================
elif menu == "📝 Gestionar Tareas":
    st.subheader("Mis Tareas Asignadas")
    # ... (Misma lógica de Iniciar/Completar que tenías, pero filtrando por el usuario actual)

# ==================== PANEL ADMIN ====================
elif menu == "⚙️ Panel Admin" and st.session_state.role == "admin":
    st.subheader("Asignación de Tareas (Solo Administrador)")
    # ... (Lógica para INSERT en la tabla asignaciones)

# ==================== DASHBOARD ====================
elif menu == "📊 Dashboard" and st.session_state.role == "admin":
    st.subheader("Estado General de Lotes")
    # ... (Gráficos y tablas de tiempos totales)