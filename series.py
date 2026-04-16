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

CAMPOS_UNIDAD = {
    "vin_number": "VIN NUMBER",
    "reefer_serial": "REEFER SERIAL",
    "reefer_model": "REEFER MODEL",
    "evaporator_serial_mjs11": "EVAPORATOR SERIAL MJS11",
    "evaporator_serial_mjd22": "EVAPORATOR SERIAL MJD22",
    "engine_serial": "ENGINE SERIAL",
    "compressor_serial": "COMPRESSOR SERIAL",
    "generator_serial": "GENERATOR SERIAL",
    "battery_charger_serial": "BATTERY CHARGER SERIAL"
}

ID_ACTIVIDAD_SERIES = "Toma de Series"

st.markdown(f"""
<style>
    .main-header {{ font-size: 2.3rem; font-weight: bold; color: {CARRIER_BLUE}; text-align: center; margin-bottom: 20px; }}
    .metric-card {{ background-color: #ffffff; padding: 20px; border-radius: 10px; border-left: 5px solid {CARRIER_BLUE}; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); }}
    .stButton>button {{ width: 100%; border-radius: 5px; height: 3em; background-color: {CARRIER_BLUE}; color: white; }}
    .st-d5 {{ background-color: #f0f2f6; padding: 15px; border-radius: 10px; border: 1px solid #d1d3d4; margin-bottom: 10px; }}
</style>
""", unsafe_allow_html=True)

# ==================== GESTIÓN DE CONEXIÓN (ANTI-ERROR 1226) ====================
def get_db_connection():
    return mysql.connector.connect(
        host=st.secrets["db"]["host"],
        port=int(st.secrets["db"]["port"]),
        user=st.secrets["db"]["user"],
        password=st.secrets["db"]["password"],
        database=st.secrets["db"]["database"],
        autocommit=True
    )

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
    st.title("🔐 Acceso Carrier")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        user = execute_read("SELECT * FROM users WHERE username=%s AND password=%s", (u, p))
        if user:
            st.session_state.update({"login": True, "user": u, "role": user[0]['role']})
            st.rerun()
        else:
            st.error("Credenciales incorrectas")
    st.stop()

# ==================== SIDEBAR ====================
with st.sidebar:
    st.image(LOGO_URL, width=150)
    st.write(f"💼 **Perfil:** {st.session_state.role.upper()}")
    st.write(f"👤 **Usuario:** {st.session_state.user}")
    st.divider()
    
    is_admin = st.session_state.role.upper() == "ADMIN"
    
    if is_admin:
        menu = st.radio("Menú Principal", ["📸 Registro de Unidades", "🎯 Asignación de Tareas", "📊 Dashboard Operativo"])
        
        # --- BOTÓN RESET (SOLO ADMIN Y NO BORRA USER/LOGIN) ---
        st.divider()
        if st.button("🔄 Resetear Campos de Datos", use_container_width=True):
            keep = ["login", "user", "role"]
            for key in list(st.session_state.keys()):
                if key not in keep:
                    del st.session_state[key]
            st.success("Campos limpiados")
            time.sleep(0.5)
            st.rerun()
    else:
        menu = "🎯 Mis Tareas"
        
    st.divider()
    if st.button("Cerrar Sesión", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ==================== 1. REGISTRO (Solo Admin) ====================
if menu == "📸 Registro de Unidades" and is_admin:
    st.markdown('<div class="main-header">REGISTRO DE SERIES Y COMPONENTES</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        tipo = st.radio("Modo", ["Existente", "Nueva Unidad"], key="modo_reg")
        if tipo == "Nueva Unidad":
            u_num = st.text_input("Escriba Unit Number", key="new_u")
            lote_input = st.text_input("ID de Lote (Opcional)", key="new_l")
        else:
            u_db = execute_read("SELECT unit_number FROM unidades")
            u_num = st.selectbox("Seleccione Unidad", [x['unit_number'] for x in u_db] if u_db else [], key="sel_u")
            
    with col2:
        campo_db = st.selectbox("Componente", list(CAMPOS_UNIDAD.keys()), format_func=lambda x: CAMPOS_UNIDAD[x], key="sel_c")
        valor = st.text_input("Valor de Serie", key="val_s")

    if st.button("💾 Guardar Registro"):
        if u_num and valor:
            if tipo == "Nueva Unidad":
                execute_write(f"INSERT INTO unidades (unit_number, id_lote, {campo_db}) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE {campo_db}=%s", (u_num, lote_input, valor, valor))
            else:
                execute_write(f"UPDATE unidades SET {campo_db}=%s WHERE unit_number=%s", (valor, u_num))
            st.success("✅ Registro guardado")

# ==================== 2. ASIGNACIÓN (Solo Admin) ====================
elif menu == "🎯 Asignación de Tareas" and is_admin:
    st.markdown('<div class="main-header">CONTROL DE ASIGNACIONES</div>', unsafe_allow_html=True)
    
    u_data = execute_read("SELECT unit_number FROM unidades")
    act_data = execute_read("SELECT nombre FROM actividades")
    tec_data = execute_read("SELECT username FROM users WHERE role='tecnico'")

    col1, col2, col3 = st.columns(3)
    u_sel = col1.selectbox("Unidad", [x['unit_number'] for x in u_data] if u_data else [], key="asig_u")
    tec_sel = col2.selectbox("Técnico", [x['username'] for x in tec_data] if tec_data else [], key="asig_t")
    
    acts = [x['nombre'] for x in act_data] if act_data else []
    if ID_ACTIVIDAD_SERIES not in acts: acts.append(ID_ACTIVIDAD_SERIES)
    act_sel = col3.selectbox("Actividad", acts, key="asig_a")

    if st.button("📌 Crear Tarea"):
        execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'pendiente')", (u_sel, act_sel, tec_sel))
        st.success("✅ Tarea asignada exitosamente.")

# ==================== 3. MIS TAREAS (Técnicos) ====================
elif menu == "🎯 Mis Tareas":
    st.markdown('<div class="main-header">MIS TAREAS ASIGNADAS</div>', unsafe_allow_html=True)
    
    tareas = execute_read("SELECT * FROM asignaciones WHERE tecnico = %s AND estado != 'completada'", (st.session_state.user,))

    if not tareas:
        st.info("No tienes tareas asignadas.")
    else:
        df_tareas = pd.DataFrame(tareas)
        st.dataframe(df_tareas[['id', 'unidad', 'actividad_id', 'estado']], use_container_width=True, hide_index=True)
        
        st.divider()
        tarea_id = st.selectbox("Seleccione tarea para gestionar", df_tareas['id'], key="gestion_id")
        tarea = df_tareas[df_tareas['id'] == tarea_id].iloc[0]
        
        es_toma_series = tarea['actividad_id'] == ID_ACTIVIDAD_SERIES
        
        col1, col2 = st.columns(2)
        if tarea['estado'] == 'pendiente':
            if col1.button("▶️ Iniciar Tarea"):
                execute_write("UPDATE asignaciones SET fecha_inicio=NOW(), estado='en_proceso' WHERE id=%s", (tarea_id,))
                st.rerun()
        
        elif tarea['estado'] == 'en_proceso':
            if es_toma_series:
                st.markdown('<div class="st-d5">📋 <b>FORMULARIO DE TOMA DE SERIES</b></div>', unsafe_allow_html=True)
                with st.form("form_tec_series"):
                    inputs = {}
                    f1, f2 = st.columns(2)
                    for i, (k, v) in enumerate(CAMPOS_UNIDAD.items()):
                        with (f1 if i % 2 == 0 else f2):
                            inputs[k] = st.text_input(v)
                    
                    if st.form_submit_button("✅ Guardar y Finalizar"):
                        set_q = ", ".join([f"{k}=%s" for k in inputs.keys()])
                        execute_write(f"UPDATE unidades SET {set_q} WHERE unit_number=%s", list(inputs.values()) + [tarea['unidad']])
                        execute_write("UPDATE asignaciones SET fecha_fin=NOW(), estado='completada', tiempo_minutos=TIMESTAMPDIFF(MINUTE, fecha_inicio, NOW()) WHERE id=%s", (tarea_id,))
                        st.success("✅ Datos guardados y tarea finalizada")
                        time.sleep(1)
                        st.rerun()
            else:
                if col2.button("✅ Finalizar Tarea"):
                    execute_write("UPDATE asignaciones SET fecha_fin=NOW(), estado='completada', tiempo_minutos=TIMESTAMPDIFF(MINUTE, fecha_inicio, NOW()) WHERE id=%s", (tarea_id,))
                    st.rerun()

# ==================== 4. DASHBOARD OPERATIVO ====================
elif menu == "📊 Dashboard Operativo" and is_admin:
    st.markdown('<div class="main-header">DASHBOARD ESTRATÉGICO DE PRODUCCIÓN</div>', unsafe_allow_html=True)
    
    u_raw = execute_read("SELECT * FROM unidades")
    a_raw = execute_read("SELECT * FROM asignaciones")
    
    if u_raw:
        df_u = pd.DataFrame(u_raw)
        df_a = pd.DataFrame(a_raw) if a_raw else pd.DataFrame()
        
        # KPIs
        total_u = len(df_u)
        pendientes = len(df_a[df_a['estado'] == 'pendiente']) if not df_a.empty else 0
        completas = len(df_u[df_u['vin_number'].notnull() & df_u['reefer_serial'].notnull()])
        avance = round((completas/total_u*100),1) if total_u > 0 else 0

        k1, k2, k3, k4 = st.columns(4)
        k1.markdown(f'<div class="metric-card"><h3>Unidades</h3><h2>{total_u}</h2></div>', unsafe_allow_html=True)
        k2.markdown(f'<div class="metric-card"><h3>Completas</h3><h2>{completas}</h2></div>', unsafe_allow_html=True)
        k3.markdown(f'<div class="metric-card"><h3>Avance</h3><h2>{avance}%</h2></div>', unsafe_allow_html=True)
        k4.markdown(f'<div class="metric-card"><h3>Pendientes</h3><h2>{pendientes}</h2></div>', unsafe_allow_html=True)

        st.divider()
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.subheader("👨‍🔧 Tareas por Técnico")
            if not df_a.empty:
                fig = px.bar(df_a[df_a['estado']=='completada'], x='tecnico', title="Productividad")
                st.plotly_chart(fig, use_container_width=True)
        
        with col_g2:
            st.subheader("📋 Inventario de Unidades")
            st.dataframe(df_u, use_container_width=True)

        # Exportación
        st.divider()
        if st.button("📥 Exportar Reporte Excel"):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_u.to_excel(writer, sheet_name='Unidades', index=False)
                if not df_a.empty: df_a.to_excel(writer, sheet_name='Asignaciones', index=False)
            st.download_button("Descargar", output.getvalue(), "Reporte_Carrier.xlsx")

    # Auto-refresh
    time.sleep(60)
    st.rerun()
