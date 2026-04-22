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

st.markdown(f"""
<style>
    .stApp {{ background-color: white; }}
    .main-header {{ font-size: 2.2rem; font-weight: 700; color: {CARRIER_BLUE}; border-bottom: 3px solid {CARRIER_BLUE}; padding-bottom: 10px; margin-bottom: 25px; }}
    .section-title {{ font-size: 1.3rem; font-weight: 600; color: #333; margin-top: 20px; border-left: 5px solid {CARRIER_BLUE}; padding-left: 15px; margin-bottom: 15px; }}
    .time-badge {{ background-color: {CARRIER_BLUE}; color: white; padding: 5px 15px; border-radius: 20px; font-size: 0.9rem; float: right; }}
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
            st.error(f"Error: {e}"); return False
    return False

# ==================== ESTADO DE SESIÓN ====================
if "login" not in st.session_state:
    st.session_state.update({"login": False, "user": "", "role": "", "last_count": 0})

# --- LOGIN ---
if not st.session_state.login:
    st.markdown(f'<div style="text-align: center; padding: 50px;"><img src="{LOGO_URL}" width="600"></div>', unsafe_allow_html=True)
    _, col_c, _ = st.columns([1,1.5,1])
    with col_c:
        u_log = st.text_input("Usuario")
        p_log = st.text_input("Contraseña", type="password")
        if st.button("Ingresar al Sistema", use_container_width=True):
            user = execute_read("SELECT * FROM users WHERE username=%s AND password=%s", (u_log.strip(), p_log.strip()))
            if user:
                st.session_state.update({"login": True, "user": user[0]['username'], "role": user[0]['role'].lower()})
                st.rerun()
            else: st.error("Credenciales incorrectas")
    st.stop()

# ==================== NAVEGACIÓN ====================
with st.sidebar:
    st.image(LOGO_URL, width=400)
    st.markdown(f"🕒 **Hora local:** {hora_actual}")
    st.divider()
    if st.session_state.role == "admin":
        menu = st.radio("MENÚ PRINCIPAL", ["📊 Dashboard Ejecutivo", "🎯 Control de Asignaciones", "📸 Registro de Unidades", "👥 Gestión de Usuarios"])
    else:
        menu = st.radio("ÁREA DE TRABAJO", ["🎯 Mis Tareas", "🔔 Nueva Solicitud"])
    if st.button("Cerrar Sesión Segura", use_container_width=True):
        st.session_state.clear(); st.rerun()

# ==================== DASHBOARD EJECUTIVO ====================
if menu == "📊 Dashboard Ejecutivo":
    st.markdown(f'<div class="time-badge">Tijuana: {hora_actual}</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-header">Panel de Rendimiento Operativo</div>', unsafe_allow_html=True)
    
    asig = execute_read("SELECT * FROM asignaciones")
    unid = execute_read("SELECT * FROM unidades")
    
    if asig:
        df_a = pd.DataFrame(asig)
        stats = df_a.groupby('tecnico').agg(Total=('id', 'count'), Completadas=('estado', lambda x: (x == 'completada').sum())).reset_index()
        st.markdown('<div class="section-title">Estadísticas por Técnico</div>', unsafe_allow_html=True)
        st.dataframe(stats, use_container_width=True, hide_index=True)
        
        c1, c2 = st.columns([2, 1])
        with c1: st.plotly_chart(px.bar(df_a, x='tecnico', color='estado', title="Carga de Trabajo"), use_container_width=True)
        with c2: st.plotly_chart(px.pie(df_a, names='estado', title="Estado Global", hole=0.5), use_container_width=True)

    # --- MATRIZ DE ESTATUS (LOS "✔") ---
    st.markdown('<div class="section-title">📊 Estatus de Proceso por Unidad</div>', unsafe_allow_html=True)
    if unid:
        completas_raw = execute_read("SELECT unidad, actividad_id FROM asignaciones WHERE estado = 'completada'")
        comp_set = {(r['unidad'], r['actividad_id']) for r in completas_raw}
        st_data = []
        for u in unid:
            row = {"LOTE": u['id_lote'], "#económico": u['unit_number']}
            for act in ACTIVIDADES_CARRIER: row[act] = "✔" if (u['unit_number'], act) in comp_set else ""
            st_data.append(row)
        st.dataframe(pd.DataFrame(st_data), use_container_width=True, hide_index=True)

    # --- DESCARGAS ---
    st.markdown('<div class="section-title">📥 Centro de Descargas y Reportes</div>', unsafe_allow_html=True)
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        if unid:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as wr:
                pd.DataFrame(unid).to_excel(wr, index=False, sheet_name='Series_Unidades')
                if asig: pd.DataFrame(asig).to_excel(wr, index=False, sheet_name='Reporte_Actividades')
            st.download_button("📊 Descargar Reporte Maestro (Excel)", buf.getvalue(), f"Reporte_{fecha_hoy}.xlsx", use_container_width=True)
    with col_d2:
        u_ev = st.selectbox("Unidad para Fotos:", [u['unit_number'] for u in unid] if unid else [])
        if st.button("Generar ZIP de Evidencias", use_container_width=True):
            fotos = execute_read("SELECT nombre_archivo, contenido FROM evidencias WHERE unit_number = %s", (u_ev,))
            if fotos:
                bz = io.BytesIO()
                with zipfile.ZipFile(bz, "a", zipfile.ZIP_DEFLATED, False) as z:
                    for f in fotos: z.writestr(f['nombre_archivo'], f['contenido'])
                st.download_button(f"Bajar {u_ev}.zip", bz.getvalue(), f"{u_ev}_fotos.zip", use_container_width=True)

# ==================== CONTROL DE ASIGNACIONES ====================
elif menu == "🎯 Control de Asignaciones":
    st.markdown('<div class="main-header">Gestión de Órdenes</div>', unsafe_allow_html=True)
    sols = execute_read("SELECT * FROM asignaciones WHERE estado='solicitado'")
    
    if len(sols) > st.session_state.last_count:
        st.markdown(f'<audio autoplay><source src="{SOUND_URL}" type="audio/mp3"></audio>', unsafe_allow_html=True)
    st.session_state.last_count = len(sols)

    for s in sols:
        col_inf, col_ap, col_den = st.columns([4, 1, 1])
        with col_inf:
            st.warning(f"**{s['tecnico']}** solicita **{s['actividad_id']}** - {s['unidad']}")
            dup = execute_read("SELECT tecnico FROM asignaciones WHERE unidad=%s AND actividad_id=%s AND estado='completada'", (s['unidad'], s['actividad_id']))
            if dup: st.error(f"⚠️ YA COMPLETADO POR {dup[0]['tecnico']}")
        if col_ap.button("✅ Aprobar", key=f"ap_{s['id']}"): 
            execute_write("UPDATE asignaciones SET estado='pendiente' WHERE id=%s", (s['id'],)); st.rerun()
        if col_den.button("❌ Borrar", key=f"de_{s['id']}"): 
            execute_write("DELETE FROM asignaciones WHERE id=%s", (s['id'],)); st.rerun()

    st.markdown('<div class="section-title">Asignación Directa y Correcciones</div>', unsafe_allow_html=True)
    # Bloque de eliminación de tareas activas restaurado
    activas = execute_read("SELECT * FROM asignaciones WHERE estado IN ('pendiente', 'en_proceso')")
    for a in activas:
        with st.expander(f"Tarea Activa: {a['tecnico']} - {a['unidad']}"):
            if st.button("🗑️ Eliminar por Error", key=f"el_{a['id']}"):
                execute_write("DELETE FROM asignaciones WHERE id=%s", (a['id'],)); st.rerun()

# ==================== MIS TAREAS ====================
elif menu == "🎯 Mis Tareas":
    st.markdown('<div class="main-header">Panel de Trabajo</div>', unsafe_allow_html=True)
    tareas = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado IN ('pendiente', 'en_proceso')", (st.session_state.user,))
    
    for t in tareas:
        with st.expander(f"📦 {t['unidad']} - {t['actividad_id']}", expanded=True):
            if t['estado'] == 'pendiente':
                if st.button("▶️ Iniciar Trabajo", key=f"in_{t['id']}", use_container_width=True):
                    execute_write("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id'])); st.rerun()
            else:
                if t['actividad_id'].lower() == "evidencia":
                    archivos = st.file_uploader("Fotos (Máx 50)", accept_multiple_files=True, type=['jpg','png','jpeg'], key=f"f_{t['id']}")
                    if st.button("Finalizar con Fotos", key=f"btn_{t['id']}", use_container_width=True):
                        if archivos:
                            bar = st.progress(0)
                            for i, f in enumerate(archivos):
                                execute_write("INSERT INTO evidencias (unit_number, nombre_archivo, contenido, tecnico) VALUES (%s,%s,%s,%s)", (t['unidad'], f.name, f.read(), st.session_state.user))
                                bar.progress((i+1)/len(archivos))
                            execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id'])); st.rerun()
                elif t['actividad_id'].lower() == "toma de series":
                    with st.form(f"ser_{t['id']}"):
                        res = {k: st.text_input(v) for k, v in CAMPOS_SERIES.items()}
                        if st.form_submit_button("Guardar Series"):
                            q = ", ".join([f"{k}=%s" for k in res.keys()])
                            execute_write(f"UPDATE unidades SET {q} WHERE unit_number=%s", list(res.values()) + [t['unidad']])
                            execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id'])); st.rerun()
                else:
                    if st.button("✅ Finalizar", key=f"fin_{t['id']}", use_container_width=True):
                        execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id'])); st.rerun()

# ==================== NUEVA SOLICITUD ====================
elif menu == "🔔 Nueva Solicitud":
    st.markdown('<div class="main-header">Solicitar Actividad</div>', unsafe_allow_html=True)
    unids = execute_read("SELECT unit_number, id_lote FROM unidades")
    with st.form("sol_f"):
        u_sel = st.selectbox("Unidad", [f"{x['id_lote']} - {x['unit_number']}" for x in unids])
        a_sel = st.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.form_submit_button("Enviar Solicitud"):
            unidad = u_sel.split(" - ")[1]
            existing = execute_read("SELECT id FROM asignaciones WHERE tecnico=%s AND unidad=%s AND estado != 'completada'", (st.session_state.user, unidad))
            if existing: st.error("Ya tienes una tarea activa para esta unidad.")
            else:
                execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'solicitado')", (unidad, a_sel, st.session_state.user))
                st.toast("Solicitud enviada"); st.rerun()

# ==================== REGISTRO DE UNIDADES ====================
elif menu == "📸 Registro de Unidades":
    st.markdown('<div class="main-header">Registro Maestro</div>', unsafe_allow_html=True)
    with st.form("reg_u"):
        c1, c2 = st.columns(2)
        u_n = c1.text_input("Número Económico")
        l_n = c1.text_input("Lote")
        campo = c2.selectbox("Campo", list(CAMPOS_SERIES.keys()), format_func=lambda x: CAMPOS_SERIES[x])
        val = c2.text_input("Valor")
        if st.form_submit_button("Guardar Registro"):
            execute_write(f"INSERT INTO unidades (unit_number, id_lote, {campo}) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE id_lote=%s, {campo}=%s", (u_n, l_n, val, l_n, val))
            st.toast("Guardado"); st.rerun()

# ==================== GESTIÓN DE USUARIOS ====================
elif menu == "👥 Gestión de Usuarios":
    st.markdown('<div class="main-header">Administración</div>', unsafe_allow_html=True)
    with st.form("u_f"):
        nu = st.text_input("Usuario"); np = st.text_input("Pass", type="password"); nr = st.selectbox("Rol", ["tecnico", "admin"])
        if st.form_submit_button("Crear"):
            execute_write("INSERT INTO users (username, password, role) VALUES (%s,%s,%s)", (nu, np, nr)); st.rerun()
