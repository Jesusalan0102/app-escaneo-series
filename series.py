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

# CSS Original
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

# ==================== NAVEGACIÓN ====================
with st.sidebar:
    st.image(LOGO_URL, width=300)
    st.write(f"🕒 **{hora_actual}** | 👤 **{st.session_state.user}**")
    st.divider()
    if st.session_state.role == "admin":
        menu = st.radio("MENÚ", ["📊 Dashboard Ejecutivo", "🎯 Control de Asignaciones", "📸 Registro de Unidades", "👥 Gestión de Usuarios"])
    else:
        menu = st.radio("TRABAJO", ["🎯 Mis Tareas", "🔔 Nueva Solicitud"])
    if st.button("Cerrar Sesión"): st.session_state.clear(); st.rerun()

# ==================== DASHBOARD EJECUTIVO (ORIGINAL RESTAURADO) ====================
if menu == "📊 Dashboard Ejecutivo":
    st.markdown('<div class="main-header">Panel de Rendimiento Operativo</div>', unsafe_allow_html=True)
    
    unid = execute_read("SELECT * FROM unidades")
    asig = execute_read("SELECT * FROM asignaciones")
    f_count = execute_read("SELECT unit_number, COUNT(*) as total FROM evidencias GROUP BY unit_number")
    f_dict = {r['unit_number']: r['total'] for r in f_count}

    if asig:
        df_asig = pd.DataFrame(asig)
        st.plotly_chart(px.bar(df_asig, x='tecnico', color='estado', title="Carga de Trabajo por Técnico"), use_container_width=True)

    # Centro de Descargas (Excel y ZIP con contador)
    st.markdown('<div class="section-title">📥 Centro de Descargas</div>', unsafe_allow_html=True)
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        if unid:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as wr:
                pd.DataFrame(unid).to_excel(wr, index=False, sheet_name='Series')
                if asig: pd.DataFrame(asig).to_excel(wr, index=False, sheet_name='Actividades')
            st.download_button("📊 Descargar Excel Maestro", buf.getvalue(), f"Reporte_{fecha_hoy}.xlsx", use_container_width=True)
    with col_d2:
        if unid:
            sel_u = st.selectbox("Unidad para ZIP:", [f"{u['unit_number']} ({f_dict.get(u['unit_number'], 0)} fotos)" for u in unid])
            u_clean = sel_u.split(" (")[0]
            if st.button(f"Generar ZIP {u_clean}", disabled=(f_dict.get(u_clean, 0) == 0)):
                ev_data = execute_read("SELECT nombre_archivo, contenido FROM evidencias WHERE unit_number=%s", (u_clean,))
                bz = io.BytesIO()
                with zipfile.ZipFile(bz, "a", zipfile.ZIP_DEFLATED) as zf:
                    for f in ev_data: zf.writestr(f['nombre_archivo'], f['contenido'])
                st.download_button(f"Descargar ZIP", bz.getvalue(), f"{u_clean}_fotos.zip")

    # Matriz de Estatus Original
    st.markdown('<div class="section-title">📊 Matriz de Avance por Unidad</div>', unsafe_allow_html=True)
    if unid:
        comp_set = {(r['unidad'], r['actividad_id']) for r in asig if r['estado'] == 'completada'}
        res_list = []
        for u in unid:
            row = {"LOTE": u['id_lote'], "# Económico": u['unit_number'], "📸": f_dict.get(u['unit_number'], 0)}
            for act in ACTIVIDADES_CARRIER:
                row[act] = "✔" if (u['unit_number'], act) in comp_set else ""
            res_list.append(row)
        st.dataframe(pd.DataFrame(res_list), use_container_width=True, hide_index=True)

    # Inventario por Lotes
    st.markdown('<div class="section-title">📦 Inventario de Series por Lote</div>', unsafe_allow_html=True)
    if unid:
        df_u = pd.DataFrame(unid)
        for lote in sorted(df_u['id_lote'].unique()):
            with st.expander(f"Lote: {lote}"):
                st.table(df_u[df_u['df_u']['id_lote']==lote][['unit_number'] + list(CAMPOS_SERIES.keys())])

# ==================== MIS TAREAS (CAMARA MEJORADA) ====================
elif menu == "🎯 Mis Tareas":
    st.markdown('<div class="main-header">Mis Actividades</div>', unsafe_allow_html=True)
    tareas = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado IN ('pendiente', 'en_proceso')", (st.session_state.user,))
    
    for t in tareas:
        with st.expander(f"📦 {t['unidad']} - {t['actividad_id']}", expanded=True):
            if t['estado'] == 'pendiente':
                if st.button("▶️ Iniciar", key=f"ini_{t['id']}", use_container_width=True):
                    execute_write("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                    st.toast("Actividad iniciada"); st.rerun()
            else:
                if t['actividad_id'].lower() == "evidencia":
                    # CARGA MULTIPLE PARA CAMARA DE CELULAR
                    archivos = st.file_uploader("Tomar Fotos (Cámara)", accept_multiple_files=True, type=['jpg','png','jpeg'], key=f"cam_{t['id']}")
                    if st.button("Finalizar y Enviar Evidencias", key=f"save_{t['id']}"):
                        if archivos:
                            prog = st.progress(0)
                            for i, f in enumerate(archivos):
                                execute_write("INSERT INTO evidencias (unit_number, nombre_archivo, contenido, tecnico) VALUES (%s,%s,%s,%s)", (t['unidad'], f.name, f.read(), st.session_state.user))
                                prog.progress((i+1)/len(archivos))
                            execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                            st.toast("✅ Fotos guardadas correctamente", icon="📸"); st.rerun()
                
                elif t['actividad_id'].lower() == "toma de series":
                    with st.form(f"ser_{t['id']}"):
                        res = {k: st.text_input(v) for k, v in CAMPOS_SERIES.items()}
                        if st.form_submit_button("Guardar Series"):
                            q = ", ".join([f"{k}=%s" for k in res.keys()])
                            execute_write(f"UPDATE unidades SET {q} WHERE unit_number=%s", list(res.values()) + [t['unidad']])
                            execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                            st.toast("Series guardadas exitosamente", icon="💾"); st.rerun()
                else:
                    if st.button("✅ Finalizar Actividad", key=f"fin_{t['id']}"):
                        execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                        st.toast("¡Operación Exitosa!", icon="✅"); st.rerun()

# ==================== OTROS MENÚS (RESTAURADOS) ====================
elif menu == "🎯 Control de Asignaciones":
    st.markdown('<div class="main-header">Aprobación y Asignación</div>', unsafe_allow_html=True)
    sols = execute_read("SELECT * FROM asignaciones WHERE estado='solicitado'")
    for s in sols:
        c1, c2, c3 = st.columns([4,1,1])
        c1.warning(f"**{s['tecnico']}** solicita {s['actividad_id']} en {s['unidad']}")
        if c2.button("Autorizar", key=f"at_{s['id']}"):
            execute_write("UPDATE asignaciones SET estado='pendiente' WHERE id=%s", (s['id'],))
            st.toast(f"Solicitud de {s['tecnico']} aprobada"); st.rerun()
        if c3.button("Borrar", key=f"br_{s['id']}"):
            execute_write("DELETE FROM asignaciones WHERE id=%s", (s['id'],)); st.rerun()

elif menu == "📸 Registro de Unidades":
    st.markdown('<div class="main-header">Registro Maestro</div>', unsafe_allow_html=True)
    with st.form("reg_u"):
        u_num = st.text_input("Número Económico"); l_num = st.text_input("Número de Lote")
        campo = st.selectbox("Campo a Registrar", list(CAMPOS_SERIES.keys()), format_func=lambda x: CAMPOS_SERIES[x])
        valor = st.text_input("Valor del Serial")
        if st.form_submit_button("Guardar Registro"):
            execute_write(f"INSERT INTO unidades (unit_number, id_lote, {campo}) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE id_lote=%s, {campo}=%s", (u_num, l_num, valor, l_num, valor))
            st.toast("Registro guardado con éxito", icon="💾")

elif menu == "👥 Gestión de Usuarios":
    st.markdown('<div class="main-header">Usuarios</div>', unsafe_allow_html=True)
    users = execute_read("SELECT id, username, role FROM users")
    for u in users:
        c1, c2, c3 = st.columns([3,2,1])
        c1.write(f"👤 **{u['username']}**"); c2.info(f"ROL: {u['role']}")
        if c3.button("Eliminar", key=f"du_{u['id']}"):
            execute_write("DELETE FROM users WHERE id=%s", (u['id'],)); st.rerun()
    with st.form("nu"):
        nu = st.text_input("Usuario"); np = st.text_input("Pass", type="password"); nr = st.selectbox("Rol", ["tecnico", "admin"])
        if st.form_submit_button("Crear"):
            execute_write("INSERT INTO users (username, password, role) VALUES (%s,%s,%s)", (nu, np, nr)); st.rerun()

elif menu == "🔔 Nueva Solicitud":
    st.markdown('<div class="main-header">Nueva Solicitud</div>', unsafe_allow_html=True)
    unids = execute_read("SELECT unit_number, id_lote FROM unidades")
    with st.form("sol_f"):
        u = st.selectbox("Unidad", [f"{x['id_lote']} - {x['unit_number']}" for x in unids])
        a = st.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.form_submit_button("Enviar"):
            execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'solicitado')", (u.split(" - ")[1], a, st.session_state.user))
            st.toast("Solicitud enviada exitosamente", icon="🔔"); st.rerun()
