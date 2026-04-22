import streamlit as st
import pandas as pd
import mysql.connector
import plotly.express as px
from datetime import datetime
import io
import pytz 
import zipfile
from streamlit_autorefresh import st_autorefresh

# ==================== CONFIGURACIÓN INICIAL ====================
st.set_page_config(page_title="Carrier Transicold - Panel de Control", layout="wide")
st_autorefresh(interval=30 * 1000, key="global_refresh")

tijuana_tz = pytz.timezone('America/Tijuana')
ahora_tj = datetime.now(tijuana_tz)
fecha_hoy = ahora_tj.strftime('%Y-%m-%d')
hora_actual = ahora_tj.strftime('%H:%M:%S')

CARRIER_BLUE = "#002B5B"
LOGO_URL = "https://raw.githubusercontent.com/Jesusalan0102/app-escaneo-series/main/carrierlogo2.jpeg.jpg"
SOUND_URL = "https://raw.githubusercontent.com/rafaelEscalante/notification-sounds/master/pings/ping-8.mp3"

CAMPOS_SERIES = {
    "vin_number": "VIN Number", 
    "reefer_serial": "Serie del Reefer",
    "reefer_model": "Modelo del Reefer", 
    "evaporator_serial_mjs11": "Evaporador MJS11",
    "evaporator_serial_mjd22": "Evaporador MJD22", 
    "engine_serial": "Motor",
    "compressor_serial": "Compresor", 
    "generator_serial": "Generador",
    "battery_charger_serial": "Cargador de Batería"
}

ACTIVIDADES_CARRIER = [
    "Cableado", "Programación", "Soldadura", "Check de fugas", 
    "Vacío", "Cerrado", "Pre-viaje", "Horas Corridas", 
    "Standby", "GPS", "Run", "Corriendo", "Inspección", 
    "Accesorios", "Toma de Valores", "Evidencia", "Toma de Series"
]

# Estilos CSS Mejorados
st.markdown(f"""
<style>
    .stApp {{ background-color: #F8F9FA; }}
    .main-header {{ 
        font-size: 2rem; font-weight: 700; color: {CARRIER_BLUE}; 
        border-bottom: 3px solid {CARRIER_BLUE}; padding-bottom: 10px; margin-bottom: 25px; 
    }}
    .section-title {{ 
        font-size: 1.2rem; font-weight: 600; color: #333; 
        margin-top: 20px; border-left: 5px solid {CARRIER_BLUE}; 
        padding-left: 15px; margin-bottom: 15px; 
    }}
    .stButton>button {{ width: 100%; border-radius: 5px; height: 3em; font-weight: bold; }}
    .time-badge {{ 
        background-color: {CARRIER_BLUE}; color: white; 
        padding: 5px 15px; border-radius: 20px; font-size: 0.9rem; float: right; 
    }}
</style>
""", unsafe_allow_html=True)

# ==================== FUNCIONES DE BASE DE DATOS ====================
def get_db_connection():
    try: 
        return mysql.connector.connect(**st.secrets["db"], autocommit=True)
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

def execute_read(query, params=None):
    conn = get_db_connection()
    if conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(query, params or ())
        res = cur.fetchall()
        cur.close()
        conn.close()
        return res
    return []

def execute_write(query, params=None):
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(query, params or ())
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            st.error(f"Error en la base de datos: {e}")
            return False
    return False

# ==================== LÓGICA DE SESIÓN ====================
if "login" not in st.session_state:
    st.session_state.update({"login": False, "user": "", "role": "", "last_count": 0})

if not st.session_state.login:
    st.markdown(f'<div style="text-align: center; padding: 50px;"><img src="{LOGO_URL}" width="400"></div>', unsafe_allow_html=True)
    col_l, col_c, col_r = st.columns([1,1.5,1])
    with col_c:
        with st.form("login_form"):
            st.markdown(f"<h3 style='text-align:center; color:{CARRIER_BLUE}'>Panel de Acceso</h3>", unsafe_allow_html=True)
            u_log = st.text_input("Usuario")
            p_log = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar al Sistema"):
                user = execute_read("SELECT * FROM users WHERE username=%s AND password=%s", (u_log.strip(), p_log.strip()))
                if user:
                    st.session_state.update({"login": True, "user": user[0]['username'], "role": user[0]['role'].lower()})
                    st.rerun()
                else: st.error("Credenciales incorrectas")
    st.stop()

# ==================== NAVEGACIÓN SIDEBAR ====================
with st.sidebar:
    st.image(LOGO_URL, width=200)
    st.write(f"👤 **{st.session_state.user.upper()}** ({st.session_state.role})")
    st.markdown("---")
    if st.session_state.role == "admin":
        menu = st.radio("MENÚ", ["📊 Dashboard Ejecutivo", "🎯 Control de Asignaciones", "📸 Registro de Unidades", "👥 Gestión de Usuarios"])
    else:
        menu = st.radio("TRABAJO", ["🎯 Mis Tareas", "🔔 Nueva Solicitud"])
    
    if st.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

# ==================== VISTAS ====================

if menu == "📊 Dashboard Ejecutivo":
    st.markdown(f'<div class="time-badge">{hora_actual}</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-header">Panel Operativo</div>', unsafe_allow_html=True)
    
    asig = execute_read("SELECT * FROM asignaciones")
    unid = execute_read("SELECT * FROM unidades")
    
    if asig:
        df_a = pd.DataFrame(asig)
        st.plotly_chart(px.bar(df_a, x='tecnico', color='estado', title="Carga por Técnico", barmode='group'), use_container_width=True)

    st.markdown('<div class="section-title">Estatus de Proceso</div>', unsafe_allow_html=True)
    if unid:
        completas = {(r['unidad'], r['actividad_id']) for r in execute_read("SELECT unidad, actividad_id FROM asignaciones WHERE estado='completada'")}
        status_data = []
        for u in unid:
            row = {"LOTE": u['id_lote'], "UNIDAD": u['unit_number']}
            for act in ACTIVIDADES_CARRIER:
                row[act] = "✅" if (u['unit_number'], act) in completas else ""
            status_data.append(row)
        st.dataframe(pd.DataFrame(status_data), use_container_width=True, hide_index=True)

elif menu == "🎯 Control de Asignaciones":
    st.markdown('<div class="main-header">Gestión de Órdenes</div>', unsafe_allow_html=True)
    sols = execute_read("SELECT * FROM asignaciones WHERE estado='solicitado'")
    
    if len(sols) > st.session_state.last_count:
        st.markdown(f'<audio autoplay><source src="{SOUND_URL}" type="audio/mp3"></audio>', unsafe_allow_html=True)
    st.session_state.last_count = len(sols)

    for s in sols:
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"**{s['tecnico']}** solicita **{s['actividad_id']}** para la unidad **{s['unidad']}**")
            if c2.button("✅ Aprobar", key=f"ap_{s['id']}"):
                execute_write("UPDATE asignaciones SET estado='pendiente' WHERE id=%s", (s['id'],))
                st.rerun()
            if c3.button("🗑️ Borrar", key=f"de_{s['id']}"):
                execute_write("DELETE FROM asignaciones WHERE id=%s", (s['id'],))
                st.rerun()

elif menu == "🎯 Mis Tareas":
    st.markdown('<div class="main-header">Mis Actividades</div>', unsafe_allow_html=True)
    tareas = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado IN ('pendiente', 'en_proceso')", (st.session_state.user,))
    
    if not tareas: st.info("No tienes tareas pendientes.")
    
    for t in tareas:
        with st.expander(f"Unidad: {t['unidad']} - Actividad: {t['actividad_id']}", expanded=True):
            if t['estado'] == 'pendiente':
                if st.button("▶️ Iniciar Trabajo", key=f"st_{t['id']}"):
                    execute_write("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                    st.rerun()
            else:
                if t['actividad_id'].lower() == "evidencia":
                    archivos = st.file_uploader("Subir fotos (Max 50)", accept_multiple_files=True, type=['jpg','jpeg','png'])
                    if st.button("Finalizar y Guardar Evidencias", key=f"ev_{t['id']}"):
                        if not archivos:
                            st.warning("⚠️ Debes subir al menos una foto.")
                        else:
                            conn = get_db_connection()
                            cur = conn.cursor()
                            try:
                                bar = st.progress(0)
                                for i, arc in enumerate(archivos):
                                    cur.execute("INSERT INTO evidencias (unit_number, nombre_archivo, contenido, tecnico) VALUES (%s,%s,%s,%s)", 
                                               (t['unidad'], arc.name, arc.read(), st.session_state.user))
                                    bar.progress((i+1)/len(archivos))
                                cur.execute("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                                st.success("¡Evidencias guardadas!")
                                st.rerun()
                            finally:
                                cur.close()
                                conn.close()
                
                elif t['actividad_id'].lower() == "toma de series":
                    with st.form(f"f_ser_{t['id']}"):
                        res = {k: st.text_input(v) for k, v in CAMPOS_SERIES.items()}
                        if st.form_submit_button("Guardar Datos"):
                            sets = ", ".join([f"{k}=%s" for k in res.keys()])
                            execute_write(f"UPDATE unidades SET {sets} WHERE unit_number=%s", list(res.values()) + [t['unidad']])
                            execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                            st.rerun()
                else:
                    if st.button("✅ Terminar Actividad"):
                        execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                        st.rerun()

elif menu == "🔔 Nueva Solicitud":
    st.markdown('<div class="main-header">Nueva Solicitud</div>', unsafe_allow_html=True)
    unid_db = execute_read("SELECT unit_number, id_lote FROM unidades")
    evidencias_db = {row['unit_number'] for row in execute_read("SELECT DISTINCT unit_number FROM evidencias")}
    
    with st.form("sol_form"):
        # Filtro visual en el selectbox
        opciones = []
        for x in unid_db:
            marca = " 📸 (Con Evidencia)" if x['unit_number'] in evidencias_db else " ⭕ (Sin Evidencia)"
            opciones.append(f"{x['id_lote']} - {x['unit_number']}{marca}")
            
        u_sel = st.selectbox("Seleccionar Unidad", opciones)
        a_sel = st.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.form_submit_button("Enviar Solicitud"):
            unit_clean = u_sel.split(" - ")[1].split(" ")[0] # Extrae solo el número económico
            execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s,%s,%s,'solicitado')", 
                         (unit_clean, a_sel, st.session_state.user))
            st.toast("Solicitud enviada correctamente")

elif menu == "📸 Registro de Unidades":
    st.markdown('<div class="main-header">Registro Maestro</div>', unsafe_allow_html=True)
    with st.form("reg_u"):
        c1, c2 = st.columns(2)
        u_num = c1.text_input("Número Económico")
        l_num = c1.text_input("Lote")
        campo = c2.selectbox("Campo Específico", ["Ninguno"] + list(CAMPOS_SERIES.keys()))
        valor = c2.text_input("Serial")
        if st.form_submit_button("Registrar"):
            if campo != "Ninguno":
                execute_write(f"INSERT INTO unidades (unit_number, id_lote, {campo}) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE id_lote=%s, {campo}=%s", 
                             (u_num, l_num, valor, l_num, valor))
            else:
                execute_write("INSERT INTO unidades (unit_number, id_lote) VALUES (%s,%s) ON DUPLICATE KEY UPDATE id_lote=%s", (u_num, l_num, l_num))
            st.success("Unidad actualizada")

elif menu == "👥 Gestión de Usuarios":
    st.markdown('<div class="main-header">Usuarios</div>', unsafe_allow_html=True)
    with st.form("u_add"):
        n = st.text_input("Username")
        p = st.text_input("Password", type="password")
        r = st.selectbox("Rol", ["tecnico", "admin"])
        if st.form_submit_button("Crear"):
            execute_write("INSERT INTO users (username, password, role) VALUES (%s,%s,%s)", (n, p, r))
            st.success("Usuario creado")
