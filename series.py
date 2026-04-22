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

# Configuración de Hora Local (Tijuana, B.C.)
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

# Estilos CSS (Originales + Mejoras)
st.markdown(f"""
<style>
    .stApp {{ background-color: white; }}
    .main-header {{ 
        font-size: 2.2rem; font-weight: 700; color: {CARRIER_BLUE}; 
        border-bottom: 3px solid {CARRIER_BLUE}; padding-bottom: 10px; margin-bottom: 25px; 
    }}
    .section-title {{ 
        font-size: 1.3rem; font-weight: 600; color: #333; 
        margin-top: 20px; border-left: 5px solid {CARRIER_BLUE}; 
        padding-left: 15px; margin-bottom: 15px; 
    }}
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
            cur.close()
            conn.close()
            return True
        except Exception as e:
            st.error(f"Error en la base de datos: {e}")
            return False
    return False

# ==================== ESTADO DE SESIÓN ====================
if "login" not in st.session_state:
    st.session_state.update({"login": False, "user": "", "role": "", "last_count": 0})

# ==================== LOGIN (Original) ====================
if not st.session_state.login:
    st.markdown(f'<div style="text-align: center; padding: 50px;"><img src="{LOGO_URL}" width="600"></div>', unsafe_allow_html=True)
    col_l, col_c, col_r = st.columns([1,1.5,1])
    with col_c:
        with st.form("login_form"):
            st.markdown(f"<h3 style='text-align:center; color:{CARRIER_BLUE}'>Panel de Acceso</h3>", unsafe_allow_html=True)
            u_log = st.text_input("Usuario")
            p_log = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar al Sistema", use_container_width=True):
                user = execute_read("SELECT * FROM users WHERE username=%s AND password=%s", (u_log.strip(), p_log.strip()))
                if user:
                    st.session_state.update({
                        "login": True, 
                        "user": user[0]['username'],
                        "role": user[0]['role'].lower()
                    })
                    st.rerun()
                else: 
                    st.error("Credenciales incorrectas")
    st.stop()

# ==================== NAVEGACIÓN ====================
with st.sidebar:
    st.image(LOGO_URL, width=400)
    st.markdown(f"🕒 **Hora local:** {hora_actual}")
    st.markdown("---")
    st.write(f"👤 **Usuario:** {st.session_state.user}")
    
    if st.session_state.role == "admin":
        menu = st.radio("MENÚ PRINCIPAL", 
                       ["📊 Dashboard Ejecutivo", "🎯 Control de Asignaciones", 
                        "📸 Registro de Unidades", "👥 Gestión de Usuarios"])
    else:
        menu = st.radio("ÁREA DE TRABAJO", ["🎯 Mis Tareas", "🔔 Nueva Solicitud"])
    
    st.markdown("---")
    if st.button("Cerrar Sesión Segura", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ==================== DASHBOARD EJECUTIVO (Admin) ====================
if menu == "📊 Dashboard Ejecutivo":
    st.markdown(f'<div class="time-badge">Tijuana: {hora_actual}</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-header">Panel de Rendimiento Operativo</div>', unsafe_allow_html=True)
    
    asig = execute_read("SELECT * FROM asignaciones")
    unid = execute_read("SELECT * FROM unidades")
    
    if asig:
        df_a = pd.DataFrame(asig)
        stats = df_a.groupby('tecnico').agg(
            Total=('id', 'count'),
            Completadas=('estado', lambda x: (x == 'completada').sum()),
            En_Curso=('estado', lambda x: (x == 'en_proceso').sum()),
            Pendientes=('estado', lambda x: (x == 'pendiente').sum())
        ).reset_index()
        stats['Rendimiento'] = ((stats['Completadas'] / stats['Total']) * 100).round(0).astype(int)

        st.markdown('<div class="section-title">Estadísticas por Técnico</div>', unsafe_allow_html=True)
        st.dataframe(stats.sort_values(by='Total', ascending=False), use_container_width=True, hide_index=True)
        
        c1, c2 = st.columns([2, 1])
        with c1:
            st.plotly_chart(px.bar(df_a, x='tecnico', color='estado', title="Carga de Trabajo"), use_container_width=True)
        with c2:
            st.plotly_chart(px.pie(df_a, names='estado', title="Estado Global", hole=0.5), use_container_width=True)

    # --- TABLA DE ESTATUS (Original ✔) ---
    st.markdown('<div class="section-title">📊 Estatus de Proceso por Unidad</div>', unsafe_allow_html=True)
    if unid:
        completadas_raw = execute_read("SELECT unidad, actividad_id FROM asignaciones WHERE estado = 'completada'")
        completed_set = {(row['unidad'], row['actividad_id']) for row in completadas_raw}
        status_data = []
        for u in unid:
            row_status = {"LOTE": u['id_lote'], "#económico": u['unit_number']}
            for act in ACTIVIDADES_CARRIER:
                row_status[act] = "✔" if (u['unit_number'], act) in completed_set else ""
            status_data.append(row_status)
        st.dataframe(pd.DataFrame(status_data), use_container_width=True, hide_index=True)

    # --- NUEVA SECCIÓN: DESCARGA DE EVIDENCIAS EN ZIP ---
    st.markdown('<div class="section-title">📂 Descarga de Evidencias (Carpeta por Unidad)</div>', unsafe_allow_html=True)
    if unid:
        u_sel_ev = st.selectbox("Unidad para descargar fotos:", [u['unit_number'] for u in unid])
        ev_archivos = execute_read("SELECT nombre_archivo, contenido FROM evidencias WHERE unit_number = %s", (u_sel_ev,))
        if ev_archivos:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for ev in ev_archivos:
                    zip_file.writestr(ev['nombre_archivo'], ev['contenido'])
            st.download_button(f"📥 Descargar ZIP Unidad {u_sel_ev}", buf.getvalue(), f"{u_sel_ev}_evidencia.zip", "application/zip")
        else:
            st.info("Sin fotos para esta unidad.")

    # --- REPORTE MAESTRO EXCEL (Original Restaurado) ---
    st.markdown('<div class="section-title">📥 Reportes y Descargas</div>', unsafe_allow_html=True)
    if unid:
        df_u = pd.DataFrame(unid)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_u.to_excel(writer, index=False, sheet_name='Series_Unidades')
            if asig: df_a.to_excel(writer, index=False, sheet_name='Actividades')
        st.download_button("📊 Descargar Reporte Maestro General (Excel)", buffer.getvalue(), f"Carrier_Reporte_{fecha_hoy}.xlsx", use_container_width=True)

        for lote in sorted(df_u['id_lote'].unique()):
            with st.expander(f"📦 Lote: {lote}"):
                st.table(df_u[df_u['id_lote']==lote][['unit_number'] + list(CAMPOS_SERIES.keys())])

# ==================== CONTROL DE ASIGNACIONES (Admin) ====================
elif menu == "🎯 Control de Asignaciones":
    st.markdown('<div class="main-header">Gestión de Órdenes</div>', unsafe_allow_html=True)
    sols = execute_read("SELECT * FROM asignaciones WHERE estado='solicitado'")
    
    # Lógica de Sonido (Original)
    if len(sols) > st.session_state.last_count:
        st.markdown(f'<audio autoplay><source src="{SOUND_URL}" type="audio/mp3"></audio>', unsafe_allow_html=True)
    st.session_state.last_count = len(sols)

    for s in sols:
        col_inf, col_ap, col_den = st.columns([4, 1, 1])
        with col_inf:
            st.warning(f"**{s['tecnico']}** solicita **{s['actividad_id']}** - Unidad: **{s['unidad']}**")
            dup = execute_read("SELECT tecnico FROM asignaciones WHERE unidad=%s AND actividad_id=%s AND estado='completada'", (s['unidad'], s['actividad_id']))
            if dup: st.error(f"⚠️ YA COMPLETADO POR {dup[0]['tecnico']}")
        
        if col_ap.button("✅ Aprobar", key=f"ap_{s['id']}"):
            execute_write("UPDATE asignaciones SET estado='pendiente' WHERE id=%s", (s['id'],))
            st.rerun()
        if col_den.button("❌ Borrar", key=f"de_{s['id']}"):
            execute_write("DELETE FROM asignaciones WHERE id=%s", (s['id'],))
            st.rerun()

    # Asignación Manual (Original)
    st.markdown('<div class="section-title">Asignación Directa</div>', unsafe_allow_html=True)
    u_db = execute_read("SELECT unit_number, id_lote FROM unidades")
    t_db = execute_read("SELECT username FROM users WHERE role='tecnico'")
    with st.form("manual_assign"):
        c1, c2, c3 = st.columns(3)
        u_sel = c1.selectbox("Unidad", [f"{x['id_lote']} - {x['unit_number']}" for x in u_db])
        t_sel = c2.selectbox("Técnico", [x['username'] for x in t_db])
        a_sel = c3.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.form_submit_button("Crear Orden"):
            execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s,%s,%s,'pendiente')", (u_sel.split(" - ")[1], a_sel, t_sel))
            st.rerun()

# ==================== MIS TAREAS (Técnico) ====================
elif menu == "🎯 Mis Tareas":
    st.markdown('<div class="main-header">Mis Actividades</div>', unsafe_allow_html=True)
    tareas = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado IN ('pendiente', 'en_proceso')", (st.session_state.user,))
    
    if not tareas:
        st.info("No tienes tareas asignadas.")
    
    for t in tareas:
        with st.expander(f"📦 {t['unidad']} - {t['actividad_id']}"):
            if t['estado'] == 'pendiente':
                if st.button("▶️ Iniciar", key=f"st_{t['id']}", use_container_width=True):
                    execute_write("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                    st.rerun()
            else:
                # CASO EVIDENCIA (Mejorado con Carga de 50 fotos)
                if t['actividad_id'].lower() == "evidencia":
                    archivos = st.file_uploader("Cargar Fotos (Máximo 50)", accept_multiple_files=True, type=['jpg','png','jpeg'], key=f"f_{t['id']}")
                    if st.button("Guardar Evidencia y Finalizar", key=f"btn_{t['id']}"):
                        if archivos:
                            bar = st.progress(0)
                            for i, arc in enumerate(archivos):
                                execute_write("INSERT INTO evidencias (unit_number, nombre_archivo, contenido, tecnico) VALUES (%s,%s,%s,%s)", 
                                             (t['unidad'], arc.name, arc.read(), st.session_state.user))
                                bar.progress((i+1)/len(archivos))
                            execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                            st.success("Archivos guardados correctamente.")
                            st.rerun()
                
                # CASO TOMA DE SERIES (Original Restaurado)
                elif t['actividad_id'].lower() == "toma de series":
                    with st.form(f"ser_{t['id']}"):
                        res = {k: st.text_input(v) for k, v in CAMPOS_SERIES.items()}
                        if st.form_submit_button("Guardar Series"):
                            set_q = ", ".join([f"{k}=%s" for k in res.keys()])
                            execute_write(f"UPDATE unidades SET {set_q} WHERE unit_number=%s", list(res.values()) + [t['unidad']])
                            execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                            st.rerun()
                
                else:
                    if st.button("✅ Terminar Actividad", key=f"f_{t['id']}"):
                        execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                        st.rerun()

# ==================== NUEVA SOLICITUD (Técnico) ====================
elif menu == "🔔 Nueva Solicitud":
    st.markdown('<div class="main-header">Solicitar Actividad</div>', unsafe_allow_html=True)
    u_db = execute_read("SELECT unit_number, id_lote FROM unidades")
    with st.form("sol_f"):
        u_sel = st.selectbox("Unidad", [f"{x['id_lote']} - {x['unit_number']}" for x in u_db])
        a_sel = st.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.form_submit_button("Enviar Solicitud"):
            execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'solicitado')", (u_sel.split(" - ")[1], a_sel, st.session_state.user))
            st.toast("Solicitud enviada")
            st.rerun()

# ==================== REGISTRO DE UNIDADES (Original Restaurado) ====================
elif menu == "📸 Registro de Unidades":
    st.markdown('<div class="main-header">Registro Maestro de Unidades</div>', unsafe_allow_html=True)
    with st.form("reg_u"):
        col1, col2 = st.columns(2)
        u_num = col1.text_input("Número Económico")
        l_num = col1.text_input("Número de Lote")
        campo = col2.selectbox("Campo a Registrar", ["Ninguno"] + list(CAMPOS_SERIES.keys()))
        valor = col2.text_input("Valor del Serial")
        if st.form_submit_button("Guardar Registro"):
            if campo != "Ninguno":
                execute_write(f"INSERT INTO unidades (unit_number, id_lote, {campo}) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE id_lote=%s, {campo}=%s", (u_num, l_num, valor, l_num, valor))
            else:
                execute_write("INSERT INTO unidades (unit_number, id_lote) VALUES (%s,%s) ON DUPLICATE KEY UPDATE id_lote=%s", (u_num, l_num, l_num))
            st.success("✅ Registro guardado")
            st.rerun()

# ==================== GESTIÓN DE USUARIOS (Original Restaurado) ====================
elif menu == "👥 Gestión de Usuarios":
    st.markdown('<div class="main-header">Usuarios del Sistema</div>', unsafe_allow_html=True)
    with st.form("u_f"):
        n_u = st.text_input("Nombre de Usuario")
        n_p = st.text_input("Contraseña", type="password")
        n_r = st.selectbox("Rol", ["tecnico", "admin"])
        if st.form_submit_button("Crear Usuario"):
            execute_write("INSERT INTO users (username, password, role) VALUES (%s,%s,%s)", (n_u, n_p, n_r))
            st.success("Usuario creado")
            st.rerun()

