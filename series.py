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

# --- ESTILOS PROFESIONALES AVANZADOS ---
st.markdown(f"""
<style>
    /* Globales */
    .stApp {{ background-color: {BACKGROUND_COLOR}; }}
    .main-header {{ font-size: 2.5rem; font-weight: 800; color: {CARRIER_BLUE}; text-align: center; margin-bottom: 30px; letter-spacing: -1px; }}
    
    /* Contenedor del Logo (Punto 1) */
    .logo-container {{ text-align: center; background-color: white; padding: 25px; border-radius: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom: 25px; border: 1px solid #e1e8ed; }}
    
    /* Tarjetas de UI Generales */
    .stButton>button {{ width: 100%; border-radius: 8px; height: 3.2em; background-color: {CARRIER_BLUE}; color: white; font-weight: bold; border: none; transition: 0.3s; }}
    .stButton>button:hover {{ background-color: #004080; box-shadow: 0 4px 8px rgba(0,0,0,0.2); }}
    
    /* Estilo de Formularios y Inputs */
    .stTextInput>div>div>input, .stSelectbox>div>div>div {{ border-radius: 8px !important; border: 1px solid #c8d1d9 !important; padding: 10px !important; }}
    
    /* Tarjetas de Registro/Asignación */
    .card {{ background-color: #ffffff; padding: 25px; border-radius: 15px; border-left: 6px solid {CARRIER_BLUE}; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #e1e8ed; }}
    
    /* Recuadro Contable de Tareas (Punto 2) */
    .task-accounting-card {{ background-color: white; padding: 20px; border-radius: 12px; border: 1px solid #e1e8ed; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 15px; }}
    .task-header {{ font-size: 1.3rem; font-weight: 700; color: {CARRIER_BLUE}; border-bottom: 2px solid #e1e8ed; padding-bottom: 10px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; }}
    .task-count {{ background-color: {CARRIER_BLUE}; color: white; padding: 5px 12px; border-radius: 20px; font-size: 0.9rem; }}
    .task-list {{ list-style-type: none; padding: 0; margin: 0; }}
    .task-item {{ padding: 10px 0; border-bottom: 1px solid #f0f2f6; display: flex; justify-content: space-between; }}
    .task-item:last-child {{ border-bottom: none; }}
    .status-badge {{ padding: 3px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: bold; }}
    .status-pendiente {{ background-color: #FFE082; color: #827717; }}
    .status-en_proceso {{ background-color: #BBDEFB; color: #1565C0; }}

    /* Tablas */
    .dataframe {{ border-radius: 10px; overflow: hidden; border: 1px solid #e1e8ed !important; }}
</style>
""", unsafe_allow_html=True)

# ==================== CONEXIÓN CON VALIDACIÓN ====================
def get_db_connection():
    try:
        return mysql.connector.connect(**st.secrets["db"], autocommit=True)
    except Error as e:
        st.error(f"Error de conexión a la base de datos: {e}")
        return None

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
        except Error as e:
            st.error(f"Error de lectura: {e}")
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
        except Error as e:
            return e
    return "No hay conexión"

# ==================== LOGIN ====================
if "login" not in st.session_state:
    st.session_state.update({"login": False, "user": "", "role": ""})

if not st.session_state.login:
    # Logo formal en el login (Punto 1)
    st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}" width="350"></div>', unsafe_allow_html=True)
    st.markdown('<div class="main-header">Acceso al Sistema</div>', unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        u_log = st.text_input("Usuario").strip()
        p_log = st.text_input("Contraseña", type="password").strip()
        
        if st.button("Entrar"):
            if u_log and p_log:
                user = execute_read("SELECT * FROM users WHERE TRIM(LOWER(username)) = TRIM(LOWER(%s)) AND password = %s", (u_log, p_log))
                if user:
                    st.session_state.update({"login": True, "user": user[0]['username'], "role": user[0]['role'].lower()})
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")
            else:
                st.warning("Por favor, ingrese sus credenciales.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==================== SIDEBAR PROFESIONAL ====================
with st.sidebar:
    # Logo formal en Sidebar (Punto 1)
    st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}" width="200"></div>', unsafe_allow_html=True)
    st.write(f"👤 Usuario: **{st.session_state.user}**")
    st.divider()
    
    is_admin = st.session_state.role == "admin"
    menu = st.radio("Menú Principal", ["📸 Registro", "🎯 Asignación", "📊 Dashboard", "👥 Usuarios"]) if is_admin else "🎯 Mis Tareas"

    if st.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

# ==================== SECCIONES ====================

if menu == "👥 Usuarios":
    st.subheader("Gestión de Usuarios")
    with st.form("crear_u"):
        nu = st.text_input("Nuevo Usuario").strip()
        np = st.text_input("Contraseña").strip()
        nr = st.selectbox("Rol", ["tecnico", "admin"])
        if st.form_submit_button("Registrar"):
            if nu and np:
                check = execute_read("SELECT * FROM users WHERE username = %s", (nu,))
                if check: st.warning(f"El usuario '{nu}' ya existe.")
                else:
                    res = execute_write("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (nu, np, nr))
                    if res is True: st.success("Registrado correctamente.")
                    else: st.error(f"Error: {res}")
            else: st.warning("Todos los campos son obligatorios.")

elif menu == "📸 Registro":
    st.markdown('<div class="main-header">REGISTRO TÉCNICO DE UNIDADES</div>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            u_num = st.text_input("Unit Number").strip()
            lote = st.text_input("Lote").strip()
        with c2:
            campo = st.selectbox("Campo", list(CAMPOS_SERIES.keys()), format_func=lambda x: CAMPOS_SERIES[x])
            valor = st.text_input("Serial").strip()
        if st.button("💾 Guardar"):
            if u_num and lote and valor:
                execute_write(f"INSERT INTO unidades (unit_number, id_lote, {campo}) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE id_lote=%s, {campo}=%s", (u_num, lote, valor, lote, valor))
                st.success(f"Unidad {u_num} actualizada.")
            else: st.warning("Faltan datos para el registro.")
        st.markdown('</div>', unsafe_allow_html=True)

elif menu == "🎯 Asignación":
    st.markdown('<div class="main-header">ASIGNACIÓN Y GESTIÓN</div>', unsafe_allow_html=True)
    with st.expander("📌 Asignar Tarea", expanded=True):
        u_db = execute_read("SELECT unit_number, id_lote FROM unidades")
        t_db = execute_read("SELECT username FROM users WHERE role='tecnico'")
        u_list = [f"{x['id_lote']} - {x['unit_number']}" for x in u_db]
        c1, c2, c3 = st.columns(3)
        u_s = c1.selectbox("Unidad", u_list) if u_list else c1.info("No hay unidades.")
        t_s = c2.selectbox("Técnico", [x['username'] for x in t_db]) if t_db else c2.info("No hay técnicos.")
        a_s = c3.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.button("Confirmar") and u_s and t_s:
            execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'pendiente')", (u_s.split(" - ")[1], a_s, t_s))
            st.rerun()

    st.subheader("🗑️ Control de Tareas Activas")
    asig_activas = execute_read("SELECT * FROM asignaciones WHERE estado != 'completada'")
    for a in asig_activas:
        col_t, col_b = st.columns([4, 1])
        col_t.markdown(f'<div class="card"><strong>{a["unidad"]}</strong> | {a["actividad_id"]} | {a["tecnico"]} ({a["estado"]})</div>', unsafe_allow_html=True)
        if col_b.button("Eliminar", key=f"del_{a['id']}"):
            execute_write("DELETE FROM asignaciones WHERE id = %s", (a['id'],))
            st.rerun()

elif menu == "🎯 Mis Tareas":
    st.markdown('<div class="main-header">PANEL DE TAREAS</div>', unsafe_allow_html=True)
    
    mis_t_raw = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado!='completada'", (st.session_state.user,))
    
    if not mis_t_raw:
        st.info("No tienes tareas pendientes.")
    else:
        df_mis_t = pd.DataFrame(mis_t_raw)
        
        # --- RECUADRO CONTABLE DE TAREAS (Punto 2) ---
        # Agrupamos tareas por unidad para contabilizar
        unidades_tareas = df_mis_t['unidad'].unique()
        
        for unidad in unidades_tareas:
            tareas_unidad = df_mis_t[df_mis_t['unidad'] == unidad]
            num_tareas = len(tareas_unidad)
            
            with st.container():
                st.markdown(f"""
                <div class="task-accounting-card">
                    <div class="task-header">
                        <span>📦 Unidad: {unidad}</span>
                        <span class="task-count">{num_tareas} Actividades</span>
                    </div>
                    <ul class="task-list">
                """, unsafe_allow_html=True)
                
                # Iterar sobre las tareas de esta unidad
                for _, task in tareas_unidad.iterrows():
                    status_class = f"status-{task['estado']}"
                    st.markdown(f"""
                        <li class="task-item">
                            <span>🛠️ {task['actividad_id']}</span>
                            <span class="status-badge {status_class}">{task['estado'].upper()}</span>
                        </li>
                    """, unsafe_allow_html=True)
                
                st.markdown("</ul>", unsafe_allow_html=True)
                
                # Acciones (Manteniendo la funcionalidad original dentro del nuevo diseño)
                # Usamos expansor para las acciones de cada tarea específica
                for _, task in tareas_unidad.iterrows():
                    with st.expander(f"Acciones para {task['actividad_id']} (ID: {task['id']})", expanded=False):
                        if task['estado'] == 'pendiente':
                            if st.button(f"🚀 Iniciar #{task['id']}", key=f"start_{task['id']}"):
                                execute_write("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=NOW() WHERE id=%s", (task['id'],))
                                st.rerun()
                        elif task['actividad_id'] == "toma de series":
                            with st.form(f"f_{task['id']}"):
                                res = {k: st.text_input(v) for k, v in CAMPOS_SERIES.items()}
                                if st.form_submit_button("Guardar y Finalizar"):
                                    set_q = ", ".join([f"{k}=%s" for k in res.keys()])
                                    execute_write(f"UPDATE unidades SET {set_q} WHERE unit_number=%s", list(res.values()) + [task['unidad']])
                                    execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW() WHERE id=%s", (task['id'],))
                                    st.rerun()
                        else:
                            if st.button(f"✅ Completar #{task['id']}", key=f"comp_{task['id']}"):
                                execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW() WHERE id=%s", (task['id'],))
                                st.rerun()
                
                st.markdown("</div>", unsafe_allow_html=True)

elif menu == "📊 Dashboard":
    st.markdown('<div class="main-header">DASHBOARD DE PRODUCTIVIDAD</div>', unsafe_allow_html=True)
    asig = execute_read("SELECT tecnico, estado, id FROM asignaciones")
    unid = execute_read("SELECT * FROM unidades")
    
    if asig:
        df_a = pd.DataFrame(asig)
        pivot = df_a.pivot_table(index='tecnico', columns='estado', values='id', aggfunc='count', fill_value=0).reset_index()
        for c in ['pendiente', 'en_proceso', 'completada']:
            if c not in pivot.columns: pivot[c] = 0
        
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### Resumen Numérico de Tareas")
        st.dataframe(pivot, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1: st.plotly_chart(px.bar(df_a, x='tecnico', color='estado', barmode='group', title="Carga por Técnico", color_discrete_sequence=px.colors.qualitative.Bold), use_container_width=True)
        with c2: st.plotly_chart(px.pie(df_a, names='estado', title="Estado Global", hole=0.4, color_discrete_sequence=px.colors.qualitative.Safe), use_container_width=True)

    if unid:
        df_u = pd.DataFrame(unid)
        
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 🏗️ Unidades por Proyecto / Lote")
        for lote in df_u['id_lote'].unique():
            with st.expander(f"LOTE: {lote}"):
                st.table(df_u[df_u['id_lote']==lote][['unit_number'] + list(CAMPOS_SERIES.keys())])
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 📋 Registro Maestro General")
        st.dataframe(df_u, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_u.to_excel(writer, index=False, sheet_name='Series')
            if asig: pd.DataFrame(asig).to_excel(writer, index=False, sheet_name='Productividad')
        st.download_button("📥 Excel", buffer.getvalue(), f"Reporte_Carrier_{datetime.now().strftime('%Y%m%d')}.xlsx")

    time.sleep(60)
    st.rerun()
