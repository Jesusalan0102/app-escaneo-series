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
</style>
""", unsafe_allow_html=True)

# ==================== DATABASE ====================
@st.cache_resource(show_spinner="Conectando a BD...")
def get_db():
    try:
        # Credenciales actualizadas según tu configuración de Clever Cloud
        conn = mysql.connector.connect(
            host="bmffi0bgsqnener2omcu-mysql.services.clever-cloud.com",
            port=3306,
            user="uo8vbdsnvm2ojwta",
            password="aXSKib5oxXDEwjlozeQP",
            database="bmffi0bgsqnener2omcu",
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
        # Usamos el nombre de columna real verificado en la estructura
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
    st.title("🔐 Acceso Carrier")
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

# ==================== MENÚ Y SIDEBAR ====================
with st.sidebar:
    st.image(LOGO_URL, width=150)
    st.markdown(f"**Usuario:** {st.session_state.user}")
    st.divider()
    
    # Notificación de actividades en la parte izquierda
    st.subheader("📋 Mis Actividades")
    try:
        cur = get_cursor(dictionary=True)
        cur.execute("SELECT unidad, actividad_id FROM asignaciones WHERE tecnico = %s AND estado != 'completada'", (st.session_state.user,))
        tareas = cur.fetchall()
        cur.close()
        if tareas:
            for t in tareas:
                st.write(f"● {t['unidad']} - {t['actividad_id']}")
        else:
            st.info("Sin tareas pendientes")
    except:
        pass

    st.divider()
    menu_options = ["📸 Ingreso Series"]
    if st.session_state.role == "admin":
        menu_options.append("📊 Dashboard Admin")
    
    menu = st.radio("Navegación", menu_options)
    
    if st.button("Cerrar Sesión"):
        st.session_state.login = False
        st.rerun()

# ==================== CONTENIDO PRINCIPAL ====================
if menu == "📸 Ingreso Series":
    st.markdown('<h1 class="main-header">CARRIER TRANSICOLD</h1>', unsafe_allow_html=True)
    
    df_u = get_unidades()
    lista_u = df_u["unit_number"].astype(str).tolist() if not df_u.empty else []
    lista_u.insert(0, "+ Nueva Unidad")
    
    sel_u = st.selectbox("Seleccione Unit Number", lista_u)
    
    if sel_u == "+ Nueva Unidad":
        unit_final = st.text_input("Escriba el nuevo Unit Number")
    else:
        unit_final = sel_u

    mapa_campos = {
        "VIN": "vin_number",
        "REEFER": "reefer",
        "ENGINE": "engine_serial",
        "COMPRESSOR": "compressor_serial"
    }
    campo_label = st.selectbox("Elemento a registrar", list(mapa_campos.keys()))
    campo_db = mapa_campos[campo_label]
    valor_final = st.text_input(f"Número de Serie para {campo_label}")

    if st.button("💾 Guardar y Notificar", type="primary"):
        if unit_final and valor_final:
            try:
                cur = get_cursor()
                # Esta sentencia permite agregar múltiples series a un mismo Unit Number
                sql = f"""
                    INSERT INTO unidades (unit_number, {campo_db}) 
                    VALUES (%s, %s) 
                    ON DUPLICATE KEY UPDATE {campo_db} = %s
                """
                cur.execute(sql, (unit_final, valor_final, valor_final))
                cur.close()
                
                st.success(f"✅ ¡Registro Exitoso! {campo_label} guardado para la unidad {unit_final}.")
                st.balloons() # Notificación visual
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Error al guardar: {e}")
        else:
            st.warning("⚠️ Complete todos los campos antes de guardar")

elif menu == "📊 Dashboard Admin":
    st.subheader("Estado General de Tareas")
    st.info("Solo visible para el administrador.")
    # Aquí puedes agregar tablas de la tabla 'asignaciones'