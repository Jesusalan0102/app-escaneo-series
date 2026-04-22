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
st_autorefresh(interval=45 * 1000, key="global_refresh")

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

# Estilos CSS
st.markdown(f"""
<style>
    .stApp {{ background-color: #F8F9FA; }}
    .main-header {{ 
        font-size: 2.2rem; font-weight: 800; color: {CARRIER_BLUE}; 
        border-bottom: 4px solid {CARRIER_BLUE}; padding-bottom: 10px; margin-bottom: 25px; 
    }}
    .section-title {{ 
        font-size: 1.4rem; font-weight: 700; color: #1E3A8A; 
        margin-top: 25px; margin-bottom: 15px; border-left: 5px solid {CARRIER_BLUE}; padding-left: 10px;
    }}
    .stMetric {{ background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #DDD; }}
</style>
""", unsafe_allow_html=True)

# ==================== FUNCIONES DE BASE DE DATOS ====================
def get_db_connection():
    try: return mysql.connector.connect(**st.secrets["db"], autocommit=True)
    except Exception as e: return None

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
        except: return False
    return False

# ==================== LÓGICA DE ACCESO ====================
if "login" not in st.session_state:
    st.session_state.update({"login": False, "user": "", "role": "", "last_count": 0})

if not st.session_state.login:
    st.markdown(f'<div style="text-align: center; padding: 40px;"><img src="{LOGO_URL}" width="450"></div>', unsafe_allow_html=True)
    col_l, col_c, col_r = st.columns([1,1.2,1])
    with col_c:
        with st.form("login"):
            st.markdown("<h3 style='text-align:center;'>Acceso al Sistema</h3>", unsafe_allow_html=True)
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                user = execute_read("SELECT * FROM users WHERE username=%s AND password=%s", (u.strip(), p.strip()))
                if user:
                    st.session_state.update({"login": True, "user": user[0]['username'], "role": user[0]['role'].lower()})
                    st.rerun()
                else: st.error("Error de credenciales")
    st.stop()

# ==================== SIDEBAR ====================
with st.sidebar:
    st.image(LOGO_URL, width=200)
    st.write(f"👤 **{st.session_state.user.upper()}** | {st.session_state.role}")
    st.divider()
    if st.session_state.role == "admin":
        menu = st.radio("PANEL CONTROL", ["📊 Dashboard", "🎯 Asignación de Tareas", "📸 Unidades", "👥 Usuarios"])
    else:
        menu = st.radio("MI TRABAJO", ["🎯 Mis Tareas", "🔔 Solicitar Actividad"])
    
    if st.button("Salir"):
        st.session_state.clear()
        st.rerun()

# ==================== DASHBOARD (ADMIN) ====================
if menu == "📊 Dashboard":
    st.markdown('<div class="main-header">Productividad y Estatus Global</div>', unsafe_allow_html=True)
    
    asig = execute_read("SELECT * FROM asignaciones")
    unid = execute_read("SELECT * FROM unidades")
    
    if asig:
        df_a = pd.DataFrame(asig)
        # Métricas rápidas
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Tareas Totales", len(df_a))
        m2.metric("Completadas ✅", len(df_a[df_a['estado'] == 'completada']))
        m3.metric("En Proceso ⏳", len(df_a[df_a['estado'] == 'en_proceso']))
        m4.metric("Pendientes ⚠️", len(df_a[df_a['estado'] == 'pendiente']))

        st.markdown('<div class="section-title">Productividad por Técnico</div>', unsafe_allow_html=True)
        # Gráfica de barras por técnico
        fig_barra = px.bar(df_a, x="tecnico", color="estado", 
                          title="Carga de Trabajo por Usuario",
                          barmode="group", color_discrete_map={'completada':'#2ECC71', 'en_proceso':'#F1C40F', 'pendiente':'#E67E22', 'solicitado':'#3498DB'})
        st.plotly_chart(fig_barra, use_container_width=True)

        # Tabla de Rendimiento
        stats = df_a.groupby('tecnico').agg(
            Total=('id', 'count'),
            Hechas=('estado', lambda x: (x == 'completada').sum()),
            Eficiencia=('estado', lambda x: f"{int((x == 'completada').sum() / len(x) * 100)}%")
        ).reset_index()
        st.table(stats)

    st.markdown('<div class="section-title">Estatus por Unidad (Matriz)</div>', unsafe_allow_html=True)
    if unid:
        c_set = {(r['unidad'], r['actividad_id']) for r in execute_read("SELECT unidad, actividad_id FROM asignaciones WHERE estado = 'completada'")}
        matriz = []
        for u in unid:
            fila = {"Lote": u['id_lote'], "Económico": u['unit_number']}
            for act in ACTIVIDADES_CARRIER:
                fila[act] = "✅" if (u['unit_number'], act) in c_set else ""
            matriz.append(fila)
        st.dataframe(pd.DataFrame(matriz), use_container_width=True, hide_index=True)

# ==================== ASIGNACIÓN DE TAREAS (ADMIN) ====================
elif menu == "🎯 Asignación de Tareas":
    st.markdown('<div class="main-header">Control y Asignación</div>', unsafe_allow_html=True)
    
    # 1. Solicitudes entrantes
    st.markdown('<div class="section-title">Solicitudes Pendientes (Alertas)</div>', unsafe_allow_html=True)
    sols = execute_read("SELECT * FROM asignaciones WHERE estado='solicitado'")
    
    if len(sols) > st.session_state.last_count:
        st.markdown(f'<audio autoplay><source src="{SOUND_URL}"></audio>', unsafe_allow_html=True)
    st.session_state.last_count = len(sols)

    if not sols: st.info("No hay solicitudes nuevas.")
    for s in sols:
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"👷 **{s['tecnico']}** requiere realizar **{s['actividad_id']}** en Unidad **{s['unidad']}**")
            if c2.button("✅ Aprobar", key=f"ap_{s['id']}"):
                execute_write("UPDATE asignaciones SET estado='pendiente' WHERE id=%s", (s['id'],))
                st.rerun()
            if c3.button("❌ Rechazar", key=f"re_{s['id']}"):
                execute_write("DELETE FROM asignaciones WHERE id=%s", (s['id'],))
                st.rerun()

    # 2. Asignación Directa (Manual)
    st.markdown('<div class="section-title">Asignación Manual Directa</div>', unsafe_allow_html=True)
    unid_list = execute_read("SELECT unit_number, id_lote FROM unidades")
    tecs_list = execute_read("SELECT username FROM users WHERE role='tecnico'")
    
    with st.form("manual_asig"):
        col1, col2, col3 = st.columns(3)
        u_sel = col1.selectbox("Unidad", [f"{x['id_lote']} - {x['unit_number']}" for x in unid_list])
        t_sel = col2.selectbox("Asignar a Técnico", [x['username'] for x in tecs_list])
        a_sel = col3.selectbox("Actividad", ACTIVIDADES_CARRIER)
        
        if st.form_submit_button("Crear Orden de Trabajo", use_container_width=True):
            unit_final = u_sel.split(" - ")[1]
            execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s,%s,%s,'pendiente')", 
                         (unit_final, a_sel, t_sel))
            st.success(f"Tarea asignada a {t_sel}")
            st.rerun()

# ==================== MIS TAREAS (TÉCNICO) ====================
elif menu == "🎯 Mis Tareas":
    st.markdown('<div class="main-header">Mis Tareas Asignadas</div>', unsafe_allow_html=True)
    tareas = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado IN ('pendiente', 'en_proceso')", (st.session_state.user,))
    
    if not tareas: st.info("No tienes tareas pendientes por ahora.")
    
    for t in tareas:
        with st.expander(f"📦 UNIDAD: {t['unidad']} | {t['actividad_id']}", expanded=True):
            if t['estado'] == 'pendiente':
                if st.button("▶️ INICIAR", key=f"in_{t['id']}", use_container_width=True):
                    execute_write("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                    st.rerun()
            else:
                if t['actividad_id'].lower() == "evidencia":
                    files = st.file_uploader("Subir fotos (Max 40)", accept_multiple_files=True, key=f"f_{t['id']}")
                    if st.button("💾 GUARDAR TODO", key=f"sv_{t['id']}"):
                        if files:
                            conn = get_db_connection(); cur = conn.cursor()
                            bar = st.progress(0)
                            for i, f in enumerate(files):
                                cur.execute("INSERT INTO evidencias (unit_number, nombre_archivo, contenido, tecnico) VALUES (%s,%s,%s,%s)", 
                                           (t['unidad'], f.name, f.read(), st.session_state.user))
                                bar.progress((i+1)/len(files))
                            cur.execute("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                            conn.commit(); cur.close(); conn.close()
                            st.rerun()
                elif t['actividad_id'].lower() == "toma de series":
                    with st.form(f"ser_{t['id']}"):
                        inputs = {k: st.text_input(v) for k, v in CAMPOS_SERIES.items()}
                        if st.form_submit_button("Guardar Series"):
                            q = ", ".join([f"{k}=%s" for k in inputs.keys()])
                            execute_write(f"UPDATE unidades SET {q} WHERE unit_number=%s", list(inputs.values()) + [t['unidad']])
                            execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                            st.rerun()
                else:
                    if st.button("✅ TERMINAR", key=f"fi_{t['id']}", use_container_width=True):
                        execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                        st.rerun()

# ==================== SOLICITUD (TÉCNICO) ====================
elif menu == "🔔 Solicitar Actividad":
    st.markdown('<div class="main-header">Solicitar Nueva Tarea</div>', unsafe_allow_html=True)
    unid_db = execute_read("SELECT unit_number, id_lote FROM unidades")
    ev_check = {r['unit_number'] for r in execute_read("SELECT DISTINCT unit_number FROM evidencias")}
    
    with st.form("solic_f"):
        opciones = [f"{x['id_lote']} - {x['unit_number']} {'📸' if x['unit_number'] in ev_check else '⭕'}" for x in unid_db]
        u_sel = st.selectbox("Unidad", opciones)
        a_sel = st.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.form_submit_button("Enviar Solicitud"):
            u_clean = u_sel.split(" - ")[1].split(" ")[0]
            execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s,%s,%s,'solicitado')", (u_clean, a_sel, st.session_state.user))
            st.toast("Solicitud enviada!")

# ==================== RESTO DE MÓDULOS (ADMIN) ====================
elif menu == "📸 Unidades":
    st.markdown('<div class="main-header">Registro de Unidades</div>', unsafe_allow_html=True)
    with st.form("reg_u"):
        c1, c2 = st.columns(2)
        un = c1.text_input("Económico")
        lt = c1.text_input("Lote")
        cp = col2 = c2.selectbox("Campo", ["Ninguno"] + list(CAMPOS_SERIES.keys()))
        vl = c2.text_input("Valor")
        if st.form_submit_button("Registrar"):
            if cp != "Ninguno":
                execute_write(f"INSERT INTO unidades (unit_number, id_lote, {cp}) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE id_lote=%s, {cp}=%s", (un, lt, vl, lt, vl))
            else:
                execute_write("INSERT INTO unidades (unit_number, id_lote) VALUES (%s,%s) ON DUPLICATE KEY UPDATE id_lote=%s", (un, lt, lt))
            st.success("Unidad actualizada")

elif menu == "👥 Usuarios":
    st.markdown('<div class="main-header">Gestión de Usuarios</div>', unsafe_allow_html=True)
    with st.form("usr"):
        u_n = st.text_input("Username")
        u_p = st.text_input("Password", type="password")
        u_r = st.selectbox("Rol", ["tecnico", "admin"])
        if st.form_submit_button("Crear Usuario"):
            execute_write("INSERT INTO users (username, password, role) VALUES (%s,%s,%s)", (u_n, u_p, u_r))
            st.success("Usuario Creado")
