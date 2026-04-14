import streamlit as st
import pandas as pd
import mysql.connector
from datetime import datetime
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

col_logo, col_title = st.columns([1,4])
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
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    thresh = cv2.threshold(blur, 150, 255, cv2.THRESH_BINARY)[1]
    return thresh

def recortar_zona_serial(image):
    h, w, _ = image.shape
    return image[int(h*0.60):h, 0:w]

def normalizar_texto(texto):
    texto = texto.upper()
    reemplazos = {"O": "0", "S": "5"}
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

# ==================== DB ====================

@st.cache_resource
def get_db():
    return mysql.connector.connect(
        host=st.secrets["db"]["host"],
        port=st.secrets["db"]["port"],
        user=st.secrets["db"]["user"],
        password=st.secrets["db"]["password"],
        database=st.secrets["db"]["database"],
        autocommit=True
    )

# ==================== LOGIN ====================

if "login" not in st.session_state:
    st.session_state.login = False
    st.session_state.user = ""
    st.session_state.role = ""

if not st.session_state.login:
    st.title("🔐 Login")
    u = st.text_input("Usuario")
    p = st.text_input("Password", type="password")

    if st.button("Entrar"):
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE username=%s AND password=%s",(u,p))
        user = cur.fetchone()

        if user:
            st.session_state.login = True
            st.session_state.user = u
            st.session_state.role = user.get("role","tecnico")
            st.rerun()
        else:
            st.error("Credenciales incorrectas")

    st.stop()

# ==================== MENU ====================

menu = st.sidebar.radio("Menu",[
    "Ingreso Series",
    "Mis Tareas",
    "Admin" if st.session_state.role=="admin" else None,
    "Dashboard"
])

conn = get_db()

# ==================== INGRESO ====================

if menu == "Ingreso Series":

    st.subheader("📸 Escaneo / Ingreso")

    uploaded = st.file_uploader("Subir imagen", type=["jpg","png","jpeg"])
    valor = ""

    if uploaded:
        img_bytes = np.asarray(bytearray(uploaded.read()), dtype=np.uint8)
        img = cv2.imdecode(img_bytes,1)

        serie, recorte = detectar_serie(img)

        st.image(recorte, caption="Zona analizada")

        if serie:
            st.success(f"Serie detectada: {serie}")
            valor = serie
        else:
            st.error("No detectada")

    try:
        df = pd.read_sql("SELECT * FROM unidades ORDER BY `UNIT #` DESC", conn)
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

    campo = st.selectbox("Campo", list(campos.keys()))

    valor = st.text_input("Serie", value=valor)

    if st.button("Guardar"):
        if not valor or len(valor) < 5:
            st.error("Serie inválida")
            st.stop()

        cur = conn.cursor()
        col = campos[campo]

        if nuevo:
            cur.execute(f"INSERT INTO unidades (`UNIT #`, {col}) VALUES (%s,%s)",(unidad,valor))
        else:
            cur.execute(f"UPDATE unidades SET {col}=%s WHERE `UNIT #`=%s",(valor,unidad))

        st.success("Guardado")
        st.rerun()

# ==================== TAREAS ====================

elif menu == "Mis Tareas":
    st.subheader("Mis tareas")
    df = pd.read_sql("SELECT * FROM asignaciones WHERE tecnico=%s", conn, params=[st.session_state.user])
    st.dataframe(df)

# ==================== ADMIN ====================

elif menu == "Admin" and st.session_state.role=="admin":

    st.subheader("Asignar tareas")

    lotes = pd.read_sql("SELECT * FROM lotes", conn)
    acts = pd.read_sql("SELECT * FROM actividades", conn)
    tec = pd.read_sql("SELECT username FROM users WHERE role='tecnico'", conn)

    l = st.selectbox("Lote", lotes["nombre_lote"])
    a = st.selectbox("Actividad", acts["nombre"])
    t = st.selectbox("Tecnico", tec["username"])

    if st.button("Asignar"):
        lid = lotes[lotes["nombre_lote"]==l]["id"].iloc[0]
        aid = acts[acts["nombre"]==a]["id"].iloc[0]

        cur = conn.cursor()
        cur.execute("INSERT INTO asignaciones (lote_id,actividad_id,tecnico) VALUES (%s,%s,%s)",(lid,aid,t))

        st.success("Asignado")

# ==================== DASHBOARD ====================

elif menu == "Dashboard":
    st.subheader("Dashboard")

    df = pd.read_sql("SELECT * FROM asignaciones WHERE estado='completada'", conn)

    if not df.empty:
        st.bar_chart(df["duracion_minutos"])
    else:
        st.info("Sin datos")