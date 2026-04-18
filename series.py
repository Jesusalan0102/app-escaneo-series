import streamlit as st
import pandas as pd
import mysql.connector
from mysql.connector import Error
import plotly.express as px
from datetime import datetime
import io
from streamlit_autorefresh import st_autorefresh

# ==================== CONFIGURACIÓN ====================
st.set_page_config(page_title="Carrier Transicold - Panel de Gestión", layout="wide")

# Actualización automática cada 30 segundos
st_autorefresh(interval=30 * 1000, key="global_refresh")

CARRIER_BLUE = "#002B5B"
BACKGROUND_COLOR = "#F4F7F9"
LOGO_URL = "https://raw.githubusercontent.com/Jesusalan0102/app-escaneo-series/main/carrierlogo2.jpeg.jpg"

CAMPOS_SERIES = {
    "vin_number": "VIN Number",
    "reefer_serial": "Reefer Serial",
    "reefer_model": "Reefer Model",
    "evaporator_serial_mjs11": "Evaporator Serial MJS11",
    "evaporator_serial_mjd22": "Evaporator Serial MJD22",
    "engine_serial": "Engine",
    "compressor_serial": "Compressor",
    "generator_serial": "Generator",
    "battery_charger_serial": "Battery Charger"
}

ACTIVIDADES_CARRIER = [
    "Cableado", "Cerrado", "Corriendo", "Inspección", "Pretrip", 
    "Programación", "Soldadura en sitio", "Vacíos", "Accesorios", 
    "Toma de valores", "Evidencia", "Standby", "Toma de series"
]

# --- FUNCIÓN DE SONIDO ---
def reproducir_sonido():
    audio_html = """
        <audio autoplay>
            <source src="https://raw.githubusercontent.com/rafaelEscalante/notification-sounds/master/pings/ping-8.mp3" type="audio/mp3">
        </audio>
    """
    st.markdown(audio_html, unsafe_allow_html=True)

# --- ESTILOS CSS ---
st.markdown(f"""
<style>
    .stApp {{ background-color: {BACKGROUND_COLOR}; }}
    .main-header {{ font-size: 2.5rem; font-weight: 800; color: {CARRIER_BLUE}; text-align: center; margin-bottom: 30px; }}
    .logo-container {{ text-align: center; background-color: white; padding: 25px; border-radius: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom: 25px; }}
    .card {{ background-color: #ffffff; padding: 25px; border-radius: 15px; border-left: 6px solid {CARRIER_BLUE}; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #e1e8ed; }}
    .task-accounting-card {{ background-color: white; padding: 20px; border-radius: 12px; border: 1px solid #e1e8ed; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 15px; }}
    .task-header {{ font-size: 1.3rem; font-weight: 700; color: {CARRIER_BLUE}; border-bottom: 2px solid #e1e8ed; padding-bottom: 10px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; }}
    .task-count {{ background-color: {CARRIER_BLUE}; color: white; padding: 5px 12px; border-radius: 20px; font-size: 0.9rem; }}
</style>
""", unsafe_allow_html=True)

# ==================== BASE DE DATOS ====================
def get_db_connection():
    try: return mysql.connector.connect(**st.secrets["db"], autocommit=True)
    except: return None

def execute_read(query, params=None):
    conn = get_db_connection()
    if conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, params or ())
        res = cur.fetchall()
        cur.close(); conn.close()
        return res
    return []

def execute_write(query, params=None):
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(query, params or ())
            cur.close(); conn.close()
            return True
        except Exception as e: return e
    return "Error"

# ==================== LOGIN ====================
if "login" not in st.session_state:
    st.session_state.update({"login": False, "user": "", "role": "", "last_task_count": 0})

if not st.session_state.login:
    st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}" width="350"></div>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        u_log = st.text_input("Usuario").strip()
        p_log = st.text_input("Contraseña", type="password").strip()
        if st.button("Ingresar al Sistema"):
            user = execute_read("SELECT * FROM users WHERE username = %s AND password = %s", (u_log, p_log))
            if user:
                st.session_state.update({"login": True, "user": user[0]['username'], "role": user[0]['role'].lower()})
                st.rerun()
            else: st.error("Credenciales incorrectas")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==================== SIDEBAR ====================
with st.sidebar:
    st.image(LOGO_URL, width=200)
    st.write(f"👤 Usuario: **{st.session_state.user}**")
    st.write(f"🔑 Rol: **{st.session_state.role.capitalize()}**")
    st.divider()
    is_admin = st.session_state.role == "admin"
    if is_admin:
        menu = st.radio("Menú Principal", ["📸 Registro de Unidades", "🎯 Asignación y Autorización", "📊 Dashboard de Productividad", "👥 Gestión de Usuarios"])
    else:
        menu = st.radio("Menú Técnico", ["🎯 Mis Tareas Activas", "🔔 Solicitar Nueva Actividad"])

    if st.button("Cerrar Sesión"):
        st.session_state.clear(); st.rerun()

# ==================== SECCIONES ====================

if menu == "🎯 Mis Tareas Activas":
    st.markdown('<div class="main-header">Panel de Tareas del Técnico</div>', unsafe_allow_html=True)
    
    # --- LÓGICA DE NOTIFICACIÓN SONORA ---
    check_tasks = execute_read("SELECT id FROM asignaciones WHERE tecnico=%s AND estado='pendiente'", (st.session_state.user,))
    current_count = len(check_tasks)
    if current_count > st.session_state.last_task_count:
        reproducir_sonido()
        st.toast("¡Tienes una nueva actividad autorizada!", icon="🔔")
        st.success("Se ha aprobado una de tus solicitudes. Revisa el listado abajo.")
    st.session_state.last_task_count = current_count

    mis_t_raw = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado NOT IN ('completada', 'solicitado')", (st.session_state.user,))
    
    if not mis_t_raw:
        st.info("No tienes tareas autorizadas en este momento.")
    else:
        df_t = pd.DataFrame(mis_t_raw)
        # --- RECUADRO CONTABLE POR UNIDAD ---
        for unidad in df_t['unidad'].unique():
            tareas_u = df_t[df_t['unidad'] == unidad]
            st.markdown(f"""
            <div class="task-accounting-card">
                <div class="task-header">
                    <span>📦 Unidad: {unidad}</span>
                    <span class="task-count">{len(tareas_u)} Actividades Pendientes/En Proceso</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            for _, task in tareas_u.iterrows():
                with st.expander(f"🛠️ {task['actividad_id']} - Estado: {task['estado'].capitalize()}"):
                    if task['estado'] == 'pendiente':
                        if st.button(f"🚀 Iniciar Actividad #{task['id']}", key=f"in_{task['id']}"):
                            execute_write("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=NOW() WHERE id=%s", (task['id'],))
                            st.rerun()
                    elif task['estado'] == 'en_proceso':
                        if task['actividad_id'].lower() == "toma de series":
                            with st.form(f"f_series_{task['id']}"):
                                st.subheader("Registro de Series Técnicas")
                                res = {k: st.text_input(v, key=f"ser_{k}_{task['id']}") for k, v in CAMPOS_SERIES.items()}
                                if st.form_submit_button("Guardar y Finalizar Actividad"):
                                    set_q = ", ".join([f"{k}=%s" for k in res.keys()])
                                    execute_write(f"UPDATE unidades SET {set_q} WHERE unit_number=%s", list(res.values()) + [task['unidad']])
                                    execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW() WHERE id=%s", (task['id'],))
                                    st.rerun()
                        else:
                            if st.button(f"✅ Finalizar Actividad #{task['id']}", key=f"fin_{task['id']}"):
                                execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW() WHERE id=%s", (task['id'],))
                                st.rerun()

elif menu == "🔔 Solicitar Nueva Actividad":
    st.markdown('<div class="main-header">Solicitar Trabajo</div>', unsafe_allow_html=True)
    u_db = execute_read("SELECT unit_number, id_lote FROM unidades")
    u_list = [f"{x['id_lote']} - {x['unit_number']}" for x in u_db]
    with st.form("sol_tec"):
        u_sel = st.selectbox("Seleccione la Unidad", u_list)
        a_sel = st.selectbox("Actividad a Realizar", ACTIVIDADES_CARRIER)
        if st.form_submit_button("Enviar Solicitud al Administrador"):
            execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'solicitado')", (u_sel.split(" - ")[1], a_sel, st.session_state.user))
            st.success("Solicitud enviada exitosamente. Se te notificará cuando sea aprobada.")

elif menu == "🎯 Asignación y Autorización":
    st.markdown('<div class="main-header">Gestión de Autorizaciones</div>', unsafe_allow_html=True)
    
    sols = execute_read("SELECT * FROM asignaciones WHERE estado='solicitado'")
    if sols:
        st.subheader("🔔 Solicitudes Entrantes")
        for s in sols:
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.markdown(f'<div class="card">El técnico <b>{s["tecnico"]}</b> solicita trabajar en <b>{s["unidad"]}</b> (Actividad: {s["actividad_id"]})</div>', unsafe_allow_html=True)
            if c2.button("✅ Aprobar", key=f"ap_{s['id']}"):
                execute_write("UPDATE asignaciones SET estado='pendiente' WHERE id=%s", (s['id'],)); st.rerun()
            if c3.button("❌ Rechazar", key=f"re_{s['id']}"):
                execute_write("DELETE FROM asignaciones WHERE id=%s", (s['id'],)); st.rerun()
    
    st.divider()
    with st.expander("➕ Asignación Directa de Tareas"):
        u_db = execute_read("SELECT unit_number, id_lote FROM unidades")
        t_db = execute_read("SELECT username FROM users WHERE role='tecnico'")
        col1, col2, col3 = st.columns(3)
        u_m = col1.selectbox("Unidad", [f"{x['id_lote']} - {x['unit_number']}" for x in u_db])
        t_m = col2.selectbox("Técnico Responsable", [x['username'] for x in t_db])
        a_m = col3.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.button("Asignar Actividad Ahora"):
            execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'pendiente')", (u_m.split(" - ")[1], a_m, t_m))
            st.rerun()

elif menu == "📊 Dashboard de Productividad":
    st.markdown('<div class="main-header">Métricas de Rendimiento</div>', unsafe_allow_html=True)
    asig = execute_read("SELECT * FROM asignaciones")
    unid = execute_read("SELECT * FROM unidades")
    
    if asig:
        df_a = pd.DataFrame(asig)
        # Resumen contable para Admin
        st.subheader("Resumen de Actividades por Técnico")
        resumen = df_a.groupby(['tecnico', 'estado']).size().unstack(fill_value=0).reset_index()
        st.dataframe(resumen, use_container_width=True, hide_index=True)

        c1, c2 = st.columns(2)
        with c1: st.plotly_chart(px.bar(df_a, x='tecnico', color='estado', barmode='group', title="Tareas por Estado y Técnico"), use_container_width=True)
        with c2: st.plotly_chart(px.pie(df_a, names='estado', title="Distribución de Estados Globales", hole=0.4), use_container_width=True)

    if unid:
        df_u = pd.DataFrame(unid)
        st.markdown("### 🏗️ Unidades por Lotes")
        for lote in df_u['id_lote'].unique():
            with st.expander(f"Visualizar Lote: {lote}"):
                st.table(df_u[df_u['id_lote']==lote][['unit_number'] + list(CAMPOS_SERIES.keys())])
        
        # Botón de Exportación
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_u.to_excel(writer, index=False, sheet_name='Series')
            if asig: df_a.to_excel(writer, index=False, sheet_name='Actividades')
        st.download_button("📥 Descargar Reporte en Excel", buffer.getvalue(), f"Reporte_Carrier_{datetime.now().strftime('%Y%m%d')}.xlsx")

elif menu == "📸 Registro de Unidades":
    st.markdown('<div class="main-header">Registro de Series y Unidades</div>', unsafe_allow_html=True)
    with st.form("reg_master"):
        c1, c2 = st.columns(2)
        un_i = c1.text_input("Número de Unidad (Unit Number)")
        lt_i = c1.text_input("Identificador de Lote")
        cp_i = c2.selectbox("Campo a Actualizar", list(CAMPOS_SERIES.keys()), format_func=lambda x: CAMPOS_SERIES[x])
        vl_i = c2.text_input("Valor del Serial")
        if st.form_submit_button("Guardar Cambios"):
            execute_write(f"INSERT INTO unidades (unit_number, id_lote, {cp_i}) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE id_lote=%s, {cp_i}=%s", (un_i, lt_i, vl_i, lt_i, vl_i))
            st.success("Información actualizada exitosamente.")

elif menu == "👥 Gestión de Usuarios":
    st.subheader("Registro de Nuevo Personal")
    with st.form("user_form"):
        nu, np, nr = st.text_input("Nombre de Usuario"), st.text_input("Contraseña"), st.selectbox("Rol Asignado", ["tecnico", "admin"])
        if st.form_submit_button("Crear Usuario"):
            execute_write("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (nu, np, nr))
            st.success(f"Usuario {nu} creado correctamente.")
