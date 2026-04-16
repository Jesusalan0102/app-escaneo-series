import streamlit as st
import pandas as pd
import mysql.connector
from mysql.connector import Error
import plotly.express as px
from datetime import datetime
import io
import time

# ==========================================================
# 1. CONFIGURACIÓN Y ESTILOS
# ==========================================================
st.set_page_config(page_title="Carrier Transicold - Gestión Pro", layout="wide")

CARRIER_BLUE = "#002B5B"
LOGO_URL = "https://raw.githubusercontent.com/Jesusalan0102/app-escaneo-series/main/carrierlogo2.jpeg.jpg"

st.markdown(f"""
<style>
    .main-header {{ font-size: 2.5rem; font-weight: bold; color: {CARRIER_BLUE}; text-align: center; }}
    .stButton>button {{ width: 100%; border-radius: 8px; height: 3.5em; background-color: {CARRIER_BLUE}; color: white; font-weight: bold; }}
    .task-card {{ background-color: #ffffff; padding: 20px; border-radius: 12px; border-left: 6px solid {CARRIER_BLUE}; shadow: 0px 4px 10px rgba(0,0,0,0.1); margin-bottom: 15px; }}
    .form-container {{ background-color: #f8f9fa; padding: 25px; border-radius: 15px; border: 1px solid #dee2e6; }}
</style>
""", unsafe_allow_html=True)

# ==========================================================
# 2. GESTIÓN DE CONEXIÓN (SOLUCIÓN AL ERROR 1226)
# ==========================================================
def get_db_connection():
    """Crea una conexión única y la retorna. No usamos Pooling para evitar el límite de conexiones."""
    try:
        conn = mysql.connector.connect(
            host=st.secrets["db"]["host"],
            port=int(st.secrets["db"]["port"]),
            user=st.secrets["db"]["user"],
            password=st.secrets["db"]["password"],
            database=st.secrets["db"]["database"]
        )
        return conn
    except Error as e:
        st.error(f"❌ Error de conexión: {e}")
        return None

def run_query(query, params=None, is_select=False):
    """Ejecuta una consulta y cierra la conexión inmediatamente para liberar cupo."""
    conn = get_db_connection()
    if not conn: return None
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params or ())
        if is_select:
            return cursor.fetchall()
        conn.commit()
        return True
    except Error as e:
        st.error(f"❌ Error SQL: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

# ==========================================================
# 3. INICIALIZACIÓN DE TABLAS (DDL EXPENDIDO)
# ==========================================================
def init_system():
    # Ejecutamos todo en un solo bloque para ahorrar conexiones
    db_init_query = """
    CREATE TABLE IF NOT EXISTS unidades (
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
    );
    """
    # Nota: mysql-connector no permite múltiples statements por defecto en un execute, 
    # así que lo llamamos una vez por tabla de forma controlada.
    run_query(db_init_query)
    run_query("""
    CREATE TABLE IF NOT EXISTS asignaciones (
        id INT AUTO_INCREMENT PRIMARY KEY,
        unidad VARCHAR(50),
        actividad_id VARCHAR(100),
        tecnico VARCHAR(100),
        estado ENUM('pendiente', 'en_proceso', 'completada') DEFAULT 'pendiente',
        fecha_asignacion DATETIME DEFAULT CURRENT_TIMESTAMP,
        fecha_inicio DATETIME,
        fecha_fin DATETIME,
        tiempo_minutos INT
    );
    """)

init_system()

# ==========================================================
# 4. LÓGICA DE NEGOCIO Y CAMPOS
# ==========================================================
CAMPOS_SERIES = {
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

ACTIVIDAD_ESPECIAL = "REGISTRO DE SERIES Y COMPONENTES"

# ==========================================================
# 5. AUTENTICACIÓN
# ==========================================================
if "auth" not in st.session_state:
    st.session_state.update({"auth": False, "user": "", "role": ""})

if not st.session_state.auth:
    st.markdown('<div class="main-header">Carrier Transicold Login</div>', unsafe_allow_html=True)
    with st.form("login_form"):
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar"):
            res = run_query("SELECT * FROM users WHERE username=%s AND password=%s", (u, p), True)
            if res:
                st.session_state.update({"auth": True, "user": u, "role": res[0]['role']})
                st.rerun()
            else:
                st.error("Acceso denegado.")
    st.stop()

# ==========================================================
# 6. INTERFAZ PRINCIPAL
# ==========================================================
is_admin = st.session_state.role.lower() == "admin"

with st.sidebar:
    st.image(LOGO_URL, width=150)
    st.subheader(f"Bienvenido, {st.session_state.user}")
    st.info(f"Rol: {st.session_state.role.upper()}")
    
    if is_admin:
        menu = st.radio("Menú Administrador", ["Asignar Tareas", "Dashboard", "Inventario de Unidades"])
    else:
        menu = "Mis Actividades Técnicas"
    
    if st.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

# --- VISTA TÉCNICO: TAREAS Y TOMA DE SERIES ---
if menu == "Mis Actividades Técnicas":
    st.header("🎯 Mis Tareas Asignadas")
    
    # Filtro: Solo tareas del técnico logueado
    tareas = run_query("SELECT * FROM asignaciones WHERE tecnico=%s AND estado!='completada'", (st.session_state.user,), True)
    
    if not tareas:
        st.info("No tienes tareas pendientes.")
    else:
        df_tareas = pd.DataFrame(tareas)
        st.dataframe(df_tareas[['id', 'unidad', 'actividad_id', 'estado']], use_container_width=True)
        
        id_t = st.selectbox("Selecciona ID de Tarea para trabajar", df_tareas['id'])
        t_sel = df_tareas[df_tareas['id'] == id_t].iloc[0]

        if t_sel['estado'] == 'pendiente':
            if st.button("▶️ Iniciar Trabajo"):
                run_query("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=NOW() WHERE id=%s", (id_t,))
                st.rerun()
        
        elif t_sel['estado'] == 'en_proceso':
            if t_sel['actividad_id'] == ACTIVIDAD_ESPECIAL:
                st.markdown('<div class="form-container">', unsafe_allow_html=True)
                st.subheader(f"Registro de Componentes - Unidad {t_sel['unidad']}")
                
                with st.form("form_series"):
                    # Filtro de lotes y llenado dinámico
                    lote = st.text_input("Lote")
                    inputs = {}
                    c1, c2 = st.columns(2)
                    for i, (key, label) in enumerate(CAMPOS_SERIES.items()):
                        with (c1 if i % 2 == 0 else c2):
                            inputs[key] = st.text_input(label)
                    
                    if st.form_submit_button("✅ Finalizar y Guardar Series"):
                        # Actualizar unidad
                        set_clause = ", ".join([f"{k}=%s" for k in inputs.keys()])
                        run_query(f"UPDATE unidades SET id_lote=%s, {set_clause} WHERE unit_number=%s", 
                                 [lote] + list(inputs.values()) + [t_sel['unidad']])
                        # Finalizar tarea
                        run_query("UPDATE asignaciones SET estado='completada', fecha_fin=NOW(), tiempo_minutos=TIMESTAMPDIFF(MINUTE, fecha_inicio, NOW()) WHERE id=%s", (id_t,))
                        st.success("¡Datos guardados y tarea cerrada!")
                        time.sleep(1)
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                if st.button("✅ Finalizar Tarea"):
                    run_query("UPDATE asignaciones SET estado='completada', fecha_fin=NOW() WHERE id=%s", (id_t,))
                    st.rerun()

# --- VISTA ADMIN: ASIGNACIÓN ---
elif menu == "Asignar Tareas" and is_admin:
    st.header("📌 Asignación de Trabajo")
    
    unidades = run_query("SELECT unit_number FROM unidades", is_select=True)
    tecnicos = run_query("SELECT username FROM users WHERE role='tecnico'", is_select=True)
    
    with st.form("asig_form"):
        u = st.selectbox("Unidad", [x['unit_number'] for x in unidades] if unidades else [])
        t = st.selectbox("Asignar a Técnico", [x['username'] for x in tecnicos] if tecnicos else [])
        a = st.selectbox("Actividad", [ACTIVIDAD_ESPECIAL, "Pintura", "Instalación Eléctrica", "Prueba de Vacío"])
        
        if st.form_submit_button("Crear Asignación"):
            run_query("INSERT INTO asignaciones (unidad, actividad_id, tecnico) VALUES (%s, %s, %s)", (u, a, t))
            st.success("Tarea asignada correctamente.")

# --- VISTA ADMIN: DASHBOARD ---
elif menu == "Dashboard" and is_admin:
    st.header("📊 Reporte de Producción")
    
    df_u = pd.DataFrame(run_query("SELECT * FROM unidades", is_select=True))
    df_a = pd.DataFrame(run_query("SELECT * FROM asignaciones", is_select=True))
    
    if not df_u.empty:
        st.metric("Total Unidades", len(df_u))
        st.subheader("Avance por Unidad")
        st.dataframe(df_u, use_container_width=True)
        
        # Exportar Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_u.to_excel(writer, sheet_name='Unidades', index=False)
            df_a.to_excel(writer, sheet_name='Asignaciones', index=False)
        
        st.download_button("📥 Descargar Reporte Excel", output.getvalue(), "reporte_carrier.xlsx")
