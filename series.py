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

CAMPOS_UNIDAD = {
    "vin_number": "VIN NUMBER",
    "reefer_serial": "REEFER SERIAL",
    "reefer_model": "REEFER MODEL",
    "evaporator_serial_mjs11": "EVAPORATOR SERIAL MJS11",
    "evaporator_serial_mjd22": "EVAPORATOR SERIAL MJD22",
    "engine_serial": "ENGINE SERIAL",
    "compressor_serial": "COMPRESSOR SERIAL",
    "generator_serial": "GENERATOR SERIAL",
    "battery_charger_serial": "BATTERY CHARGER SERIAL"
}

ID_ACTIVIDAD_SERIES = "Toma de Series"

st.markdown(f"""
<style>
    .main-header {{ font-size: 2.3rem; font-weight: bold; color: {CARRIER_BLUE}; text-align: center; margin-bottom: 20px; }}
    .metric-card {{ background-color: #ffffff; padding: 20px; border-radius: 10px; border-left: 5px solid {CARRIER_BLUE}; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); }}
    .stButton>button {{ width: 100%; border-radius: 5px; height: 3em; background-color: {CARRIER_BLUE}; color: white; }}
    .st-d5 {{ background-color: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #dee2e6; margin-bottom: 10px; }}
</style>
""", unsafe_allow_html=True)

# ==================== CONEXIÓN ====================
def get_db_connection():
    return mysql.connector.connect(
        **st.secrets["db"],
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

# ==================== LOGIN ====================
if "login" not in st.session_state:
    st.session_state.update({"login": False, "user": "", "role": ""})

if not st.session_state.login:
    st.title("🔐 Acceso Carrier")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        user = execute_read("SELECT * FROM users WHERE username=%s AND password=%s", (u, p))
        if user:
            st.session_state.update({"login": True, "user": u, "role": user[0]['role']})
            st.rerun()
        else:
            st.error("Credenciales incorrectas")
    st.stop()

# ==================== SIDEBAR ====================
with st.sidebar:
    st.image(LOGO_URL, width=150)
    st.write(f"💼 **Perfil:** {st.session_state.role.upper()}")
    st.divider()
    
    is_admin = st.session_state.role.upper() == "ADMIN"
    if is_admin:
        menu = st.radio("Menú", ["📸 Registro", "🎯 Asignación", "📊 Dashboard", "👥 Usuarios"])
        
        st.divider()
        st.warning("⚠️ ZONA DE PELIGRO")
        if st.button("🗑️ ELIMINAR TODA LA DATA", help="Borra unidades y tareas permanentemente"):
            execute_write("SET FOREIGN_KEY_CHECKS = 0")
            execute_write("TRUNCATE TABLE asignaciones")
            execute_write("TRUNCATE TABLE unidades")
            execute_write("SET FOREIGN_KEY_CHECKS = 1")
            st.success("Base de datos reseteada correctamente.")
            time.sleep(1)
            st.rerun()
    else:
        menu = "🎯 Mis Tareas"

    if st.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

# ==================== GESTIÓN DE USUARIOS (Solo Admin) ====================
if menu == "👥 Usuarios" and is_admin:
    st.markdown('<div class="main-header">GESTIÓN DE USUARIOS</div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["➕ Agregar Usuario", "🗑️ Eliminar Usuario"])
    
    with tab1:
        with st.form("nuevo_usuario"):
            new_u = st.text_input("Nombre de Usuario")
            new_p = st.text_input("Contraseña", type="password")
            new_r = st.selectbox("Rol", ["tecnico", "admin"])
            if st.form_submit_button("Crear Usuario"):
                if new_u and new_p:
                    execute_write("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (new_u, new_p, new_r))
                    st.success(f"Usuario {new_u} creado")
    
    with tab2:
        users = execute_read("SELECT username FROM users")
        user_to_del = st.selectbox("Seleccione usuario a eliminar", [u['username'] for u in users])
        if st.button("Eliminar"):
            if user_to_del != st.session_state.user:
                execute_write("DELETE FROM users WHERE username=%s", (user_to_del,))
                st.success("Usuario eliminado")
                st.rerun()
            else:
                st.error("No puedes eliminarte a ti mismo")

# ==================== REGISTRO Y ASIGNACIÓN ====================
elif menu == "📸 Registro" and is_admin:
    st.markdown('<div class="main-header">REGISTRO DE UNIDADES</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        tipo = st.radio("Modo", ["Nueva Unidad", "Existente"])
        u_num = st.text_input("Unit Number")
        lote = st.text_input("Lote (Obligatorio)")
    with c2:
        campo = st.selectbox("Campo", list(CAMPOS_UNIDAD.keys()), format_func=lambda x: CAMPOS_UNIDAD[x])
        valor = st.text_input("Valor")
    
    if st.button("💾 Guardar"):
        if u_num and lote:
            execute_write(f"INSERT INTO unidades (unit_number, id_lote, {campo}) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE id_lote=%s, {campo}=%s", (u_num, lote, valor, lote, valor))
            st.success("Unidad registrada")

elif menu == "🎯 Asignación" and is_admin:
    st.markdown('<div class="main-header">ASIGNAR TAREAS</div>', unsafe_allow_html=True)
    u_data = execute_read("SELECT unit_number, id_lote FROM unidades")
    tec_data = execute_read("SELECT username FROM users WHERE role='tecnico'")
    
    col1, col2, col3 = st.columns(3)
    u_sel = col1.selectbox("Unidad", [f"{x['id_lote']} - {x['unit_number']}" for x in u_data] if u_data else [])
    tec_sel = col2.selectbox("Técnico", [x['username'] for x in tec_data] if tec_data else [])
    act_sel = col3.selectbox("Actividad", [ID_ACTIVIDAD_SERIES, "Inspección Pre-Entrega", "Mantenimiento"])

    if st.button("📌 Asignar"):
        u_clean = u_sel.split(" - ")[1]
        execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'pendiente')", (u_clean, act_sel, tec_sel))
        st.success("Tarea enviada")

# ==================== MIS TAREAS (TÉCNICOS) ====================
elif menu == "🎯 Mis Tareas":
    st.markdown(f'<div class="main-header">TAREAS DE {st.session_state.user.upper()}</div>', unsafe_allow_html=True)
    tareas = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado!='completada'", (st.session_state.user,))
    
    if not tareas:
        st.info("Sin tareas pendientes")
    else:
        for t in tareas:
            with st.expander(f"📦 Unidad: {t['unidad']} - {t['actividad_id']}"):
                if t['estado'] == 'pendiente':
                    if st.button(f"Iniciar {t['id']}"):
                        execute_write("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=NOW() WHERE id=%s", (t['id'],))
                        st.rerun()
                else:
                    if t['actividad_id'] == ID_ACTIVIDAD_SERIES:
                        with st.form(f"f_{t['id']}"):
                            inputs = {k: st.text_input(v) for k, v in CAMPOS_UNIDAD.items()}
                            if st.form_submit_button("Guardar"):
                                set_q = ", ".join([f"{k}=%s" for k in inputs.keys()])
                                execute_write(f"UPDATE unidades SET {set_q} WHERE unit_number=%s", list(inputs.values()) + [t['unidad']])
                                execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW(), tiempo_minutos=TIMESTAMPDIFF(MINUTE, fecha_inicio, NOW()) WHERE id=%s", (t['id'],))
                                st.rerun()

# ==================== DASHBOARD (LOTE > UNIDAD > VIN) ====================
elif menu == "📊 Dashboard" and is_admin:
    st.markdown('<div class="main-header">CONTROL ESTRATÉGICO POR LOTES</div>', unsafe_allow_html=True)
    
    data = execute_read("""
        SELECT u.id_lote, u.unit_number, u.vin_number, a.tecnico, a.estado, a.actividad_id, a.tiempo_minutos 
        FROM unidades u 
        LEFT JOIN asignaciones a ON u.unit_number = a.unidad
    """)
    
    if data:
        df = pd.DataFrame(data)
        
        # Productividad
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🚀 Tareas por Técnico")
            df_prod = df[df['estado'] == 'completada'].groupby('tecnico').size().reset_index(name='Tareas')
            st.plotly_chart(px.bar(df_prod, x='tecnico', y='Tareas', color='tecnico'), use_container_width=True)
            
        with c2:
            st.subheader("📊 Distribución por Actividad")
            st.plotly_chart(px.pie(df, names='actividad_id', hole=0.4), use_container_width=True)

        st.divider()
        
        # JERARQUÍA LOTE > UNIDAD > VIN
        lotes = df['id_lote'].unique()
        for lote in lotes:
            with st.expander(f"🏗️ LOTE: {lote}", expanded=True):
                df_lote = df[df['id_lote'] == lote]
                st.dataframe(
                    df_lote[['unit_number', 'vin_number', 'tecnico', 'actividad_id', 'estado']],
                    column_config={
                        "unit_number": "UNIDAD",
                        "vin_number": "VIN ASIGNADO",
                        "tecnico": "RESPONSABLE",
                        "estado": st.column_config.StatusColumn("ESTADO")
                    },
                    use_container_width=True, hide_index=True
                )
    
    time.sleep(60)
    st.rerun()
