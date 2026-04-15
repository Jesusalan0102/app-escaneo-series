import streamlit as st
import pandas as pd
import mysql.connector
import plotly.express as px
from datetime import datetime
import io

# ==================== CONFIGURACIÓN ====================
st.set_page_config(page_title="Carrier Transicold - Sistema de Gestión", layout="wide")

CARRIER_BLUE = "#002B5B"
LOGO_URL = "https://raw.githubusercontent.com/Jesusalan0102/app-escaneo-series/main/carrierlogo2.jpeg.jpg"

st.markdown(f"""
<style>
    .main-header {{ font-size: 2.3rem; font-weight: bold; color: {CARRIER_BLUE}; text-align: center; margin-bottom: 20px; }}
    .metric-card {{ background-color: #ffffff; padding: 20px; border-radius: 10px; border-left: 5px solid {CARRIER_BLUE}; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); }}
    .stButton>button {{ width: 100%; border-radius: 5px; height: 3em; background-color: {CARRIER_BLUE}; color: white; }}
</style>
""", unsafe_allow_html=True)

# ==================== CONEXIÓN ====================
@st.cache_resource(show_spinner=False, ttl=300)
def get_db():
    try:
        conn = mysql.connector.connect(
            host=st.secrets["db"]["host"],
            port=int(st.secrets["db"]["port"]),
            user=st.secrets["db"]["user"],
            password=st.secrets["db"]["password"],
            database=st.secrets["db"]["database"],
            autocommit=True,
            connection_timeout=20,
            buffered=True
        )
        return conn
    except Exception as e:
        st.error(f"❌ Error de conexión: {str(e)}")
        st.stop()

def get_cursor(dictionary=False):
    conn = get_db()
    if not conn.is_connected():
        conn.reconnect(attempts=3, delay=5)
    return conn.cursor(dictionary=dictionary)

# ==================== LOGIN ====================
if "login" not in st.session_state:
    st.session_state.update({"login": False, "user": "", "role": ""})

if not st.session_state.login:
    st.title("🔐 Acceso Carrier")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        try:
            cur = get_cursor(dictionary=True)
            cur.execute("SELECT * FROM users WHERE username=%s AND password=%s", (u, p))
            user = cur.fetchone()
            cur.close()
            if user:
                st.session_state.update({"login": True, "user": u, "role": user['role']})
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")
        except Exception as e:
            st.error(f"Error en login: {str(e)}")
    st.stop()

# ==================== SIDEBAR ====================
with st.sidebar:
    st.image(LOGO_URL, width=150)
    st.write(f"💼 **Perfil:** {st.session_state.role.upper()}")
    st.write(f"👤 **Usuario:** {st.session_state.user}")
    st.divider()
    menu = st.radio("Menú Principal", ["📸 Registro de Unidades", "🎯 Asignación de Tareas", "📊 Dashboard Operativo"])
    
    if st.button("🔄 Resetear Aplicación", use_container_width=True):
        # Limpieza más efectiva
        for key in list(st.session_state.keys()):
            if key not in ["login", "user", "role"]:
                del st.session_state[key]
        st.success("✅ Aplicación reseteada correctamente")
        st.rerun()
        
    if st.button("Cerrar Sesión", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ==================== 1. REGISTRO DE UNIDADES ====================
if menu == "📸 Registro de Unidades":
    st.markdown('<div class="main-header">REGISTRO DE SERIES Y COMPONENTES</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        tipo = st.radio("Modo", ["Existente", "Nueva Unidad"], key="tipo_reg")
        if tipo == "Nueva Unidad":
            u_num = st.text_input("Escriba Unit Number", key="u_num")
            lote_input = st.text_input("ID de Lote (Opcional)", key="lote_input")
        else:
            cur = get_cursor(dictionary=True)
            cur.execute("SELECT unit_number FROM unidades")
            u_db = pd.DataFrame(cur.fetchall())
            cur.close()
            u_num = st.selectbox("Seleccione Unidad", u_db["unit_number"] if not u_db.empty else ["No hay datos"], key="select_unidad")

    with col2:
        campo = st.selectbox("Componente", ["vin_number", "reefer", "engine_serial", "compressor_serial"], key="campo_sel")
        valor = st.text_input("Valor de Serie", key="valor_ser")

    if st.button("💾 Guardar Registro", use_container_width=True):
        if u_num and valor:
            try:
                cur = get_cursor()
                if tipo == "Nueva Unidad":
                    sql = f"INSERT INTO unidades (unit_number, {campo}) VALUES (%s, %s) ON DUPLICATE KEY UPDATE {campo}=%s"
                    cur.execute(sql, (u_num, valor, valor))
                else:
                    sql = f"UPDATE unidades SET {campo}=%s WHERE unit_number=%s"
                    cur.execute(sql, (valor, u_num))
                cur.close()
                st.success(f"✅ Unidad {u_num} guardada correctamente.")
            except Exception as e:
                st.error(f"Error al guardar: {str(e)}")

# ==================== 2. ASIGNACIÓN DE TAREAS (RESTABLECIDA) ====================
elif menu == "🎯 Asignación de Tareas":
    st.markdown('<div class="main-header">CONTROL DE ASIGNACIONES</div>', unsafe_allow_html=True)
    
    cur = get_cursor(dictionary=True)
    cur.execute("SELECT unit_number FROM unidades WHERE vin_number IS NOT NULL")
    u_data = pd.DataFrame(cur.fetchall())
    cur.execute("SELECT nombre FROM actividades")
    act_data = pd.DataFrame(cur.fetchall())
    cur.execute("SELECT username FROM users WHERE role='tecnico'")
    tec_data = pd.DataFrame(cur.fetchall())
    cur.close()

    col1, col2, col3 = st.columns(3)
    with col1: 
        u_sel = st.selectbox("Unidad", u_data["unit_number"] if not u_data.empty else [], key="asig_unidad")
    with col2: 
        tec_sel = st.selectbox("Técnico", tec_data["username"] if not tec_data.empty else [], key="asig_tecnico")
    with col3: 
        act_sel = st.selectbox("Actividad", act_data["nombre"] if not act_data.empty else ["Inspeccion"], key="asig_actividad")

    if st.button("📌 Crear Tarea", use_container_width=True):
        if u_sel and tec_sel and act_sel:
            try:
                cur = get_cursor()
                cur.execute("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'pendiente')", 
                           (u_sel, act_sel, tec_sel))
                cur.close()
                st.success("✅ Tarea asignada exitosamente.")
            except Exception as e:
                st.error(f"Error al asignar tarea: {e}")

# ==================== 3. DASHBOARD PROFESIONAL ====================
elif menu == "📊 Dashboard Operativo":
    st.markdown('<div class="main-header">DASHBOARD ESTRATÉGICO DE PRODUCCIÓN</div>', unsafe_allow_html=True)
    
    try:
        cur = get_cursor(dictionary=True)
        cur.execute("SELECT COUNT(DISTINCT unit_number) as total FROM unidades")
        total_unidades = cur.fetchone()['total'] or 0
        
        cur.execute("SELECT COUNT(*) as completas FROM unidades WHERE vin_number IS NOT NULL AND reefer IS NOT NULL")
        completas = cur.fetchone()['completas'] or 0
        
        cur.execute("SELECT tecnico, COUNT(*) as cantidad FROM asignaciones WHERE estado='completada' GROUP BY tecnico")
        df_tec = pd.DataFrame(cur.fetchall())
        
        cur.execute("SELECT COUNT(*) as pendientes FROM asignaciones WHERE estado='pendiente'")
        pendientes = cur.fetchone()['pendientes'] or 0
        cur.close()
        
        avance = round((completas / total_unidades * 100), 1) if total_unidades > 0 else 0
    except:
        total_unidades = completas = pendientes = 0
        avance = 0
        df_tec = pd.DataFrame()

    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f'<div class="metric-card"><h3>Total Unidades</h3><h2>{total_unidades}</h2><p>Registradas</p></div>', unsafe_allow_html=True)
    with k2:
        st.markdown(f'<div class="metric-card"><h3>Unidades Completas</h3><h2>{completas}</h2><p>Con VIN + Reefer</p></div>', unsafe_allow_html=True)
    with k3:
        st.markdown(f'<div class="metric-card"><h3>Avance General</h3><h2>{avance}%</h2><p>Progreso</p></div>', unsafe_allow_html=True)
        st.progress(avance / 100)
    with k4:
        st.markdown(f'<div class="metric-card"><h3>Tareas Pendientes</h3><h2>{pendientes}</h2><p>Por completar</p></div>', unsafe_allow_html=True)

    st.divider()

    col_g1, col_g2 = st.columns([1,1])
    with col_g1:
        st.subheader("👨‍🔧 Productividad Individual por Técnico")
        if not df_tec.empty:
            fig = px.bar(df_tec, x='tecnico', y='cantidad', color='cantidad', color_continuous_scale='Blues')
            st.plotly_chart(fig, use_container_width=True)

    # Reportes Solo Admin
    if st.session_state.role.upper() == "ADMIN":
        st.divider()
        st.subheader("📄 Reportes y Exportaciones (Solo Admin)")
        if st.button("📥 Exportar Todo a Excel", use_container_width=True):
            try:
                cur = get_cursor(dictionary=True)
                cur.execute("SELECT * FROM unidades")
                df_u = pd.DataFrame(cur.fetchall())
                cur.execute("SELECT * FROM asignaciones")
                df_a = pd.DataFrame(cur.fetchall())
                cur.close()

                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_u.to_excel(writer, sheet_name='Unidades', index=False)
                    df_a.to_excel(writer, sheet_name='Asignaciones', index=False)
                output.seek(0)

                st.download_button(
                    label="⬇️ Descargar Reporte Excel",
                    data=output,
                    file_name=f"Reporte_Carrier_{timestamp}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                st.success("✅ Reporte generado correctamente")
            except Exception as e:
                st.error(f"Error al generar Excel: {str(e)}")
