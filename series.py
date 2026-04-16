import streamlit as st
import pandas as pd
import mysql.connector
import plotly.express as px
from datetime import datetime
import io
import time

# ==================== CONFIGURACIÓN ====================
st.set_page_config(page_title="Carrier Transicold - Sistema de Gestión", layout="wide")

CARRIER_BLUE = "#002B5B"
LOGO_URL = "https://raw.githubusercontent.com/Jesusalan0102/app-escaneo-series/main/carrierlogo2.jpeg.jpg"

# 9 Campos técnicos (image_bd38cd.png)
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

# 13 Actividades (image_bfe824.png)
ACTIVIDADES_CARRIER = [
    "Cableado", "Cerrado", "Corriendo", "Inspección", "Pretrip", 
    "Programación", "Soldadura en sitio", "Vacios", "Accesorios", 
    "toma de valores", "Evidencia", "standby", "toma de series"
]

st.markdown(f"""
<style>
    .main-header {{ font-size: 2.3rem; font-weight: bold; color: {CARRIER_BLUE}; text-align: center; margin-bottom: 20px; }}
    .metric-card {{ background-color: #ffffff; padding: 20px; border-radius: 10px; border-left: 5px solid {CARRIER_BLUE}; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); }}
    .stButton>button {{ width: 100%; border-radius: 5px; height: 3em; background-color: {CARRIER_BLUE}; color: white; }}
</style>
""", unsafe_allow_html=True)

# ==================== CONEXIÓN MEJORADA ====================
def get_db_connection():
    return mysql.connector.connect(
        host=st.secrets["db"]["host"],
        port=int(st.secrets["db"]["port"]),
        user=st.secrets["db"]["user"],
        password=st.secrets["db"]["password"],
        database=st.secrets["db"]["database"],
        autocommit=True
    )

def execute_read(query, params=None):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(query, params or ())
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

def execute_write(query, params=None):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(query, params or ())
        return True
    finally:
        cur.close()
        conn.close()

# ==================== LOGIN (CORREGIDO) ====================
if "login" not in st.session_state:
    st.session_state.update({"login": False, "user": "", "role": ""})

if not st.session_state.login:
    st.title("🔐 Acceso Carrier")
    # Usamos strip() para evitar errores por espacios accidentales
    u_input = st.text_input("Usuario").strip()
    p_input = st.text_input("Contraseña", type="password").strip()
    
    if st.button("Entrar"):
        user_data = execute_read("SELECT * FROM users WHERE username=%s AND password=%s", (u_input, p_input))
        if user_data:
            # Guardamos el nombre exacto de la DB para evitar discrepancias
            st.session_state.update({
                "login": True, 
                "user": user_data[0]['username'], 
                "role": user_data[0]['role']
            })
            st.rerun()
        else:
            st.error("Credenciales incorrectas. Verifique mayúsculas y espacios.")
    st.stop()

# ==================== SIDEBAR ====================
with st.sidebar:
    st.image(LOGO_URL, width=150)
    st.write(f"💼 **Perfil:** {st.session_state.role.upper()}")
    st.write(f"👤 **Usuario:** {st.session_state.user}")
    st.divider()
    
    is_admin = st.session_state.role.upper() == "ADMIN"
    if is_admin:
        menu = st.radio("Menú", ["📸 Registro", "🎯 Asignación", "📊 Dashboard", "👥 Usuarios"])
    else:
        menu = "🎯 Mis Tareas"

    if st.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

# ==================== GESTIÓN USUARIOS ====================
if menu == "👥 Usuarios" and is_admin:
    st.markdown('<div class="main-header">GESTIÓN DE USUARIOS</div>', unsafe_allow_html=True)
    with st.form("nuevo_u"):
        nu, np, nr = st.text_input("Nombre"), st.text_input("Password"), st.selectbox("Rol", ["tecnico", "admin"])
        if st.form_submit_button("Crear Usuario"):
            execute_write("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (nu, np, nr))
            st.success("Usuario registrado")

# ==================== REGISTRO DE UNIDADES ====================
elif menu == "📸 Registro" and is_admin:
    st.markdown('<div class="main-header">REGISTRO DE UNIDADES</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        u_num = st.text_input("Unit Number")
        lote = st.text_input("ID Lote")
    with c2:
        campo = st.selectbox("Campo a registrar", list(CAMPOS_SERIES.keys()), format_func=lambda x: CAMPOS_SERIES[x])
        valor = st.text_input("Valor de la Serie")
    
    if st.button("💾 Guardar"):
        if u_num and lote:
            execute_write(f"INSERT INTO unidades (unit_number, id_lote, {campo}) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE id_lote=%s, {campo}=%s", (u_num, lote, valor, lote, valor))
            st.success("Información guardada")

# ==================== ASIGNACIÓN ====================
elif menu == "🎯 Asignación" and is_admin:
    st.markdown('<div class="main-header">ASIGNAR TAREAS</div>', unsafe_allow_html=True)
    unidades = execute_read("SELECT unit_number, id_lote FROM unidades")
    tecnicos = execute_read("SELECT username FROM users WHERE role='tecnico'")
    
    c1, c2, c3 = st.columns(3)
    u_sel = c1.selectbox("Unidad", [f"{x['id_lote']} - {x['unit_number']}" for x in unidades] if unidades else [])
    t_sel = c2.selectbox("Técnico", [x['username'] for x in tecnicos] if tecnicos else [])
    a_sel = c3.selectbox("Actividad", ACTIVIDADES_CARRIER)

    if st.button("📌 Asignar"):
        execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'pendiente')", (u_sel.split(" - ")[1], a_sel, t_sel))
        st.success("Tarea asignada")

# ==================== MIS TAREAS (TÉCNICOS) ====================
elif menu == "🎯 Mis Tareas":
    st.markdown(f'<div class="main-header">TAREAS DE {st.session_state.user.upper()}</div>', unsafe_allow_html=True)
    st.info("🔄 Actualización automática cada 60s activa")
    
    tareas = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado!='completada'", (st.session_state.user,))
    
    if not tareas:
        st.info("No tienes tareas pendientes")
    else:
        for t in tareas:
            with st.expander(f"📦 Unidad: {t['unidad']} | {t['actividad_id']}"):
                if t['estado'] == 'pendiente':
                    if st.button(f"Iniciar {t['id']}"):
                        execute_write("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=NOW() WHERE id=%s", (t['id'],))
                        st.rerun()
                elif t['actividad_id'] == "toma de series":
                    with st.form(f"f_{t['id']}"):
                        # Despliega los 9 campos técnicos
                        res = {k: st.text_input(v) for k, v in CAMPOS_SERIES.items()}
                        if st.form_submit_button("Guardar y Finalizar"):
                            sets = ", ".join([f"{k}=%s" for k in res.keys()])
                            execute_write(f"UPDATE unidades SET {sets} WHERE unit_number=%s", list(res.values()) + [t['unidad']])
                            execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW(), tiempo_minutos=TIMESTAMPDIFF(MINUTE, fecha_inicio, NOW()) WHERE id=%s", (t['id'],))
                            st.rerun()
                else:
                    if st.button(f"Finalizar Tarea {t['id']}"):
                        execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW(), tiempo_minutos=TIMESTAMPDIFF(MINUTE, fecha_inicio, NOW()) WHERE id=%s", (t['id'],))
                        st.rerun()
    
    time.sleep(60)
    st.rerun()

# ==================== DASHBOARD (ADMIN) ====================
elif menu == "📊 Dashboard" and is_admin:
    st.markdown('<div class="main-header">DASHBOARD DE OPERACIONES</div>', unsafe_allow_html=True)
    data = execute_read("SELECT u.*, a.tecnico, a.estado, a.actividad_id FROM unidades u LEFT JOIN asignaciones a ON u.unit_number = a.unidad")
    
    if data:
        df = pd.DataFrame(data)
        c1, c2 = st.columns(2)
        c1.plotly_chart(px.bar(df[df['estado']=='completada'].groupby('tecnico').size().reset_index(name='T'), x='tecnico', y='T', title="Productividad"), use_container_width=True)
        c2.plotly_chart(px.pie(df, names='estado', title="Estado de Tareas"), use_container_width=True)
        
        st.subheader("🏗️ Control por Lotes")
        for lote in df['id_lote'].unique():
            with st.expander(f"LOTE: {lote}"):
                st.dataframe(df[df['id_lote']==lote][['unit_number', 'vin_number', 'tecnico', 'actividad_id', 'estado']], use_container_width=True, hide_index=True)
        
        st.subheader("📋 Información Técnica Registrada")
        st.dataframe(df.drop(columns=['tecnico', 'estado', 'actividad_id']).drop_duplicates(), use_container_width=True, hide_index=True)

        if st.button("📥 Exportar a Excel"):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Reporte_Carrier')
            st.download_button(label="⬇️ Descargar Archivo", data=output.getvalue(), file_name=f"Reporte_{datetime.now().strftime('%Y%m%d')}.xlsx")
    
    time.sleep(60)
    st.rerun()
