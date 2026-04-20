import streamlit as st
import pandas as pd
import mysql.connector
import plotly.express as px
from datetime import datetime
import io
import pytz 
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
    "Cableado", "Cerrado", "Corriendo", "Inspección", "Pretrip", 
    "Programación", "Soldadura en Sitio", "Vacíos", "Accesorios", 
    "Toma de Valores", "Evidencia", "Standby", "Toma de Series"
]

# --- ESTILOS CSS ---
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
    except: 
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

# ==================== LOGIN ====================
if not st.session_state.login:
    st.markdown(f'<div style="text-align: center; padding: 50px;"><img src="{LOGO_URL}" width="600"></div>', unsafe_allow_html=True)
    col_l, col_c, col_r = st.columns([1,1.5,1])
    with col_c:
        u_log = st.text_input("Usuario")
        p_log = st.text_input("Contraseña", type="password")
        if st.button("Ingresar al Sistema", use_container_width=True):
            user = execute_read("SELECT * FROM users WHERE username=%s AND password=%s", (u_log.strip(), p_log.strip()))
            if user:
                st.session_state.update({
                    "login": True, 
                    "user": user[0]['username'],   # Se guarda tal como está en BD
                    "role": user[0]['role'].lower()
                })
                st.success(f"Bienvenido, {user[0]['username']}")
                st.rerun()
            else: 
                st.error("Credenciales incorrectas")
    st.stop()

# ==================== NAVEGACIÓN ====================
with st.sidebar:
    st.image(LOGO_URL, width=400)
    st.markdown(f"🕒 **Hora local:** {hora_actual}")
    st.markdown("---")
    st.write(f"👤 **Usuario:** {st.session_state.user}")   # ← Respeta mayúsculas y minúsculas
    st.write(f"🏢 **Sede:** Tijuana, B.C.")
    st.markdown("---")
    
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

# ==================== DASHBOARD EJECUTIVO ====================
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
        st.dataframe(
            stats.sort_values(by='Total', ascending=False),
            use_container_width=True, 
            hide_index=True,
            column_config={
                "tecnico": "Nombre del Técnico",
                "Total": st.column_config.NumberColumn("Asignadas", format="%d 📋"),
                "Rendimiento": st.column_config.ProgressColumn("Rendimiento", format="%.0f%%", min_value=0, max_value=100),
                "Completadas": "Completadas ✅", 
                "En_Curso": "En Proceso ⚙️", 
                "Pendientes": "Pendientes ⏳"
            }
        )
        
        c1, c2 = st.columns([2, 1])
        with c1:
            st.plotly_chart(px.bar(df_a, x='tecnico', color='estado', title="Distribución de Carga de Trabajo",
                                   color_discrete_map={'completada': '#2ECC71', 'en_proceso': '#3498DB', 'pendiente': '#F1C40F', 'solicitado': '#E74C3C'}), 
                            use_container_width=True)
        with c2:
            st.plotly_chart(px.pie(df_a, names='estado', title="Estado Global", hole=0.5), use_container_width=True)

        st.markdown('<div class="section-title">Historial Completo de Actividades</div>', unsafe_allow_html=True)
        st.dataframe(df_a, use_container_width=True, hide_index=True)

    if unid:
        df_u = pd.DataFrame(unid)
        st.markdown('<div class="section-title">Inventario de Series por Lote</div>', unsafe_allow_html=True)
        for lote in sorted(df_u['id_lote'].unique()):
            with st.expander(f"📦 Ver Lote: {lote}"):
                st.table(df_u[df_u['id_lote']==lote][['unit_number'] + list(CAMPOS_SERIES.keys())])
        
        st.divider()
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_u.to_excel(writer, index=False, sheet_name='Series_Unidades')
            if asig: 
                df_a.to_excel(writer, index=False, sheet_name='Reporte_Actividades')
        
        st.download_button("📥 Descargar Reporte Maestro (Excel)", buffer.getvalue(), f"Reporte_Carrier_{fecha_hoy}.xlsx", use_container_width=True)

# ==================== CONTROL DE ASIGNACIONES ====================
elif menu == "🎯 Control de Asignaciones":
    st.markdown('<div class="main-header">Gestión de Órdenes y Autorizaciones</div>', unsafe_allow_html=True)
    
    sols = execute_read("SELECT * FROM asignaciones WHERE estado='solicitado'")
    if len(sols) > st.session_state.last_count:
        st.markdown(f'<audio autoplay><source src="{SOUND_URL}" type="audio/mp3"></audio>', unsafe_allow_html=True)
        st.toast(f"Nueva solicitud de {sols[-1]['tecnico']}", icon="🔔")
    st.session_state.last_count = len(sols)

    if sols:
        st.markdown('<div class="section-title">Solicitudes por Aprobar</div>', unsafe_allow_html=True)
        for s in sols:
            col_inf, col_ap, col_den = st.columns([4, 1, 1])
            col_inf.warning(f"**Técnico:** {s['tecnico']} | **Actividad:** {s['actividad_id']} | **Unidad:** {s['unidad']}")
            if col_ap.button("✅ Aprobar", key=f"ap_{s['id']}", use_container_width=True):
                if execute_write("UPDATE asignaciones SET estado='pendiente' WHERE id=%s", (s['id'],)):
                    st.success(f"✅ Solicitud de {s['tecnico']} aprobada correctamente")
                    st.balloons()
                    st.rerun()
            if col_den.button("❌ Denegar", key=f"de_{s['id']}", use_container_width=True):
                if execute_write("DELETE FROM asignaciones WHERE id=%s", (s['id'],)):
                    st.error(f"❌ Solicitud de {s['tecnico']} denegada")
                    st.rerun()
    
    st.markdown('<div class="section-title">Asignación Directa de Tarea</div>', unsafe_allow_html=True)
    u_db = execute_read("SELECT unit_number, id_lote FROM unidades")
    t_db = execute_read("SELECT username FROM users WHERE role='tecnico'")
    with st.form("manual_assign"):
        c1, c2, c3 = st.columns(3)
        u_sel = c1.selectbox("Unidad / Lote", [f"{x['id_lote']} - {x['unit_number']}" for x in u_db])
        t_sel = c2.selectbox("Asignar a Técnico", [x['username'] for x in t_db])
        a_sel = c3.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.form_submit_button("Crear Orden de Trabajo", use_container_width=True):
            if execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s,%s,%s,'pendiente')", 
                           (u_sel.split(" - ")[1], a_sel, t_sel)):
                st.success(f"✅ Tarea asignada correctamente a **{t_sel}**")
                st.rerun()

# ==================== MIS TAREAS ====================
elif menu == "🎯 Mis Tareas":
    st.markdown('<div class="main-header">Panel de Actividades</div>', unsafe_allow_html=True)
    
    pendientes = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado='pendiente'", (st.session_state.user,))
    if len(pendientes) > st.session_state.last_count:
        st.markdown(f'<audio autoplay><source src="{SOUND_URL}" type="audio/mp3"></audio>', unsafe_allow_html=True)
        st.toast("Tienes una nueva tarea asignada", icon="🛠️")
    st.session_state.last_count = len(pendientes)

    tareas_activas = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado IN ('pendiente', 'en_proceso')", (st.session_state.user,))
    if not tareas_activas:
        st.info("No tienes actividades pendientes por el momento.")
    else:
        for t in tareas_activas:
            with st.expander(f"📦 Unidad: {t['unidad']} - Actividad: {t['actividad_id']}"):
                if t['estado'] == 'pendiente':
                    if st.button("▶️ Comenzar Trabajo", key=f"start_{t['id']}", use_container_width=True):
                        st_time = datetime.now(tijuana_tz).strftime('%Y-%m-%d %H:%M:%S')
                        if execute_write("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=%s WHERE id=%s", (st_time, t['id'])):
                            st.success("✅ Trabajo iniciado correctamente")
                            st.rerun()
                else:
                    if t['actividad_id'].lower() == "toma de series":
                        with st.form(f"form_series_{t['id']}"):
                            res = {k: st.text_input(v) for k, v in CAMPOS_SERIES.items()}
                            if st.form_submit_button("Finalizar y Guardar Series"):
                                end_time = datetime.now(tijuana_tz).strftime('%Y-%m-%d %H:%M:%S')
                                set_q = ", ".join([f"{k}=%s" for k in res.keys()])
                                execute_write(f"UPDATE unidades SET {set_q} WHERE unit_number=%s", list(res.values()) + [t['unidad']])
                                execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (end_time, t['id']))
                                st.success("🎉 Tarea completada y series guardadas correctamente")
                                st.balloons()
                                st.rerun()
                    elif st.button("✅ Marcar como Terminado", key=f"fin_{t['id']}", use_container_width=True):
                        end_time = datetime.now(tijuana_tz).strftime('%Y-%m-%d %H:%M:%S')
                        if execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (end_time, t['id'])):
                            st.success("🎉 Tarea marcada como completada")
                            st.balloons()
                            st.rerun()

# ==================== NUEVA SOLICITUD ====================
elif menu == "🔔 Nueva Solicitud":
    st.markdown('<div class="main-header">Solicitar Nueva Actividad</div>', unsafe_allow_html=True)
    u_db = execute_read("SELECT unit_number, id_lote FROM unidades")
    with st.form("solicitud_form"):
        u_sel = st.selectbox("Seleccionar Unidad", [f"{x['id_lote']} - {x['unit_number']}" for x in u_db])
        a_sel = st.selectbox("Actividad a Realizar", ACTIVIDADES_CARRIER)
        if st.form_submit_button("Enviar Solicitud al Administrador", use_container_width=True):
            if execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'solicitado')", 
                           (u_sel.split(" - ")[1], a_sel, st.session_state.user)):
                st.success("📨 Solicitud enviada correctamente al administrador")
                st.toast("Esperando aprobación...", icon="⏳")
                st.rerun()

# ==================== OTRAS SECCIONES (Registro y Gestión de Usuarios) ====================
elif menu == "📸 Registro de Unidades":
    st.markdown('<div class="main-header">Captura de Información Técnica</div>', unsafe_allow_html=True)
    with st.form("reg_unidades"):
        c1, c2 = st.columns(2)
        u_num = c1.text_input("Número de Unidad")
        l_num = c1.text_input("Número de Lote")
        campo = c2.selectbox("Campo a Registrar", list(CAMPOS_SERIES.keys()), format_func=lambda x: CAMPOS_SERIES[x])
        valor = c2.text_input("Valor del Serial")
        if st.form_submit_button("Guardar Registro", use_container_width=True):
            if execute_write(f"INSERT INTO unidades (unit_number, id_lote, {campo}) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE {campo}=%s", (u_num, l_num, valor, valor)):
                st.success("✅ Registro guardado correctamente en la base de datos")
                st.toast("Datos actualizados", icon="💾")

elif menu == "👥 Gestión de Usuarios":
    st.markdown('<div class="main-header">Administración de Usuarios</div>', unsafe_allow_html=True)
    col_u, col_l = st.columns([2, 1])
    with col_u.form("new_user_form"):
        st.write("Registrar Nuevo Usuario")
        new_u = st.text_input("Usuario")
        new_p = st.text_input("Contraseña", type="password")
        new_r = st.selectbox("Rol del Sistema", ["tecnico", "admin"])
        if st.form_submit_button("Guardar Usuario", use_container_width=True):
            if execute_write("INSERT INTO users (username, password, role) VALUES (%s,%s,%s)", (new_u, new_p, new_r)):
                st.success(f"✅ Usuario **{new_u}** creado correctamente")
                st.rerun()
    with col_l:
        st.write("Usuarios Actuales")
        users_list = execute_read("SELECT username, role FROM users")
        st.table(users_list)
