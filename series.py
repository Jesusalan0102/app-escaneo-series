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

# --- ESTILOS PROFESIONALES (Toque de versiones anteriores) ---
st.markdown(f"""
<style>
    .main-header {{ font-size: 2.3rem; font-weight: bold; color: {CARRIER_BLUE}; text-align: center; margin-bottom: 20px; }}
    .stButton>button {{ width: 100%; border-radius: 8px; height: 3em; background-color: {CARRIER_BLUE}; color: white; font-weight: bold; transition: 0.3s; }}
    .stButton>button:hover {{ background-color: #004080; border: 1px solid white; }}
    .card {{ background-color: #ffffff; padding: 20px; border-radius: 12px; border-left: 6px solid {CARRIER_BLUE}; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 15px; }}
    .metric-card {{ background-color: #f1f4f9; padding: 10px; border-radius: 8px; text-align: center; border: 1px solid #d1d9e6; }}
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
    st.write(f"💼 Usuario: **{st.session_state.user}**")
    st.write(f"🔑 Rol: **{st.session_state.role.upper()}**")
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
            st.success("Usuario creado con éxito")

elif menu == "📸 Registro":
    st.markdown('<div class="main-header">REGISTRO TÉCNICO DE UNIDADES</div>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            u_num = st.text_input("Unit Number (ID)")
            lote = st.text_input("Lote / Proyecto")
        with c2:
            campo = st.selectbox("Campo a actualizar", list(CAMPOS_SERIES.keys()), format_func=lambda x: CAMPOS_SERIES[x])
            valor = st.text_input("Valor del Serial")
        if st.button("💾 Guardar Cambios"):
            execute_write(f"INSERT INTO unidades (unit_number, id_lote, {campo}) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE id_lote=%s, {campo}=%s", (u_num, lote, valor, lote, valor))
            st.success(f"Se ha actualizado {CAMPOS_SERIES[campo]} para la unidad {u_num}")
        st.markdown('</div>', unsafe_allow_html=True)

elif menu == "🎯 Asignación":
    st.markdown('<div class="main-header">GESTIÓN DE ACTIVIDADES</div>', unsafe_allow_html=True)
    
    # --- FORMULARIO DE ASIGNACIÓN ---
    with st.expander("📌 Asignar Nueva Tarea", expanded=True):
        u_db = execute_read("SELECT unit_number, id_lote FROM unidades")
        t_db = execute_read("SELECT username FROM users WHERE role='tecnico'")
        
        c1, c2, c3 = st.columns(3)
        u_list = [f"{x['id_lote']} - {x['unit_number']}" for x in u_db] if u_db else []
        u_s = c1.selectbox("Seleccionar Unidad", u_list)
        t_s = c2.selectbox("Asignar a Técnico", [x['username'] for x in t_db] if t_db else [])
        a_s = c3.selectbox("Tipo de Actividad", ACTIVIDADES_CARRIER)
        
        if st.button("Confirmar Asignación"):
            execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'pendiente')", (u_s.split(" - ")[1], a_s, t_s))
            st.rerun()

    st.divider()

    # --- LISTA DE TAREAS (Movido del Dashboard aquí) ---
    st.subheader("📋 Control de Tareas Asignadas")
    asig_activas = execute_read("SELECT id, unidad, actividad_id, tecnico, estado FROM asignaciones WHERE estado != 'completada'")
    
    if asig_activas:
        for a in asig_activas:
            with st.container():
                col_text, col_btn = st.columns([4, 1])
                with col_text:
                    st.markdown(f"""
                    <div class="card">
                        <strong>📦 Unidad:</strong> {a['unidad']} | 
                        <strong>🛠️ Actividad:</strong> {a['actividad_id']} | 
                        <strong>👤 Técnico:</strong> {a['tecnico']} | 
                        <strong>🕒 Estado:</strong> {a['estado'].upper()}
                    </div>
                    """, unsafe_allow_html=True)
                with col_btn:
                    st.write("") # Espaciador
                    if st.button("Eliminar", key=f"del_{a['id']}"):
                        execute_write("DELETE FROM asignaciones WHERE id = %s", (a['id'],))
                        st.rerun()
    else:
        st.info("No hay tareas pendientes en el sistema.")

elif menu == "🎯 Mis Tareas":
    st.subheader(f"Panel de Trabajo: {st.session_state.user}")
    mis_t = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado!='completada'", (st.session_state.user,))
    if not mis_t: st.write("No tienes tareas pendientes.")
    else:
        for t in mis_t:
            with st.expander(f"Tarea: {t['unidad']} - {t['actividad_id']}"):
                if t['estado'] == 'pendiente':
                    if st.button(f"🚀 Iniciar Tarea #{t['id']}"):
                        execute_write("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=NOW() WHERE id=%s", (t['id'],))
                        st.rerun()
                elif t['actividad_id'] == "toma de series":
                    with st.form(f"series_form_{t['id']}"):
                        st.info("Complete los seriales de la unidad")
                        respuestas = {k: st.text_input(v) for k, v in CAMPOS_SERIES.items()}
                        if st.form_submit_button("Guardar y Finalizar"):
                            set_clause = ", ".join([f"{k}=%s" for k in respuestas.keys()])
                            execute_write(f"UPDATE unidades SET {set_clause} WHERE unit_number=%s", list(respuestas.values()) + [t['unidad']])
                            execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW() WHERE id=%s", (t['id'],))
                            st.rerun()
                else:
                    if st.button(f"✅ Finalizar Tarea #{t['id']}"):
                        execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW() WHERE id=%s", (t['id'],))
                        st.rerun()

elif menu == "📊 Dashboard":
    st.markdown('<div class="main-header">DASHBOARD DE PRODUCTIVIDAD</div>', unsafe_allow_html=True)
    
    asig_raw = execute_read("SELECT tecnico, estado, id FROM asignaciones")
    unidades_raw = execute_read("SELECT * FROM unidades")
    
    if asig_raw:
        df_asig = pd.DataFrame(asig_raw)
        
        # --- MÉTRICAS NUMÉRICAS (Puras) ---
        pivot = df_asig.pivot_table(index='tecnico', columns='estado', values='id', aggfunc='count', fill_value=0).reset_index()
        for col in ['pendiente', 'en_proceso', 'completada']:
            if col not in pivot.columns: pivot[col] = 0
        
        st.markdown("### 📊 Rendimiento por Técnico")
        st.dataframe(pivot.rename(columns={'tecnico': 'Técnico', 'pendiente': '🟡 Pendientes', 'en_proceso': '🔵 En Proceso', 'completada': '✅ Completadas'}), use_container_width=True, hide_index=True)

        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.bar(df_asig, x='tecnico', color='estado', title="Distribución de Carga", barmode='group', color_discrete_sequence=["#FFCC00", "#3366CC", "#009933"]), use_container_width=True)
        with c2:
            st.plotly_chart(px.pie(df_asig, names='estado', title="Estado Global de la Operación", hole=0.4), use_container_width=True)

    # --- DESGLOSE DE SERIES (Restaurado sin mezcla de datos) ---
    st.markdown("### 📋 Registro Maestro de Series")
    if unidades_raw:
        df_u = pd.DataFrame(unidades_raw)
        st.dataframe(df_u, use_container_width=True, hide_index=True)
        
        # Vista por Lotes (Toque profesional)
        st.write("### 🏗️ Unidades por Proyecto / Lote")
        for lote in df_u['id_lote'].unique():
            with st.expander(f"Ver Unidades del Lote: {lote}"):
                st.table(df_u[df_u['id_lote']==lote][['unit_number'] + list(CAMPOS_SERIES.keys())])
        
        # Exportación
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_u.to_excel(writer, index=False, sheet_name='Series_Tecnicas')
            if asig_raw: pd.DataFrame(asig_raw).to_excel(writer, index=False, sheet_name='Productividad')
        st.download_button("📥 Descargar Reporte Completo (Excel)", buffer.getvalue(), f"Reporte_Carrier_{datetime.now().strftime('%Y%m%d')}.xlsx")
    
    time.sleep(60)
    st.rerun()
