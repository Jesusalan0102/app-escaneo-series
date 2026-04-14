import streamlit as st
import pandas as pd
import mysql.connector
import cv2
import numpy as np
import easyocr
import re

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

# ==================== DATABASE ====================
@st.cache_resource(show_spinner="Conectando a BD...")
def get_db():
    try:
        conn = mysql.connector.connect(
            host=st.secrets["db"]["host"],
            port=int(st.secrets["db"]["port"]),
            user=st.secrets["db"]["user"],
            password=st.secrets["db"]["password"],
            database=st.secrets["db"]["database"],
            autocommit=True,
            connection_timeout=120
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

@st.cache_data(ttl=30)
def get_unidades():
    try:
        cur = get_cursor(dictionary=True)
        # Ajustado al nombre real: unit_number
        cur.execute("SELECT * FROM unidades ORDER BY unit_number DESC")
        res = cur.fetchall()
        cur.close()
        return pd.DataFrame(res)
    except:
        return pd.DataFrame()

# ==================== OCR ====================
@st.cache_resource
def get_ocr():
    return easyocr.Reader(['en'], gpu=False)

def detectar_serie(image):
    if image.shape[0] > 1200:
        scale = 1200 / image.shape[0]
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    reader = get_ocr()
    recorte = image[int(image.shape[0]*0.60):, :]
    gray = cv2.cvtColor(recorte, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    proc = cv2.threshold(blur, 150, 255, cv2.THRESH_BINARY)[1]
    resultados = reader.readtext(proc)
    
    mejor = None
    mejor_score = 0
    for (_, texto, prob) in resultados:
        texto = texto.upper().replace("O","0").replace("S","5").replace("I","1").replace("B","8").strip()
        for p in [r'^[A-Z]{2}\d{6}$', r'^[A-Z]{3}\d{6}$', r'^[A-Z]{3}\d{4}$']:
            if re.match(p, texto) and prob > mejor_score:
                mejor = texto
                mejor_score = prob
    return mejor, recorte

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
            cur.close()
            if user:
                st.session_state.login = True
                st.session_state.user = u
                st.session_state.role = user.get("role", "tecnico")
                st.success(f"✅ Bienvenido, {u}")
                st.rerun()
            else:
                st.error("❌ Credenciales incorrectas")
        except Exception as e:
            st.error("Error en login")
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
    valor_ocr = ""

    if uploaded:
        with st.spinner("Analizando imagen..."):
            img_bytes = np.asarray(bytearray(uploaded.read()), dtype=np.uint8)
            img = cv2.imdecode(img_bytes, 1)
            serie, recorte = detectar_serie(img)
            st.image(recorte, caption="Zona analizada", use_container_width=True)
            if serie:
                st.success(f"✅ Serie detectada: **{serie}**")
                valor_ocr = serie
            else:
                st.warning("⚠️ No se detectó la serie")

    df = get_unidades()
    # Ajustado al nombre real: unit_number
    opciones = df["unit_number"].astype(str).tolist() if not df.empty else []
    opciones.insert(0, "+ Nueva")
    unidad_sel = st.selectbox("Seleccionar Unidad", opciones)

    nuevo = (unidad_sel == "+ Nueva")
    
    # Mapeo de campos amigables a nombres reales de la DB
    mapa_campos = {
        "VIN": "vin_number",
        "REEFER": "reefer",
        "ENGINE": "engine_serial",
        "COMPRESSOR": "compressor_serial"
    }
    
    campo_label = st.selectbox("Campo a registrar", list(mapa_campos.keys()))
    campo_db = mapa_campos[campo_label]
    
    if nuevo:
        id_final = st.text_input("Escribe el nuevo número de unidad")
    else:
        id_final = unidad_sel

    valor_final = st.text_input("Serie / Número", value=valor_ocr)

    if st.button("💾 Guardar", type="primary"):
        if not valor_final or not id_final:
            st.error("Faltan datos por completar")
        else:
            try:
                cur = get_cursor()
                if nuevo:
                    cur.execute(f"INSERT INTO unidades (unit_number, {campo_db}) VALUES (%s, %s)", (id_final, valor_final))
                else:
                    cur.execute(f"UPDATE unidades SET {campo_db} = %s WHERE unit_number = %s", (valor_final, id_final))
                cur.close()
                st.success("✅ Guardado correctamente")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")

# ==================== ADMIN ====================
elif menu == "Admin" and st.session_state.role == "admin":
    st.subheader("🔧 Asignar Tareas")

    ACTIVIDADES = ["Cableado", "Cerrado", "Corriendo", "Inspeccion", "Pretrip", 
                   "Programación", "Soldadura en sitio", "Vacíos", "Accesorios", 
                   "Alarma", "toma de valores", "Evidencia", "lista para irse", "standby"]

    try:
        cur = get_cursor(dictionary=True)
        cur.execute("SELECT * FROM lotes")
        lotes = pd.DataFrame(cur.fetchall())
        cur.execute("SELECT username FROM users WHERE role='tecnico'")
        tecnicos = pd.DataFrame(cur.fetchall())
        df_unidades = get_unidades()
        cur.close()

        lote_sel = st.selectbox("Lote", lotes["nombre_lote"] if not lotes.empty else ["Sin lotes"])
        unidad_sel = st.selectbox("Unidad / VIN", df_unidades["unit_number"].astype(str).tolist() if not df_unidades.empty else ["Sin unidades"])
        actividad_sel = st.selectbox("Actividad", ACTIVIDADES)
        tecnico_sel = st.selectbox("Técnico", tecnicos["username"] if not tecnicos.empty else ["Sin técnicos"])

        if st.button("📌 Asignar Tarea", type="primary"):
            if lote_sel and unidad_sel and tecnico_sel:
                lid = lotes[lotes["nombre_lote"] == lote_sel]["id"].iloc[0]
                cur = get_cursor()
                cur.execute("""
                    INSERT INTO asignaciones (lote_id, unidad, actividad_id, tecnico, estado)
                    VALUES (%s, %s, %s, %s, 'pendiente')
                """, (lid, unidad_sel, actividad_sel, tecnico_sel))
                cur.close()
                st.success(f"Tarea asignada a {tecnico_sel}")
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
                   duracion_minutos, fecha_asignacion
            FROM asignaciones 
            WHERE tecnico = %s 
            ORDER BY fecha_asignacion DESC
        """, (st.session_state.user,))
        df_tareas = pd.DataFrame(cur.fetchall())
        cur.close()

        if df_tareas.empty:
            st.info("No tienes tareas asignadas aún.")
        else:
            for _, tarea in df_tareas.iterrows():
                with st.expander(f"🔧 {tarea['unidad']} - {tarea['actividad']} ({tarea['estado']})"):
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("▶️ Iniciar", key=f"i{tarea['id']}"):
                            cur = get_cursor()
                            cur.execute("UPDATE asignaciones SET start_time=NOW(), estado='en_progreso' WHERE id=%s", (tarea['id'],))
                            cur.close()
                            st.success("⏱️ Iniciado")
                            st.rerun()
                    with c2:
                        if st.button("⏹️ Completar", key=f"c{tarea['id']}"):
                            cur = get_cursor()
                            cur.execute("""
                                UPDATE asignaciones 
                                SET end_time=NOW(), 
                                    duracion_minutos = TIMESTAMPDIFF(MINUTE, start_time, NOW()),
                                    estado='completada'
                                WHERE id=%s
                            """, (tarea['id'],))
                            cur.close()
                            st.success("✅ Tarea completada")
                            st.rerun()
                    st.caption(f"Tiempo: **{tarea['duracion_minutos']}** minutos")
    except Exception as e:
        st.error(f"Error cargando tareas: {e}")

# ==================== DASHBOARD ====================
elif menu == "Dashboard":
    st.subheader("📊 Dashboard")
    try:
        cur = get_cursor(dictionary=True)
        cur.execute("SELECT tecnico, unidad, actividad_id as actividad, duracion_minutos FROM asignaciones WHERE estado='completada'")
        df = pd.DataFrame(cur.fetchall())
        cur.close()

        if df.empty:
            st.info("Aún no hay tareas completadas")
        else:
            st.dataframe(df, use_container_width=True)
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Tiempo Total", f"{df['duracion_minutos'].sum()} min")
            with col2:
                st.metric("Tareas Completadas", len(df))

            st.subheader("Tiempo por Técnico")
            st.bar_chart(df.groupby("tecnico")["duracion_minutos"].sum())
    except Exception as e:
        st.error(f"Error en Dashboard: {e}")