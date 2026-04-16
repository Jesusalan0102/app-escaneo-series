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

st.markdown(f"""
<style>
    .main-header {{ font-size: 2.3rem; font-weight: bold; color: {CARRIER_BLUE}; text-align: center; margin-bottom: 20px; }}
    .stButton>button {{ width: 100%; border-radius: 5px; height: 3em; background-color: {CARRIER_BLUE}; color: white; }}
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

# ==================== LOGIN ====================
if "login" not in st.session_state:
    st.session_state.update({"login": False, "user": "", "role": ""})

if not st.session_state.login:
    st.markdown('<div class="main-header">Acceso Carrier</div>', unsafe_allow_html=True)
    u_log = st.text_input("Usuario").strip()
    p_log = st.text_input("Contraseña", type="password").strip()
    
    if st.button("Entrar"):
        user = execute_read("SELECT * FROM users WHERE LOWER(username)=LOWER(%s) AND password=%s", (u_log, p_log))
        if user:
            st.session_state.update({"login": True, "user": user[0]['username'], "role": user[0]['role'].lower()})
            st.rerun()
        else:
            st.error("Credenciales incorrectas.")
    st.stop()

# ==================== SIDEBAR ====================
with st.sidebar:
    st.image(LOGO_URL, width=150)
    st.write(f"💼 Perfil: **{st.session_state.role.upper()}**")
    st.divider()
    
    is_admin = st.session_state.role == "admin"
    if is_admin:
        menu = st.radio("Menú", ["📸 Registro", "🎯 Asignación", "📊 Dashboard", "👥 Usuarios"])
    else:
        menu = "🎯 Mis Tareas"

    if st.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

# ==================== SECCIONES ====================

if menu == "👥 Usuarios":
    st.subheader("Gestión de Usuarios")
    with st.form("crear_u"):
        nu, np, nr = st.text_input("Usuario"), st.text_input("Pass"), st.selectbox("Rol", ["tecnico", "admin"])
        if st.form_submit_button("Registrar"):
            execute_write("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (nu, np, nr))
            st.success("Usuario creado")

elif menu == "📸 Registro":
    st.subheader("Registro de Unidades")
    c1, c2 = st.columns(2)
    with c1:
        u_n, l_n = st.text_input("Unit Number"), st.text_input("Lote")
    with c2:
        f_n = st.selectbox("Campo", list(CAMPOS_SERIES.keys()), format_func=lambda x: CAMPOS_SERIES[x])
        v_n = st.text_input("Valor")
    if st.button("💾 Guardar"):
        execute_write(f"INSERT INTO unidades (unit_number, id_lote, {f_n}) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE id_lote=%s, {f_n}=%s", (u_n, l_n, v_n, l_n, v_n))
        st.success("Registrado")

elif menu == "🎯 Asignación":
    st.subheader("Asignar Actividad")
    u_db = execute_read("SELECT unit_number, id_lote FROM unidades")
    t_db = execute_read("SELECT username FROM users WHERE role='tecnico'")
    c1, c2, c3 = st.columns(3)
    u_s = c1.selectbox("Unidad", [f"{x['id_lote']} - {x['unit_number']}" for x in u_db] if u_db else [])
    t_s = c2.selectbox("Técnico", [x['username'] for x in t_db] if t_db else [])
    a_s = c3.selectbox("Actividad", ACTIVIDADES_CARRIER)
    if st.button("📌 Asignar"):
        execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'pendiente')", (u_s.split(" - ")[1], a_s, t_s))
        st.success("Tarea asignada")

elif menu == "🎯 Mis Tareas":
    st.subheader(f"Tareas de {st.session_state.user}")
    mis_t = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado!='completada'", (st.session_state.user,))
    if not mis_t: st.write("Sin tareas.")
    else:
        for t in mis_t:
            with st.expander(f"📦 {t['unidad']} - {t['actividad_id']}"):
                if t['estado'] == 'pendiente':
                    if st.button(f"Iniciar #{t['id']}"):
                        execute_write("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=NOW() WHERE id=%s", (t['id'],))
                        st.rerun()
                elif t['actividad_id'] == "toma de series":
                    with st.form(f"form_{t['id']}"):
                        res = {k: st.text_input(v) for k, v in CAMPOS_SERIES.items()}
                        if st.form_submit_button("Guardar"):
                            set_q = ", ".join([f"{k}=%s" for k in res.keys()])
                            execute_write(f"UPDATE unidades SET {set_q} WHERE unit_number=%s", list(res.values()) + [t['unidad']])
                            execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW() WHERE id=%s", (t['id'],))
                            st.rerun()
                else:
                    if st.button(f"Finalizar #{t['id']}"):
                        execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW() WHERE id=%s", (t['id'],))
                        st.rerun()
    time.sleep(60)
    st.rerun()

elif menu == "📊 Dashboard":
    st.subheader("Estado de Producción")
    res = execute_read("SELECT u.*, a.tecnico, a.estado, a.actividad_id FROM unidades u LEFT JOIN asignaciones a ON u.unit_number = a.unidad")
    if res:
        df = pd.DataFrame(res)
        c1, c2 = st.columns(2)
        with c1:
            df_tec = df.dropna(subset=['tecnico'])
            # Muestra productividad incluyendo todos los técnicos con tareas
            fig_prod = px.bar(df_tec, x='tecnico', color='estado', title="Carga de Trabajo por Técnico", 
                             labels={'tecnico': 'Técnico', 'count': 'Cantidad'}, barmode='group')
            st.plotly_chart(fig_prod, use_container_width=True)
        with c2:
            st.plotly_chart(px.pie(df, names='estado', title="Estado de Todas las Tareas"), use_container_width=True)
        
        st.write("### 🏗️ Jerarquía por Lotes")
        if not df['id_lote'].dropna().empty:
            for lote in df['id_lote'].unique():
                with st.expander(f"LOTE: {lote}"):
                    st.table(df[df['id_lote']==lote][['unit_number', 'tecnico', 'actividad_id', 'estado']])
        
        st.write("### 📋 Registro al Momento")
        st.dataframe(df.drop(columns=['tecnico', 'estado', 'actividad_id']).drop_duplicates(), hide_index=True)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        st.download_button("📥 Reporte Excel", buffer.getvalue(), "reporte_carrier.xlsx")
    
    time.sleep(60)
    st.rerun()
