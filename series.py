import streamlit as st
import pandas as pd
import mysql.connector
from mysql.connector import Error
import plotly.express as px
from datetime import datetime
import io
import time

# ==================== CONFIGURACIÓN ====================
st.set_page_config(page_title="Carrier Transicold - Panel de Gestión", layout="wide")

CARRIER_BLUE = "#002B5B"
BACKGROUND_COLOR = "#F4F7F9"
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
    .stApp {{ background-color: {BACKGROUND_COLOR}; }}
    .main-header {{ font-size: 2.5rem; font-weight: 800; color: {CARRIER_BLUE}; text-align: center; margin-bottom: 30px; }}
    .logo-container {{ text-align: center; background-color: white; padding: 25px; border-radius: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom: 25px; border: 1px solid #e1e8ed; }}
    .stButton>button {{ width: 100%; border-radius: 8px; height: 3.2em; background-color: {CARRIER_BLUE}; color: white; font-weight: bold; border: none; }}
    .card {{ background-color: #ffffff; padding: 25px; border-radius: 15px; border-left: 6px solid {CARRIER_BLUE}; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #e1e8ed; }}
    .task-accounting-card {{ background-color: white; padding: 20px; border-radius: 12px; border: 1px solid #e1e8ed; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 15px; }}
    .task-header {{ font-size: 1.3rem; font-weight: 700; color: {CARRIER_BLUE}; border-bottom: 2px solid #e1e8ed; padding-bottom: 10px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; }}
    .task-count {{ background-color: {CARRIER_BLUE}; color: white; padding: 5px 12px; border-radius: 20px; font-size: 0.9rem; }}
    .status-badge {{ padding: 3px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: bold; }}
    .status-solicitado {{ background-color: #FFAB91; color: #D84315; border: 1px solid #FF5722; }}
    .status-pendiente {{ background-color: #FFE082; color: #827717; }}
    .status-en_proceso {{ background-color: #BBDEFB; color: #1565C0; }}
</style>
""", unsafe_allow_html=True)

# ==================== CONEXIÓN ====================
def get_db_connection():
    try: return mysql.connector.connect(**st.secrets["db"], autocommit=True)
    except Error: return None

def execute_read(query, params=None):
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(query, params or ())
            res = cur.fetchall()
            cur.close()
            conn.close()
            return res
        except Error: return []
    return []

def execute_write(query, params=None):
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(query, params or ())
            cur.close()
            conn.close()
            return True
        except Error as e: return e
    return "No hay conexión"

# ==================== LOGIN ====================
if "login" not in st.session_state:
    st.session_state.update({"login": False, "user": "", "role": ""})

if not st.session_state.login:
    st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}" width="350"></div>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        u_log = st.text_input("Usuario").strip()
        p_log = st.text_input("Contraseña", type="password").strip()
        if st.button("Entrar"):
            user = execute_read("SELECT * FROM users WHERE TRIM(LOWER(username)) = TRIM(LOWER(%s)) AND password = %s", (u_log, p_log))
            if user:
                st.session_state.update({"login": True, "user": user[0]['username'], "role": user[0]['role'].lower()})
                st.rerun()
            else: st.error("Credenciales incorrectas.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}" width="200"></div>', unsafe_allow_html=True)
    st.write(f"👤 Usuario: **{st.session_state.user}**")
    st.divider()
    
    is_admin = st.session_state.role == "admin"
    if is_admin:
        menu = st.radio("Menú", ["📸 Registro", "🎯 Asignación", "📊 Dashboard", "👥 Usuarios"])
    else:
        menu = st.radio("Menú Técnico", ["🎯 Mis Tareas", "🔔 Solicitar Unidad"])

    if st.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

# ==================== SECCIONES ====================

if menu == "🎯 Mis Tareas":
    st.markdown('<div class="main-header">PANEL DE TAREAS AUTORIZADAS</div>', unsafe_allow_html=True)
    mis_t_raw = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado NOT IN ('completada', 'solicitado')", (st.session_state.user,))
    
    if not mis_t_raw:
        st.info("No tienes tareas autorizadas pendientes.")
    else:
        df_mis_t = pd.DataFrame(mis_t_raw)
        for unidad in df_mis_t['unidad'].unique():
            tareas_u = df_mis_t[df_mis_t['unidad'] == unidad]
            
            # Recuadro Contable de la Unidad
            st.markdown(f"""
            <div class="task-accounting-card">
                <div class="task-header">
                    <span>📦 Unidad: {unidad}</span>
                    <span class="task-count">{len(tareas_u)} Actividades</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Lista de actividades dentro de esa unidad
            for _, task in tareas_u.iterrows():
                with st.expander(f"🛠️ {task['actividad_id'].upper()} (Estado: {task['estado'].upper()})"):
                    # Si está pendiente, botón para iniciar
                    if task['estado'] == 'pendiente':
                        if st.button(f"🚀 Iniciar Actividad #{task['id']}", key=f"in_{task['id']}"):
                            execute_write("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=NOW() WHERE id=%s", (task['id'],))
                            st.rerun()
                    
                    # Si ya está en proceso, mostrar formularios o finalizar
                    elif task['estado'] == 'en_proceso':
                        # SECCIÓN RESTAURADA: TOMA DE SERIES
                        if task['actividad_id'] == "toma de series":
                            st.subheader("📝 Registro de Series")
                            with st.form(f"form_series_{task['id']}"):
                                data_input = {}
                                c1, c2 = st.columns(2)
                                i = 0
                                for key, label in CAMPOS_SERIES.items():
                                    col = c1 if i % 2 == 0 else c2
                                    data_input[key] = col.text_input(label, key=f"{key}_{task['id']}")
                                    i += 1
                                
                                if st.form_submit_button("💾 Guardar Todo y Finalizar"):
                                    # Actualizar tabla Unidades
                                    set_clause = ", ".join([f"{k}=%s" for k in data_input.keys()])
                                    execute_write(f"UPDATE unidades SET {set_clause} WHERE unit_number=%s", list(data_input.values()) + [task['unidad']])
                                    # Marcar asignación como completada
                                    execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW() WHERE id=%s", (task['id'],))
                                    st.success("Series guardadas con éxito.")
                                    st.rerun()
                        
                        # Actividad Normal (solo botón finalizar)
                        else:
                            if st.button(f"✅ Marcar como Finalizado #{task['id']}", key=f"fin_{task['id']}"):
                                execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW() WHERE id=%s", (task['id'],))
                                st.rerun()

elif menu == "🔔 Solicitar Unidad":
    st.markdown('<div class="main-header">SOLICITAR TRABAJO</div>', unsafe_allow_html=True)
    u_db = execute_read("SELECT unit_number, id_lote FROM unidades")
    u_list = [f"{x['id_lote']} - {x['unit_number']}" for x in u_db]
    with st.form("sol_tec"):
        u_sel = st.selectbox("Unidad", u_list)
        a_sel = st.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.form_submit_button("Enviar Solicitud"):
            execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'solicitado')", (u_sel.split(" - ")[1], a_sel, st.session_state.user))
            st.success("Solicitud enviada al Administrador.")

elif menu == "🎯 Asignación":
    st.markdown('<div class="main-header">GESTIÓN DE ASIGNACIONES</div>', unsafe_allow_html=True)
    st.subheader("🔔 Solicitudes por Autorizar")
    sols = execute_read("SELECT * FROM asignaciones WHERE estado='solicitado'")
    if sols:
        for s in sols:
            col_t, col_a, col_r = st.columns([3, 1, 1])
            col_t.markdown(f'<div class="card"><strong>{s["tecnico"]}</strong> solicita <strong>{s["unidad"]}</strong> para <strong>{s["actividad_id"]}</strong></div>', unsafe_allow_html=True)
            if col_a.button("✅ Autorizar", key=f"a_{s['id']}"):
                execute_write("UPDATE asignaciones SET estado='pendiente' WHERE id=%s", (s['id'],))
                st.rerun()
            if col_r.button("❌ Rechazar", key=f"r_{s['id']}"):
                execute_write("DELETE FROM asignaciones WHERE id=%s", (s['id'],))
                st.rerun()
    
    st.divider()
    with st.expander("➕ Asignación Manual Directa"):
        u_db = execute_read("SELECT unit_number, id_lote FROM unidades")
        t_db = execute_read("SELECT username FROM users WHERE role='tecnico'")
        c1, c2, c3 = st.columns(3)
        u_s = c1.selectbox("Unidad", [f"{x['id_lote']} - {x['unit_number']}" for x in u_db])
        t_s = c2.selectbox("Técnico", [x['username'] for x in t_db])
        a_s = c3.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.button("Confirmar Asignación Directa"):
            execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'pendiente')", (u_s.split(" - ")[1], a_s, t_s))
            st.rerun()

    st.subheader("🗑️ Control de Tareas Activas")
    activas = execute_read("SELECT * FROM asignaciones WHERE estado != 'completada'")
    for a in activas:
        c_text, c_del = st.columns([4, 1])
        c_text.markdown(f'<div class="card">{a["unidad"]} | {a["actividad_id"]} | {a["tecnico"]} ({a["estado"]})</div>', unsafe_allow_html=True)
        if c_del.button("Eliminar", key=f"del_{a['id']}"):
            execute_write("DELETE FROM asignaciones WHERE id=%s", (a['id'],))
            st.rerun()

elif menu == "📊 Dashboard":
    st.markdown('<div class="main-header">DASHBOARD DE PRODUCTIVIDAD</div>', unsafe_allow_html=True)
    asig = execute_read("SELECT * FROM asignaciones")
    unid = execute_read("SELECT * FROM unidades")
    
    if asig:
        df_a = pd.DataFrame(asig)
        pivot = df_a.pivot_table(index='tecnico', columns='estado', values='id', aggfunc='count', fill_value=0).reset_index()
        for c in ['pendiente', 'en_proceso', 'completada', 'solicitado']:
            if c not in pivot.columns: pivot[c] = 0
        st.dataframe(pivot, use_container_width=True, hide_index=True)
        
        c1, c2 = st.columns(2)
        with c1: st.plotly_chart(px.bar(df_a, x='tecnico', color='estado', barmode='group', title="Productividad por Técnico"), use_container_width=True)
        with c2: st.plotly_chart(px.pie(df_a, names='estado', title="Estado Global", hole=0.4), use_container_width=True)

    if unid:
        df_u = pd.DataFrame(unid)
        st.markdown("### 🏗️ Unidades por Proyecto / Lote")
        for lote in df_u['id_lote'].unique():
            with st.expander(f"LOTE: {lote}"):
                st.table(df_u[df_u['id_lote']==lote][['unit_number'] + list(CAMPOS_SERIES.keys())])
        
        st.markdown("### 📋 Registro Maestro")
        st.dataframe(df_u, use_container_width=True, hide_index=True)
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_u.to_excel(writer, index=False, sheet_name='Series')
            if asig: pd.DataFrame(asig).to_excel(writer, index=False, sheet_name='Productividad')
        st.download_button("📥 Descargar Reporte Excel", buffer.getvalue(), f"Reporte_{datetime.now().strftime('%Y%m%d')}.xlsx")

elif menu == "📸 Registro":
    st.markdown('<div class="main-header">REGISTRO DE UNIDADES</div>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        u_num = c1.text_input("Unit Number")
        lote = c1.text_input("Lote")
        campo = c2.selectbox("Campo", list(CAMPOS_SERIES.keys()), format_func=lambda x: CAMPOS_SERIES[x])
        valor = c2.text_input("Serial")
        if st.button("💾 Guardar Datos"):
            execute_write(f"INSERT INTO unidades (unit_number, id_lote, {campo}) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE id_lote=%s, {campo}=%s", (u_num, lote, valor, lote, valor))
            st.success("Guardado correctamente.")
        st.markdown('</div>', unsafe_allow_html=True)

elif menu == "👥 Usuarios":
    st.subheader("Gestión de Usuarios")
    with st.form("u_form"):
        nu, np, nr = st.text_input("Nombre"), st.text_input("Password"), st.selectbox("Rol", ["tecnico", "admin"])
        if st.form_submit_button("Crear Usuario"):
            execute_write("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (nu, np, nr))
            st.success("Usuario Creado.")

time.sleep(60)
st.rerun()
