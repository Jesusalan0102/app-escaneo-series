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

# Campos actualizados según imagen técnica
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

# ID de la actividad para toma de series
ID_ACTIVIDAD_SERIES = "Toma de Series"

st.markdown(f"""
<style>
    .main-header {{ font-size: 2.3rem; font-weight: bold; color: {CARRIER_BLUE}; text-align: center; margin-bottom: 20px; }}
    .metric-card {{ background-color: #ffffff; padding: 20px; border-radius: 10px; border-left: 5px solid {CARRIER_BLUE}; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); }}
    .stButton>button {{ width: 100%; border-radius: 5px; height: 3em; background-color: {CARRIER_BLUE}; color: white; }}
    .st-d5 {{ background-color: #f0f2f6; padding: 15px; border-radius: 10px; border: 1px solid #d1d3d4; margin-bottom: 10px; }}
</style>
""", unsafe_allow_html=True)

# ==================== GESTIÓN DE CONEXIÓN OPTIMIZADA ====================
def get_db_connection():
    """Crea y retorna una conexión limpia."""
    return mysql.connector.connect(
        host=st.secrets["db"]["host"],
        port=int(st.secrets["db"]["port"]),
        user=st.secrets["db"]["user"],
        password=st.secrets["db"]["password"],
        database=st.secrets["db"]["database"],
        autocommit=True
    )

def run_query(query, params=None, is_select=False):
    """Ejecuta una consulta y cierra la conexión inmediatamente para evitar el error 1226."""
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(query, params or ())
        if is_select:
            return cur.fetchall()
        return True
    except Exception as e:
        st.error(f"Error SQL: {e}")
        return None
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
        user = run_query("SELECT * FROM users WHERE username=%s AND password=%s", (u, p), True)
        if user:
            st.session_state.update({"login": True, "user": u, "role": user[0]['role']})
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")
    st.stop()

# ==================== SIDEBAR ====================
with st.sidebar:
    st.image(LOGO_URL, width=150)
    st.write(f"💼 **Perfil:** {st.session_state.role.upper()}")
    st.write(f"👤 **Usuario:** {st.session_state.user}")
    st.divider()
    
    is_admin = st.session_state.role.upper() == "ADMIN"
    menu_options = ["📸 Registro de Unidades", "🎯 Asignación de Tareas", "📊 Dashboard Operativo"] if is_admin else ["🎯 Mis Tareas"]
    menu = st.radio("Menú Principal", menu_options)
    
    st.divider()
    if st.button("Cerrar Sesión", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ==================== 1. REGISTRO (Solo Admin) ====================
if menu == "📸 Registro de Unidades" and is_admin:
    st.markdown('<div class="main-header">REGISTRO DE SERIES Y COMPONENTES</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        tipo = st.radio("Modo", ["Existente", "Nueva Unidad"], key="tipo_reg")
        if tipo == "Nueva Unidad":
            u_num = st.text_input("Escriba Unit Number")
            lote_input = st.text_input("ID de Lote (Opcional)")
        else:
            u_db = run_query("SELECT unit_number FROM unidades", is_select=True)
            u_num = st.selectbox("Seleccione Unidad", [x['unit_number'] for x in u_db] if u_db else ["No hay datos"])
            
    with col2:
        campo_db = st.selectbox("Componente", list(CAMPOS_UNIDAD.keys()), format_func=lambda x: CAMPOS_UNIDAD[x])
        valor = st.text_input("Valor de Serie")

    if st.button("💾 Guardar Registro"):
        if u_num and u_num != "No hay datos" and valor:
            if tipo == "Nueva Unidad":
                run_query(f"INSERT INTO unidades (unit_number, id_lote, {campo_db}) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE {campo_db}=%s", (u_num, lote_input, valor, valor))
            else:
                run_query(f"UPDATE unidades SET {campo_db}=%s WHERE unit_number=%s", (valor, u_num))
            st.success(f"✅ Unidad {u_num} actualizada.")

# ==================== 2. ASIGNACIÓN (Solo Admin) ====================
elif menu == "🎯 Asignación de Tareas" and is_admin:
    st.markdown('<div class="main-header">CONTROL DE ASIGNACIONES</div>', unsafe_allow_html=True)
    
    u_data = run_query("SELECT unit_number FROM unidades", is_select=True)
    act_data = run_query("SELECT nombre FROM actividades", is_select=True)
    tec_data = run_query("SELECT username FROM users WHERE role='tecnico'", is_select=True)

    c1, c2, c3 = st.columns(3)
    u_sel = c1.selectbox("Unidad", [x['unit_number'] for x in u_data] if u_data else [])
    tec_sel = c2.selectbox("Técnico", [x['username'] for x in tec_data] if tec_data else [])
    act_sel = c3.selectbox("Actividad", [x['nombre'] for x in act_data] if act_data else [ID_ACTIVIDAD_SERIES])

    if st.button("📌 Crear Tarea"):
        run_query("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'pendiente')", (u_sel, act_sel, tec_sel))
        st.success("✅ Tarea asignada exitosamente.")

# ==================== 3. MIS TAREAS (Técnicos) ====================
elif menu == "🎯 Mis Tareas":
    st.markdown(f'<div class="main-header">TAREAS DE {st.session_state.user.upper()}</div>', unsafe_allow_html=True)
    
    tareas = run_query("SELECT * FROM asignaciones WHERE tecnico = %s AND estado != 'completada' ORDER BY fecha_asignacion DESC", (st.session_state.user,), True)

    if not tareas:
        st.info("No tienes tareas pendientes.")
    else:
        df_tareas = pd.DataFrame(tareas)
        st.dataframe(df_tareas[['id', 'unidad', 'actividad_id', 'estado']], use_container_width=True)
        
        st.divider()
        tarea_id = st.selectbox("Gestionar Tarea ID:", df_tareas['id'])
        t_info = df_tareas[df_tareas['id'] == tarea_id].iloc[0]
        
        es_toma_series = t_info['actividad_id'] == ID_ACTIVIDAD_SERIES
        
        col1, col2 = st.columns(2)
        if t_info['estado'] == 'pendiente':
            if col1.button("▶️ Iniciar Tarea"):
                run_query("UPDATE asignaciones SET fecha_inicio=NOW(), estado='en_proceso' WHERE id=%s", (tarea_id,))
                st.rerun()
        
        elif t_info['estado'] == 'en_proceso':
            # Formulario dinámico para Toma de Series
            if es_toma_series:
                st.markdown('<div class="st-d5">📋 <b>LLENADO DE SERIES</b></div>', unsafe_allow_html=True)
                with st.form("form_series_tecnico"):
                    inputs = {}
                    f_c1, f_c2 = st.columns(2)
                    for i, (col_db, label) in enumerate(CAMPOS_UNIDAD.items()):
                        with (f_c1 if i % 2 == 0 else f_c2):
                            inputs[col_db] = st.text_input(label)
                    
                    if st.form_submit_button("✅ Guardar y Finalizar"):
                        # Actualizar Unidades
                        set_q = ", ".join([f"{k}=%s" for k in inputs.keys()])
                        run_query(f"UPDATE unidades SET {set_q} WHERE unit_number=%s", list(inputs.values()) + [t_info['unidad']])
                        # Cerrar Tarea
                        run_query("UPDATE asignaciones SET estado='completada', fecha_fin=NOW(), tiempo_minutos=TIMESTAMPDIFF(MINUTE, fecha_inicio, NOW()) WHERE id=%s", (tarea_id,))
                        st.success("Datos guardados.")
                        time.sleep(1)
                        st.rerun()
            else:
                if col2.button("✅ Finalizar Tarea"):
                    run_query("UPDATE asignaciones SET estado='completada', fecha_fin=NOW(), tiempo_minutos=TIMESTAMPDIFF(MINUTE, fecha_inicio, NOW()) WHERE id=%s", (tarea_id,))
                    st.rerun()

# ==================== 4. DASHBOARD ====================
elif menu == "📊 Dashboard Operativo" and is_admin:
    st.markdown('<div class="main-header">DASHBOARD DE PRODUCCIÓN</div>', unsafe_allow_html=True)
    
    unidades = run_query("SELECT * FROM unidades", is_select=True)
    asig = run_query("SELECT * FROM asignaciones", is_select=True)
    
    if unidades:
        df_u = pd.DataFrame(unidades)
        st.metric("Total Unidades", len(df_u))
        st.subheader("Inventario")
        st.dataframe(df_u, use_container_width=True)
        
        # Botón de exportación
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_u.to_excel(writer, sheet_name='Unidades', index=False)
        st.download_button("📥 Descargar Excel", output.getvalue(), "reporte.xlsx")
