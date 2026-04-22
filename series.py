import streamlit as st
import pandas as pd
import mysql.connector
import plotly.express as px
from datetime import datetime
import io
import pytz
import zipfile
from streamlit_autorefresh import st_autorefresh

# ==================== CONFIGURACIÓN INICIAL ====================
st.set_page_config(
    page_title="Carrier Transicold - Panel de Control",
    layout="wide",
    initial_sidebar_state="expanded"
)
st_autorefresh(interval=30 * 1000, key="global_refresh")

tijuana_tz  = pytz.timezone('America/Tijuana')
ahora_tj    = datetime.now(tijuana_tz)
fecha_hoy   = ahora_tj.strftime('%Y-%m-%d')
hora_actual = ahora_tj.strftime('%H:%M:%S')

CARRIER_BLUE   = "#002B5B"
CARRIER_ACCENT = "#0057A8"
LOGO_URL  = "https://raw.githubusercontent.com/Jesusalan0102/app-escaneo-series/main/carrierlogo2.jpeg.jpg"
SOUND_URL = "https://raw.githubusercontent.com/rafaelEscalante/notification-sounds/master/pings/ping-8.mp3"

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
    "Standby", "GPS", "Run", "Corriendo", "Inspección",
    "Accesorios", "Toma de Valores", "Evidencia", "Toma de Series",
]

MAX_FOTOS = 100   # Límite máximo de fotos por tarea de Evidencia

# ==================== CSS ====================
st.markdown(f"""
<style>
/* ── Base ── */
.stApp {{ background-color: #F0F4F9; }}

/* ── Sidebar ── */
section[data-testid="stSidebar"] > div:first-child {{
    background: linear-gradient(180deg, {CARRIER_BLUE} 0%, #01418a 100%);
    padding-top: 1rem;
}}
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] div {{ color: #e8eef8 !important; }}
section[data-testid="stSidebar"] .stRadio > label {{ color: white !important; font-weight: 600; }}
section[data-testid="stSidebar"] hr {{ border-color: rgba(255,255,255,0.18) !important; }}
section[data-testid="stSidebar"] button {{
    background: rgba(255,255,255,0.12) !important;
    color: white !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
    border-radius: 8px !important;
}}
section[data-testid="stSidebar"] button:hover {{ background: rgba(255,255,255,0.22) !important; }}

/* ── Títulos ── */
.main-header {{
    font-size: 1.85rem; font-weight: 700; color: {CARRIER_BLUE};
    border-bottom: 3px solid {CARRIER_ACCENT};
    padding-bottom: 10px; margin-bottom: 22px;
}}
.section-title {{
    font-size: 1rem; font-weight: 600; color: {CARRIER_BLUE};
    border-left: 4px solid {CARRIER_ACCENT};
    padding: 8px 12px; margin: 20px 0 12px 0;
    background: white; border-radius: 0 6px 6px 0;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}}

/* ── KPI cards ── */
.kpi-wrap {{
    background: white; border-radius: 12px;
    padding: 18px 20px; text-align: center;
    box-shadow: 0 2px 10px rgba(0,43,91,0.09);
    border-top: 4px solid {CARRIER_ACCENT};
}}
.kpi-wrap.green  {{ border-top-color: #16a34a; }}
.kpi-wrap.amber  {{ border-top-color: #d97706; }}
.kpi-wrap.red    {{ border-top-color: #dc2626; }}
.kpi-wrap.purple {{ border-top-color: #7c3aed; }}
.kpi-num {{ font-size: 2.1rem; font-weight: 700; color: {CARRIER_BLUE}; line-height: 1.1; }}
.kpi-wrap.green  .kpi-num {{ color: #16a34a; }}
.kpi-wrap.amber  .kpi-num {{ color: #d97706; }}
.kpi-wrap.red    .kpi-num {{ color: #dc2626; }}
.kpi-wrap.purple .kpi-num {{ color: #7c3aed; }}
.kpi-lbl {{
    font-size: 0.78rem; color: #6b7280; font-weight: 500;
    text-transform: uppercase; letter-spacing: 0.4px; margin-top: 4px;
}}

/* ── Badge hora ── */
.time-badge {{
    background: {CARRIER_BLUE}; color: white;
    padding: 5px 14px; border-radius: 20px;
    font-size: 0.85rem; float: right; margin-top: 2px;
}}

/* ── Expanders ── */
div[data-testid="stExpander"] {{
    background: white; border-radius: 10px;
    box-shadow: 0 1px 5px rgba(0,0,0,0.07);
    border: 1px solid #e5eaf2; margin-bottom: 8px;
}}

/* ── Botones ── */
.stButton > button {{
    border-radius: 8px; font-weight: 600;
    transition: transform .15s, box-shadow .15s;
}}
.stButton > button:hover {{
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0,43,91,0.18);
}}

/* ── Uploader / Cámara ── */
div[data-testid="stFileUploader"],
div[data-testid="stCameraInput"] {{
    background: white; border-radius: 10px;
    border: 2px dashed #c3cfe2; padding: 8px;
}}

/* ── Formularios ── */
div[data-testid="stForm"] {{
    background: white; border-radius: 12px;
    padding: 20px 24px;
    box-shadow: 0 2px 10px rgba(0,43,91,0.07);
    border: 1px solid #e5eaf2;
}}
</style>
""", unsafe_allow_html=True)


# ==================== BASE DE DATOS ====================
def get_db_connection():
    try:
        return mysql.connector.connect(**st.secrets["db"], autocommit=True)
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

def execute_read(query, params=None):
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute(query, params or ())
            res = cur.fetchall()
            cur.close(); conn.close()
            return res
        except Exception as e:
            st.error(f"Error de consulta: {e}")
    return []

def execute_write(query, params=None):
    conn = get_db_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(query, params or ())
            cur.close(); conn.close()
            return True
        except Exception as e:
            st.error(f"Error en base de datos: {e}")
            return False
    return False


# ==================== ESTADO DE SESIÓN ====================
for k, v in {"login": False, "user": "", "role": "", "last_count": 0}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ==================== LOGIN ====================
if not st.session_state.login:
    st.markdown(
        f'<div style="text-align:center;padding:40px 0 10px;">'
        f'<img src="{LOGO_URL}" width="520" style="border-radius:8px;"></div>',
        unsafe_allow_html=True,
    )
    _, col_c, _ = st.columns([1, 1.3, 1])
    with col_c:
        st.markdown(
            '<div style="background:white;padding:32px;border-radius:16px;'
            'box-shadow:0 6px 28px rgba(0,43,91,0.14);">',
            unsafe_allow_html=True,
        )
        with st.form("login_form"):
            st.markdown(
                f"<h3 style='text-align:center;color:{CARRIER_BLUE};margin-bottom:18px;'>"
                "🔐 Panel de Acceso</h3>",
                unsafe_allow_html=True,
            )
            u_log = st.text_input("👤 Usuario")
            p_log = st.text_input("🔑 Contraseña", type="password")
            if st.form_submit_button("Ingresar al Sistema", use_container_width=True, type="primary"):
                user = execute_read(
                    "SELECT * FROM users WHERE username=%s AND password=%s",
                    (u_log.strip(), p_log.strip()),
                )
                if user:
                    st.session_state.update({
                        "login": True,
                        "user":  user[0]["username"],
                        "role":  user[0]["role"].lower(),
                    })
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()


# ==================== SIDEBAR ====================
with st.sidebar:
    st.image(LOGO_URL, width=220)
    st.markdown(
        f"<p style='margin:4px 0;font-size:.88rem;'>🕒 <b>{hora_actual}</b> &nbsp;|&nbsp; {fecha_hoy}</p>",
        unsafe_allow_html=True,
    )
    st.markdown("---")
    role_label = "🛡 Administrador" if st.session_state.role == "admin" else "🔧 Técnico"
    st.markdown(
        f"<p style='margin:0;'>👤 <b>{st.session_state.user}</b></p>"
        f"<span style='background:rgba(255,255,255,.18);padding:2px 10px;"
        f"border-radius:20px;font-size:.8rem;'>{role_label}</span>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    if st.session_state.role == "admin":
        menu = st.radio(
            "MENÚ PRINCIPAL",
            ["📊 Dashboard Ejecutivo", "🎯 Control de Asignaciones",
             "📸 Registro de Unidades", "👥 Gestión de Usuarios"],
        )
    else:
        menu = st.radio("ÁREA DE TRABAJO", ["🎯 Mis Tareas", "🔔 Nueva Solicitud"])

    st.markdown("---")
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.clear()
        st.rerun()


# ==================== DASHBOARD EJECUTIVO ====================
if menu == "📊 Dashboard Ejecutivo":
    st.markdown(
        f'<div class="time-badge">🕒 Tijuana: {hora_actual}</div>'
        f'<div class="main-header">📊 Panel de Rendimiento Operativo</div>',
        unsafe_allow_html=True,
    )

    asig = execute_read("SELECT * FROM asignaciones")
    unid = execute_read("SELECT * FROM unidades")
    df_a = pd.DataFrame(asig) if asig else pd.DataFrame()

    # ── KPIs ──
    total_u = len(unid)
    total_t = len(df_a)
    comp_t  = int((df_a["estado"] == "completada").sum()) if not df_a.empty else 0
    proc_t  = int((df_a["estado"] == "en_proceso").sum()) if not df_a.empty else 0
    pend_t  = int((df_a["estado"] == "pendiente").sum())  if not df_a.empty else 0
    pct_av  = round(comp_t / total_t * 100) if total_t else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    for col, val, lbl, cls in [
        (k1, total_u,       "Total Unidades",  ""),
        (k2, comp_t,        "Completadas",     "green"),
        (k3, proc_t,        "En Proceso",      "amber"),
        (k4, pend_t,        "Pendientes",      "red"),
        (k5, f"{pct_av}%",  "Avance Global",   "purple"),
    ]:
        with col:
            st.markdown(
                f'<div class="kpi-wrap {cls}">'
                f'<div class="kpi-num">{val}</div>'
                f'<div class="kpi-lbl">{lbl}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Estadísticas y gráficas ──
    if not df_a.empty:
        st.markdown('<div class="section-title">📈 Estadísticas por Técnico</div>', unsafe_allow_html=True)
        stats = df_a.groupby("tecnico").agg(
            Total      =("id",     "count"),
            Completadas=("estado", lambda x: (x == "completada").sum()),
            En_Curso   =("estado", lambda x: (x == "en_proceso").sum()),
            Pendientes =("estado", lambda x: (x == "pendiente").sum()),
        ).reset_index()
        stats["Rendimiento %"] = ((stats["Completadas"] / stats["Total"]) * 100).round(0).astype(int)
        st.dataframe(stats.sort_values("Total", ascending=False), use_container_width=True, hide_index=True)

        COLOR_MAP = {
            "completada": "#16a34a", "en_proceso": "#f59e0b",
            "pendiente":  "#dc2626", "solicitado": "#6b7280",
        }
        c1, c2 = st.columns([2, 1])
        with c1:
            fig_b = px.bar(
                df_a, x="tecnico", color="estado",
                title="Carga de Trabajo por Técnico",
                color_discrete_map=COLOR_MAP, template="plotly_white",
            )
            fig_b.update_layout(paper_bgcolor="white", plot_bgcolor="white")
            st.plotly_chart(fig_b, use_container_width=True)
        with c2:
            fig_p = px.pie(
                df_a, names="estado", title="Distribución Global",
                hole=0.52, color_discrete_map=COLOR_MAP, template="plotly_white",
            )
            fig_p.update_layout(paper_bgcolor="white")
            st.plotly_chart(fig_p, use_container_width=True)

    # ── Tabla estatus por unidad ──
    st.markdown('<div class="section-title">📋 Estatus de Proceso por Unidad</div>', unsafe_allow_html=True)
    if unid:
        completadas_raw = execute_read(
            "SELECT unidad, actividad_id FROM asignaciones WHERE estado='completada'"
        )
        completed_set = {(r["unidad"], r["actividad_id"]) for r in completadas_raw}
        status_data = []
        for u in unid:
            row = {"LOTE": u["id_lote"], "#Económico": u["unit_number"]}
            for act in ACTIVIDADES_CARRIER:
                row[act] = "✔" if (u["unit_number"], act) in completed_set else "–"
            status_data.append(row)
        st.dataframe(pd.DataFrame(status_data), use_container_width=True, hide_index=True, height=340)

    # ── Descarga de evidencias ──
    st.markdown('<div class="section-title">📂 Descarga de Evidencias por Unidad</div>', unsafe_allow_html=True)
    if unid:
        col_ev1, col_ev2 = st.columns([3, 1])
        with col_ev1:
            u_sel_ev = st.selectbox("Selecciona unidad:", [u["unit_number"] for u in unid], key="ev_sel")
        ev_archivos = execute_read(
            "SELECT nombre_archivo, contenido FROM evidencias WHERE unit_number=%s", (u_sel_ev,)
        )
        with col_ev2:
            st.metric("📸 Fotos", len(ev_archivos))
        if ev_archivos:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "a", zipfile.ZIP_DEFLATED, False) as zf:
                for ev in ev_archivos:
                    zf.writestr(ev["nombre_archivo"], ev["contenido"])
            st.download_button(
                f"📥 Descargar {len(ev_archivos)} fotos — Unidad {u_sel_ev}",
                buf.getvalue(), f"{u_sel_ev}_evidencia.zip", "application/zip",
                use_container_width=True,
            )
        else:
            st.info("Sin fotos cargadas para esta unidad.")

    # ── Reporte maestro Excel ──
    st.markdown('<div class="section-title">📥 Reportes y Descargas</div>', unsafe_allow_html=True)
    if unid:
        df_u = pd.DataFrame(unid)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_u.to_excel(writer, index=False, sheet_name="Series_Unidades")
            if not df_a.empty:
                df_a.to_excel(writer, index=False, sheet_name="Actividades")
        st.download_button(
            "📊 Descargar Reporte Maestro General (Excel)",
            buffer.getvalue(), f"Carrier_Reporte_{fecha_hoy}.xlsx",
            use_container_width=True, type="primary",
        )
        st.markdown("<br>", unsafe_allow_html=True)
        for lote in sorted(df_u["id_lote"].unique()):
            n = len(df_u[df_u["id_lote"] == lote])
            with st.expander(f"📦 Lote: {lote}  ({n} unidades)"):
                st.table(df_u[df_u["id_lote"] == lote][["unit_number"] + list(CAMPOS_SERIES.keys())])


# ==================== CONTROL DE ASIGNACIONES (Admin) ====================
elif menu == "🎯 Control de Asignaciones":
    st.markdown('<div class="main-header">🎯 Gestión de Órdenes de Trabajo</div>', unsafe_allow_html=True)

    sols = execute_read("SELECT * FROM asignaciones WHERE estado='solicitado'")

    # Alerta sonora cuando llegan nuevas solicitudes
    if len(sols) > st.session_state.last_count:
        st.markdown(
            f'<audio autoplay><source src="{SOUND_URL}" type="audio/mp3"></audio>',
            unsafe_allow_html=True,
        )
    st.session_state.last_count = len(sols)

    if not sols:
        st.success("✅ Sin solicitudes pendientes de aprobar.")
    else:
        st.markdown('<div class="section-title">🔔 Solicitudes Nuevas</div>', unsafe_allow_html=True)
        for s in sols:
            col_inf, col_ap, col_den = st.columns([4, 1, 1])
            with col_inf:
                st.warning(
                    f"**{s['tecnico']}** solicita **{s['actividad_id']}** — Unidad: **{s['unidad']}**"
                )
                dup = execute_read(
                    "SELECT tecnico FROM asignaciones "
                    "WHERE unidad=%s AND actividad_id=%s AND estado='completada'",
                    (s["unidad"], s["actividad_id"]),
                )
                if dup:
                    st.error(f"⚠️ Ya completado por {dup[0]['tecnico']}")
            if col_ap.button("✅ Aprobar", key=f"ap_{s['id']}"):
                execute_write("UPDATE asignaciones SET estado='pendiente' WHERE id=%s", (s["id"],))
                st.rerun()
            if col_den.button("❌ Borrar", key=f"de_{s['id']}"):
                execute_write("DELETE FROM asignaciones WHERE id=%s", (s["id"],))
                st.rerun()

    # Asignación manual
    st.markdown('<div class="section-title">➕ Asignación Directa</div>', unsafe_allow_html=True)
    u_db = execute_read("SELECT unit_number, id_lote FROM unidades")
    t_db = execute_read("SELECT username FROM users WHERE role='tecnico'")
    with st.form("manual_assign"):
        c1, c2, c3 = st.columns(3)
        u_sel = c1.selectbox("Unidad",    [f"{x['id_lote']} - {x['unit_number']}" for x in u_db])
        t_sel = c2.selectbox("Técnico",   [x["username"] for x in t_db])
        a_sel = c3.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.form_submit_button("📋 Crear Orden", use_container_width=True, type="primary"):
            execute_write(
                "INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) "
                "VALUES (%s,%s,%s,'pendiente')",
                (u_sel.split(" - ")[1], a_sel, t_sel),
            )
            st.success("✅ Orden creada correctamente.")
            st.rerun()


# ==================== MIS TAREAS (Técnico) ====================
elif menu == "🎯 Mis Tareas":
    st.markdown('<div class="main-header">🎯 Mis Actividades</div>', unsafe_allow_html=True)

    tareas = execute_read(
        "SELECT * FROM asignaciones WHERE tecnico=%s AND estado IN ('pendiente','en_proceso')",
        (st.session_state.user,),
    )

    if not tareas:
        st.info("✅ No tienes tareas asignadas en este momento.")

    for t in tareas:
        icono = "⏳" if t["estado"] == "pendiente" else "▶️"
        with st.expander(f"{icono} Unidad **{t['unidad']}** — {t['actividad_id']}"):

            # ── PENDIENTE: iniciar ──
            if t["estado"] == "pendiente":
                st.markdown(
                    "<p style='color:#d97706;font-weight:600;'>Estado: Pendiente de inicio</p>",
                    unsafe_allow_html=True,
                )
                if st.button("▶️ Iniciar Actividad", key=f"ini_{t['id']}",
                             use_container_width=True, type="primary"):
                    execute_write(
                        "UPDATE asignaciones SET estado='en_proceso', fecha_inicio=%s WHERE id=%s",
                        (datetime.now(tijuana_tz), t["id"]),
                    )
                    st.rerun()

            # ── EN PROCESO ──
            else:
                st.markdown(
                    "<p style='color:#16a34a;font-weight:600;'>▶️ Actividad en proceso</p>",
                    unsafe_allow_html=True,
                )

                # ── EVIDENCIA: cámara + archivos ──
                if t["actividad_id"].lower() == "evidencia":
                    st.markdown(
                        f"<p style='font-size:.9rem;color:#374151;'>"
                        f"Toma fotos con la cámara o sube archivos desde tu dispositivo. "
                        f"Límite: <b>{MAX_FOTOS} fotos</b> en total.</p>",
                        unsafe_allow_html=True,
                    )

                    tab_cam, tab_arch = st.tabs(["📷 Cámara", "📁 Subir Archivos"])

                    with tab_cam:
                        foto_cam = st.camera_input(
                            "Captura una foto de evidencia",
                            key=f"cam_{t['id']}",
                        )
                        if foto_cam:
                            ts = datetime.now(tijuana_tz).strftime("%Y%m%d_%H%M%S")
                            nombre_cam = f"cam_{t['unidad']}_{ts}.jpg"
                            ok = execute_write(
                                "INSERT INTO evidencias "
                                "(unit_number, nombre_archivo, contenido, tecnico) "
                                "VALUES (%s,%s,%s,%s)",
                                (t["unidad"], nombre_cam, foto_cam.getvalue(), st.session_state.user),
                            )
                            if ok:
                                st.success(f"✅ Foto guardada: {nombre_cam}")
                                st.rerun()

                    with tab_arch:
                        archivos = st.file_uploader(
                            f"Selecciona fotos (máx. {MAX_FOTOS})",
                            accept_multiple_files=True,
                            type=["jpg", "jpeg", "png"],
                            key=f"fup_{t['id']}",
                        )
                        if archivos:
                            if len(archivos) > MAX_FOTOS:
                                st.warning(
                                    f"⚠️ Seleccionaste {len(archivos)} fotos. "
                                    f"Solo se guardarán las primeras {MAX_FOTOS}."
                                )
                                archivos = archivos[:MAX_FOTOS]
                            else:
                                st.info(f"📸 {len(archivos)} foto(s) lista(s) para guardar.")

                            if st.button("💾 Guardar Fotos", key=f"savef_{t['id']}",
                                         use_container_width=True, type="primary"):
                                barra = st.progress(0, text="Guardando fotos...")
                                for i, arc in enumerate(archivos):
                                    execute_write(
                                        "INSERT INTO evidencias "
                                        "(unit_number, nombre_archivo, contenido, tecnico) "
                                        "VALUES (%s,%s,%s,%s)",
                                        (t["unidad"], arc.name, arc.read(), st.session_state.user),
                                    )
                                    barra.progress((i + 1) / len(archivos),
                                                   text=f"Guardando {i+1}/{len(archivos)}...")
                                st.success(f"✅ {len(archivos)} foto(s) guardada(s).")
                                st.rerun()

                    # Contador de fotos ya subidas
                    fotos_prev = execute_read(
                        "SELECT COUNT(*) AS total FROM evidencias "
                        "WHERE unit_number=%s AND tecnico=%s",
                        (t["unidad"], st.session_state.user),
                    )
                    total_prev = fotos_prev[0]["total"] if fotos_prev else 0
                    if total_prev:
                        st.markdown(
                            f"<p style='font-size:.85rem;color:#374151;margin-top:10px;'>"
                            f"📂 <b>{total_prev} foto(s)</b> ya guardadas para esta unidad.</p>",
                            unsafe_allow_html=True,
                        )

                    st.markdown("---")
                    if st.button("✅ Finalizar Evidencia", key=f"finev_{t['id']}",
                                 use_container_width=True):
                        execute_write(
                            "UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s",
                            (datetime.now(tijuana_tz), t["id"]),
                        )
                        st.success("✅ Actividad completada.")
                        st.rerun()

                # ── TOMA DE SERIES ──
                elif t["actividad_id"].lower() == "toma de series":
                    with st.form(f"ser_{t['id']}"):
                        st.markdown(
                            "<p style='font-size:.9rem;color:#374151;margin-bottom:10px;'>"
                            "Ingresa los seriales de cada componente:</p>",
                            unsafe_allow_html=True,
                        )
                        items = list(CAMPOS_SERIES.items())
                        mid   = (len(items) + 1) // 2
                        col_a, col_b = st.columns(2)
                        res = {}
                        for i, (k, v) in enumerate(items):
                            target = col_a if i < mid else col_b
                            res[k] = target.text_input(v, key=f"s_{t['id']}_{k}")
                        if st.form_submit_button("💾 Guardar Series",
                                                  use_container_width=True, type="primary"):
                            set_q = ", ".join([f"{k}=%s" for k in res])
                            execute_write(
                                f"UPDATE unidades SET {set_q} WHERE unit_number=%s",
                                list(res.values()) + [t["unidad"]],
                            )
                            execute_write(
                                "UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s",
                                (datetime.now(tijuana_tz), t["id"]),
                            )
                            st.rerun()

                # ── ACTIVIDAD GENÉRICA ──
                else:
                    if st.button("✅ Terminar Actividad", key=f"fin_{t['id']}",
                                 use_container_width=True, type="primary"):
                        execute_write(
                            "UPDATE asignaciones SET estado='completada', fecha_fin=%s WHERE id=%s",
                            (datetime.now(tijuana_tz), t["id"]),
                        )
                        st.rerun()


# ==================== NUEVA SOLICITUD (Técnico) ====================
elif menu == "🔔 Nueva Solicitud":
    st.markdown('<div class="main-header">🔔 Solicitar Actividad</div>', unsafe_allow_html=True)
    u_db = execute_read("SELECT unit_number, id_lote FROM unidades")
    with st.form("sol_f"):
        u_sel = st.selectbox("Unidad",    [f"{x['id_lote']} - {x['unit_number']}" for x in u_db])
        a_sel = st.selectbox("Actividad", ACTIVIDADES_CARRIER)
        if st.form_submit_button("📤 Enviar Solicitud", use_container_width=True, type="primary"):
            execute_write(
                "INSERT INTO asignaciones (unidad, actividad_id, tecnico, estado) "
                "VALUES (%s,%s,%s,'solicitado')",
                (u_sel.split(" - ")[1], a_sel, st.session_state.user),
            )
            st.toast("✅ Solicitud enviada correctamente")
            st.rerun()


# ==================== REGISTRO DE UNIDADES (Admin) ====================
elif menu == "📸 Registro de Unidades":
    st.markdown('<div class="main-header">📸 Registro Maestro de Unidades</div>', unsafe_allow_html=True)
    with st.form("reg_u"):
        col1, col2 = st.columns(2)
        u_num  = col1.text_input("Número Económico")
        l_num  = col1.text_input("Número de Lote")
        campo  = col2.selectbox("Campo a Registrar", ["Ninguno"] + list(CAMPOS_SERIES.keys()))
        valor  = col2.text_input("Valor del Serial")
        if st.form_submit_button("💾 Guardar Registro", use_container_width=True, type="primary"):
            if campo != "Ninguno":
                execute_write(
                    f"INSERT INTO unidades (unit_number, id_lote, {campo}) VALUES (%s,%s,%s) "
                    f"ON DUPLICATE KEY UPDATE id_lote=%s, {campo}=%s",
                    (u_num, l_num, valor, l_num, valor),
                )
            else:
                execute_write(
                    "INSERT INTO unidades (unit_number, id_lote) VALUES (%s,%s) "
                    "ON DUPLICATE KEY UPDATE id_lote=%s",
                    (u_num, l_num, l_num),
                )
            st.success("✅ Registro guardado correctamente")
            st.rerun()


# ==================== GESTIÓN DE USUARIOS (Admin) ====================
elif menu == "👥 Gestión de Usuarios":
    st.markdown('<div class="main-header">👥 Usuarios del Sistema</div>', unsafe_allow_html=True)

    # Lista de usuarios existentes
    usuarios = execute_read("SELECT username, role FROM users ORDER BY role, username")
    if usuarios:
        st.markdown('<div class="section-title">👥 Usuarios Registrados</div>', unsafe_allow_html=True)
        df_users = pd.DataFrame(usuarios)
        df_users.columns = ["Usuario", "Rol"]
        st.dataframe(df_users, use_container_width=True, hide_index=True)

    # Formulario nuevo usuario
    st.markdown('<div class="section-title">➕ Crear Nuevo Usuario</div>', unsafe_allow_html=True)
    with st.form("u_f"):
        c1, c2, c3 = st.columns(3)
        n_u = c1.text_input("Nombre de Usuario")
        n_p = c2.text_input("Contraseña", type="password")
        n_r = c3.selectbox("Rol", ["tecnico", "admin"])
        if st.form_submit_button("👤 Crear Usuario", use_container_width=True, type="primary"):
            if n_u and n_p:
                execute_write(
                    "INSERT INTO users (username, password, role) VALUES (%s,%s,%s)",
                    (n_u, n_p, n_r),
                )
                st.success(f"✅ Usuario **{n_u}** creado correctamente.")
                st.rerun()
            else:
                st.warning("⚠️ Completa todos los campos antes de guardar.")
