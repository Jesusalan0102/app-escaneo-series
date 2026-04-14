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

# ==================== OCR ====================

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

PATRONES = [
    r'^[A-Z]{2}\d{6}$',
    r'^[A-Z]{3}\d{6}$',
    r'^[A-Z]{3}\d{4}$'
]

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
    reader = get_ocr()
    recorte = recortar_zona_serial(image)
    proc = preprocesar(recorte)
    resultados = reader.readtext(proc)
    serie = extraer_serie(resultados)
    return serie, recorte

# ==================== DATABASE ====================

@st.cache_resource(show_spinner="Conectando a la base de datos...")
def get_db():
    try:
        conn = mysql.connector.connect(
            host=st.secrets["db"]["host"],
            port=int(st.secrets["db"]["port"]),
            user=st.secrets["db"]["user"],
            password=st.secrets["db"]["password"],
            database=st.secrets["db"]["database"],
            autocommit=True,
            connection_timeout=300,
            ssl_disabled=True
        )
        return conn
    except Exception as e:
        st.error(f"❌ Error al conectar con la base de datos: {str(e)}")
        st.stop()


def get_cursor(dictionary=False):
    """Obtiene cursor seguro con reconexión automática"""
    conn = get_db()
    try:
        conn.ping(reconnect=True, attempts=3, delay=5)
    except Exception as e:
        st.error(f"❌ Error de reconexión a la base de datos: {e}")
        st.stop()
    return conn.cursor(dictionary=dictionary)

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

# ==================== MENU ====================

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
        img_bytes = np.asarray(bytearray(uploaded.read()), dtype=np.uint8)
        img = cv2.imdecode(img_bytes, 1)

        serie, recorte = detectar_serie(img)
        st.image(recorte, caption="Zona analizada por OCR", use_column_width=True)

        if serie:
            st.success(f"✅ Serie detectada: **{serie}**")
            valor = serie
        else:
            st.warning("⚠️ No se detectó la serie automáticamente")

    # Cargar unidades
    try:
        cur = get_cursor(dictionary=True)
        cur.execute("SELECT * FROM unidades ORDER BY `UNIT #` DESC")
        df = pd.DataFrame(cur.fetchall())
    except:
        df = pd.DataFrame()

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
            st.error("❌ La serie debe tener al menos 5 caracteres")
        else:
            try:
                cur = get_cursor()
                col = campos[campo]

                if nuevo:
                    cur.execute(f"INSERT INTO unidades (`UNIT #`, {col}) VALUES (%s, %s)", 
                               (unidad, valor))
                else:
                    cur.execute(f"UPDATE unidades SET {col}=%s WHERE `UNIT #`=%s", 
                               (valor, unidad))
                
                st.success("✅ Guardado correctamente")
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")

# ==================== MIS TAREAS ====================

elif menu == "Mis Tareas":
    st.subheader("📋 Mis Tareas Asignadas")
    try:
        cur = get_cursor(dictionary=True)
        cur.execute("SELECT * FROM asignaciones WHERE tecnico = %s", (st.session_state.user,))
        df_tareas = pd.DataFrame(cur.fetchall())
        
        if not df_tareas.empty:
            st.dataframe(df_tareas, use_container_width=True)
        else:
            st.info("No tienes tareas asignadas por el momento.")
    except Exception as e:
        st.error(f"Error al cargar tareas: {e}")

# ==================== ADMIN ====================

elif menu == "Admin" and st.session_state.role == "admin":
    st.subheader("🔧 Asignar Tareas")
    try:
        cur = get_cursor(dictionary=True)
        
        cur.execute("SELECT * FROM lotes")
        lotes = pd.DataFrame(cur.fetchall())
        
        cur.execute("SELECT * FROM actividades")
        acts = pd.DataFrame(cur.fetchall())
        
        cur.execute("SELECT username FROM users WHERE role='tecnico'")
        tec = pd.DataFrame(cur.fetchall())

        if lotes.empty or acts.empty or tec.empty:
            st.warning("Faltan datos en las tablas de lotes, actividades o técnicos.")
        else:
            l = st.selectbox("Lote", lotes["nombre_lote"])
            a = st.selectbox("Actividad", acts["nombre"])
            t = st.selectbox("Técnico", tec["username"])

            if st.button("Asignar Tarea", type="primary"):
                lid = lotes[lotes["nombre_lote"] == l]["id"].iloc[0]
                aid = acts[acts["nombre"] == a]["id"].iloc[0]

                cur = get_cursor()
                cur.execute(
                    "INSERT INTO asignaciones (lote_id, actividad_id, tecnico, estado) "
                    "VALUES (%s, %s, %s, 'pendiente')",
                    (lid, aid, t)
                )
                st.success("✅ Tarea asignada correctamente")
    except Exception as e:
        st.error(f"Error en Admin: {e}")

# ==================== DASHBOARD ====================

elif menu == "Dashboard":
    st.subheader("📊 Dashboard")
    try:
        cur = get_cursor(dictionary=True)
        cur.execute("SELECT * FROM asignaciones WHERE estado='completada'")
        df = pd.DataFrame(cur.fetchall())

        if not df.empty:
            st.dataframe(df, use_container_width=True)
            if "duracion_minutos" in df.columns:
                st.bar_chart(df["duracion_minutos"])
        else:
            st.info("Aún no hay tareas completadas.")
    except Exception as e:
        st.error(f"Error al cargar dashboard: {e}")