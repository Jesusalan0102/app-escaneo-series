import streamlit as st
import pandas as pd
import mysql.connector
from mysql.connector import Error, pooling
import plotly.express as px
from datetime import datetime
import io
import time

# ==========================================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS (CSS)
# ==========================================================
st.set_page_config(page_title="Carrier Transicold - Gestión de Series", layout="wide")

CARRIER_BLUE = "#002B5B"
LOGO_URL = "https://raw.githubusercontent.com/Jesusalan0102/app-escaneo-series/main/carrierlogo2.jpeg.jpg"

st.markdown(f"""
<style>
    .main-header {{ font-size: 2.3rem; font-weight: bold; color: {CARRIER_BLUE}; text-align: center; margin-bottom: 20px; }}
    .metric-card {{ background-color: #ffffff; padding: 20px; border-radius: 10px; border-left: 5px solid {CARRIER_BLUE}; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); }}
    .stButton>button {{ width: 100%; border-radius: 5px; height: 3em; background-color: {CARRIER_BLUE}; color: white; font-weight: bold; }}
    .st-d5 {{ background-color: #f0f2f6; padding: 15px; border-radius: 8px; border: 1px solid #d1d3d4; margin-bottom: 15px; }}
    .status-badge {{ padding: 5px 10px; border-radius: 15px; font-size: 0.8rem; font-weight: bold; }}
</style>
""", unsafe_allow_html=True)

# ==========================================================
# 2. GESTIÓN DE BASE DE DATOS Y POOL DE CONEXIONES
# ==========================================================
@st.cache_resource
def init_connection_pool():
    try:
        return pooling.MySQLConnectionPool(
            pool_name="carrier_pool",
            pool_size=5,
            host=st.secrets["db"]["host"],
            port=int(st.secrets["db"]["port"]),
            user=st.secrets["db"]["user"],
            password=st.secrets["db"]["password"],
            database=st.secrets["db"]["database"],
            autocommit=True
        )
    except Exception as e:
        st.error(f"❌ Error crítico de base de datos: {str(e)}")
        return None

db_pool = init_connection_pool()

def execute_query(query, params=None, is_select=False):
    conn = db_pool.get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params or ())
        if is_select:
            result = cursor.fetchall()
            return result
        return True
    except Error as e:
        st.error(f"Error en SQL: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

# Crear tablas si no existen (Respaldo automático)
def setup_tables():
    queries = [
        """CREATE TABLE IF NOT EXISTS unidades (
            unit_number VARCHAR(50) PRIMARY KEY,
            id_lote VARCHAR(50),
            vin_number VARCHAR(100),
            reefer_serial VARCHAR(100),
            reefer_model VARCHAR(100),
            evaporator_serial_mjs11 VARCHAR(100),
            evaporator_serial_mjd22 VARCHAR(100),
            engine_serial VARCHAR(100),
            compressor_serial VARCHAR(100),
            generator_serial VARCHAR(100),
            battery_charger_serial VARCHAR(100)
        )""",
        """CREATE TABLE IF NOT EXISTS asignaciones (
            id INT AUTO_INCREMENT PRIMARY KEY,
            unidad VARCHAR(50),
            actividad_id VARCHAR(100),
            tecnico VARCHAR(100),
            estado ENUM('pendiente', 'en_proceso', 'completada') DEFAULT 'pendiente',
            fecha_asignacion DATETIME DEFAULT CURRENT_TIMESTAMP,
            fecha_inicio DATETIME,
            fecha_fin DATETIME,
            tiempo_minutos INT
        )"""
    ]
    for q in queries:
        execute_query(q)

setup_tables()

# ==========================================================
# 3. CONSTANTES Y CONFIGURACIÓN DINÁMICA
# ==========================================================
CAMPOS_TECNICOS = {
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

NOMBRE_ACTIVIDAD_ESPECIAL = "REGISTRO DE SERIES Y COMPONENTES"

# ==========================================================
# 4. SISTEMA DE AUTENTICACIÓN
# ==========================================================
if "login" not in st.session_state:
    st.session_state.update({"login": False, "user": "", "role": ""})

if not st.session_state.login:
    st.title("🔐 Acceso Carrier Transicold")
    with st.container():
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.button("Ingresar al Sistema"):
            user_data = execute_query("SELECT * FROM users WHERE username=%s AND password=%s", (u, p), True)
            if user_data:
                st.session_state.update({"login": True, "user": u, "role": user_data[0]['role']})
                st.rerun()
            else:
                st.error("Credenciales inválidas")
    st.stop()

# ==========================================================
# 5. MENÚ LATERAL (SIDEBAR)
# ==========================================================
with st.sidebar:
    st.image(LOGO_URL, width=180)
    st.markdown(f"**Usuario:** `{st.session_state.user}`")
    st.markdown(f"**Rol:** `{st.session_state.role.upper()}`")
    st.divider()
    
    is_admin = st.session_state.role.lower() == "admin"
    menu = st.radio("Navegación", 
                    ["🎯 Mis Tareas"] if not is_admin else 
                    ["🎯 Asignación de Tareas", "📊 Dashboard Operativo", "📸 Registro Manual"])
    
    st.divider()
    if st.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

# ==========================================================
# 6. MÓDULO: MIS TAREAS (VISTA TÉCNICO)
# ==========================================================
if menu == "🎯 Mis Tareas":
    st.markdown(f'<div class="main-header">MIS TAREAS - {st.session_state.user.upper()}</div>', unsafe_allow_html=True)
    
    tareas = execute_query("""
        SELECT * FROM asignaciones 
        WHERE tecnico = %s AND estado != 'completada'
        ORDER BY fecha_asignacion DESC
    """, (st.session_state.user,), True)

    if not tareas:
        st.info("No tienes tareas pendientes en este momento.")
    else:
        df_t = pd.DataFrame(tareas)
        st.dataframe(df_t[['id', 'unidad', 'actividad_id', 'estado', 'fecha_asignacion']], use_container_width=True)
        
        tarea_sel = st.selectbox("Seleccione Tarea para trabajar", df_t['id'].tolist())
        t_info = df_t[df_t['id'] == tarea_sel].iloc[0]
        
        c1, c2 = st.columns(2)
        with c1:
            if t_info['estado'] == 'pendiente':
                if st.button("▶️ INICIAR ACTIVIDAD"):
                    execute_query("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=NOW() WHERE id=%s", (tarea_sel,))
                    st.rerun()
            else:
                st.warning("Estatus: EN PROCESO")

        # --- FLUJO DINÁMICO DE REGISTRO DE SERIES ---
        if t_info['estado'] == 'en_proceso' and t_info['actividad_id'] == NOMBRE_ACTIVIDAD_ESPECIAL:
            st.markdown('<div class="st-d5">', unsafe_allow_html=True)
            st.subheader(f"Llenado de Componentes: Unidad {t_info['unidad']}")
            
            with st.form("form_series"):
                input_data = {}
                col_a, col_b = st.columns(2)
                for i, (db_col, label) in enumerate(CAMPOS_TECNICOS.items()):
                    with (col_a if i % 2 == 0 else col_b):
                        input_data[db_col] = st.text_input(label)
                
                if st.form_submit_button("✅ GUARDAR Y FINALIZAR TAREA"):
                    # 1. Actualizar datos de la unidad
                    set_query = ", ".join([f"{k}=%s" for k in input_data.keys()])
                    values = list(input_data.values()) + [t_info['unidad']]
                    execute_query(f"UPDATE unidades SET {set_query} WHERE unit_number=%s", tuple(values))
                    
                    # 2. Cerrar tarea
                    execute_query("""
                        UPDATE asignaciones SET 
                        estado='completada', fecha_fin=NOW(), 
                        tiempo_minutos=TIMESTAMPDIFF(MINUTE, fecha_inicio, NOW()) 
                        WHERE id=%s
                    """, (tarea_sel,))
                    st.success("Registro completado exitosamente")
                    time.sleep(1)
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        
        elif t_info['estado'] == 'en_proceso':
            if st.button("✅ FINALIZAR TAREA"):
                execute_query("UPDATE asignaciones SET estado='completada', fecha_fin=NOW() WHERE id=%s", (tarea_sel,))
                st.rerun()

# ==========================================================
# 7. MÓDULO: ASIGNACIÓN DE TAREAS (VISTA ADMIN)
# ==========================================================
elif menu == "🎯 Asignación de Tareas" and is_admin:
    st.markdown('<div class="main-header">PANEL DE ASIGNACIONES</div>', unsafe_allow_html=True)
    
    unidades = execute_query("SELECT unit_number FROM unidades", is_select=True)
    tecnicos = execute_query("SELECT username FROM users WHERE role='tecnico'", is_select=True)
    actividades = execute_query("SELECT nombre FROM actividades", is_select=True)

    with st.container():
        c1, c2, c3 = st.columns(3)
        u_sel = c1.selectbox("Unidad", [u['unit_number'] for u in unidades] if unidades else [])
        t_sel = c2.selectbox("Técnico", [t['username'] for t in tecnicos] if tecnicos else [])
        a_sel = c3.selectbox("Actividad", [a['nombre'] for a in actividades] if actividades else [NOMBRE_ACTIVIDAD_ESPECIAL])

        if st.button("📌 ASIGNAR TAREA"):
            if u_sel and t_sel and a_sel:
                execute_query("INSERT INTO asignaciones (unidad, actividad_id, tecnico) VALUES (%s, %s, %s)", (u_sel, a_sel, t_sel))
                st.success("Tarea asignada correctamente")
            else:
                st.error("Complete todos los campos")

# ==========================================================
# 8. MÓDULO: DASHBOARD Y EXPORTACIÓN
# ==========================================================
elif menu == "📊 Dashboard Operativo" and is_admin:
    st.markdown('<div class="main-header">MONITOREO DE PRODUCCIÓN</div>', unsafe_allow_html=True)
    
    df_u = pd.DataFrame(execute_query("SELECT * FROM unidades", is_select=True))
    df_a = pd.DataFrame(execute_query("SELECT * FROM asignaciones", is_select=True))

    if not df_u.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Unidades", len(df_u))
        col2.metric("Tareas Completas", len(df_a[df_a['estado'] == 'completada']) if not df_a.empty else 0)
        
        # Exportación Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_u.to_excel(writer, index=False, sheet_name='Unidades')
            df_a.to_excel(writer, index=False, sheet_name='Asignaciones')
        
        st.download_button(
            label="📥 DESCARGAR REPORTE TOTAL (EXCEL)",
            data=output.getvalue(),
            file_name=f"Reporte_Carrier_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.ms-excel"
        )
        
        st.divider()
        st.subheader("Estado de Unidades")
        st.dataframe(df_u, use_container_width=True)
