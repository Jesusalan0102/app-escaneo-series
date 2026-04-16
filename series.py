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

# Campos actualizados según imagen adjunta
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
    .st-d5 {{ background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 10px; }}
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
    
    is_admin = st.session_state.role.upper() == "ADMIN"
    
    if is_admin:
        menu_options = ["📸 Registro de Unidades", "🎯 Asignación de Tareas", "📊 Dashboard Operativo"]
    else:
        menu_options = ["🎯 Mis Tareas"]
        
    menu = st.radio("Menú Principal", menu_options)
    
    st.divider()
    
    if st.button("🔄 Resetear Aplicación", use_container_width=True):
        for key in list(st.session_state.keys()):
            if key not in ["login", "user", "role"]:
                del st.session_state[key]
        st.success("✅ Aplicación reseteada")
        st.rerun()
        
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
            u_num = st.text_input("Escriba Unit Number", key="u_num")
            lote_input = st.text_input("ID de Lote (Opcional)", key="lote_input")
        else:
            cur = get_cursor(dictionary=True)
            cur.execute("SELECT unit_number FROM unidades")
            u_db = pd.DataFrame(cur.fetchall())
            cur.close()
            u_num = st.selectbox("Seleccione Unidad", u_db["unit_number"] if not u_db.empty else ["No hay datos"], key="select_unidad")
            
    with col2:
        campo_db = st.selectbox("Componente", list(CAMPOS_UNIDAD.keys()), format_func=lambda x: CAMPOS_UNIDAD[x], key="campo_sel")
        valor = st.text_input("Valor de Serie", key="valor_ser")

    if st.button("💾 Guardar Registro", use_container_width=True):
        if u_num and u_num != "No hay datos" and valor:
            try:
                cur = get_cursor()
                if tipo == "Nueva Unidad":
                    # Adaptado para usar lote_input si se proporciona
                    if lote_input:
                        sql = f"INSERT INTO unidades (unit_number, id_lote, {campo_db}) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE {campo_db}=%s"
                        cur.execute(sql, (u_num, lote_input, valor, valor))
                    else:
                        sql = f"INSERT INTO unidades (unit_number, {campo_db}) VALUES (%s, %s) ON DUPLICATE KEY UPDATE {campo_db}=%s"
                        cur.execute(sql, (u_num, valor, valor))
                else:
                    sql = f"UPDATE unidades SET {campo_db}=%s WHERE unit_number=%s"
                    cur.execute(sql, (valor, u_num))
                cur.close()
                st.success(f"✅ Unidad {u_num} guardada correctamente.")
            except Exception as e:
                st.error(f"Error al guardar: {str(e)}")
        else:
            st.warning("Asegúrese de seleccionar una unidad válida y proporcionar un valor de serie.")

# ==================== 2. ASIGNACIÓN (Solo Admin) ====================
elif menu == "🎯 Asignación de Tareas" and is_admin:
    st.markdown('<div class="main-header">CONTROL DE ASIGNACIONES</div>', unsafe_allow_html=True)
    
    cur = get_cursor(dictionary=True)
    cur.execute("SELECT unit_number FROM unidades")
    u_data = pd.DataFrame(cur.fetchall())
    cur.execute("SELECT nombre FROM actividades")
    act_data = pd.DataFrame(cur.fetchall())
    cur.execute("SELECT username FROM users WHERE role='tecnico'")
    tec_data = pd.DataFrame(cur.fetchall())
    cur.close()

    col1, col2, col3 = st.columns(3)
    with col1: u_sel = st.selectbox("Unidad", u_data["unit_number"] if not u_data.empty else [], key="asig_unidad")
    with col2: tec_sel = st.selectbox("Técnico", tec_data["username"] if not tec_data.empty else [], key="asig_tecnico")
    with col3: act_sel = st.selectbox("Actividad", act_data["nombre"] if not act_data.empty else ["Inspeccion"], key="asig_actividad")

    if st.button("📌 Crear Tarea", use_container_width=True):
        if u_sel and tec_sel and act_sel:
            try:
                cur = get_cursor()
                cur.execute("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s, %s, %s, 'pendiente')", (u_sel, act_sel, tec_sel))
                cur.close()
                st.success("✅ Tarea asignada exitosamente.")
            except Exception as e:
                st.error(f"Error al asignar: {e}")
        else:
            st.warning("Por favor complete todos los campos para asignar la tarea.")

# ==================== 3. MIS TAREAS (Técnicos) - CON TOMA DE SERIES INTEGRADA ====================
elif menu == "🎯 Mis Tareas" or (not is_admin and menu == "🎯 Mis Tareas"):
    st.markdown('<div class="main-header">MIS TAREAS ASIGNADAS</div>', unsafe_allow_html=True)
    
    # IMPORTANTE: Filtrado por usuario logueado
    cur = get_cursor(dictionary=True)
    cur.execute("""
        SELECT id, unidad, actividad_id, estado, fecha_asignacion, fecha_inicio, fecha_fin, tiempo_minutos 
        FROM asignaciones 
        WHERE tecnico = %s 
        ORDER BY fecha_asignacion DESC
    """, (st.session_state.user,))
    df_tareas = pd.DataFrame(cur.fetchall())
    cur.close()

    if df_tareas.empty:
        st.info("No tienes tareas asignadas.")
    else:
        st.dataframe(df_tareas, use_container_width=True, hide_index=True)
        
        st.divider()
        st.subheader("Gestión de Tarea")
        tarea_id = st.selectbox("Seleccione tarea para gestionar", df_tareas['id'].tolist(), format_func=lambda x: f"Tarea {x} - Unidad {df_tareas[df_tareas['id']==x]['unidad'].values[0]} - {df_tareas[df_tareas['id']==x]['actividad_id'].values[0]}")
        tarea = df_tareas[df_tareas['id'] == tarea_id].iloc[0]
        
        col1, col2 = st.columns(2)
        with col1:
            if tarea['estado'] == 'pendiente':
                if st.button("▶️ Iniciar Tarea", use_container_width=True):
                    cur = get_cursor()
                    cur.execute("UPDATE asignaciones SET fecha_inicio=NOW(), estado='en_proceso' WHERE id=%s", (tarea_id,))
                    cur.close()
                    st.success("✅ Tarea iniciada")
                    st.rerun()
            else:
                st.button("▶️ Iniciar Tarea", disabled=True, use_container_width=True)
        
        # Lógica especial para Toma de Series
        es_toma_series = tarea['actividad_id'] == ID_ACTIVIDAD_SERIES
        
        with col2:
            if tarea['estado'] == 'en_proceso':
                label_fin = "✅ Guardar y Finalizar" if es_toma_series else "✅ Finalizar Tarea"
                if st.button(label_fin, use_container_width=True, key="fin_tarea"):
                    
                    if es_toma_series:
                        # Si es toma de series, validar que se hayan llenado los campos
                        series_data = st.session_state.get(f"series_form_{tarea_id}", {})
                        if not any(series_data.values()):
                            st.error("Por favor, ingrese al menos un número de serie antes de finalizar.")
                            st.stop()
                        
                        try:
                            cur = get_cursor()
                            # Construir consulta UPDATE dinámicamente
                            set_clauses = []
                            params = []
                            for campo_db, valor in series_data.items():
                                if valor:
                                    set_clauses.append(f"{campo_db}=%s")
                                    params.append(valor)
                            
                            if set_clauses:
                                params.append(tarea['unidad'])
                                sql_update_unidades = f"UPDATE unidades SET {', '.join(set_clauses)} WHERE unit_number=%s"
                                cur.execute(sql_update_unidades, tuple(params))
                            
                            # Finalizar tarea
                            cur.execute("""
                                UPDATE asignaciones 
                                SET fecha_fin=NOW(), estado='completada',
                                tiempo_minutos=TIMESTAMPDIFF(MINUTE, fecha_inicio, NOW())
                                WHERE id=%s
                            """, (tarea_id,))
                            cur.close()
                            st.success("✅ Series guardadas y tarea finalizada")
                            # Limpiar estado del formulario
                            if f"series_form_{tarea_id}" in st.session_state:
                                del st.session_state[f"series_form_{tarea_id}"]
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al guardar series o finalizar tarea: {e}")
                    else:
                        # Finalización normal de tarea
                        try:
                            cur = get_cursor()
                            cur.execute("""
                                UPDATE asignaciones 
                                SET fecha_fin=NOW(), estado='completada',
                                tiempo_minutos=TIMESTAMPDIFF(MINUTE, fecha_inicio, NOW())
                                WHERE id=%s
                            """, (tarea_id,))
                            cur.close()
                            st.success("✅ Tarea finalizada y tiempo registrado")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al finalizar tarea: {e}")
            else:
                st.button("✅ Finalizar Tarea", disabled=True, use_container_width=True, key="fin_tarea_dis")

        # Mostrar formulario de series si está en proceso y es la actividad correcta
        if tarea['estado'] == 'en_proceso' and es_toma_series:
            st.divider()
            st.markdown(f'<div class="st-d5">📋 <b>FORMULARIO DE TOMA DE SERIES - Unidad: {tarea["unidad"]}</b></div>', unsafe_allow_html=True)
            
            # Inicializar estado para el formulario si no existe
            if f"series_form_{tarea_id}" not in st.session_state:
                st.session_state[f"series_form_{tarea_id}"] = {campo: "" for campo in CAMPOS_UNIDAD.keys()}
            
            # Crear inputs para cada campo
            form_cols = st.columns(2)
            campos_keys = list(CAMPOS_UNIDAD.keys())
            mid = len(campos_keys) // 2 + len(campos_keys) % 2
            
            for i, campo_db in enumerate(campos_keys):
                col = form_cols[0] if i < mid else form_cols[1]
                label = CAMPOS_UNIDAD[campo_db]
                # Usar key específica para persistir valor en session_state
                st.session_state[f"series_form_{tarea_id}"][campo_db] = col.text_input(
                    label, 
                    value=st.session_state[f"series_form_{tarea_id}"][campo_db],
                    key=f"input_{tarea_id}_{campo_db}"
                )

# ==================== 4. DASHBOARD (Solo Admin) - CON AUTO-REFRESH ====================
elif menu == "📊 Dashboard Operativo" and is_admin:
    st.markdown('<div class="main-header">DASHBOARD ESTRATÉGICO DE PRODUCCIÓN</div>', unsafe_allow_html=True)
    
    # Datos del dashboard
    try:
        cur = get_cursor(dictionary=True)
        cur.execute("SELECT COUNT(DISTINCT unit_number) as total FROM unidades")
        total_unidades = cur.fetchone()['total'] or 0
        
        # Lógica de "completas" ajustada a nuevos campos (requiere VIN y Reefer Serial)
        cur.execute("SELECT COUNT(*) as completas FROM unidades WHERE vin_number IS NOT NULL AND reefer_serial IS NOT NULL")
        completas = cur.fetchone()['completas'] or 0
        
        cur.execute("""SELECT tecnico, COUNT(*) as tareas, SUM(tiempo_minutos) as total_minutos 
                       FROM asignaciones WHERE estado='completada' GROUP BY tecnico""")
        df_prod = pd.DataFrame(cur.fetchall())
        
        cur.execute("SELECT COUNT(*) as pendientes FROM asignaciones WHERE estado='pendiente'")
        pendientes = cur.fetchone()['pendientes'] or 0
        cur.close()
        
        avance = round((completas / total_unidades * 100), 1) if total_unidades > 0 else 0
    except:
        total_unidades = completas = pendientes = 0
        avance = 0
        df_prod = pd.DataFrame()

    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(f'<div class="metric-card"><h3>Total Unidades</h3><h2>{total_unidades}</h2><p>Registradas</p></div>', unsafe_allow_html=True)
    with k2:
        st.markdown(f'<div class="metric-card"><h3>Unidades Completas</h3><h2>{completas}</h2><p>VIN + Reefer Serial</p></div>', unsafe_allow_html=True)
    with k3:
        st.markdown(f'<div class="metric-card"><h3>Avance General</h3><h2>{avance}%</h2><p>Progreso</p></div>', unsafe_allow_html=True)
        st.progress(avance / 100)
    with k4:
        st.markdown(f'<div class="metric-card"><h3>Tareas Pendientes</h3><h2>{pendientes}</h2><p>Por completar</p></div>', unsafe_allow_html=True)

    st.divider()

    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("👨‍🔧 Productividad por Técnico")
        if not df_prod.empty:
            fig = px.bar(df_prod, x='tecnico', y='tareas', color='tareas', color_continuous_scale='Blues', labels={'tareas':'Tareas Completadas', 'tecnico':'Técnico'})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos de productividad disponibles.")

    with col2:
        st.subheader("⏱️ Tiempo Total por Técnico (Min)")
        if not df_prod.empty:
             fig_time = px.pie(df_prod, values='total_minutos', names='tecnico', title='Distribución de Tiempo Trabajado', hole=0.4)
             st.plotly_chart(fig_time, use_container_width=True)

    st.divider()
    st.subheader("📋 Lista Completa de Unidades Registradas")
    cur = get_cursor(dictionary=True)
    cur.execute("SELECT * FROM unidades ORDER BY unit_number")
    df_unidades = pd.DataFrame(cur.fetchall())
    cur.close()
    if not df_unidades.empty:
        # Renombrar columnas para visualización amigable basada en CAMPOS_UNIDAD
        rename_map = {k: CAMPOS_UNIDAD[k] for k in CAMPOS_UNIDAD if k in df_unidades.columns}
        rename_map['unit_number'] = 'UNIT #'
        rename_map['id_lote'] = 'LOTE'
        st.dataframe(df_unidades.rename(columns=rename_map), use_container_width=True, hide_index=True)
    else:
        st.info("No hay unidades registradas.")

    # Exportación Excel
    st.divider()
    st.subheader("📄 Reportes (Solo Admin)")
    if st.button("📥 Exportar Todo a Excel", use_container_width=True):
        try:
            with st.spinner("Generando reporte Excel..."):
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
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
                st.success("✅ Reporte generado correctamente. Haga clic en el botón de descarga.")
        except Exception as e:
            st.error(f"Error al generar Excel: {str(e)}")
            
    # Auto-refresh cada 60 segundos
    st.info("🔄 Dashboard se actualizará automáticamente cada 60 segundos...")
    time.sleep(60)
    st.rerun()
