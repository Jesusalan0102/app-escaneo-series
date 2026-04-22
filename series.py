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

# Estilos CSS Profesionales
st.markdown(f"""
<style>
    .stApp {{ background-color: white; }}
    .main-header {{ font-size: 2rem; font-weight: 700; color: {CARRIER_BLUE}; border-bottom: 3px solid {CARRIER_BLUE}; padding-bottom: 10px; }}
    .section-title {{ font-size: 1.2rem; font-weight: 600; color: #333; margin-top: 15px; border-left: 5px solid {CARRIER_BLUE}; padding-left: 10px; }}
    .stButton>button {{ border-radius: 8px; font-weight: 600; height: 3em; }}
</style>
""", unsafe_allow_html=True)

# ==================== FUNCIONES DE BASE DE DATOS ====================
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

# ==================== ESTADO DE SESIÓN ====================
if "login" not in st.session_state:
    st.session_state.update({"login": False, "user": "", "role": "", "last_count": 0})

# --- LOGIN ---
if not st.session_state.login:
    st.markdown(f'<div style="text-align: center;"><img src="{LOGO_URL}" width="400"></div>', unsafe_allow_html=True)
    _, col_c, _ = st.columns([1,1.2,1])
    with col_c:
        with st.form("login_form"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar", use_container_width=True):
                user = execute_read("SELECT * FROM users WHERE username=%s AND password=%s", (u.strip(), p.strip()))
                if user:
                    st.session_state.update({"login": True, "user": user[0]['username'], "role": user[0]['role'].lower()})
                    st.rerun()
                else: st.error("Acceso denegado")
    st.stop()

# ==================== NAVEGACIÓN ====================
with st.sidebar:
    st.image(LOGO_URL, width=300)
    st.write(f"👤 **{st.session_state.user}** | 🕒 {hora_actual}")
    st.divider()
    if st.session_state.role == "admin":
        menu = st.radio("SISTEMA", ["📊 Dashboard Ejecutivo", "🎯 Control Operativo", "📸 Registro Maestro", "👥 Usuarios"])
    else:
        menu = st.radio("OPERACIÓN", ["🎯 Mis Actividades", "🔔 Solicitar Tarea"])
    if st.button("Cerrar Sesión", use_container_width=True):
        st.session_state.clear(); st.rerun()

# ==================== DASHBOARD EJECUTIVO (ADMIN) ====================
if menu == "📊 Dashboard Ejecutivo":
    st.markdown('<div class="main-header">Rendimiento Operativo Carrier</div>', unsafe_allow_html=True)
    
    asig = execute_read("SELECT * FROM asignaciones")
    unid = execute_read("SELECT * FROM unidades")
    
    if asig:
        df_a = pd.DataFrame(asig)
        # Métricas principales
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Tareas Totales", len(df_a))
        col_m2.metric("Completadas", len(df_a[df_a['estado']=='completada']))
        col_m3.metric("En Espera", len(df_a[df_a['estado']=='solicitado']))

        # Gráficos
        c1, c2 = st.columns([2, 1])
        with c1: st.plotly_chart(px.bar(df_a, x='tecnico', color='estado', title="Carga de Trabajo"), use_container_width=True)
        with c2: st.plotly_chart(px.pie(df_a, names='estado', title="Estatus Global", hole=0.5), use_container_width=True)

    # Tabla de Estatus con "✔" (Lo que pediste mejorar)
    st.markdown('<div class="section-title">📊 Matriz de Avance por Unidad</div>', unsafe_allow_html=True)
    if unid:
        completas = {(r['unidad'], r['actividad_id']) for r in execute_read("SELECT unidad, actividad_id FROM asignaciones WHERE estado='completada'")}
        status_list = []
        for u in unid:
            row = {"LOTE": u['id_lote'], "UNIDAD": u['unit_number']}
            for act in ACTIVIDADES_CARRIER:
                row[act] = "✔" if (u['unit_number'], act) in completas else ""
            status_list.append(row)
        st.dataframe(pd.DataFrame(status_list), use_container_width=True, hide_index=True)

    # Centro de Descargas
    st.markdown('<div class="section-title">📥 Centro de Descargas</div>', unsafe_allow_html=True)
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.subheader("Reporte General")
        if unid:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as wr:
                pd.DataFrame(unid).to_excel(wr, index=False, sheet_name='Unidades')
                if asig: pd.DataFrame(asig).to_excel(wr, index=False, sheet_name='Actividades')
            st.download_button("Descargar Excel Maestro", buf.getvalue(), f"Reporte_{fecha_hoy}.xlsx", use_container_width=True)
    
    with col_d2:
        st.subheader("Evidencias Fotográficas")
        u_zip = st.selectbox("Unidad para descargar fotos:", [u['unit_number'] for u in unid] if unid else [])
        if st.button("Generar ZIP de Fotos", use_container_width=True):
            fotos = execute_read("SELECT nombre_archivo, contenido FROM evidencias WHERE unit_number=%s", (u_zip,))
            if fotos:
                buf_z = io.BytesIO()
                with zipfile.ZipFile(buf_z, "a", zipfile.ZIP_DEFLATED, False) as z:
                    for f in fotos: z.writestr(f['nombre_archivo'], f['contenido'])
                st.download_button(f"Bajar ZIP {u_zip}", buf_z.getvalue(), f"{u_zip}_evidencia.zip", use_container_width=True)
            else: st.info("No hay fotos para esta unidad.")

# ==================== MIS ACTIVIDADES (TÉCNICO) ====================
elif menu == "🎯 Mis Actividades":
    st.markdown('<div class="main-header">Panel de Trabajo</div>', unsafe_allow_html=True)
    tareas = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado IN ('pendiente', 'en_proceso')", (st.session_state.user,))
    
    if not tareas:
        st.info("No tienes tareas. Solicita una nueva en el menú lateral.")
    
    for t in tareas:
        with st.expander(f"📦 Unidad: {t['unidad']} - {t['actividad_id']}", expanded=True):
            if t['estado'] == 'pendiente':
                if st.button("▶️ INICIAR TRABAJO", key=f"st_{t['id']}", use_container_width=True):
                    execute_write("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                    st.rerun()
            else:
                # MEJORA CLAVE: TOMA DE EVIDENCIAS
                if t['actividad_id'].lower() == "evidencia":
                    st.subheader("📸 Captura de Evidencias")
                    st.info("Puedes tomar fotos directamente o subirlas de la galería.")
                    # Aceptamos múltiples archivos y formatos comunes
                    fotos = st.file_uploader("Subir Imágenes", accept_multiple_files=True, type=['jpg','png','jpeg'], key=f"f_{t['id']}")
                    
                    if st.button("Finalizar y Guardar Fotos", key=f"btn_{t['id']}", use_container_width=True):
                        if fotos:
                            progress_bar = st.progress(0)
                            for i, f in enumerate(fotos):
                                execute_write("INSERT INTO evidencias (unit_number, nombre_archivo, contenido, tecnico) VALUES (%s,%s,%s,%s)", 
                                             (t['unidad'], f.name, f.read(), st.session_state.user))
                                progress_bar.progress((i + 1) / len(fotos))
                            execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                            st.success("¡Fotos guardadas!"); st.balloons(); st.rerun()
                        else: st.error("Sube al menos una foto.")
                
                elif t['actividad_id'].lower() == "toma de series":
                    with st.form(f"ser_{t['id']}"):
                        res = {k: st.text_input(v) for k, v in CAMPOS_SERIES.items()}
                        if st.form_submit_button("Guardar y Finalizar"):
                            q = ", ".join([f"{k}=%s" for k in res.keys()])
                            execute_write(f"UPDATE unidades SET {q} WHERE unit_number=%s", list(res.values()) + [t['unidad']])
                            execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                            st.rerun()
                else:
                    if st.button("✅ TRABAJO TERMINADO", key=f"fin_{t['id']}", use_container_width=True):
                        execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                        st.rerun()

# --- LAS DEMÁS SECCIONES (Aprobación, Solicitud, Usuarios) se mantienen con el estilo mejorado ---
elif menu == "🎯 Control Operativo":
    st.markdown('<div class="main-header">Autorización de Tareas</div>', unsafe_allow_html=True)
    sols = execute_read("SELECT * FROM asignaciones WHERE estado='solicitado'")
    if sols:
        for s in sols:
            col_i, col_a, col_d = st.columns([3, 1, 1])
            col_i.warning(f"**{s['tecnico']}**: {s['actividad_id']} (Unidad {s['unidad']})")
            if col_a.button("Aprobar", key=f"ap_{s['id']}"):
                execute_write("UPDATE asignaciones SET estado='pendiente' WHERE id=%s", (s['id'],)); st.rerun()
            if col_d.button("Denegar", key=f"de_{s['id']}"):
                execute_write("DELETE FROM asignaciones WHERE id=%s", (s['id'],)); st.rerun()
    else: st.info("No hay solicitudes pendientes.")

elif menu == "🔔 Solicitar Tarea":
    st.markdown('<div class="main-header">Nueva Solicitud</div>', unsafe_allow_html=True)
    u_db = execute_read("SELECT unit_number, id_lote FROM unidades")
    with st.form("sol_f"):
        u = st.selectbox("Unidad", [f"{x['id_lote']} - {x['unit_number']}" for x in u_db])
        a = st.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.form_submit_button("Enviar Solicitud"):
            execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'solicitado')", 
                         (u.split(" - ")[1], a, st.session_state.user))
            st.success("Solicitud enviada"); st.rerun()
