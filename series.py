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

# Campos exactos de la imagen técnica proporcionada
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
        if st.button("🗑️ ELIMINAR TODA LA DATA (Excepto Usuarios)"):
            execute_write("SET FOREIGN_KEY_CHECKS = 0")
            execute_write("TRUNCATE TABLE asignaciones")
            execute_write("TRUNCATE TABLE unidades")
            execute_write("SET FOREIGN_KEY_CHECKS = 1")
            st.success("Base de datos de producción limpiada correctamente.")
            st.rerun()
    else:
        menu = "🎯 Mis Tareas"

    if st.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

# ==================== GESTIÓN DE USUARIOS (Admin) ====================
if menu == "👥 Usuarios" and is_admin:
    st.markdown('<div class="main-header">GESTIÓN DE USUARIOS</div>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["➕ Crear Usuario", "🗑️ Eliminar Usuario"])
    
    with t1:
        with st.form("crear_user"):
            nu = st.text_input("Nombre de Usuario")
            np = st.text_input("Contraseña", type="password")
            nr = st.selectbox("Rol", ["tecnico", "admin"])
            if st.form_submit_button("Registrar Usuario"):
                execute_write("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (nu, np, nr))
                st.success(f"Usuario {nu} creado.")

    with t2:
        users_list = execute_read("SELECT username FROM users")
        u_to_del = st.selectbox("Seleccione usuario", [u['username'] for u in users_list])
        if st.button("Confirmar Eliminación"):
            if u_to_del != st.session_state.user:
                execute_write("DELETE FROM users WHERE username=%s", (u_to_del,))
                st.success("Usuario eliminado.")
                st.rerun()
            else:
                st.error("No puedes eliminar tu propia cuenta.")

# ==================== REGISTRO DE UNIDADES ====================
elif menu == "📸 Registro" and is_admin:
    st.markdown('<div class="main-header">REGISTRO DE UNIDADES</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        tipo = st.radio("Modo", ["Nueva Unidad", "Existente"])
        u_num = st.text_input("Unit Number")
        lote = st.text_input("Lote (Obligatorio)")
    with c2:
        campo = st.selectbox("Campo", list(CAMPOS_UNIDAD.keys()), format_func=lambda x: CAMPOS_UNIDAD[x])
        valor = st.text_input("Valor de Serie")
        
    if st.button("💾 Guardar Datos"):
        if u_num and lote:
            execute_write(f"INSERT INTO unidades (unit_number, id_lote, {campo}) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE id_lote=%s, {campo}=%s", (u_num, lote, valor, lote, valor))
            st.success("Información guardada en la base de datos.")

# ==================== ASIGNACIÓN DE TAREAS ====================
elif menu == "🎯 Asignación" and is_admin:
    st.markdown('<div class="main-header">ASIGNAR TRABAJO</div>', unsafe_allow_html=True)
    u_db = execute_read("SELECT unit_number, id_lote FROM unidades")
    tec_db = execute_read("SELECT username FROM users WHERE role='tecnico'")
    actividades = [ID_ACTIVIDAD_SERIES, "Inspección Pre-Entrega", "Mantenimiento Preventivo", "Lavado", "Entrega"]
    
    c1, c2, c3 = st.columns(3)
    u_s = c1.selectbox("Unidad (Lote - Unidad)", [f"{x['id_lote']} - {x['unit_number']}" for x in u_db] if u_db else [])
    t_s = c2.selectbox("Técnico Responsable", [x['username'] for x in tec_db] if tec_db else [])
    a_s = c3.selectbox("Actividad a Realizar", actividades)
    
    if st.button("📌 Enviar Tarea"):
        if u_s:
            execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'pendiente')", (u_s.split(" - ")[1], a_s, t_s))
            st.success("Tarea asignada correctamente.")

# ==================== TAREAS TÉCNICO ====================
elif menu == "🎯 Mis Tareas":
    st.markdown(f'<div class="main-header">MIS TAREAS: {st.session_state.user.upper()}</div>', unsafe_allow_html=True)
    tareas = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado!='completada' ORDER BY fecha_asignacion DESC", (st.session_state.user,))
    
    if not tareas:
        st.info("No tienes tareas pendientes actualmente.")
    else:
        for t in tareas:
            with st.expander(f"📦 Unidad: {t['unidad']} | Actividad: {t['actividad_id']}"):
                if t['estado'] == 'pendiente':
                    if st.button(f"Comenzar {t['id']}"):
                        execute_write("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=NOW() WHERE id=%s", (t['id'],))
                        st.rerun()
                elif t['actividad_id'] == ID_ACTIVIDAD_SERIES:
                    with st.form(f"form_ser_{t['id']}"):
                        st.write("Complete todos los campos de series:")
                        respuestas = {k: st.text_input(v) for k, v in CAMPOS_UNIDAD.items()}
                        if st.form_submit_button("Finalizar Registro"):
                            sets = ", ".join([f"{k}=%s" for k in respuestas.keys()])
                            execute_write(f"UPDATE unidades SET {sets} WHERE unit_number=%s", list(respuestas.values()) + [t['unidad']])
                            execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW(), tiempo_minutos=TIMESTAMPDIFF(MINUTE, fecha_inicio, NOW()) WHERE id=%s", (t['id'],))
                            st.rerun()
                else:
                    if st.button(f"Marcar como Finalizado {t['id']}"):
                        execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW(), tiempo_minutos=TIMESTAMPDIFF(MINUTE, fecha_inicio, NOW()) WHERE id=%s", (t['id'],))
                        st.rerun()

# ==================== DASHBOARD ESTRATÉGICO ====================
elif menu == "📊 Dashboard" and is_admin:
    st.markdown('<div class="main-header">CONTROL DE PRODUCCIÓN POR LOTES</div>', unsafe_allow_html=True)
    data = execute_read("""
        SELECT u.id_lote, u.unit_number, u.vin_number, a.tecnico, a.estado, a.actividad_id 
        FROM unidades u 
        LEFT JOIN asignaciones a ON u.unit_number = a.unidad
    """)
    
    if data:
        df = pd.DataFrame(data)
        
        # Gráficos de Productividad
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            df_p = df[df['estado']=='completada'].groupby('tecnico').size().reset_index(name='Total')
            st.plotly_chart(px.bar(df_p, x='tecnico', y='Total', title="Tareas Completadas por Técnico", color='Total'), use_container_width=True)
        with col_g2:
            st.plotly_chart(px.pie(df, names='estado', title="Estado de las Tareas Asignadas", hole=0.4), use_container_width=True)

        st.divider()
        st.subheader("📋 Detalle por Jerarquía de Lote")
        
        for lote in df['id_lote'].unique():
            with st.expander(f"🏗️ LOTE: {lote}", expanded=True):
                df_lote = df[df['id_lote']==lote][['unit_number', 'vin_number', 'tecnico', 'estado', 'actividad_id']]
                st.dataframe(df_lote, use_container_width=True, hide_index=True)
    else:
        st.info("No hay datos registrados para mostrar gráficas.")

    time.sleep(60)
    st.rerun()
