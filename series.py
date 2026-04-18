import streamlit as st
import pandas as pd
import mysql.connector
from mysql.connector import Error
import plotly.express as px
from datetime import datetime
import io
import time
from streamlit_autorefresh import st_autorefresh

# ==================== CONFIGURACIÓN ====================
st.set_page_config(page_title="Carrier Transicold - Sistema Integral", layout="wide")

# Autorefresh cada 30 segundos para mantener datos vivos y disparar alarmas
st_autorefresh(interval=30 * 1000, key="global_refresh")

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

# --- FUNCIÓN SONIDO ---
def play_notification_sound():
    audio_html = """
        <audio autoplay>
            <source src="https://raw.githubusercontent.com/rafaelEscalante/notification-sounds/master/pings/ping-8.mp3" type="audio/mp3">
        </audio>
    """
    st.markdown(audio_html, unsafe_allow_html=True)

# --- ESTILOS ---
st.markdown(f"""
<style>
    .stApp {{ background-color: {BACKGROUND_COLOR}; }}
    .main-header {{ font-size: 2.5rem; font-weight: 800; color: {CARRIER_BLUE}; text-align: center; margin-bottom: 30px; }}
    .logo-container {{ text-align: center; background-color: white; padding: 25px; border-radius: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom: 25px; border: 1px solid #e1e8ed; }}
    .stButton>button {{ width: 100%; border-radius: 8px; height: 3.2em; background-color: {CARRIER_BLUE}; color: white; font-weight: bold; border: none; }}
    .card {{ background-color: #ffffff; padding: 25px; border-radius: 15px; border-left: 6px solid {CARRIER_BLUE}; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #e1e8ed; }}
    .task-accounting-card {{ background-color: white; padding: 20px; border-radius: 12px; border: 1px solid #e1e8ed; margin-bottom: 15px; }}
    .task-header {{ font-size: 1.3rem; font-weight: 700; color: {CARRIER_BLUE}; border-bottom: 2px solid #e1e8ed; padding-bottom: 10px; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; }}
    .task-count {{ background-color: {CARRIER_BLUE}; color: white; padding: 5px 12px; border-radius: 20px; font-size: 0.9rem; }}
</style>
""", unsafe_allow_html=True)

# ==================== DB ====================
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
    st.session_state.update({"login": False, "user": "", "role": ""})

if not st.session_state.login:
    st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}" width="350"></div>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        u_log = st.text_input("Usuario")
        p_log = st.text_input("Contraseña", type="password")
        if st.button("Acceder"):
            user = execute_read("SELECT * FROM users WHERE username = %s AND password = %s", (u_log, p_log))
            if user:
                st.session_state.update({"login": True, "user": user[0]['username'], "role": user[0]['role'].lower()})
                st.rerun()
            else: st.error("Usuario/Contraseña incorrectos")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==================== SIDEBAR ====================
with st.sidebar:
    st.markdown(f'<div class="logo-container"><img src="{LOGO_URL}" width="180"></div>', unsafe_allow_html=True)
    st.write(f"💼 Perfil: **{st.session_state.user.upper()}**")
    st.divider()
    is_admin = st.session_state.role == "admin"
    menu = st.radio("Navegación", ["📸 Registro", "🎯 Asignación", "📊 Dashboard", "👥 Usuarios"]) if is_admin else st.radio("Navegación", ["🎯 Mis Tareas", "🔔 Solicitar Unidad"])
    if st.button("Cerrar Sesión"):
        st.session_state.clear(); st.rerun()

# ==================== SECCIONES ====================

if menu == "🎯 Mis Tareas":
    st.markdown('<div class="main-header">MIS TAREAS AUTORIZADAS</div>', unsafe_allow_html=True)
    
    # Alarma sonora para nuevas autorizaciones
    check_new = execute_read("SELECT id FROM asignaciones WHERE tecnico=%s AND estado='pendiente'", (st.session_state.user,))
    if check_new:
        play_notification_sound()
        st.toast("¡Nueva tarea autorizada!", icon="🔔")

    mis_t = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado NOT IN ('completada', 'solicitado')", (st.session_state.user,))
    if not mis_t:
        st.info("Sin tareas pendientes por ahora.")
    else:
        df_t = pd.DataFrame(mis_t)
        for unidad in df_t['unidad'].unique():
            tareas_u = df_t[df_t['unidad'] == unidad]
            st.markdown(f'<div class="task-accounting-card"><div class="task-header"><span>📦 Unidad: {unidad}</span><span class="task-count">{len(tareas_u)} Actividades</span></div></div>', unsafe_allow_html=True)
            for _, task in tareas_u.iterrows():
                with st.expander(f"🛠️ {task['actividad_id'].upper()}"):
                    if task['estado'] == 'pendiente':
                        if st.button(f"🚀 Iniciar #{task['id']}", key=f"start_{task['id']}"):
                            execute_write("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=NOW() WHERE id=%s", (task['id'],))
                            st.rerun()
                    elif task['estado'] == 'en_proceso':
                        if task['actividad_id'] == "toma de series":
                            with st.form(f"form_ser_{task['id']}"):
                                data = {k: st.text_input(v, key=f"inp_{k}_{task['id']}") for k, v in CAMPOS_SERIES.items()}
                                if st.form_submit_button("💾 Guardar Series y Finalizar"):
                                    set_q = ", ".join([f"{k}=%s" for k in data.keys()])
                                    execute_write(f"UPDATE unidades SET {set_q} WHERE unit_number=%s", list(data.values()) + [task['unidad']])
                                    execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW() WHERE id=%s", (task['id'],))
                                    st.rerun()
                        else:
                            if st.button(f"✅ Finalizar Actividad #{task['id']}", key=f"end_{task['id']}"):
                                execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW() WHERE id=%s", (task['id'],))
                                st.rerun()

elif menu == "🔔 Solicitar Unidad":
    st.markdown('<div class="main-header">SOLICITUD DE TRABAJO</div>', unsafe_allow_html=True)
    unidades = execute_read("SELECT unit_number, id_lote FROM unidades")
    u_list = [f"{x['id_lote']} - {x['unit_number']}" for x in unidades]
    with st.form("sol_form"):
        u_sel = st.selectbox("Unidad", u_list)
        a_sel = st.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.form_submit_button("Enviar Solicitud"):
            execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'solicitado')", (u_sel.split(" - ")[1], a_sel, st.session_state.user))
            st.success("Solicitud enviada al Administrador.")

elif menu == "🎯 Asignación":
    st.markdown('<div class="main-header">PANEL DE AUTORIZACIÓN</div>', unsafe_allow_html=True)
    sols = execute_read("SELECT * FROM asignaciones WHERE estado='solicitado'")
    if sols:
        for s in sols:
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.markdown(f'<div class="card"><strong>{s["tecnico"]}</strong> solicita <strong>{s["unidad"]}</strong> para <strong>{s["actividad_id"]}</strong></div>', unsafe_allow_html=True)
            if c2.button("✅ Autorizar", key=f"ok_{s['id']}"):
                execute_write("UPDATE asignaciones SET estado='pendiente' WHERE id=%s", (s['id'],)); st.rerun()
            if c3.button("❌ Rechazar", key=f"no_{s['id']}"):
                execute_write("DELETE FROM asignaciones WHERE id=%s", (s['id'],)); st.rerun()
    
    st.divider()
    with st.expander("➕ Asignación Manual"):
        u_db = execute_read("SELECT unit_number, id_lote FROM unidades")
        t_db = execute_read("SELECT username FROM users WHERE role='tecnico'")
        col1, col2, col3 = st.columns(3)
        u_m = col1.selectbox("Unidad", [f"{x['id_lote']} - {x['unit_number']}" for x in u_db])
        t_m = col2.selectbox("Técnico", [x['username'] for x in t_db])
        a_m = col3.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.button("Asignar"):
            execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'pendiente')", (u_m.split(" - ")[1], a_m, t_m))
            st.rerun()

elif menu == "📊 Dashboard":
    st.markdown('<div class="main-header">DASHBOARD DE PRODUCTIVIDAD</div>', unsafe_allow_html=True)
    asig = execute_read("SELECT * FROM asignaciones")
    unid = execute_read("SELECT * FROM unidades")
    
    if asig:
        df_a = pd.DataFrame(asig)
        c1, c2 = st.columns(2)
        with c1: st.plotly_chart(px.bar(df_a, x='tecnico', color='estado', barmode='group', title="Tareas por Técnico"), use_container_width=True)
        with c2: st.plotly_chart(px.pie(df_a, names='estado', title="Estado Global", hole=0.4), use_container_width=True)
        
    if unid:
        df_u = pd.DataFrame(unid)
        st.markdown("### 🏗️ Lotes y Unidades")
        for lote in df_u['id_lote'].unique():
            with st.expander(f"LOTE: {lote}"):
                st.table(df_u[df_u['id_lote']==lote][['unit_number'] + list(CAMPOS_SERIES.keys())])
        
        st.markdown("### 📋 Registro General")
        st.dataframe(df_u, use_container_width=True, hide_index=True)
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_u.to_excel(writer, index=False, sheet_name='Series')
            if asig: pd.DataFrame(asig).to_excel(writer, index=False, sheet_name='Actividades')
        st.download_button("📥 Exportar Reporte Excel", buffer.getvalue(), f"Carrier_Report_{datetime.now().strftime('%Y%m%d')}.xlsx")

elif menu == "📸 Registro":
    st.markdown('<div class="main-header">REGISTRO DE UNIDADES</div>', unsafe_allow_html=True)
    with st.form("reg_u"):
        c1, c2 = st.columns(2)
        un_i = c1.text_input("Unit Number")
        lt_i = c1.text_input("Lote")
        cp_i = c2.selectbox("Campo", list(CAMPOS_SERIES.keys()), format_func=lambda x: CAMPOS_SERIES[x])
        vl_i = c2.text_input("Valor Serial")
        if st.form_submit_button("Guardar Unidad"):
            execute_write(f"INSERT INTO unidades (unit_number, id_lote, {cp_i}) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE id_lote=%s, {cp_i}=%s", (un_i, lt_i, vl_i, lt_i, vl_i))
            st.success("Guardado correctamente.")

elif menu == "👥 Usuarios":
    st.subheader("Control de Usuarios")
    with st.form("new_user"):
        nu, np, nr = st.text_input("Nombre"), st.text_input("Pass"), st.selectbox("Rol", ["tecnico", "admin"])
        if st.form_submit_button("Crear"):
            execute_write("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (nu, np, nr))
            st.success("Usuario creado")
