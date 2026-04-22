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
st_autorefresh(interval=45 * 1000, key="global_refresh") # Aumentado a 45s para estabilidad

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

# Estilos CSS (Dashboard y Botones)
st.markdown(f"""
<style>
    .stApp {{ background-color: #F4F7F9; }}
    .main-header {{ 
        font-size: 2.2rem; font-weight: 800; color: {CARRIER_BLUE}; 
        border-bottom: 4px solid {CARRIER_BLUE}; padding-bottom: 10px; margin-bottom: 25px; 
    }}
    .section-title {{ 
        font-size: 1.4rem; font-weight: 700; color: #1E3A8A; 
        margin-top: 25px; margin-bottom: 15px; padding-left: 10px;
        border-left: 5px solid {CARRIER_BLUE};
    }}
    .stMetric {{ background-color: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
    .stButton>button {{ height: 3.5em !important; font-weight: bold !important; border-radius: 8px !important; }}
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
        cur.close() ; conn.close()
        return res
    return []

def execute_write(query, params=None):
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(query, params or ())
            cur.close() ; conn.close()
            return True
        except Exception as e:
            st.error(f"Error DB: {e}")
            return False
    return False

# ==================== LÓGICA DE ACCESO ====================
if "login" not in st.session_state:
    st.session_state.update({"login": False, "user": "", "role": "", "last_count": 0})

if not st.session_state.login:
    st.markdown(f'<div style="text-align: center; padding: 40px;"><img src="{LOGO_URL}" width="500"></div>', unsafe_allow_html=True)
    col_l, col_c, col_r = st.columns([1,1.2,1])
    with col_c:
        with st.form("login_form"):
            st.markdown(f"<h3 style='text-align:center;'>Control de Acceso</h3>", unsafe_allow_html=True)
            u_log = st.text_input("Usuario")
            p_log = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar", use_container_width=True):
                user = execute_read("SELECT * FROM users WHERE username=%s AND password=%s", (u_log.strip(), p_log.strip()))
                if user:
                    st.session_state.update({"login": True, "user": user[0]['username'], "role": user[0]['role'].lower()})
                    st.rerun()
                else: st.error("Credenciales Incorrectas")
    st.stop()

# ==================== NAVEGACIÓN ====================
with st.sidebar:
    st.image(LOGO_URL, width=250)
    st.info(f"👤 **{st.session_state.user.upper()}**\n\n📅 {fecha_hoy} | 🕒 {hora_actual}")
    st.divider()
    if st.session_state.role == "admin":
        menu = st.radio("NAVEGACIÓN", ["📊 Dashboard", "🎯 Órdenes", "📸 Unidades", "👥 Usuarios"])
    else:
        menu = st.radio("MI TRABAJO", ["🎯 Tareas Asignadas", "🔔 Solicitar Actividad"])
    
    if st.button("Cerrar Sesión", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ==================== DASHBOARD EJECUTIVO (Admin) ====================
if menu == "📊 Dashboard":
    st.markdown('<div class="main-header">Dashboard Operativo</div>', unsafe_allow_html=True)
    
    asig = execute_read("SELECT * FROM asignaciones")
    unid = execute_read("SELECT * FROM unidades")
    
    if asig:
        df_a = pd.DataFrame(asig)
        # KPIs Rápidos
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Tareas", len(df_a))
        k2.metric("Completadas", len(df_a[df_a['estado'] == 'completada']))
        k3.metric("En Proceso", len(df_a[df_a['estado'] == 'en_proceso']))
        k4.metric("Pendientes", len(df_a[df_a['estado'] == 'pendiente']))
        
        st.divider()
        
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown('<div class="section-title">Estatus por Unidad</div>', unsafe_allow_html=True)
            if unid:
                comp_raw = execute_read("SELECT unidad, actividad_id FROM asignaciones WHERE estado = 'completada'")
                c_set = {(r['unidad'], r['actividad_id']) for r in comp_raw}
                status_list = []
                for u in unid:
                    row = {"Lote": u['id_lote'], "Económico": u['unit_number']}
                    for act in ACTIVIDADES_CARRIER:
                        row[act] = "✅" if (u['unit_number'], act) in c_set else ""
                    status_list.append(row)
                st.dataframe(pd.DataFrame(status_list), use_container_width=True, hide_index=True)
        
        with c2:
            st.markdown('<div class="section-title">Productividad</div>', unsafe_allow_html=True)
            st.plotly_chart(px.pie(df_a, names='estado', hole=0.6, color_discrete_sequence=px.colors.qualitative.Pastel), use_container_width=True)

    # Reportes y ZIP
    st.markdown('<div class="section-title">Gestión de Archivos</div>', unsafe_allow_html=True)
    exp1, exp2 = st.columns(2)
    with exp1:
        if unid:
            u_sel = st.selectbox("Unidad para Fotos:", [u['unit_number'] for u in unid])
            if st.button("Generar ZIP de Evidencias"):
                ev_f = execute_read("SELECT nombre_archivo, contenido FROM evidencias WHERE unit_number = %s", (u_sel,))
                if ev_f:
                    buf = io.BytesIO()
                    with zipfile.ZipFile(buf, "a", zipfile.ZIP_DEFLATED) as zf:
                        for e in ev_f: zf.writestr(e['nombre_archivo'], e['contenido'])
                    st.download_button(f"📥 Descargar ZIP {u_sel}", buf.getvalue(), f"Fotos_{u_sel}.zip", "application/zip")
                else: st.warning("No hay fotos.")
    
    with exp2:
        if unid:
            df_u = pd.DataFrame(unid)
            buf_ex = io.BytesIO()
            with pd.ExcelWriter(buf_ex, engine='openpyxl') as wr:
                df_u.to_excel(wr, index=False, sheet_name='Unidades')
                if asig: pd.DataFrame(asig).to_excel(wr, index=False, sheet_name='Logs')
            st.download_button("📊 Descargar Reporte Excel", buf_ex.getvalue(), f"Reporte_{fecha_hoy}.xlsx", use_container_width=True)

# ==================== TAREAS (Técnico) ====================
elif menu == "🎯 Tareas Asignadas":
    st.markdown('<div class="main-header">Mis Actividades</div>', unsafe_allow_html=True)
    tareas = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado IN ('pendiente', 'en_proceso')", (st.session_state.user,))
    
    if not tareas: st.info("Sin tareas pendientes.")
    
    for t in tareas:
        with st.expander(f"📌 UNIDAD: {t['unidad']} | {t['actividad_id']}", expanded=True):
            if t['estado'] == 'pendiente':
                if st.button("▶️ INICIAR ACTIVIDAD", key=f"s_{t['id']}", use_container_width=True):
                    execute_write("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                    st.rerun()
            else:
                # OPTIMIZACIÓN CARGA MASIVA (40+ FOTOS)
                if t['actividad_id'].lower() == "evidencia":
                    files = st.file_uploader("Subir Evidencias (JPG/PNG)", accept_multiple_files=True, key=f"up_{t['id']}")
                    if st.button("💾 GUARDAR Y FINALIZAR", key=f"b_{t['id']}", use_container_width=True):
                        if files:
                            conn = get_db_connection()
                            cur = conn.cursor()
                            try:
                                bar = st.progress(0, text="Subiendo archivos a la base de datos...")
                                for i, f in enumerate(files):
                                    cur.execute("INSERT INTO evidencias (unit_number, nombre_archivo, contenido, tecnico) VALUES (%s,%s,%s,%s)", 
                                               (t['unidad'], f.name, f.read(), st.session_state.user))
                                    bar.progress((i + 1) / len(files))
                                
                                cur.execute("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                                conn.commit() # Un solo commit para todo el lote
                                st.success(f"✅ {len(files)} fotos guardadas correctamente.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error en carga masiva: {e}")
                            finally:
                                cur.close() ; conn.close()
                        else: st.warning("Suba al menos una foto.")
                
                elif t['actividad_id'].lower() == "toma de series":
                    with st.form(f"f_{t['id']}"):
                        res = {k: st.text_input(v) for k, v in CAMPOS_SERIES.items()}
                        if st.form_submit_button("GUARDAR SERIES"):
                            q = ", ".join([f"{k}=%s" for k in res.keys()])
                            execute_write(f"UPDATE unidades SET {q} WHERE unit_number=%s", list(res.values()) + [t['unidad']])
                            execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                            st.rerun()
                else:
                    if st.button("✅ FINALIZAR ACTIVIDAD", key=f"f_{t['id']}", use_container_width=True):
                        execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                        st.rerun()

# ==================== SOLICITUD (Técnico) ====================
elif menu == "🔔 Solicitar Actividad":
    st.markdown('<div class="main-header">Nueva Solicitud</div>', unsafe_allow_html=True)
    u_db = execute_read("SELECT unit_number, id_lote FROM unidades")
    ev_exist = {r['unit_number'] for r in execute_read("SELECT DISTINCT unit_number FROM evidencias")}
    
    with st.form("sol_f"):
        opts = [f"{x['id_lote']} - {x['unit_number']} {'📸' if x['unit_number'] in ev_exist else '⭕'}" for x in u_db]
        u_sel = st.selectbox("Seleccione Unidad", opts)
        a_sel = st.selectbox("Actividad a Realizar", ACTIVIDADES_CARRIER)
        if st.form_submit_button("Enviar Solicitud"):
            u_clean = u_sel.split(" - ")[1].split(" ")[0]
            execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s,%s,%s,'solicitado')", (u_clean, a_sel, st.session_state.user))
            st.toast("Solicitud enviada al administrador")
            st.rerun()

# ==================== GESTIÓN ADMIN (Resto de funciones) ====================
elif menu == "🎯 Órdenes":
    st.markdown('<div class="main-header">Control de Órdenes</div>', unsafe_allow_html=True)
    sols = execute_read("SELECT * FROM asignaciones WHERE estado='solicitado'")
    
    if len(sols) > st.session_state.last_count:
        st.markdown(f'<audio autoplay><source src="{SOUND_URL}" type="audio/mp3"></audio>', unsafe_allow_html=True)
    st.session_state.last_count = len(sols)

    for s in sols:
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"📢 **{s['tecnico']}**: {s['actividad_id']} (Unidad {s['unidad']})")
            if c2.button("Aprobar", key=f"a_{s['id']}"):
                execute_write("UPDATE asignaciones SET estado='pendiente' WHERE id=%s", (s['id'],))
                st.rerun()
            if c3.button("Eliminar", key=f"d_{s['id']}"):
                execute_write("DELETE FROM asignaciones WHERE id=%s", (s['id'],))
                st.rerun()

elif menu == "📸 Unidades":
    st.markdown('<div class="main-header">Registro de Unidades</div>', unsafe_allow_html=True)
    with st.form("r_u"):
        col1, col2 = st.columns(2)
        u_n = col1.text_input("Económico")
        l_n = col1.text_input("Lote")
        campo = col2.selectbox("Campo", ["Ninguno"] + list(CAMPOS_SERIES.keys()))
        val = col2.text_input("Valor")
        if st.form_submit_button("Guardar"):
            if campo != "Ninguno":
                execute_write(f"INSERT INTO unidades (unit_number, id_lote, {campo}) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE id_lote=%s, {campo}=%s", (u_n, l_n, val, l_n, val))
            else:
                execute_write("INSERT INTO unidades (unit_number, id_lote) VALUES (%s,%s) ON DUPLICATE KEY UPDATE id_lote=%s", (u_n, l_n, l_n))
            st.success("Guardado")

elif menu == "👥 Usuarios":
    st.markdown('<div class="main-header">Gestión de Usuarios</div>', unsafe_allow_html=True)
    with st.form("u_g"):
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        r = st.selectbox("Rol", ["tecnico", "admin"])
        if st.form_submit_button("Crear"):
            execute_write("INSERT INTO users (username, password, role) VALUES (%s,%s,%s)", (u, p, r))
            st.rerun()
