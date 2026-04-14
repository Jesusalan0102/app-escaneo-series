import streamlit as st
import pandas as pd
import mysql.connector
import cv2
import numpy as np
import easyocr
import re
from datetime import datetime

# ==================== CONFIG ====================
st.set_page_config(page_title="Carrier Transicold - Gestión", page_icon="📋", layout="wide")

CARRIER_BLUE = "#002B5B"
LOGO_URL = "https://raw.githubusercontent.com/Jesusalan0102/app-escaneo-series/main/carrierlogo2.jpeg.jpg"

st.markdown(f"""
<style>
.main-header {{ font-size: 2.4rem; font-weight: bold; color: {CARRIER_BLUE}; text-align: center; }}
.stButton>button {{ background-color: {CARRIER_BLUE}; color: white; border-radius: 8px; font-weight: bold; }}
</style>
""", unsafe_allow_html=True)

col_logo, col_title = st.columns([1, 4])
with col_logo:
    st.image(LOGO_URL, width=260)
with col_title:
    st.markdown('<h1 class="main-header">CARRIER TRANSICOLD</h1>', unsafe_allow_html=True)

# ==================== OCR (OPTIMIZADO) ====================
@st.cache_resource
def get_ocr():
    return easyocr.Reader(['en'], gpu=False)

def preprocesar(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(blur, 150, 255, cv2.THRESH_BINARY)[1]
    return thresh

def recortar_zona_serial(image):
    h, w, _ = image.shape
    return image[int(h * 0.60):h, 0:w]

def normalizar_texto(texto):
    texto = texto.upper()
    reemplazos = {"O": "0", "S": "5", "I": "1", "B": "8"}
    for k, v in reemplazos.items():
        texto = texto.replace(k, v)
    return texto

PATRONES = [r'^[A-Z]{2}\d{6}$', r'^[A-Z]{3}\d{6}$', r'^[A-Z]{3}\d{4}$']

def extraer_serie(resultados):
    mejor = None
    mejor_score = 0
    for (_, texto, prob) in resultados:
        texto = normalizar_texto(texto)
        for p in PATRONES:
            if re.match(p, texto) and prob > mejor_score:
                mejor = texto
                mejor_score = prob
    return mejor

def detectar_serie(image):
    if image.shape[0] > 1200:
        scale = 1200 / image.shape[0]
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    
    reader = get_ocr()
    recorte = recortar_zona_serial(image)
    proc = preprocesar(recorte)
    resultados = reader.readtext(proc)
    serie = extraer_serie(resultados)
    return serie, recorte

# ==================== DATABASE ====================
@st.cache_resource(show_spinner="Conectando a MySQL...")
def get_db():
    try:
        conn = mysql.connector.connect(
            host=st.secrets["db"]["host"],
            port=int(st.secrets["db"]["port"]),
            user=st.secrets["db"]["user"],
            password=st.secrets["db"]["password"],
            database=st.secrets["db"]["database"],
            autocommit=True,
            connection_timeout=180,
            ssl_disabled=True
        )
        return conn
    except Exception as e:
        st.error(f"❌ Error de conexión: {e}")
        st.stop()

def get_cursor(dictionary=False):
    conn = get_db()
    try:
        conn.ping(reconnect=True, attempts=3, delay=5)
    except:
        st.error("❌ Error de reconexión")
        st.stop()
    return conn.cursor(dictionary=dictionary)

# ==================== FUNCIÓN GLOBAL PARA UNIDADES (CORREGIDO) ====================
@st.cache_data(ttl=60)
def get_unidades():
    try:
        cur = get_cursor(dictionary=True)
        cur.execute("SELECT * FROM unidades ORDER BY `UNIT #` DESC")
        return pd.DataFrame(cur.fetchall())
    except:
        return pd.DataFrame()

# ==================== LOGIN ====================
if "login" not in st.session_state:
    st.session_state.login = False
    st.session_state.user = ""
    st.session_state.role = ""

if not st.session_state.login:
    st.title("🔐 Login")
    u = st.text_input("Usuario")
    p = st.text_input("Password", type="password")

    if st.button("Entrar", type="primary"):
        try:
            cur = get_cursor(dictionary=True)
            cur.execute("SELECT * FROM users WHERE username=%s AND password=%s", (u, p))
            user = cur.fetchone()
            if user:
                st.session_state.login = True
                st.session_state.user = u
                st.session_state.role = user.get("role", "tecnico")
                st.success(f"✅ Bienvenido, {u}")
                st.rerun()
            else:
                st.error("❌ Credenciales incorrectas")
        except Exception as e:
            st.error(f"Error en login: {e}")
    st.stop()

# ==================== MENÚ ====================
menu_options = ["Ingreso Series", "Mis Tareas", "Dashboard"]
if st.session_state.role == "admin":
    menu_options.insert(2, "Admin")

menu = st.sidebar.radio("Menú", menu_options)

# ==================== INGRESO SERIES ====================
if menu == "Ingreso Series":
    st.subheader("📸 Escaneo / Ingreso de Series")

    uploaded = st.file_uploader("Subir imagen de la placa", type=["jpg", "png", "jpeg"])
    valor = ""

    if uploaded:
        with st.spinner("Analizando imagen con OCR..."):
            img_bytes = np.asarray(bytearray(uploaded.read()), dtype=np.uint8)
            img = cv2.imdecode(img_bytes, 1)
            serie, recorte = detectar_serie(img)
            st.image(recorte, caption="Zona analizada", use_column_width=True)

            if serie:
                st.success(f"✅ Serie detectada: **{serie}**")
                valor = serie
            else:
                st.warning("⚠️ No se detectó automáticamente")

    df = get_unidades()

    if not df.empty:
        opciones = df["UNIT #"].astype(str).tolist()
        opciones.append("+ Nueva")
        unidad = st.selectbox("Unidad", opciones)
    else:
        unidad = st.text_input("Unidad")

    nuevo = unidad == "+ Nueva" or df.empty

    campos = {
        "VIN": "`VIN NUMBER`",
        "REEFER": "`REEFER SERIAL NDUG7CN0-AH-A`",
        "ENGINE": "`ENGINE SERIAL`",
        "COMPRESSOR": "`COMPRESSOR SERIAL`"
    }

    campo = st.selectbox("Campo a registrar", list(campos.keys()))
    valor = st.text_input("Serie / Número", value=valor)

    if st.button("💾 Guardar", type="primary"):
        if not valor or len(valor) < 5:
            st.error("La serie debe tener al menos 5 caracteres")
        else:
            try:
                cur = get_cursor()
                col = campos[campo]
                if nuevo:
                    cur.execute(f"INSERT INTO unidades (`UNIT #`, {col}) VALUES (%s, %s)", (unidad, valor))
                else:
                    cur.execute(f"UPDATE unidades SET {col}=%s WHERE `UNIT #`=%s", (valor, unidad))
                st.success("✅ Guardado correctamente")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")

# ==================== ADMIN - ASIGNAR TAREAS ====================
elif menu == "Admin" and st.session_state.role == "admin":
    st.subheader("🔧 Asignar Tareas por Lote y VIN")

    ACTIVIDADES = [
        "Cableado", "Cerrado", "Corriendo", "Inspeccion", "Pretrip",
        "Programación", "Soldadura en sitio", "Vacíos", "Accesorios",
        "Alarma", "toma de valores", "Evidencia", "lista para irse", "standby"
    ]

    try:
        cur = get_cursor(dictionary=True)
        cur.execute("SELECT * FROM lotes")
        lotes = pd.DataFrame(cur.fetchall())
        cur.execute("SELECT username FROM users WHERE role='tecnico'")
        tecnicos = pd.DataFrame(cur.fetchall())
        df_unidades = get_unidades()

        if lotes.empty or tecnicos.empty or df_unidades.empty:
            st.warning("Faltan datos en lotes, técnicos o unidades.")
        else:
            lote_sel = st.selectbox("Lote", lotes["nombre_lote"])
            unidad_sel = st.selectbox("VIN / Unidad", df_unidades["UNIT #"].astype(str).tolist())
            actividad_sel = st.selectbox("Actividad", ACTIVIDADES)
            tecnico_sel = st.selectbox("Técnico", tecnicos["username"])

            if st.button("📌 Asignar Tarea", type="primary"):
                lid = lotes[lotes["nombre_lote"] == lote_sel]["id"].iloc[0]
                cur = get_cursor()
                cur.execute("""
                    INSERT INTO asignaciones 
                    (lote_id, unidad, actividad_id, tecnico, estado)
                    VALUES (%s, %s, %s, %s, 'pendiente')
                """, (lid, unidad_sel, actividad_sel, tecnico_sel))
                st.success(f"✅ Tarea asignada a {tecnico_sel} → {unidad_sel} ({actividad_sel})")
                st.rerun()
    except Exception as e:
        st.error(f"Error en Admin: {e}")

# ==================== MIS TAREAS ====================
elif menu == "Mis Tareas":
    st.subheader("📋 Mis Tareas")

    try:
        cur = get_cursor(dictionary=True)
        cur.execute("""
            SELECT id, unidad, actividad_id as actividad, estado, 
                   start_time, duracion_minutos, fecha_asignacion
            FROM asignaciones 
            WHERE tecnico = %s
            ORDER BY fecha_asignacion DESC
        """, (st.session_state.user,))
        df_tareas = pd.DataFrame(cur.fetchall())

        if df_tareas.empty:
            st.info("No tienes tareas asignadas.")
        else:
            for idx, tarea in df_tareas.iterrows():
                with st.expander(f"🔧 {tarea['unidad']} - {tarea['actividad']} ({tarea['estado']})", expanded=True):
                    col1, col2, col3 = st.columns([2, 2, 3])
                    with col1:
                        if st.button("▶️ Iniciar", key=f"start_{tarea['id']}"):
                            cur = get_cursor()
                            cur.execute("UPDATE asignaciones SET start_time = NOW(), estado = 'en_progreso' WHERE id = %s", (tarea['id'],))
                            st.success("⏱️ Tiempo iniciado")
                            st.rerun()
                    with col2:
                        if st.button("⏹️ Detener y Completar", key=f"stop_{tarea['id']}"):
                            cur = get_cursor()
                            cur.execute("""
                                UPDATE asignaciones 
                                SET end_time = NOW(),
                                    duracion_minutos = TIMESTAMPDIFF(MINUTE, start_time, NOW()),
                                    estado = 'completada'
                                WHERE id = %s
                            """, (tarea['id'],))
                            st.success("✅ Tarea completada")
                            st.rerun()
                    st.caption(f"Tiempo acumulado: **{tarea.get('duracion_minutos', 0)} minutos**")
    except Exception as e:
        st.error(f"Error cargando tareas: {e}")

# ==================== DASHBOARD ====================
elif menu == "Dashboard":
    st.subheader("📊 Dashboard General")
    try:
        cur = get_cursor(dictionary=True)
        cur.execute("""
            SELECT tecnico, unidad, actividad_id as actividad, 
                   duracion_minutos, fecha_asignacion
            FROM asignaciones 
            WHERE estado = 'completada'
        """)
        df = pd.DataFrame(cur.fetchall())

        if df.empty:
            st.info("Aún no hay tareas completadas.")
        else:
            st.dataframe(df, use_container_width=True)
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Tiempo total", f"{df['duracion_minutos'].sum()} min")
            with col2:
                st.metric("Tareas completadas", len(df))

            st.subheader("Tiempo por Técnico")
            st.bar_chart(df.groupby("tecnico")["duracion_minutos"].sum())
    except Exception as e:
        st.error(f"Error en dashboard: {e}")