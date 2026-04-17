import streamlit as st
import pandas as pd
import mysql.connector
import plotly.express as px
from datetime import datetime
import io
import time

# ==================== CONFIGURACIÓN ====================
st.set_page_config(page_title="Carrier Transicold - Gestión", layout="wide")

CARRIER_BLUE = "#002B5B"
LOGO_URL = "https://raw.githubusercontent.com/Jesusalan0102/app-escaneo-series/main/carrierlogo2.jpeg.jpg"

CAMPOS_SERIES = {
    "vin_number": "VIN NUMBER",
    "reefer_serial": "REEFER SERIAL",
    "reefer_model": "REEFER MODEL",
    "evaporator_serial_mjs11": "EVAPORATOR SERIAL MJS11",
    "evaporator_serial_mjd22": "EVAPORATOR SERIAL MJD22",
    "engine_serial": "ENGINE",
    "compressor_serial": "COMPRESSOR",
    "generator_serial": "GENERATOR",
    "battery_charger_serial": "BATTERY CHARGER"
}

ACTIVIDADES_CARRIER = [
    "Cableado", "Cerrado", "Corriendo", "Inspección", "Pretrip", 
    "Programación", "Soldadura en sitio", "Vacios", "Accesorios", 
    "toma de valores", "Evidencia", "standby", "toma de series"
]

st.markdown(f"""
<style>
    .main-header {{ font-size: 2.3rem; font-weight: bold; color: {CARRIER_BLUE}; text-align: center; margin-bottom: 20px; }}
    .stButton>button {{ width: 100%; border-radius: 5px; height: 3em; background-color: {CARRIER_BLUE}; color: white; }}
    .card {{ background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 5px solid {CARRIER_BLUE}; margin-bottom: 10px; }}
    div[data-testid="stExpander"] {{ border: 1px solid {CARRIER_BLUE}; border-radius: 10px; }}
</style>
""", unsafe_allow_html=True)

# ==================== CONEXIÓN ====================
def get_db_connection():
    return mysql.connector.connect(**st.secrets["db"], autocommit=True)

def execute_read(query, params=None):
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(query, params or ())
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

def execute_write(query, params=None):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(query, params or ())
        return True
    finally:
        cur.close()
        conn.close()

# ==================== LOGIN ====================
if "login" not in st.session_state:
    st.session_state.update({"login": False, "user": "", "role": ""})

if not st.session_state.login:
    st.markdown('<div class="main-header">Acceso Carrier</div>', unsafe_allow_html=True)
    u_log = st.text_input("Usuario").strip()
    p_log = st.text_input("Contraseña", type="password").strip()
    
    if st.button("Entrar"):
        user = execute_read("SELECT * FROM users WHERE LOWER(username)=LOWER(%s) AND password=%s", (u_log, p_log))
        if user:
            st.session_state.update({"login": True, "user": user[0]['username'], "role": user[0]['role'].lower()})
            st.rerun()
        else:
            st.error("Credenciales incorrectas.")
    st.stop()

# ==================== SIDEBAR ====================
with st.sidebar:
    st.image(LOGO_URL, width=150)
    st.write(f"💼 Perfil: **{st.session_state.role.upper()}**")
    st.divider()
    
    is_admin = st.session_state.role == "admin"
    if is_admin:
        menu = st.radio("Menú", ["📸 Registro", "🎯 Asignación", "📊 Dashboard", "👥 Usuarios"])
    else:
        menu = "🎯 Mis Tareas"

    if st.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

# ==================== SECCIONES ====================

if menu == "👥 Usuarios":
    st.subheader("Gestión de Usuarios")
    with st.form("crear_u"):
        nu, np, nr = st.text_input("Usuario"), st.text_input("Pass"), st.selectbox("Rol", ["tecnico", "admin"])
        if st.form_submit_button("Registrar"):
            execute_write("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (nu, np, nr))
            st.success("Usuario creado")

elif menu == "📸 Registro":
    st.markdown('<div class="main-header">REGISTRO DE UNIDADES</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        u_num = st.text_input("Unit Number")
        lote = st.text_input("Lote")
    with c2:
        campo = st.selectbox("Campo", list(CAMPOS_SERIES.keys()), format_func=lambda x: CAMPOS_SERIES[x])
        valor = st.text_input("Valor")
    if st.button("💾 Guardar"):
        execute_write(f"INSERT INTO unidades (unit_number, id_lote, {campo}) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE id_lote=%s, {campo}=%s", (u_num, lote, valor, lote, valor))
        st.success("Información técnica actualizada.")

elif menu == "🎯 Asignación":
    st.markdown('<div class="main-header">ASIGNACIÓN Y GESTIÓN</div>', unsafe_allow_html=True)
    
    # --- PARTE 1: NUEVA ASIGNACIÓN ---
    with st.expander("➕ Nueva Asignación de Tarea", expanded=True):
        u_db = execute_read("SELECT unit_number, id_lote FROM unidades")
        t_db = execute_read("SELECT username FROM users WHERE role='tecnico'")
        
        c1, c2, c3 = st.columns(3)
        u_list = [f"{x['id_lote']} - {x['unit_number']}" for x in u_db] if u_db else []
        u_s = c1.selectbox("Unidad", u_list)
        t_s = c2.selectbox("Técnico", [x['username'] for x in t_db] if t_db else [])
        a_s = c3.selectbox("Actividad", ACTIVIDADES_CARRIER)
        
        if st.button("📌 Confirmar Asignación"):
            execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'pendiente')", (u_s.split(" - ")[1], a_s, t_s))
            st.success("Tarea asignada correctamente.")
            st.rerun()

    st.divider()

    # --- PARTE 2: ELIMINACIÓN (REUBICADO Y FORMATEADO) ---
    st.subheader("🗑️ Control de Tareas Activas")
    asig_activas = execute_read("SELECT id, unidad, actividad_id, tecnico, estado FROM asignaciones WHERE estado != 'completada'")
    
    if asig_activas:
        for a in asig_activas:
            with st.container():
                st.markdown(f"""
                <div class="card">
                    <strong>Unidad:</strong> {a['unidad']} | 
                    <strong>Actividad:</strong> {a['actividad_id']} | 
                    <strong>Técnico:</strong> {a['tecnico']} | 
                    <strong>Estado:</strong> {a['estado'].upper()}
                </div>
                """, unsafe_allow_html=True)
                
                # Botón de eliminación con clave única
                if st.button(f"Eliminar Asignación #{a['id']}", key=f"del_task_{a['id']}", type="secondary"):
                    execute_write("DELETE FROM asignaciones WHERE id = %s", (a['id'],))
                    st.toast(f"Tarea {a['id']} eliminada.")
                    st.rerun()
    else:
        st.info("No hay tareas pendientes por gestionar.")

elif menu == "🎯 Mis Tareas":
    st.subheader(f"Tareas de {st.session_state.user}")
    mis_t = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado!='completada'", (st.session_state.user,))
    if not mis_t: st.write("Sin tareas asignadas.")
    else:
        for t in mis_t:
            with st.expander(f"📦 {t['unidad']} - {t['actividad_id']}"):
                if t['estado'] == 'pendiente':
                    if st.button(f"Iniciar #{t['id']}"):
                        execute_write("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=NOW() WHERE id=%s", (t['id'],))
                        st.rerun()
                elif t['actividad_id'] == "toma de series":
                    with st.form(f"form_{t['id']}"):
                        res = {k: st.text_input(v) for k, v in CAMPOS_SERIES.items()}
                        if st.form_submit_button("Finalizar Registro"):
                            set_q = ", ".join([f"{k}=%s" for k in res.keys()])
                            execute_write(f"UPDATE unidades SET {set_q} WHERE unit_number=%s", list(res.values()) + [t['unidad']])
                            execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW() WHERE id=%s", (t['id'],))
                            st.rerun()
                else:
                    if st.button(f"Marcar como Finalizada #{t['id']}"):
                        execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW() WHERE id=%s", (t['id'],))
                        st.rerun()
    time.sleep(60)
    st.rerun()

elif menu == "📊 Dashboard":
    st.subheader("Métricas de Operación")
    
    # Obtener datos frescos
    unidades_raw = execute_read("SELECT * FROM unidades")
    asig_raw = execute_read("SELECT * FROM asignaciones")
    
    df_unidades = pd.DataFrame(unidades_raw) if unidades_raw else pd.DataFrame()
    df_asig = pd.DataFrame(asig_raw) if asig_raw else pd.DataFrame()

    if not df_asig.empty:
        # Métricas numéricas
        pivot = df_asig.pivot_table(index='tecnico', columns='estado', values='id', aggfunc='count', fill_value=0).reset_index()
        for col in ['pendiente', 'en_proceso', 'completada']:
            if col not in pivot.columns: pivot[col] = 0
        
        st.markdown("#### Resumen de Productividad")
        st.dataframe(pivot.rename(columns={'tecnico': 'Técnico', 'pendiente': 'Pendientes', 'en_proceso': 'En Proceso', 'completada': 'Completadas'}), use_container_width=True, hide_index=True)

        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(px.bar(df_asig, x='tecnico', color='estado', title="Carga por Técnico", barmode='group'), use_container_width=True)
        with c2:
            st.plotly_chart(px.pie(df_asig, names='estado', title="Estado de Tareas"), use_container_width=True)

    # Registro de Series (Independiente)
    st.markdown("#### Registro Técnico de Unidades")
    if not df_unidades.empty:
        st.dataframe(df_unidades, use_container_width=True, hide_index=True)
        
        # Botón de descarga
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            if not df_unidades.empty: df_unidades.to_excel(writer, index=False, sheet_name='Series')
            if not df_asig.empty: df_asig.to_excel(writer, index=False, sheet_name='Asignaciones')
        st.download_button("📥 Exportar a Excel", buffer.getvalue(), f"Reporte_{datetime.now().strftime('%Y%m%d')}.xlsx")

    time.sleep(60)
    st.rerun()
