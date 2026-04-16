import streamlit as st
import pandas as pd
import mysql.connector
import plotly.express as px
from datetime import datetime
import io
import time

# ==================== CONFIGURACIÓN ====================
st.set_page_config(page_title="Carrier Transicold - Sistema de Gestión", layout="wide")

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
    .delete-btn>button {{ background-color: #FF4B4B !important; }}
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
        st.success("Información registrada.")

elif menu == "🎯 Asignación":
    st.subheader("Nueva Asignación")
    u_db = execute_read("SELECT unit_number, id_lote FROM unidades")
    t_db = execute_read("SELECT username FROM users WHERE role='tecnico'")
    
    c1, c2, c3 = st.columns(3)
    u_list = [f"{x['id_lote']} - {x['unit_number']}" for x in u_db] if u_db else []
    u_s = c1.selectbox("Unidad", u_list)
    t_s = c2.selectbox("Técnico", [x['username'] for x in t_db] if t_db else [])
    a_s = c3.selectbox("Actividad", ACTIVIDADES_CARRIER)
    
    if st.button("📌 Asignar"):
        execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'pendiente')", (u_s.split(" - ")[1], a_s, t_s))
        st.success("Tarea asignada")

    st.divider()
    # --- NUEVA SECCIÓN: ELIMINAR/DESASIGNAR ---
    st.subheader("🗑️ Gestionar Asignaciones Activas")
    asig_activas = execute_read("SELECT id, unidad, actividad_id, tecnico, estado FROM asignaciones WHERE estado != 'completada'")
    if asig_activas:
        for a in asig_activas:
            col_info, col_btn = st.columns([4, 1])
            col_info.write(f"**Unidad:** {a['unidad']} | **Actividad:** {a['actividad_id']} | **Técnico:** {a['tecnico']} ({a['estado']})")
            if col_btn.button("Eliminar", key=f"del_{a['id']}"):
                execute_write("DELETE FROM asignaciones WHERE id = %s", (a['id'],))
                st.toast(f"Asignación {a['id']} eliminada")
                st.rerun()
    else:
        st.info("No hay asignaciones pendientes o en proceso para eliminar.")

elif menu == "🎯 Mis Tareas":
    st.subheader(f"Tareas de {st.session_state.user}")
    mis_t = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado!='completada'", (st.session_state.user,))
    if not mis_t: st.write("Sin tareas pendientes.")
    else:
        for t in mis_t:
            with st.expander(f"📦 {t['unidad']} - {t['actividad_id']}"):
                if t['estado'] == 'pendiente':
                    if st.button(f"Iniciar Trabajo #{t['id']}"):
                        execute_write("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=NOW() WHERE id=%s", (t['id'],))
                        st.rerun()
                elif t['actividad_id'] == "toma de series":
                    with st.form(f"form_{t['id']}"):
                        res = {k: st.text_input(v) for k, v in CAMPOS_SERIES.items()}
                        if st.form_submit_button("Guardar"):
                            set_q = ", ".join([f"{k}=%s" for k in res.keys()])
                            execute_write(f"UPDATE unidades SET {set_q} WHERE unit_number=%s", list(res.values()) + [t['unidad']])
                            execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW() WHERE id=%s", (t['id'],))
                            st.rerun()
                else:
                    if st.button(f"Finalizar Tarea #{t['id']}"):
                        execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW() WHERE id=%s", (t['id'],))
                        st.rerun()
    time.sleep(60)
    st.rerun()

elif menu == "📊 Dashboard":
    st.subheader("Dashboard de Control y Métricas")
    res = execute_read("SELECT u.*, a.tecnico, a.actividad_id, a.estado FROM unidades u LEFT JOIN asignaciones a ON u.unit_number = a.unidad")
    
    if res:
        df = pd.DataFrame(res)
        
        # --- MÉTRICAS NUMÉRICAS POR TÉCNICO ---
        st.markdown("### 📈 Resumen Numérico por Técnico")
        df_stats = df.dropna(subset=['tecnico'])
        if not df_stats.empty:
            pivot_stats = df_stats.pivot_table(index='tecnico', columns='estado', values='unit_number', aggfunc='count', fill_value=0).reset_index()
            for col in ['pendiente', 'en_proceso', 'completada']:
                if col not in pivot_stats.columns: pivot_stats[col] = 0
            
            pivot_stats['Total'] = pivot_stats['pendiente'] + pivot_stats['en_proceso'] + pivot_stats['completada']
            st.dataframe(pivot_stats.rename(columns={'tecnico': 'Técnico', 'pendiente': 'Pendientes 🟡', 'en_proceso': 'En Proceso 🔵', 'completada': 'Completadas ✅'}), use_container_width=True, hide_index=True)

        # --- GRÁFICAS ---
        c1, c2 = st.columns(2)
        with c1:
            if not df_stats.empty:
                fig_prod = px.bar(df_stats, x='tecnico', color='estado', title="Carga por Técnico", barmode='group')
                st.plotly_chart(fig_prod, use_container_width=True)
        with c2:
            st.plotly_chart(px.pie(df, names='estado', title="Estado Global"), use_container_width=True)

        # --- VISTA POR LOTES ---
        st.write("### 🏗️ Jerarquía por Lotes")
        for lote in df['id_lote'].unique():
            with st.expander(f"LOTE: {lote}"):
                st.table(df[df['id_lote']==lote][['unit_number', 'tecnico', 'actividad_id', 'estado']])
        
        # --- EXPORTACIÓN ---
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Desglose_General')
            if not df_stats.empty:
                pivot_stats.to_excel(writer, index=False, sheet_name='Metricas_Tecnicos')
        
        st.download_button("📥 Descargar Reporte (Excel)", buffer.getvalue(), f"Reporte_Carrier_{datetime.now().strftime('%Y%m%d')}.xlsx")
    
    time.sleep(60)
    st.rerun()
