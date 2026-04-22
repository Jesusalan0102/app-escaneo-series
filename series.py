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

# Estilos CSS
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

# ==================== ESTADO DE SESIÓN ====================
if "login" not in st.session_state:
    st.session_state.update({"login": False, "user": "", "role": "", "last_count": 0})

if not st.session_state.login:
    st.markdown(f'<div style="text-align: center; padding: 50px;"><img src="{LOGO_URL}" width="600"></div>', unsafe_allow_html=True)
    _, col_c, _ = st.columns([1,1.5,1])
    with col_c:
        u_log = st.text_input("Usuario")
        p_log = st.text_input("Contraseña", type="password")
        if st.button("Ingresar", use_container_width=True):
            user = execute_read("SELECT * FROM users WHERE username=%s AND password=%s", (u_log.strip(), p_log.strip()))
            if user:
                st.session_state.update({"login": True, "user": user[0]['username'], "role": user[0]['role'].lower()})
                st.rerun()
            else: st.error("Acceso incorrecto")
    st.stop()

# ==================== NAVEGACIÓN ====================
with st.sidebar:
    st.image(LOGO_URL, width=400)
    st.write(f"👤 **{st.session_state.user}** | {hora_actual}")
    st.divider()
    if st.session_state.role == "admin":
        menu = st.radio("MENÚ", ["📊 Dashboard", "🎯 Asignaciones", "📸 Unidades", "👥 Usuarios"])
    else:
        menu = st.radio("MENÚ", ["🎯 Mis Tareas", "🔔 Nueva Solicitud"])
    if st.button("Salir"): st.session_state.clear(); st.rerun()

# ==================== LÓGICA DE MENÚS ====================

if menu == "📊 Dashboard":
    st.markdown('<div class="main-header">Panel Operativo</div>', unsafe_allow_html=True)
    unid = execute_read("SELECT * FROM unidades")
    
    # Matriz de Estatus con Contador de Fotos integrado
    st.markdown('<div class="section-title">📊 Matriz de Avance y Evidencias</div>', unsafe_allow_html=True)
    if unid:
        conteo_f = execute_read("SELECT unit_number, COUNT(*) as total FROM evidencias GROUP BY unit_number")
        dict_f = {r['unit_number']: r['total'] for r in conteo_f}
        completas = {(r['unidad'], r['actividad_id']) for r in execute_read("SELECT unidad, actividad_id FROM asignaciones WHERE estado='completada'")}
        
        res_list = []
        for u in unid:
            row = {"LOTE": u['id_lote'], "UNIDAD": u['unit_number'], "📸 FOTOS": dict_f.get(u['unit_number'], 0)}
            for act in ACTIVIDADES_CARRIER:
                row[act] = "✔" if (u['unit_number'], act) in completas else ""
            res_list.append(row)
        st.dataframe(pd.DataFrame(res_list), use_container_width=True, hide_index=True)

    # Descarga ZIP por Selección
    st.markdown('<div class="section-title">📥 Descarga de Evidencias</div>', unsafe_allow_html=True)
    if unid:
        u_sel = st.selectbox("Seleccionar Unidad para descargar fotos:", [u['unit_number'] for u in unid])
        cant = dict_f.get(u_sel, 0)
        if st.button(f"Generar ZIP ({cant} fotos)", disabled=(cant==0)):
            fotos = execute_read("SELECT nombre_archivo, contenido FROM evidencias WHERE unit_number=%s", (u_sel,))
            bz = io.BytesIO()
            with zipfile.ZipFile(bz, "a", zipfile.ZIP_DEFLATED) as z:
                for f in fotos: z.writestr(f['nombre_archivo'], f['contenido'])
            st.download_button(f"Descargar ZIP {u_sel}", bz.getvalue(), f"{u_sel}_evidencias.zip")

elif menu == "🎯 Asignaciones":
    st.markdown('<div class="main-header">Autorizaciones</div>', unsafe_allow_html=True)
    sols = execute_read("SELECT * FROM asignaciones WHERE estado='solicitado'")
    for s in sols:
        col_t, col_a, col_d = st.columns([4, 1, 1])
        col_t.warning(f"**{s['tecnico']}** solicita: {s['actividad_id']} (Unidad: {s['unidad']})")
        if col_a.button("✅ Autorizar", key=f"a_{s['id']}"):
            execute_write("UPDATE asignaciones SET estado='pendiente' WHERE id=%s", (s['id'],))
            st.toast(f"Tarea de {s['tecnico']} autorizada correctamente", icon="✅")
            st.rerun()
        if col_d.button("❌ Rechazar", key=f"r_{s['id']}"):
            execute_write("DELETE FROM asignaciones WHERE id=%s", (s['id'],))
            st.toast("Solicitud eliminada", icon="🗑️")
            st.rerun()

elif menu == "🎯 Mis Tareas":
    st.markdown('<div class="main-header">Mis Actividades</div>', unsafe_allow_html=True)
    tareas = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado IN ('pendiente', 'en_proceso')", (st.session_state.user,))
    
    for t in tareas:
        with st.expander(f"📦 UNIDAD: {t['unidad']} - {t['actividad_id']}", expanded=True):
            if t['estado'] == 'pendiente':
                if st.button("▶️ INICIAR TRABAJO", key=f"st_{t['id']}", use_container_width=True):
                    execute_write("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                    st.toast("Cronómetro iniciado", icon="⏱️")
                    st.rerun()
            else:
                if t['actividad_id'].lower() == "evidencia":
                    st.info("💡 Consejo: Puedes tomar una foto, esperar a que cargue y tomar otra, o seleccionar varias de tu galería.")
                    # Soporte múltiple para simular flujo tipo WhatsApp
                    archivos = st.file_uploader("Capturar Evidencias (Cámara/Galería)", accept_multiple_files=True, type=['jpg','png','jpeg'], key=f"cam_{t['id']}")
                    
                    if st.button("Finalizar y Enviar Todo", key=f"env_{t['id']}", use_container_width=True):
                        if archivos:
                            prog = st.progress(0)
                            for i, f in enumerate(archivos):
                                execute_write("INSERT INTO evidencias (unit_number, nombre_archivo, contenido, tecnico) VALUES (%s,%s,%s,%s)", 
                                             (t['unidad'], f.name, f.read(), st.session_state.user))
                                prog.progress((i + 1) / len(archivos))
                            execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                            st.toast("Evidencias guardadas con éxito", icon="📸")
                            st.rerun()
                        else: st.warning("Debes capturar al menos una foto.")
                
                elif t['actividad_id'].lower() == "toma de series":
                    with st.form(f"f_ser_{t['id']}"):
                        res = {k: st.text_input(v) for k, v in CAMPOS_SERIES.items()}
                        if st.form_submit_button("Guardar Series y Finalizar"):
                            q = ", ".join([f"{k}=%s" for k in res.keys()])
                            execute_write(f"UPDATE unidades SET {q} WHERE unit_number=%s", list(res.values()) + [t['unidad']])
                            execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                            st.toast("Series registradas exitosamente", icon="💾")
                            st.rerun()
                else:
                    if st.button("✅ TERMINAR ACTIVIDAD", key=f"end_{t['id']}", use_container_width=True):
                        execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']))
                        st.toast("¡Buen trabajo! Actividad finalizada", icon="🎉")
                        st.rerun()

elif menu == "🔔 Nueva Solicitud":
    st.markdown('<div class="main-header">Solicitar Nueva Tarea</div>', unsafe_allow_html=True)
    unids = execute_read("SELECT unit_number, id_lote FROM unidades")
    with st.form("sol_f"):
        u = st.selectbox("Unidad", [f"{x['id_lote']} - {x['unit_number']}" for x in unids])
        a = st.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.form_submit_button("Enviar Solicitud al Administrador"):
            execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'solicitado')", 
                         (u.split(" - ")[1], a, st.session_state.user))
            st.toast("Solicitud enviada. Espera la autorización del admin.", icon="🔔")

elif menu == "📸 Unidades":
    st.markdown('<div class="main-header">Registro Maestro</div>', unsafe_allow_html=True)
    # Lógica de ON DUPLICATE KEY para evitar errores de registro
    with st.form("reg_u"):
        c1, c2 = st.columns(2)
        u_n = c1.text_input("Económico")
        l_n = c1.text_input("Lote")
        campo = c2.selectbox("Campo", list(CAMPOS_SERIES.keys()), format_func=lambda x: CAMPOS_SERIES[x])
        val = c2.text_input("Valor")
        if st.form_submit_button("Guardar Registro"):
            if execute_write(f"INSERT INTO unidades (unit_number, id_lote, {campo}) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE id_lote=%s, {campo}=%s", (u_n, l_n, val, l_n, val)):
                st.toast(f"Unidad {u_n} actualizada", icon="💾")

elif menu == "👥 Usuarios":
    st.markdown('<div class="main-header">Gestión de Usuarios</div>', unsafe_allow_html=True)
    # Visualización de tabla de usuarios
    users = execute_read("SELECT id, username, role FROM users")
    if users:
        df_u = pd.DataFrame(users)
        st.table(df_u)
        
    with st.form("new_u"):
        nu = st.text_input("Usuario")
        np = st.text_input("Pass", type="password")
        nr = st.selectbox("Rol", ["tecnico", "admin"])
        if st.form_submit_button("Crear"):
            execute_write("INSERT INTO users (username, password, role) VALUES (%s,%s,%s)", (nu, np, nr))
            st.toast(f"Usuario {nu} creado", icon="👤")
            st.rerun()
