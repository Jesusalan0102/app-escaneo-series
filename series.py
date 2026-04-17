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

# --- ESTILOS PROFESIONALES ---
st.markdown(f"""
<style>
    .main-header {{ font-size: 2.3rem; font-weight: bold; color: {CARRIER_BLUE}; text-align: center; margin-bottom: 20px; }}
    .stButton>button {{ width: 100%; border-radius: 8px; height: 3em; background-color: {CARRIER_BLUE}; color: white; font-weight: bold; }}
    .card {{ background-color: #ffffff; padding: 20px; border-radius: 12px; border-left: 6px solid {CARRIER_BLUE}; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 15px; }}
</style>
""", unsafe_allow_html=True)

# ==================== CONEXIÓN ====================
def get_db_connection():
    return mysql.connector.connect(**st.secrets["db"], autocommit=True)

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

# ==================== LOGIN CORREGIDO ====================
if "login" not in st.session_state:
    st.session_state.update({"login": False, "user": "", "role": ""})

if not st.session_state.login:
    st.markdown('<div class="main-header">Acceso Carrier</div>', unsafe_allow_html=True)
    
    # Formulario de login para evitar recargas accidentales
    with st.container():
        u_log = st.text_input("Usuario").strip()
        p_log = st.text_input("Contraseña", type="password").strip()
        
        if st.button("Entrar"):
            # Buscamos ignorando mayúsculas/minúsculas y espacios extras
            user = execute_read("SELECT * FROM users WHERE TRIM(LOWER(username)) = TRIM(LOWER(%s)) AND password = %s", (u_log, p_log))
            
            if user:
                st.session_state.login = True
                st.session_state.user = user[0]['username']
                st.session_state.role = user[0]['role'].lower()
                st.rerun()
            else:
                st.error("Credenciales incorrectas. Verifique mayúsculas y espacios.")
    st.stop()

# ==================== SIDEBAR ====================
with st.sidebar:
    st.image(LOGO_URL, width=150)
    st.write(f"💼 Usuario: **{st.session_state.user}**")
    st.divider()
    
    is_admin = st.session_state.role == "admin"
    if is_admin:
        menu = st.radio("Menú Principal", ["📸 Registro", "🎯 Asignación", "📊 Dashboard", "👥 Usuarios"])
    else:
        menu = "🎯 Mis Tareas"

    if st.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

# ==================== SECCIONES ====================

if menu == "👥 Usuarios":
    st.subheader("Gestión de Usuarios")
    with st.form("crear_u"):
        nu, np, nr = st.text_input("Nuevo Usuario"), st.text_input("Contraseña"), st.selectbox("Rol", ["tecnico", "admin"])
        if st.form_submit_button("Registrar Usuario"):
            execute_write("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (nu, np, nr))
            st.success("Usuario registrado.")

elif menu == "📸 Registro":
    st.markdown('<div class="main-header">REGISTRO TÉCNICO DE UNIDADES</div>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            u_num = st.text_input("Unit Number")
            lote = st.text_input("Lote")
        with c2:
            campo = st.selectbox("Campo", list(CAMPOS_SERIES.keys()), format_func=lambda x: CAMPOS_SERIES[x])
            valor = st.text_input("Valor del Serial")
        if st.button("💾 Guardar"):
            execute_write(f"INSERT INTO unidades (unit_number, id_lote, {campo}) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE id_lote=%s, {campo}=%s", (u_num, lote, valor, lote, valor))
            st.success("Guardado.")
        st.markdown('</div>', unsafe_allow_html=True)

elif menu == "🎯 Asignación":
    st.markdown('<div class="main-header">ASIGNACIÓN Y GESTIÓN</div>', unsafe_allow_html=True)
    with st.expander("📌 Asignar Tarea", expanded=True):
        u_db = execute_read("SELECT unit_number, id_lote FROM unidades")
        t_db = execute_read("SELECT username FROM users WHERE role='tecnico'")
        u_list = [f"{x['id_lote']} - {x['unit_number']}" for x in u_db] if u_db else []
        c1, c2, c3 = st.columns(3)
        u_s = c1.selectbox("Unidad", u_list)
        t_s = c2.selectbox("Técnico", [x['username'] for x in t_db] if t_db else [])
        a_s = c3.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.button("Confirmar"):
            execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'pendiente')", (u_s.split(" - ")[1], a_s, t_s))
            st.rerun()

    st.subheader("🗑️ Control de Tareas Activas")
    asig_activas = execute_read("SELECT * FROM asignaciones WHERE estado != 'completada'")
    for a in asig_activas:
        with st.container():
            col_t, col_b = st.columns([4, 1])
            col_t.markdown(f'<div class="card"><strong>{a["unidad"]}</strong> | {a["actividad_id"]} | {a["tecnico"]} ({a["estado"]})</div>', unsafe_allow_html=True)
            if col_b.button("Eliminar", key=f"del_{a['id']}"):
                execute_write("DELETE FROM asignaciones WHERE id = %s", (a['id'],))
                st.rerun()

elif menu == "🎯 Mis Tareas":
    st.subheader(f"Panel de {st.session_state.user}")
    mis_t = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado!='completada'", (st.session_state.user,))
    for t in mis_t:
        with st.expander(f"📦 {t['unidad']} - {t['actividad_id']}"):
            if t['estado'] == 'pendiente':
                if st.button(f"Iniciar #{t['id']}"):
                    execute_write("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=NOW() WHERE id=%s", (t['id'],))
                    st.rerun()
            elif t['actividad_id'] == "toma de series":
                with st.form(f"f_{t['id']}"):
                    res = {k: st.text_input(v) for k, v in CAMPOS_SERIES.items()}
                    if st.form_submit_button("Finalizar"):
                        set_q = ", ".join([f"{k}=%s" for k in res.keys()])
                        execute_write(f"UPDATE unidades SET {set_q} WHERE unit_number=%s", list(res.values()) + [t['unidad']])
                        execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW() WHERE id=%s", (t['id'],))
                        st.rerun()
            else:
                if st.button(f"Completar #{t['id']}"):
                    execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW() WHERE id=%s", (t['id'],))
                    st.rerun()

elif menu == "📊 Dashboard":
    st.markdown('<div class="main-header">DASHBOARD DE PRODUCTIVIDAD</div>', unsafe_allow_html=True)
    asig = execute_read("SELECT tecnico, estado, id FROM asignaciones")
    unid = execute_read("SELECT * FROM unidades")
    
    if asig:
        df_a = pd.DataFrame(asig)
        pivot = df_a.pivot_table(index='tecnico', columns='estado', values='id', aggfunc='count', fill_value=0).reset_index()
        for c in ['pendiente', 'en_proceso', 'completada']:
            if c not in pivot.columns: pivot[c] = 0
        st.dataframe(pivot, use_container_width=True, hide_index=True)
        
        c1, c2 = st.columns(2)
        with c1: st.plotly_chart(px.bar(df_a, x='tecnico', color='estado', barmode='group', title="Productividad"), use_container_width=True)
        with c2: st.plotly_chart(px.pie(df_a, names='estado', title="Estado Global"), use_container_width=True)

    if unid:
        st.markdown("### 📋 Registro Maestro de Series")
        df_u = pd.DataFrame(unid)
        st.dataframe(df_u, use_container_width=True, hide_index=True)
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_u.to_excel(writer, index=False, sheet_name='Series')
            if asig: pd.DataFrame(asig).to_excel(writer, index=False, sheet_name='Productividad')
        st.download_button("📥 Excel", buffer.getvalue(), f"Reporte_{datetime.now().strftime('%Y%m%d')}.xlsx")

    time.sleep(60)
    st.rerun()
