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
    "vin_number": "VIN Number", "reefer_serial": "Serie del Reefer",
    "reefer_model": "Modelo del Reefer", "evaporator_serial_mjs11": "Evaporador MJS11",
    "evaporator_serial_mjd22": "Evaporador MJD22", "engine_serial": "Motor",
    "compressor_serial": "Compresor", "generator_serial": "Generador",
    "battery_charger_serial": "Cargador de Batería"
}

ACTIVIDADES_CARRIER = [
    "Cableado", "Programación", "Soldadura", "Check de fugas", 
    "Vacío", "Cerrado", "Pre-viaje", "Horas Corridas", 
    "Standby", "GPS", "Run", "Corriendo", "Inspección", 
    "Accesorios", "Toma de Valores", "Evidencia", "Toma de Series"
]

st.markdown(f"""
<style>
    .stApp {{ background-color: white; }}
    .main-header {{ font-size: 2.2rem; font-weight: 700; color: {CARRIER_BLUE}; border-bottom: 3px solid {CARRIER_BLUE}; padding-bottom: 10px; margin-bottom: 25px; }}
    .section-title {{ font-size: 1.3rem; font-weight: 600; color: #333; margin-top: 20px; border-left: 5px solid {CARRIER_BLUE}; padding-left: 15px; margin-bottom: 15px; }}
</style>
""", unsafe_allow_html=True)

# ==================== FUNCIONES DB ====================
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
        except Exception as e:
            st.error(f"Error DB: {e}"); return False
    return False

# ==================== LOGIN ====================
if "login" not in st.session_state:
    st.session_state.update({"login": False, "user": "", "role": "", "last_count": 0})

if not st.session_state.login:
    st.markdown(f'<div style="text-align: center; padding: 50px;"><img src="{LOGO_URL}" width="500"></div>', unsafe_allow_html=True)
    _, col_c, _ = st.columns([1,1.5,1])
    with col_c:
        u_log = st.text_input("Usuario")
        p_log = st.text_input("Contraseña", type="password")
        if st.button("Ingresar", use_container_width=True):
            user = execute_read("SELECT * FROM users WHERE username=%s AND password=%s", (u_log.strip(), p_log.strip()))
            if user:
                st.session_state.update({"login": True, "user": user[0]['username'], "role": user[0]['role'].lower()})
                st.rerun()
            else: st.error("Acceso denegado")
    st.stop()

# ==================== SIDEBAR ====================
with st.sidebar:
    st.image(LOGO_URL, width=300)
    st.write(f"👤 {st.session_state.user} ({st.session_state.role})")
    st.divider()
    if st.session_state.role == "admin":
        menu = st.radio("PANEL CONTROL", ["📊 Dashboard", "🎯 Asignaciones", "📸 Registro Maestro", "👥 Usuarios"])
    else:
        menu = st.radio("TRABAJO", ["🎯 Mis Tareas", "🔔 Nueva Solicitud"])
    if st.button("Cerrar Sesión"): st.session_state.clear(); st.rerun()

# ==================== DASHBOARD (RESTAURADO) ====================
if menu == "📊 Dashboard":
    st.markdown('<div class="main-header">Resumen Operativo</div>', unsafe_allow_html=True)
    unid = execute_read("SELECT * FROM unidades")
    asig = execute_read("SELECT * FROM asignaciones")
    fotos_count = execute_read("SELECT unit_number, COUNT(*) as total FROM evidencias GROUP BY unit_number")
    f_dict = {r['unit_number']: r['total'] for r in fotos_count}

    if asig:
        df_asig = pd.DataFrame(asig)
        st.plotly_chart(px.bar(df_asig, x='tecnico', color='estado', title="Estado de Tareas"), use_container_width=True)

    st.markdown('<div class="section-title">Matriz de Proceso y Evidencias</div>', unsafe_allow_html=True)
    if unid:
        comp_set = {(r['unidad'], r['actividad_id']) for r in asig if r['estado'] == 'completada'}
        res_data = []
        for u in unid:
            row = {"LOTE": u['id_lote'], "UNIDAD": u['unit_number'], "📸 FOTOS": f_dict.get(u['unit_number'], 0)}
            for act in ACTIVIDADES_CARRIER:
                row[act] = "✔" if (u['unit_number'], act) in comp_set else ""
            res_data.append(row)
        st.dataframe(pd.DataFrame(res_data), use_container_width=True, hide_index=True)

    st.markdown('<div class="section-title">📦 Inventario de Series por Lote</div>', unsafe_allow_html=True)
    if unid:
        df_u = pd.DataFrame(unid)
        for lote in sorted(df_u['id_lote'].unique()):
            with st.expander(f"Lote: {lote}"):
                st.table(df_u[df_u['id_lote']==lote][['unit_number'] + list(CAMPOS_SERIES.keys())])

# ==================== ASIGNACIONES (RESTAURADO) ====================
elif menu == "🎯 Asignaciones":
    st.markdown('<div class="main-header">Gestión de Tareas</div>', unsafe_allow_html=True)
    
    # 1. Autorización de Solicitudes
    sols = execute_read("SELECT * FROM asignaciones WHERE estado='solicitado'")
    if sols:
        st.subheader("Solicitudes del Personal")
        for s in sols:
            col_t, col_a, col_d = st.columns([4, 1, 1])
            with col_t:
                st.info(f"**{s['tecnico']}** -> {s['actividad_id']} en {s['unidad']}")
                if execute_read("SELECT id FROM asignaciones WHERE unidad=%s AND actividad_id=%s AND estado='completada'", (s['unidad'], s['actividad_id'])):
                    st.error("⚠️ Ya fue completada anteriormente")
            if col_a.button("Autorizar", key=f"aut_{s['id']}"):
                execute_write("UPDATE asignaciones SET estado='pendiente' WHERE id=%s", (s['id'],))
                st.toast("Tarea autorizada", icon="✅"); st.rerun()
            if col_d.button("Borrar", key=f"del_{s['id']}"):
                execute_write("DELETE FROM asignaciones WHERE id=%s", (s['id'],))
                st.rerun()

    # 2. Asignación Directa y Corrección
    st.markdown('<div class="section-title">Asignación Directa / Eliminar Tareas Activas</div>', unsafe_allow_html=True)
    u_db = execute_read("SELECT unit_number, id_lote FROM unidades")
    t_db = execute_read("SELECT username FROM users WHERE role='tecnico'")
    
    with st.form("manual_assign"):
        c1, c2, c3 = st.columns(3)
        u_sel = c1.selectbox("Unidad", [f"{x['id_lote']} - {x['unit_number']}" for x in u_db])
        te_sel = c2.selectbox("Técnico", [x['username'] for x in t_db])
        ac_sel = c3.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.form_submit_button("Asignar Tarea"):
            execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s,%s,%s,'pendiente')", 
                         (u_sel.split(" - ")[1], ac_sel, te_sel))
            st.toast("Asignación exitosa"); st.rerun()

# ==================== MIS TAREAS (CAMARA TIPO WHATSAPP) ====================
elif menu == "🎯 Mis Tareas":
    st.markdown('<div class="main-header">Mis Actividades</div>', unsafe_allow_html=True)
    tareas = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado IN ('pendiente', 'en_proceso')", (st.session_state.user,))
    
    for t in tareas:
        with st.expander(f"📦 {t['unidad']} - {t['actividad_id']}", expanded=True):
            if t['estado'] == 'pendiente':
                if st.button("▶️ Iniciar", key=f"ini_{t['id']}", use_container_width=True):
                    execute_write("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                    st.rerun()
            else:
                if t['actividad_id'].lower() == "evidencia":
                    st.write("📸 Captura de Fotos (Puedes seleccionar o tomar varias)")
                    # La opción accept_multiple_files=True es clave para el flujo tipo WhatsApp
                    fotos = st.file_uploader("Cámara / Galería", type=['jpg','jpeg','png'], accept_multiple_files=True, key=f"cam_{t['id']}")
                    if st.button("Finalizar Actividad y Guardar Todo", key=f"save_{t['id']}"):
                        if fotos:
                            p = st.progress(0)
                            for i, f in enumerate(fotos):
                                execute_write("INSERT INTO evidencias (unit_number, nombre_archivo, contenido, tecnico) VALUES (%s,%s,%s,%s)", (t['unidad'], f.name, f.read(), st.session_state.user))
                                p.progress((i+1)/len(fotos))
                            execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                            st.toast("¡Evidencias subidas con éxito!", icon="📸"); st.rerun()
                
                elif t['actividad_id'].lower() == "toma de series":
                    with st.form(f"ser_{t['id']}"):
                        res = {k: st.text_input(v) for k, v in CAMPOS_SERIES.items()}
                        if st.form_submit_button("Guardar y Finalizar"):
                            q = ", ".join([f"{k}=%s" for k in res.keys()])
                            execute_write(f"UPDATE unidades SET {q} WHERE unit_number=%s", list(res.values()) + [t['unidad']])
                            execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                            st.toast("Series registradas", icon="💾"); st.rerun()
                else:
                    if st.button("✅ Finalizar Actividad", key=f"fin_{t['id']}", use_container_width=True):
                        execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                        st.toast("Actividad guardada"); st.rerun()

# ==================== REGISTRO MAESTRO (RESTAURADO) ====================
elif menu == "📸 Registro Maestro":
    st.markdown('<div class="main-header">Control de Unidades</div>', unsafe_allow_html=True)
    with st.form("reg_unid"):
        c1, c2 = st.columns(2)
        u_num = c1.text_input("Número Económico")
        l_num = c1.text_input("Lote")
        campo = c2.selectbox("Campo", list(CAMPOS_SERIES.keys()), format_func=lambda x: CAMPOS_SERIES[x])
        valor = c2.text_input("Valor del Serial")
        if st.form_submit_button("Guardar Registro", use_container_width=True):
            if execute_write(f"INSERT INTO unidades (unit_number, id_lote, {campo}) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE id_lote=%s, {campo}=%s", (u_num, l_num, valor, l_num, valor)):
                st.toast("Unidad actualizada", icon="💾")

# ==================== GESTIÓN DE USUARIOS (RESTAURADO) ====================
elif menu == "👥 Usuarios":
    st.markdown('<div class="main-header">Administración de Usuarios</div>', unsafe_allow_html=True)
    u_list = execute_read("SELECT id, username, role FROM users")
    if u_list:
        for u in u_list:
            c1, c2, c3 = st.columns([3,2,1])
            c1.write(f"👤 **{u['username']}**")
            c2.info(f"ROL: {u['role'].upper()}")
            if c3.button("Borrar", key=f"du_{u['id']}"):
                execute_write("DELETE FROM users WHERE id=%s", (u['id'],)); st.rerun()
            st.divider()
    
    with st.form("add_user"):
        n_u = st.text_input("Nuevo Usuario")
        n_p = st.text_input("Pass", type="password")
        n_r = st.selectbox("Rol", ["tecnico", "admin"])
        if st.form_submit_button("Crear"):
            execute_write("INSERT INTO users (username, password, role) VALUES (%s,%s,%s)", (n_u, n_p, n_r))
            st.toast("Usuario creado"); st.rerun()

# ==================== NUEVA SOLICITUD ====================
elif menu == "🔔 Nueva Solicitud":
    st.markdown('<div class="main-header">Solicitar Actividad</div>', unsafe_allow_html=True)
    unids = execute_read("SELECT unit_number, id_lote FROM unidades")
    with st.form("new_sol"):
        u = st.selectbox("Unidad", [f"{x['id_lote']} - {x['unit_number']}" for x in unids])
        a = st.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.form_submit_button("Enviar Solicitud"):
            execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'solicitado')", (u.split(" - ")[1], a, st.session_state.user))
            st.toast("Enviado al administrador", icon="🔔"); st.rerun()
