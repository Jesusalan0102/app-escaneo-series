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
    .metric-card {{ background-color: #ffffff; padding: 20px; border-radius: 10px; border-left: 5px solid {CARRIER_BLUE}; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); }}
    .stButton>button {{ width: 100%; border-radius: 5px; height: 3em; background-color: {CARRIER_BLUE}; color: white; }}
</style>
""", unsafe_allow_html=True)

# ==================== CONEXIÓN ====================
def get_db_connection():
    return mysql.connector.connect(
        **st.secrets["db"],
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
    st.divider()
    
    is_admin = st.session_state.role.upper() == "ADMIN"
    if is_admin:
        menu = st.radio("Menú", ["📸 Registro", "🎯 Asignación", "📊 Dashboard", "👥 Usuarios"])
        st.divider()
        if st.button("🗑️ ELIMINAR TODA LA DATA"):
            execute_write("SET FOREIGN_KEY_CHECKS = 0")
            execute_write("TRUNCATE TABLE asignaciones")
            execute_write("TRUNCATE TABLE unidades")
            execute_write("SET FOREIGN_KEY_CHECKS = 1")
            st.success("Base de datos limpia")
            st.rerun()
    else:
        menu = "🎯 Mis Tareas"

    if st.button("Cerrar Sesión"):
        st.session_state.clear()
        st.rerun()

# ==================== SECCIONES ====================

if menu == "👥 Usuarios" and is_admin:
    st.markdown('<div class="main-header">GESTIÓN DE USUARIOS</div>', unsafe_allow_html=True)
    t1, t2 = st.tabs(["➕ Crear", "🗑️ Eliminar"])
    with t1:
        with st.form("nuevo_u"):
            nu, np, nr = st.text_input("Usuario"), st.text_input("Pass", type="password"), st.selectbox("Rol", ["tecnico", "admin"])
            if st.form_submit_button("Crear"):
                execute_write("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (nu, np, nr))
                st.success("Creado")
    with t2:
        users = execute_read("SELECT username FROM users")
        u_del = st.selectbox("Usuario a eliminar", [u['username'] for u in users])
        if st.button("Eliminar"):
            execute_write("DELETE FROM users WHERE username=%s", (u_del,))
            st.rerun()

elif menu == "📸 Registro" and is_admin:
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
        st.success("Guardado")

elif menu == "🎯 Asignación" and is_admin:
    st.markdown('<div class="main-header">ASIGNAR TAREAS</div>', unsafe_allow_html=True)
    u_db = execute_read("SELECT unit_number, id_lote FROM unidades")
    tec_db = execute_read("SELECT username FROM users WHERE role='tecnico'")
    c1, c2, c3 = st.columns(3)
    u_s = c1.selectbox("Unidad", [f"{x['id_lote']} - {x['unit_number']}" for x in u_db] if u_db else [])
    t_s = c2.selectbox("Técnico", [x['username'] for x in tec_db] if tec_db else [])
    a_s = c3.selectbox("Actividad", ACTIVIDADES_CARRIER)
    if st.button("📌 Asignar"):
        execute_write("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'pendiente')", (u_s.split(" - ")[1], a_s, t_s))
        st.success("Tarea asignada")

elif menu == "🎯 Mis Tareas":
    st.markdown(f'<div class="main-header">MIS TAREAS: {st.session_state.user.upper()}</div>', unsafe_allow_html=True)
    st.info("🔄 Esta lista se actualiza automáticamente cada 60 segundos.")
    
    tareas = execute_read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado!='completada'", (st.session_state.user,))
    if not tareas: 
        st.info("Sin tareas pendientes")
    else:
        for t in tareas:
            with st.expander(f"📦 {t['unidad']} - {t['actividad_id']}"):
                if t['estado'] == 'pendiente':
                    if st.button(f"Iniciar {t['id']}"):
                        execute_write("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=NOW() WHERE id=%s", (t['id'],))
                        st.rerun()
                elif t['actividad_id'] == "toma de series":
                    with st.form(f"f_{t['id']}"):
                        res = {k: st.text_input(v) for k, v in CAMPOS_SERIES.items()}
                        if st.form_submit_button("Finalizar"):
                            sets = ", ".join([f"{k}=%s" for k in res.keys()])
                            execute_write(f"UPDATE unidades SET {sets} WHERE unit_number=%s", list(res.values()) + [t['unidad']])
                            execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW(), tiempo_minutos=TIMESTAMPDIFF(MINUTE, fecha_inicio, NOW()) WHERE id=%s", (t['id'],))
                            st.rerun()
                else:
                    if st.button(f"Finalizar {t['id']}"):
                        execute_write("UPDATE asignaciones SET estado='completada', fecha_fin=NOW(), tiempo_minutos=TIMESTAMPDIFF(MINUTE, fecha_inicio, NOW()) WHERE id=%s", (t['id'],))
                        st.rerun()

    # AUTO-REFRESCO PARA TÉCNICOS
    time.sleep(60)
    st.rerun()

elif menu == "📊 Dashboard" and is_admin:
    st.markdown('<div class="main-header">DASHBOARD OPERATIVO</div>', unsafe_allow_html=True)
    
    # 1. Obtener Datos
    data = execute_read("SELECT u.*, a.tecnico, a.estado, a.actividad_id FROM unidades u LEFT JOIN asignaciones a ON u.unit_number = a.unidad")
    
    if data:
        df = pd.DataFrame(data)
        
        # 2. Gráficos de Productividad
        c1, c2 = st.columns(2)
        with c1:
            df_prod = df[df['estado']=='completada'].groupby('tecnico').size().reset_index(name='Tareas')
            st.plotly_chart(px.bar(df_prod, x='tecnico', y='Tareas', title="Tareas por Técnico"), use_container_width=True)
        with c2:
            st.plotly_chart(px.pie(df, names='estado', title="Estado General"), use_container_width=True)
        
        st.divider()
        
        # 3. Jerarquía por Lotes
        st.subheader("🏗️ Control por Lotes")
        for lote in df['id_lote'].unique():
            with st.expander(f"LOTE: {lote}"):
                st.dataframe(df[df['id_lote']==lote][['unit_number', 'vin_number', 'tecnico', 'actividad_id', 'estado']], use_container_width=True, hide_index=True)
        
        st.divider()
        
        # 4. Registro al Momento (Información técnica completa)
        st.subheader("📋 Registro de Unidades al Momento")
        # Quitamos duplicados de unidades que puedan aparecer por tener múltiples tareas
        df_unidades_clean = df.drop(columns=['tecnico', 'estado', 'actividad_id']).drop_duplicates(subset=['unit_number'])
        st.dataframe(df_unidades_clean, use_container_width=True, hide_index=True)

        # 5. Exportación a Excel
        st.divider()
        if st.button("📥 Generar Reporte Excel"):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Dashboard_General')
                df_unidades_clean.to_excel(writer, index=False, sheet_name='Solo_Unidades')
            
            st.download_button(
                label="⬇️ Descargar Reporte",
                data=output.getvalue(),
                file_name=f"Reporte_Carrier_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    # AUTO-REFRESCO PARA ADMIN
    time.sleep(60)
    st.rerun()
