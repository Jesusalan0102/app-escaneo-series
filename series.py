import streamlit as st
import pandas as pd
import mysql.connector
from PIL import Image, ImageEnhance, ImageFilter
import easyocr
import io
import re
from datetime import datetime

# ==================== CONFIGURACIÓN ====================
st.set_page_config(page_title="Carrier Transicold - Escaneo de Series", 
                   page_icon="📷", layout="wide")

CARRIER_BLUE = "#002B5B"
LOGO_URL = "https://raw.githubusercontent.com/Jesusalan0102/app-escaneo-series/main/carrierlogo2.jpeg.jpg"

st.markdown(f"""
    <style>
        .main-header {{ font-size: 2.4rem; font-weight: bold; color: {CARRIER_BLUE}; text-align: center; }}
        .stButton>button {{ background-color: {CARRIER_BLUE}; color: white; border-radius: 8px; font-weight: bold; height: 3.2em; }}
    </style>
""", unsafe_allow_html=True)

col_logo, col_title = st.columns([1, 4])
with col_logo:
    st.image(LOGO_URL, width=260)
with col_title:
    st.markdown('<h1 class="main-header">ESCANEO DE SERIES</h1>', unsafe_allow_html=True)

# ==================== CONEXIÓN A BD ====================
@st.cache_resource
def get_db_connection():
    return mysql.connector.connect(
        host=st.secrets["db"]["host"],
        port=st.secrets["db"]["port"],
        user=st.secrets["db"]["user"],
        password=st.secrets["db"]["password"],
        database=st.secrets["db"]["database"],
        autocommit=True
    )

# ==================== LOGIN ====================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.title("🔐 Iniciar Sesión")
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    
    if st.button("Ingresar", type="primary", use_container_width=True):
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", 
                         (username, password))
            if cursor.fetchone():
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("✅ Bienvenido")
                st.rerun()
            else:
                st.error("❌ Credenciales incorrectas")
        except Exception as e:
            st.error(f"Error de conexión: {e}")
    st.stop()

# ==================== CARGAR DATOS ====================
conn = get_db_connection()
try:
    df = pd.read_sql("SELECT * FROM `unidades` ORDER BY `N` DESC", conn)
except Exception as e:
    st.error(f"Error cargando datos: {e}")
    df = pd.DataFrame()

# ==================== INFORMACIÓN LATERAL ====================
st.sidebar.success(f"**Técnico:** {st.session_state.username}")
st.sidebar.info(f"**Fecha:** {datetime.now().strftime('%d/%m/%Y %H:%M')}")
st.sidebar.info(f"**Unidades registradas:** {len(df)}")

# ==================== SELECCIÓN DE UNIDAD ====================
st.subheader("Selecciona o crea unidad")
col1, col2 = st.columns([3, 1])

with col1:
    if not df.empty:
        opciones = df["UNIT #"].astype(str).tolist()
        opciones.append("+ Nueva Unidad")
        selected_unit = st.selectbox("Unidad", opciones, key="unit_select")
    else:
        selected_unit = st.text_input("UNIT #", value="563580", key="new_unit")

is_new = selected_unit == "+ Nueva Unidad" or df.empty

# Campo a actualizar
campos = {
    "VIN NUMBER": "`VIN NUMBER`",
    "REEFER SERIAL NDUG7CN0-AH-A": "`REEFER SERIAL NDUG7CN0-AH-A`",
    "ENGINE SERIAL": "`ENGINE SERIAL`",
    "COMPRESSOR SERIAL": "`COMPRESSOR SERIAL`",
    "CARB": "`CARB`"
}

campo_seleccionado = st.selectbox("Campo a actualizar", options=list(campos.keys()))

# ==================== CAPTURA + OCR MEJORADO ====================
st.subheader("📸 Captura del número de serie")

imagen = st.camera_input("Toma foto directamente", key="camara")
if imagen is None:
    uploaded = st.file_uploader("O sube foto desde galería", 
                               type=["jpg", "jpeg", "png"])
    if uploaded:
        imagen = uploaded

if imagen is not None:
    st.image(imagen, caption="Imagen capturada", use_column_width=True)
    
    with st.spinner("🔍 Procesando imagen y extrayendo número de serie..."):
        try:
            pil_image = Image.open(io.BytesIO(imagen.getvalue()))
            
            # Procesamiento avanzado para placas metálicas reflectantes
            gray = pil_image.convert('L')
            enhanced = ImageEnhance.Contrast(gray).enhance(4.0)
            sharpened = ImageEnhance.Sharpness(enhanced).enhance(3.0)
            denoised = sharpened.filter(ImageFilter.MedianFilter(size=3))
            
            if "reader" not in st.session_state:
                st.session_state.reader = easyocr.Reader(['en'], gpu=False)
            
            # Lectura detallada
            resultados = st.session_state.reader.readtext(denoised, detail=1, 
                                                        paragraph=False, 
                                                        text_threshold=0.5)
            
            texto_completo = " ".join([res[1] for res in resultados]).upper()
            
            # Patrones optimizados para Hyundai Translead
            patrones = [
                r'VJ\d{6,8}',           # Serial más común (VJ024012)
                r'\b[A-Z]{2}\d{6,8}\b', # Dos letras + números
                r'\b\d{8,12}\b',        # Solo números largos
            ]
            
            serial_encontrado = None
            for patron in patrones:
                matches = re.findall(patron, texto_completo)
                if matches:
                    serial_encontrado = max(matches, key=len)
                    break
            
            texto_extraido = serial_encontrado or texto_completo[:60]
            
        except Exception as e:
            st.error(f"Error en OCR: {e}")
            texto_extraido = ""

    st.success(f"**Serie detectada:** {texto_extraido}")
    
    valor_final = st.text_input("Confirma o corrige el número de serie", 
                               value=texto_extraido, key="valor_serie")

    if st.button("💾 GUARDAR EN BASE DE DATOS", type="primary", use_container_width=True):
        if not valor_final or valor_final.strip() == "":
            st.error("El número de serie no puede estar vacío")
        else:
            try:
                cursor = conn.cursor()
                columna_db = campos[campo_seleccionado]
                
                if is_new:
                    query = f"INSERT INTO `unidades` (`UNIT #`, {columna_db}) VALUES (%s, %s)"
                    cursor.execute(query, (selected_unit, valor_final.strip()))
                    st.success(f"✅ Nueva unidad **{selected_unit}** creada correctamente")
                else:
                    query = f"UPDATE `unidades` SET {columna_db} = %s WHERE `UNIT #` = %s"
                    cursor.execute(query, (valor_final.strip(), selected_unit))
                    st.success(f"✅ {campo_seleccionado} actualizado correctamente")
                
                st.rerun()
                
            except mysql.connector.Error as err:
                st.error(f"❌ Error MySQL ({err.errno}): {err.msg}")
            except Exception as e:
                st.error(f"Error inesperado: {e}")
            finally:
                if 'cursor' in locals():
                    cursor.close()

# ==================== TABLA ====================
st.divider()
st.subheader("📊 Tabla actual")
st.dataframe(df, use_container_width=True, height=500)

st.caption("Carrier Transicold • Sistema de Escaneo de Series v2.1")