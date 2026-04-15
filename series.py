import streamlit as st
import pandas as pd
import mysql.connector
import plotly.express as px
from datetime import datetime

# ==================== CONFIGURACIÓN ====================
st.set_page_config(page_title="Carrier Transicold - Sistema de Gestión", layout="wide")

CARRIER_BLUE = "#002B5B"
LOGO_URL = "https://raw.githubusercontent.com/Jesusalan0102/app-escaneo-series/main/carrierlogo2.jpeg.jpg"

# Estilos CSS profesionales
st.markdown(f"""
<style>
    .main-header {{ font-size: 2.2rem; font-weight: bold; color: {CARRIER_BLUE}; text-align: center; margin-bottom: 20px; }}
    .metric-card {{ background-color: #ffffff; padding: 20px; border-radius: 10px; border-left: 5px solid {CARRIER_BLUE}; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); }}
    .stButton>button {{ width: 100%; border-radius: 5px; height: 3em; background-color: {CARRIER_BLUE}; color: white; }}
</style>
""", unsafe_allow_html=True)

# ==================== CONEXIÓN A DB (VERSIÓN ROBUSTA) ====================
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
            connection_timeout=15,
            buffered=True
        )
        return conn
    except Exception as e:
        st.error(f"❌ Error de conexión a la base de datos: {str(e)}")
        st.stop()

def get_cursor(dictionary=False):
    try:
        conn = get_db()
        if not conn.is_connected():
            conn.reconnect(attempts=3, delay=5)
        return conn.cursor(dictionary=dictionary)
    except Exception as e:
        st.error(f"❌ Error al crear cursor: {str(e)}")
        st.stop()

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
    opts = ["📸 Registro de Unidades", "🎯 Asignación de Tareas", "📊 Dashboard Operativo"]
    menu = st.radio("Menú Principal", opts)
    if st.button("Cerrar Sesión"):
        st.session_state.login = False
        st.rerun()

# ==================== 1. REGISTRO DE UNIDADES ====================
if menu == "📸 Registro de Unidades":
    st.markdown('<div class="main-header">REGISTRO DE SERIES Y COMPONENTES</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        tipo = st.radio("Modo", ["Existente", "Nueva Unidad"])
        if tipo == "Nueva Unidad":
            u_num = st.text_input("Escriba Unit Number")
            lote_id = st.text_input("ID de Lote (Ej: 30024429)")
        else:
            cur = get_cursor(dictionary=True)
            cur.execute("SELECT unit_number FROM unidades")
            u_db = pd.DataFrame(cur.fetchall())
            cur.close()
            u_num = st.selectbox("Seleccione Unidad", u_db["unit_number"] if not u_db.empty else ["No hay datos"])
            lote_id = None

    with col2:
        campo = st.selectbox("Componente", ["vin_number", "reefer", "engine_serial", "compressor_serial"])
        valor = st.text_input("Valor de Serie")

    if st.button("💾 Guardar Registro"):
        if u_num and valor:
            try:
                cur = get_cursor()
                if tipo == "Nueva Unidad":
                    sql = f"INSERT INTO unidades (unit_number, {campo}, lote_id) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE {campo}=%s, lote_id=%s"
                    cur.execute(sql, (u_num, valor, lote_id, valor, lote_id))
                else:
                    sql = f"UPDATE unidades SET {campo}=%s WHERE unit_number=%s"
                    cur.execute(sql, (valor, u_num))
                cur.close()
                st.success(f"✅ Unidad {u_num} actualizada correctamente.")
            except Exception as e:
                st.error(f"Error al guardar: {str(e)}")

# ==================== 2. ASIGNACIÓN DE TAREAS ====================
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
        u_sel = st.selectbox("Unidad", u_data["unit_number"] if not u_data.empty else [])
    with col2: 
        tec_sel = st.selectbox("Técnico", tec_data["username"] if not tec_data.empty else [])
    with col3: 
        act_sel = st.selectbox("Actividad", act_data["nombre"] if not act_data.empty else ["Cableado", "Inspeccion"])

    if st.button("📌 Crear Tarea"):
        if u_sel and tec_sel and act_sel:
            try:
                cur = get_cursor()
                cur.execute("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'pendiente')", (u_sel, act_sel, tec_sel))
                cur.close()
                st.success("✅ Tarea asignada exitosamente.")
            except Exception as e:
                st.error(f"Error al asignar: {e}")

# ==================== 3. DASHBOARD OPERATIVO ====================
elif menu == "📊 Dashboard Operativo":
    st.markdown('<div class="main-header">DASHBOARD ESTRATÉGICO DE PRODUCCIÓN</div>', unsafe_allow_html=True)
    
    try:
        cur = get_cursor(dictionary=True)
        
        # Producción General
        cur.execute("SELECT COUNT(DISTINCT unit_number) as total FROM unidades")
        prod_total = cur.fetchone()['total']
        
        # Productividad por Técnico
        cur.execute("""
            SELECT tecnico, COUNT(*) as cantidad 
            FROM asignaciones WHERE estado='completada' GROUP BY tecnico
        """)
        df_tec = pd.DataFrame(cur.fetchall())
        
        # Estatus por Lote (corregido)
        cur.execute("""
            SELECT 
                COALESCE(lote_id, 'Sin Lote') as lote_id, 
                COUNT(unit_number) as total_u, 
                SUM(CASE WHEN vin_number IS NOT NULL AND reefer IS NOT NULL THEN 1 ELSE 0 END) as completas
            FROM unidades 
            GROUP BY lote_id
        """)
        df_lotes = pd.DataFrame(cur.fetchall())
        cur.close()

    except Exception as e:
        st.error(f"Error al cargar dashboard: {str(e)}")
        prod_total = 0
        df_tec = pd.DataFrame()
        df_lotes = pd.DataFrame()

    # --- KPIs ---
    kpi1, kpi2, kpi3 = st.columns(3)
    with kpi1:
        st.markdown(f'<div class="metric-card"><h3>Producción Total</h3><h2>{prod_total}</h2><p>Unidades Únicas</p></div>', unsafe_allow_html=True)
    with kpi2:
        lotes_activos = len(df_lotes) if not df_lotes.empty else 0
        st.markdown(f'<div class="metric-card"><h3>Lotes Activos</h3><h2>{lotes_activos}</h2><p>En operación</p></div>', unsafe_allow_html=True)
    with kpi3:
        tareas_hoy = df_tec['cantidad'].sum() if not df_tec.empty else 0
        st.markdown(f'<div class="metric-card"><h3>Tareas Listas</h3><h2>{tareas_hoy}</h2><p>Productividad Total</p></div>', unsafe_allow_html=True)

    st.divider()

    # --- Gráficos ---
    c_left, c_right = st.columns([1, 1])
    with c_left:
        st.subheader("👨‍🔧 Productividad Individual")
        if not df_tec.empty:
            fig_tec = px.bar(df_tec, x='tecnico', y='cantidad', color='cantidad', 
                             color_continuous_scale='Blues', labels={'cantidad':'Tareas Finalizadas'})
            st.plotly_chart(fig_tec, use_container_width=True)

    with c_right:
        st.subheader("📦 Avance por Lote")
        if not df_lotes.empty:
            fig_lote = px.pie(df_lotes, names='lote_id', values='total_u', hole=0.4)
            st.plotly_chart(fig_lote, use_container_width=True)

    # --- Detalle por Lote ---
    st.divider()
    st.subheader("🔍 Explorador de Estatus por Lote")
    if not df_lotes.empty:
        lote_sel = st.selectbox("Seleccione un Lote para auditar", df_lotes['lote_id'].unique())
        
        cur = get_cursor(dictionary=True)
        cur.execute("SELECT unit_number, vin_number, reefer, engine_serial FROM unidades WHERE lote_id=%s", (lote_sel,))
        detalle = pd.DataFrame(cur.fetchall())
        cur.close()
        
        row = df_lotes[df_lotes['lote_id'] == lote_sel].iloc[0]
        prog = int((row['completas'] / row['total_u']) * 100) if row['total_u'] > 0 else 0
        st.write(f"**Progreso del Lote {lote_sel}:** {prog}%")
        st.progress(prog / 100)
        st.dataframe(detalle, use_container_width=True)

    # ==================== REPORTES SOLO PARA ADMINISTRADOR ====================
    if st.session_state.role.upper() == "ADMIN":
        st.divider()
        st.subheader("📄 Reportes y Exportaciones Finales (Solo Admin)")
        
        col_rep1, col_rep2 = st.columns(2)
        with col_rep1:
            if st.button("📥 Exportar Todo a Excel", use_container_width=True):
                try:
                    cur = get_cursor(dictionary=True)
                    cur.execute("SELECT * FROM unidades")
                    df_unidades = pd.DataFrame(cur.fetchall())
                    cur.execute("SELECT * FROM asignaciones")
                    df_asignaciones = pd.DataFrame(cur.fetchall())
                    cur.close()

                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    excel_file = f"Reporte_Carrier_Completo_{timestamp}.xlsx"
                    
                    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                        df_unidades.to_excel(writer, sheet_name='Unidades', index=False)
                        df_asignaciones.to_excel(writer, sheet_name='Asignaciones', index=False)
                    
                    with open(excel_file, "rb") as f:
                        st.download_button(
                            label="⬇️ Descargar Archivo Excel",
                            data=f,
                            file_name=excel_file,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    st.success("✅ Reporte Excel generado")
                except Exception as e:
                    st.error(f"Error al generar Excel: {e}")

        with col_rep2:
            st.info("Exportación a PDF próximamente (puedo agregarla si quieres)")
