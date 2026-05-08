import streamlit as st
import pandas as pd
import mysql.connector
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io
import pytz
import zipfile
import os

# ==================== CONFIGURACIÓN INICIAL ====================
st.set_page_config(
    page_title="Carrier Transicold – Sistema Operativo",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="❄️",
)

tijuana_tz = pytz.timezone('America/Tijuana')
ahora_tj = datetime.now(tijuana_tz)
fecha_hoy = ahora_tj.strftime('%Y-%m-%d')
hora_actual = ahora_tj.strftime('%H:%M:%S')

CARRIER_BLUE    = "#002B5B"
CARRIER_ACCENT  = "#0057A8"
CARRIER_LIGHT   = "#E8F0FB"
CARRIER_SUCCESS = "#16a34a"
CARRIER_WARN    = "#d97706"
CARRIER_DANGER  = "#dc2626"

LOGO_URL = "https://raw.githubusercontent.com/Jesusalan0102/app-escaneo-series/main/carrierlogo.jpg"

CAMPOS_SERIES = {
    "vin_number":              "VIN Number",
    "reefer_serial":           "Serie del Reefer",
    "reefer_model":            "Modelo del Reefer",
    "evaporator_serial_mjs11": "Evaporador MJS11",
    "evaporator_serial_mjd22": "Evaporador MJD22",
    "engine_serial":           "Motor",
    "compressor_serial":       "Compresor",
    "generator_serial":        "Generador",
    "battery_charger_serial":  "Cargador de Batería",
}

ACTIVIDADES_CARRIER = [
    "Cableado", "Programación", "Soldadura", "Check de fugas",
    "Vacío", "Cerrado", "Pre-viaje", "Horas Corridas",
    "Standby", "GPS", "Corriendo", "Inspección",
    "Accesorios", "Toma de Valores", "Evidencia", "Toma de Series",
]

MAX_FOTOS = 100

# ==================== CSS PREMIUM ====================
st.markdown(f"""
<style>
header[data-testid="stHeader"] {{ display: none !important; }}
footer {{ display: none !important; }}
#MainMenu {{ display: none !important; }}
.stDeployButton {{ display: none !important; }}
.block-container {{ padding-top: 1.5rem !important; }}
section[data-testid="stSidebar"] {{ width: 21rem !important; }}
.main-header {{ font-size: 1.75rem; font-weight: 800; color: {CARRIER_BLUE}; border-bottom: 3px solid {CARRIER_ACCENT}; padding-bottom: 12px; margin-bottom: 24px; }}
.section-title {{ font-size: 0.92rem; font-weight: 700; color: {CARRIER_BLUE}; border-left: 4px solid {CARRIER_ACCENT}; padding: 9px 14px; margin: 22px 0 14px 0; background: white; border-radius: 0 8px 8px 0; }}
.kpi-wrap {{ background: white; border-radius: 16px; padding: 20px; text-align: center; box-shadow: 0 4px 20px rgba(0,43,91,0.08); border-top: 5px solid {CARRIER_ACCENT}; }}
.kpi-num {{ font-size: 2.4rem; font-weight: 800; color: {CARRIER_BLUE}; }}
.kpi-lbl {{ font-size: 0.73rem; color: #6b7280; font-weight: 600; }}
.time-badge {{ background: {CARRIER_BLUE}; color: white; padding: 6px 16px; border-radius: 24px; float: right; }}
.login-card {{ background: white; padding: 36px 40px; border-radius: 20px; box-shadow: 0 12px 40px rgba(0,43,91,0.18); }}
.evidencia-info {{ background: #eff6ff; border-left: 5px solid #3b82f6; padding: 12px 18px; border-radius: 10px; margin-bottom: 14px; }}
.fotos-badge {{ background: #f0fdf4; border: 1px solid #86efac; border-radius: 20px; padding: 4px 14px; display: inline-block; }}
.tv-field-badge {{ background: {CARRIER_LIGHT}; border: 1px solid #c3d4f0; border-radius: 8px; padding: 6px 12px; display: inline-block; }}
.inv-info-bar {{ background: linear-gradient(90deg, {CARRIER_BLUE}, {CARRIER_ACCENT}); color: white; padding: 14px 20px; border-radius: 12px; margin-bottom: 16px; }}
.bloqueo-card {{ background: #fef2f2; border-left: 5px solid {CARRIER_DANGER}; border-radius: 10px; padding: 14px 18px; margin: 8px 0; }}
.user-chip {{ background: rgba(255,255,255,0.12); border-radius: 50px; padding: 6px 14px; color: white; display: inline-block; }}
</style>
""", unsafe_allow_html=True)

# ==================== CONEXIÓN DIRECTA A TIDB ====================
DB_CONFIG = {
    "host": "gateway01.us-east-1.prod.aws.tidbcloud.com",
    "port": 4000,
    "user": "4BgYs96t9XXhCMS.root",
    "password": "YZcSUhQ5H7Gx9vLk",
    "database": "carrier_db",
    "connection_timeout": 30,
    "autocommit": True,
    "use_pure": True,
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
        return None

def execute_query(query, params=None, fetch=True):
    conn = get_db_connection()
    if conn is None:
        return [] if fetch else False
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        if fetch:
            result = cursor.fetchall()
        else:
            result = True
        cursor.close()
        conn.close()
        return result
    except Exception as e:
        st.error(f"Error en consulta: {e}")
        return [] if fetch else False

# ==================== DIAGNÓSTICO INICIAL (OPCIONAL) ====================
# Puedes activar esto para ver los usuarios
# usuarios = execute_query("SELECT * FROM users")
# st.write(usuarios)

# ==================== ESTADO DE SESIÓN ====================
if "login" not in st.session_state:
    st.session_state.login = False
if "user" not in st.session_state:
    st.session_state.user = ""
if "role" not in st.session_state:
    st.session_state.role = ""
if "menu_sel" not in st.session_state:
    st.session_state.menu_sel = None

# ==================== LOGIN CON DIAGNÓSTICO ====================
if not st.session_state.login:
    st.markdown(f'<div style="text-align:center;padding:30px;"><img src="{LOGO_URL}" width="300"></div>', unsafe_allow_html=True)
    _, col_c, _ = st.columns([1,2,1])
    with col_c:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("<h3 style='text-align:center;color:#002B5B;'>Carrier Transicold</h3>", unsafe_allow_html=True)
        username = st.text_input("Usuario", key="login_user")
        password = st.text_input("Contraseña", type="password", key="login_pass")
        
        # Botón de diagnóstico (opcional)
        if st.checkbox("Mostrar diagnóstico"):
            total = execute_query("SELECT COUNT(*) as total FROM users")
            st.write(f"Total usuarios en BD: {total[0]['total'] if total else 0}")
            all_users = execute_query("SELECT username, password, LENGTH(password) as len_pass FROM users")
            st.write(all_users)
        
        if st.button("Ingresar", use_container_width=True, type="primary"):
            if username and password:
                with st.spinner("Verificando..."):
                    # Limpiar espacios
                    u_clean = username.strip()
                    p_clean = password.strip()
                    
                    # Consulta directa
                    query = "SELECT * FROM users WHERE username = %s AND password = %s"
                    user = execute_query(query, (u_clean, p_clean))
                    
                    # Si no funciona, probar con LOWER y TRIM
                    if not user:
                        query2 = "SELECT * FROM users WHERE LOWER(TRIM(username)) = LOWER(TRIM(%s)) AND BINARY password = BINARY %s"
                        user = execute_query(query2, (u_clean, p_clean))
                    
                    if user:
                        st.session_state.login = True
                        st.session_state.user = user[0]["username"]
                        st.session_state.role = user[0]["role"].lower()
                        st.rerun()
                    else:
                        # Mensaje detallado
                        st.error(f"❌ Credenciales incorrectas para '{u_clean}'. La tabla tiene {execute_query('SELECT COUNT(*) as total FROM users')[0]['total']} usuarios.")
                        st.info("Verifica mayúsculas, minúsculas y espacios. Si el problema persiste, usa el diagnóstico para revisar las contraseñas almacenadas.")
            else:
                st.warning("Ingresa usuario y contraseña")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# ==================== SIDEBAR ====================
with st.sidebar:
    st.image(LOGO_URL, width=200)
    st.markdown(f"<p style='margin-top:10px'><b>👤 {st.session_state.user}</b><br><span style='font-size:0.8rem'>{'🛡 Administrador' if st.session_state.role == 'admin' else '🔧 Técnico'}</span></p>", unsafe_allow_html=True)
    st.markdown("---")
    if st.session_state.role == "admin":
        menu_options = ["📊 Dashboard Ejecutivo", "🎯 Control de Asignaciones", "🎫 Tickets", "📦 Inventarios", "📸 Registro de Unidades", "👥 Gestión de Usuarios"]
    else:
        menu_options = ["🎯 Mis Tareas", "🔔 Nueva Solicitud"]
    menu = st.radio("MENÚ", menu_options, key="menu")
    st.session_state.menu_sel = menu
    st.markdown("---")
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        for k in ["login", "user", "role", "menu_sel"]:
            st.session_state[k] = False if k == "login" else None
        st.rerun()

# ==================== DASHBOARD EJECUTIVO (ADMIN) ====================
if menu == "📊 Dashboard Ejecutivo":
    st.markdown(f'<div class="time-badge">🕒 {hora_actual}</div><div class="main-header">📊 Panel de Rendimiento Operativo</div>', unsafe_allow_html=True)
    asig = execute_query("SELECT * FROM asignaciones")
    unid = execute_query("SELECT * FROM unidades")
    df_a = pd.DataFrame(asig) if asig else pd.DataFrame()
    total_u = len(unid)
    total_t = len(df_a)
    comp_t = int((df_a["estado"] == "completada").sum()) if not df_a.empty else 0
    proc_t = int((df_a["estado"] == "en_proceso").sum()) if not df_a.empty else 0
    pend_t = int((df_a["estado"] == "pendiente").sum()) if not df_a.empty else 0
    pct_av = round(comp_t / total_t * 100) if total_t else 0
    col1, col2, col3, col4, col5 = st.columns(5)
    for col, val, lbl, cls in [
        (col1, total_u, "Total Unidades", ""),
        (col2, comp_t, "Completadas", "green"),
        (col3, proc_t, "En Proceso", "amber"),
        (col4, pend_t, "Pendientes", "red"),
        (col5, f"{pct_av}%", "Avance Global", "purple"),
    ]:
        with col:
            st.markdown(f'<div class="kpi-wrap {cls}"><div class="kpi-num">{val}</div><div class="kpi-lbl">{lbl}</div></div>', unsafe_allow_html=True)
    st.markdown("<br>")
    if not df_a.empty:
        st.markdown('<div class="section-title">📈 Estadísticas por Técnico</div>', unsafe_allow_html=True)
        stats = df_a.groupby("tecnico").agg(
            Total=("id","count"),
            Completadas=("estado", lambda x: (x=="completada").sum()),
            En_Curso=("estado", lambda x: (x=="en_proceso").sum()),
            Pendientes=("estado", lambda x: (x=="pendiente").sum())
        ).reset_index()
        stats["Rendimiento %"] = ((stats["Completadas"] / stats["Total"]) * 100).round(0).astype(int)
        st.dataframe(stats.sort_values("Total", ascending=False), use_container_width=True, hide_index=True)
        COLOR_MAP = {"completada": CARRIER_SUCCESS, "en_proceso": CARRIER_WARN, "pendiente": CARRIER_DANGER, "solicitado": "#6b7280"}
        c1, c2 = st.columns(2)
        with c1:
            fig_b = px.bar(df_a, x="tecnico", color="estado", title="Carga de Trabajo por Técnico", color_discrete_map=COLOR_MAP, template="plotly_white")
            fig_b.update_layout(paper_bgcolor="white", plot_bgcolor="white")
            st.plotly_chart(fig_b, use_container_width=True)
        with c2:
            fig_p = px.pie(df_a, names="estado", title="Distribución Global", hole=0.55, color_discrete_map=COLOR_MAP, template="plotly_white")
            fig_p.update_layout(paper_bgcolor="white")
            st.plotly_chart(fig_p, use_container_width=True)
    st.markdown('<div class="section-title">📋 Estatus de Proceso por Unidad</div>', unsafe_allow_html=True)
    if unid:
        completadas_raw = execute_query("SELECT unidad, actividad_id FROM asignaciones WHERE estado='completada'")
        completed_set = {(r["unidad"], r["actividad_id"]) for r in completadas_raw}
        status_data = []
        for u in unid:
            row = {"LOTE": u["id_lote"], "#Económico": u["unit_number"]}
            for act in ACTIVIDADES_CARRIER:
                row[act] = "✔" if (u["unit_number"], act) in completed_set else "–"
            status_data.append(row)
        st.dataframe(pd.DataFrame(status_data), use_container_width=True, hide_index=True, height=340)
    st.markdown('<div class="section-title">📂 Descarga de Evidencias por Unidad</div>', unsafe_allow_html=True)
    if unid:
        col_ev1, col_ev2 = st.columns([3,1])
        with col_ev1:
            u_sel_ev = st.selectbox("Selecciona unidad:", [u["unit_number"] for u in unid], key="ev_sel")
        ev_archivos = execute_query("SELECT nombre_archivo, contenido FROM evidencias WHERE unit_number=%s", (u_sel_ev,))
        with col_ev2:
            st.metric("📸 Fotos", len(ev_archivos))
        if ev_archivos:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "a", zipfile.ZIP_DEFLATED, False) as zf:
                for ev in ev_archivos:
                    zf.writestr(ev["nombre_archivo"], ev["contenido"])
            st.download_button(f"📥 Descargar {len(ev_archivos)} fotos — Unidad {u_sel_ev}", buf.getvalue(), f"{u_sel_ev}_evidencia.zip", use_container_width=True)
        else:
            st.info("Sin fotos cargadas")
    st.markdown('<div class="section-title">📥 Reportes y Descargas</div>', unsafe_allow_html=True)
    if unid:
        df_u = pd.DataFrame(unid)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_u.to_excel(writer, index=False, sheet_name="Series_Unidades")
            if not df_a.empty:
                df_a.to_excel(writer, index=False, sheet_name="Actividades")
        st.download_button("📊 Descargar Reporte Maestro (Excel)", buffer.getvalue(), f"Carrier_Reporte_{fecha_hoy}.xlsx", use_container_width=True, type="primary")

# ==================== CONTROL DE ASIGNACIONES (ADMIN) ====================
elif menu == "🎯 Control de Asignaciones":
    st.markdown('<div class="main-header">🎯 Gestión de Órdenes de Trabajo</div>', unsafe_allow_html=True)
    solicitudes = execute_query("SELECT * FROM asignaciones WHERE estado='solicitado'")
    if solicitudes:
        st.markdown(f"### 📨 Solicitudes pendientes ({len(solicitudes)})")
        for s in solicitudes:
            with st.container():
                col1, col2, col3 = st.columns([3,1,1])
                col1.warning(f"**{s['tecnico']}** solicita **{s['actividad_id']}** para unidad **{s['unidad']}**")
                if col2.button("✅ Aprobar", key=f"ap_{s['id']}"):
                    execute_query("UPDATE asignaciones SET estado='pendiente' WHERE id=%s", (s['id'],), fetch=False)
                    st.rerun()
                if col3.button("❌ Rechazar", key=f"re_{s['id']}"):
                    execute_query("DELETE FROM asignaciones WHERE id=%s", (s['id'],), fetch=False)
                    st.rerun()
                st.markdown("---")
    else:
        st.success("No hay solicitudes pendientes")
    st.markdown("### ➕ Asignación directa")
    unidades = execute_query("SELECT unit_number FROM unidades")
    tecnicos = execute_query("SELECT username FROM users WHERE role='tecnico'")
    with st.form("asignacion_directa"):
        c1, c2, c3 = st.columns(3)
        unidad = c1.selectbox("Unidad", [u["unit_number"] for u in unidades] if unidades else [])
        tecnico = c2.selectbox("Técnico", [t["username"] for t in tecnicos] if tecnicos else [])
        actividad = c3.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.form_submit_button("📋 Crear orden", type="primary"):
            if unidad and tecnico and actividad:
                execute_query("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s,%s,%s,'pendiente')", (unidad, actividad, tecnico), fetch=False)
                st.success("Orden creada")
                st.rerun()

# ==================== MIS TAREAS (TÉCNICO) ====================
elif menu == "🎯 Mis Tareas":
    st.markdown('<div class="main-header">🎯 Mis Actividades</div>', unsafe_allow_html=True)
    tareas = execute_query("SELECT * FROM asignaciones WHERE tecnico=%s AND estado IN ('pendiente','en_proceso')", (st.session_state.user,))
    if not tareas:
        st.info("No tienes tareas pendientes")
    for t in tareas:
        with st.expander(f"{'⏳' if t['estado']=='pendiente' else '▶️'} Unidad {t['unidad']} - {t['actividad_id']}"):
            if t["estado"] == "pendiente":
                if st.button("Iniciar", key=f"ini_{t['id']}"):
                    execute_query("UPDATE asignaciones SET estado='en_proceso', fecha_inicio=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']), fetch=False)
                    st.rerun()
            else:
                if t["actividad_id"].lower() == "evidencia":
                    fotos = execute_query("SELECT COUNT(*) as total FROM evidencias WHERE unit_number=%s AND tecnico=%s", (t["unidad"], st.session_state.user))
                    total_fotos = fotos[0]["total"] if fotos else 0
                    st.info(f"📸 Fotos guardadas: {total_fotos}/{MAX_FOTOS}")
                    archivos = st.file_uploader("Selecciona fotos", accept_multiple_files=True, type=["jpg","jpeg","png"], key=f"fotos_{t['id']}")
                    if archivos and st.button("Guardar fotos", key=f"guardar_{t['id']}"):
                        for arc in archivos[:MAX_FOTOS - total_fotos]:
                            execute_query("INSERT INTO evidencias (unit_number, nombre_archivo, contenido, tecnico) VALUES (%s,%s,%s,%s)", (t["unidad"], arc.name, arc.read(), st.session_state.user), fetch=False)
                        st.rerun()
                    comentario = st.text_area("Comentario", key=f"coment_{t['id']}")
                    if st.button("✅ Finalizar", key=f"fin_{t['id']}"):
                        if comentario:
                            execute_query("INSERT INTO comentarios_actividades (asignacion_id, tecnico, comentario) VALUES (%s,%s,%s)", (t['id'], st.session_state.user, comentario), fetch=False)
                        execute_query("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']), fetch=False)
                        st.success("Actividad completada")
                        st.rerun()
                else:
                    comentario = st.text_area("Comentario", key=f"coment_{t['id']}")
                    if st.button("✅ Terminar", key=f"fin_{t['id']}", type="primary"):
                        if comentario:
                            execute_query("INSERT INTO comentarios_actividades (asignacion_id, tecnico, comentario) VALUES (%s,%s,%s)", (t['id'], st.session_state.user, comentario), fetch=False)
                        execute_query("UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']), fetch=False)
                        st.success("Actividad completada")
                        st.rerun()

# ==================== NUEVA SOLICITUD (TÉCNICO) ====================
elif menu == "🔔 Nueva Solicitud":
    st.markdown('<div class="main-header">🔔 Solicitar Actividad</div>', unsafe_allow_html=True)
    unidades = execute_query("SELECT unit_number FROM unidades")
    with st.form("nueva_solicitud"):
        unidad = st.selectbox("Unidad", [u["unit_number"] for u in unidades] if unidades else [])
        actividad = st.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.form_submit_button("Enviar solicitud", type="primary"):
            if unidad and actividad:
                existente = execute_query("SELECT id FROM asignaciones WHERE tecnico=%s AND unidad=%s AND actividad_id=%s AND estado IN ('solicitado','pendiente','en_proceso')", (st.session_state.user, unidad, actividad))
                if existente:
                    st.error("Ya tienes esta actividad pendiente o en curso")
                else:
                    execute_query("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) VALUES (%s,%s,%s,'solicitado')", (unidad, actividad, st.session_state.user), fetch=False)
                    st.success("Solicitud enviada")
                    st.rerun()

# ==================== TICKETS (SOLO ADMIN) ====================
elif menu == "🎫 Tickets":
    st.markdown('<div class="main-header">🎫 Gestión de Tickets</div>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["📋 Listado de Tickets", "➕ Crear nuevo ticket"])
    with tab1:
        tickets = execute_query("SELECT t.*, a.id as asignacion_id, a.tecnico FROM tickets t LEFT JOIN asignaciones a ON t.id = a.ticket_id ORDER BY t.ticket_num DESC")
        if tickets:
            for t in tickets:
                if not t["atendido"]:
                    estado_color = "🔴 No atendido"
                elif t["atendido"] and not t["reporte_enviado"]:
                    estado_color = "🟡 Atendido (sin reporte)"
                else:
                    estado_color = "🟢 Completado"
                with st.container():
                    st.markdown(f'<div style="background:#f8f9fa; border-left: 6px solid {CARRIER_ACCENT}; padding:12px; border-radius:10px; margin-bottom:12px;">', unsafe_allow_html=True)
                    col1, col2, col3 = st.columns([1,3,1])
                    col1.markdown(f"## #{t['ticket_num']}")
                    col1.markdown(f"**{estado_color}**")
                    col2.markdown(f"**Unidad:** {t['unit_number']} | **VIN:** {t.get('vin_number','N/D')}")
                    col2.markdown(f"**Descripción:** {t['descripcion']}")
                    col2.markdown(f"*Creado por: {t['creado_por']} | {t['fecha_creacion']}*")
                    if t.get("tecnico"):
                        col2.markdown(f"*Asignado a: {t['tecnico']}*")
                    with col3:
                        if t["atendido"] and not t["reporte_enviado"]:
                            if st.button("📤 Marcar reporte enviado", key=f"reporte_{t['id']}"):
                                execute_query("UPDATE tickets SET reporte_enviado=TRUE, fecha_reporte=%s WHERE id=%s", (datetime.now(tijuana_tz), t['id']), fetch=False)
                                st.rerun()
                        if not t["atendido"]:
                            st.caption("⏳ Esperando atención")
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No hay tickets")
    with tab2:
        unidades = execute_query("SELECT unit_number, vin_number FROM unidades")
        tecnicos = execute_query("SELECT username FROM users WHERE role='tecnico'")
        with st.form("nuevo_ticket"):
            st.markdown("### Crear nuevo ticket")
            unidad_opciones = {f"{u['unit_number']} - {u.get('vin_number','sin VIN')}": u['unit_number'] for u in unidades}
            unidad_label = st.selectbox("Unidad (SAP)", list(unidad_opciones.keys()))
            unidad_seleccionada = unidad_opciones[unidad_label]
            vin_auto = next((u.get("vin_number") for u in unidades if u["unit_number"] == unidad_seleccionada), "")
            vin = st.text_input("VIN Number", value=vin_auto)
            descripcion = st.text_area("Descripción del problema")
            tecnico_asignado = st.selectbox("Asignar a técnico", [t["username"] for t in tecnicos] if tecnicos else [])
            if st.form_submit_button("📌 Crear ticket", type="primary"):
                if unidad_seleccionada and descripcion and tecnico_asignado:
                    max_num = execute_query("SELECT MAX(ticket_num) as max_num FROM tickets")
                    next_num = (max_num[0]["max_num"] or 0) + 1 if max_num else 1
                    execute_query("INSERT INTO tickets (ticket_num, unit_number, vin_number, descripcion, creado_por) VALUES (%s,%s,%s,%s,%s)", (next_num, unidad_seleccionada, vin, descripcion, st.session_state.user), fetch=False)
                    ticket = execute_query("SELECT id FROM tickets WHERE ticket_num=%s", (next_num,))
                    if ticket:
                        execute_query("INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado, ticket_id) VALUES (%s,%s,%s,'pendiente',%s)", (unidad_seleccionada, f"Ticket #{next_num}", tecnico_asignado, ticket[0]['id']), fetch=False)
                    st.success(f"Ticket #{next_num} creado y asignado a {tecnico_asignado}")
                    st.rerun()
                else:
                    st.warning("Completa todos los campos")

# ==================== INVENTARIOS ====================
elif menu == "📦 Inventarios":
    st.markdown(f'<div class="time-badge">🕒 {hora_actual}</div><div class="main-header">📦 Gestión de Inventarios</div>', unsafe_allow_html=True)
    def get_inv_columnas():
        rows = execute_query("SELECT col_nombre, col_orden FROM inventario_columnas WHERE tabla_nombre='Principal' ORDER BY col_orden ASC")
        return [r["col_nombre"] for r in rows] if rows else []
    def save_inv_columnas(columnas):
        execute_query("DELETE FROM inventario_columnas WHERE tabla_nombre='Principal'", fetch=False)
        for i, c in enumerate(columnas):
            execute_query("INSERT INTO inventario_columnas (tabla_nombre, col_nombre, col_orden) VALUES (%s,%s,%s)", ("Principal", c, i), fetch=False)
    def get_inv_data(columnas):
        if not columnas:
            return pd.DataFrame()
        rows = execute_query("SELECT fila_idx, col_nombre, valor FROM inventario_data WHERE tabla_nombre='Principal' ORDER BY fila_idx ASC, col_nombre ASC")
        if not rows:
            return pd.DataFrame(columns=columnas)
        data_dict = {}
        for r in rows:
            fi = r["fila_idx"]
            if fi not in data_dict:
                data_dict[fi] = {c: "" for c in columnas}
            if r["col_nombre"] in columnas:
                data_dict[fi][r["col_nombre"]] = r["valor"] or ""
        return pd.DataFrame([data_dict[k] for k in sorted(data_dict.keys())], columns=columnas)
    def save_inv_data(df):
        execute_query("DELETE FROM inventario_data WHERE tabla_nombre='Principal'", fetch=False)
        for i, row in df.iterrows():
            for col in df.columns:
                execute_query("INSERT INTO inventario_data (tabla_nombre, fila_idx, col_nombre, valor) VALUES (%s,%s,%s,%s)", ("Principal", i, col, str(row[col])), fetch=False)
    columnas = get_inv_columnas()
    if not columnas:
        columnas = ["Código", "Descripción", "Cantidad", "Unidad", "Ubicación", "Estado"]
        save_inv_columnas(columnas)
    df_inv = get_inv_data(columnas)
    st.markdown(f'<div class="inv-info-bar">🗄 Inventario Principal · {len(df_inv)} registros · {len(columnas)} columnas</div>', unsafe_allow_html=True)
    tab_inv1, tab_inv2 = st.tabs(["📋 Tabla de Inventario", "⚙️ Configurar Columnas"])
    with tab_inv1:
        if st.button("➕ Agregar Fila"):
            nueva_fila = pd.DataFrame([{c: "" for c in columnas}])
            df_inv = pd.concat([df_inv, nueva_fila], ignore_index=True)
            save_inv_data(df_inv)
            st.rerun()
        if not df_inv.empty:
            df_edit = st.data_editor(df_inv, use_container_width=True, num_rows="dynamic", key="inv_editor")
            if st.button("💾 Guardar cambios"):
                save_inv_data(df_edit)
                st.success("Inventario actualizado")
                st.rerun()
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as w:
                df_inv.to_excel(w, index=False, sheet_name="Inventario")
            st.download_button("📥 Exportar a Excel", buf.getvalue(), f"Inventario_{fecha_hoy}.xlsx", use_container_width=True)
    with tab_inv2:
        with st.form("add_col"):
            nueva = st.text_input("Nueva columna")
            if st.form_submit_button("Agregar"):
                if nueva and nueva not in columnas:
                    columnas.append(nueva)
                    save_inv_columnas(columnas)
                    if not df_inv.empty:
                        df_inv[nueva] = ""
                        save_inv_data(df_inv)
                    st.rerun()
        st.markdown("### Columnas actuales")
        for i, col in enumerate(columnas):
            c1, c2, c3 = st.columns([3,2,1])
            c1.markdown(f"**{col}**")
            nuevo_nom = c2.text_input("Renombrar", value=col, key=f"ren_{i}", label_visibility="collapsed")
            if c3.button("✏️", key=f"renb_{i}"):
                if nuevo_nom and nuevo_nom != col:
                    if not df_inv.empty and col in df_inv.columns:
                        df_inv = df_inv.rename(columns={col: nuevo_nom})
                        save_inv_data(df_inv)
                    columnas[i] = nuevo_nom
                    save_inv_columnas(columnas)
                    st.rerun()
            if len(columnas) > 1 and c3.button("🗑", key=f"del_{i}"):
                columnas.pop(i)
                save_inv_columnas(columnas)
                if not df_inv.empty and col in df_inv.columns:
                    df_inv = df_inv.drop(columns=[col])
                    save_inv_data(df_inv)
                st.rerun()
            st.markdown("<hr>", unsafe_allow_html=True)

# ==================== REGISTRO DE UNIDADES (ADMIN) ====================
elif menu == "📸 Registro de Unidades":
    st.markdown('<div class="main-header">📸 Registro de Unidades</div>', unsafe_allow_html=True)
    with st.form("reg_unidad"):
        col1, col2 = st.columns(2)
        unit = col1.text_input("Número Económico (SAP)")
        lote = col1.text_input("Lote")
        campo = col2.selectbox("Campo a registrar", ["Ninguno"] + list(CAMPOS_SERIES.keys()))
        valor = col2.text_input("Valor del serial")
        if st.form_submit_button("💾 Guardar unidad", type="primary"):
            if unit:
                if campo != "Ninguno":
                    execute_query(f"INSERT INTO unidades (unit_number, id_lote, {campo}) VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE id_lote=%s, {campo}=%s", (unit, lote, valor, lote, valor), fetch=False)
                else:
                    execute_query("INSERT INTO unidades (unit_number, id_lote) VALUES (%s,%s) ON DUPLICATE KEY UPDATE id_lote=%s", (unit, lote, lote), fetch=False)
                st.success("Registro guardado")
                st.rerun()
    unidades = execute_query("SELECT * FROM unidades ORDER BY unit_number")
    if unidades:
        st.dataframe(pd.DataFrame(unidades), use_container_width=True, hide_index=True)

# ==================== GESTIÓN DE USUARIOS (ADMIN) ====================
elif menu == "👥 Gestión de Usuarios":
    st.markdown('<div class="main-header">👥 Usuarios del Sistema</div>', unsafe_allow_html=True)
    usuarios = execute_query("SELECT username, role FROM users ORDER BY username")
    if usuarios:
        st.dataframe(pd.DataFrame(usuarios), use_container_width=True, hide_index=True)
    with st.expander("➕ Crear nuevo usuario"):
        with st.form("new_user"):
            c1, c2, c3 = st.columns(3)
            u = c1.text_input("Usuario")
            p = c2.text_input("Contraseña", type="password")
            r = c3.selectbox("Rol", ["tecnico", "admin"])
            if st.form_submit_button("Crear", type="primary"):
                if u and p:
                    execute_query("INSERT INTO users (username, password, role) VALUES (%s,%s,%s)", (u, p, r), fetch=False)
                    st.success(f"Usuario {u} creado")
                    st.rerun()