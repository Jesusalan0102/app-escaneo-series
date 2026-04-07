import streamlit as st
import pandas as pd
import mysql.connector
from PIL import Image
import easyocr
import io
from datetime import datetime

# ==================== CONFIGURACIÓN CORPORATIVA ====================
st.set_page_config(page_title="Carrier Transicold - Escaneo de Series", page_icon="📷", layout="wide")

# Colores Corporativos Carrier
CARRIER_BLUE = "#002B5B"      # Azul oscuro principal
CARRIER_LIGHT_BLUE = "#00A9E0" # Azul claro
CARRIER_GRAY = "#F4F4F4"

# Logo
LOGO_URL = LOGO_URL = "https://raw.githubusercontent.com/Jesusalan0102/app-escaneo-series/main/carrierlogo.jpeg"  
# ← Cambia TU-USUARIO por tu usuario real de GitHub

# CSS Profesional Carrier
st.markdown(f"""
    <style>
        .main-header {{ 
            font-size: 2.4rem; 
            font-weight: bold; 
            color: {CARRIER_BLUE}; 
            text-align: center;
            margin-bottom: 10px;
        }}
        .subheader {{
            color: {CARRIER_BLUE};
            font-weight: 600;
        }}
        .stButton>button {{
            background-color: {CARRIER_BLUE};
            color: white;
            border-radius: 8px;
            height: 3em;
            font-weight: bold;
        }}
        .stButton>button:hover {{
            background-color: #003D80;
        }}
        .success-msg {{
            background-color: #D4EDDA;
            color: #155724;
            padding: 12px;
            border-radius: 8px;
            border-left: 5px solid #28A745;
        }}
        [data-testid="stAppViewContainer"] {{
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        }}
        .sidebar .css-1d391kg {{ background-color: {CARRIER_BLUE}; color: white; }}
    </style>
""", unsafe_allow_html=True)

# ==================== HEADER CON LOGO ====================
col_logo, col_title = st.columns([1, 4])
with col_logo:
    st.image(LOGO_URL, width=220)
with col_title:
    st.markdown('<h1 class="main-header">ESCANEO DE SERIES</h1>', unsafe_allow_html=True)
    st.markdown("**Carrier Transicold** - Sistema de Registro de Componentes")

st.markdown(f"**Técnico:** {st.session_state.get('username', 'Usuario')} | {datetime.now().strftime('%d/%m/%Y %H:%M')}")

# ==================== CONEXIÓN ====================
def get_db_connection():
    return mysql.connector.connect(
        host=st.secrets["db"]["host"], port=st.secrets["db"]["port"],
        user=st.secrets["db"]["user"], password=st.secrets["db"]["password"],
        database=st.secrets["db"]["database"]
    )

# ==================== LOGIN ====================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Iniciar Sesión")
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        if st.button("Ingresar", type="primary", use_container_width=True):
            try:
                conn = get_db_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
                user = cursor.fetchone()
                conn.close()
                if user:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.success("✅ Bienvenido al sistema")
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos")
            except Exception as e:
                st.error("Error de conexión a la base de datos")
    st.stop()

# ==================== CARGAR DATOS ====================
try:
    conn = get_db_connection()
    df = pd.read_sql("SELECT * FROM `unidades` ORDER BY `N`", conn)
except:
    df = pd.DataFrame(columns=['N', 'UNIT #', 'VIN NUMBER', 'REEFER SERIAL NDUG7CN0-AH-A',
                               'REEFER MODEL ST', 'ENGINE SERIAL', 'COMPRESSOR SERIAL', 'CARB'])

# ==================== SIDEBAR ====================
with st.sidebar:
    st.image(LOGO_URL, width=180)
    st.markdown("### Herramientas")
    st.markdown("---")
    if st.button("⬇️ Descargar Excel Completo", use_container_width=True):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name="Unidades")
        output.seek(0)
        st.download_button("📥 Descargar Archivo", data=output, 
                           file_name=f"unidades_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ==================== SELECCIÓN DE UNIDAD ====================
st.subheader("Selecciona o crea unidad")
col1, col2 = st.columns([3,1])

with col1:
    if not df.empty:
        opciones = df["UNIT #"].astype(str).tolist()
        opciones.append("+ Nueva Unidad")
        selected_unit = st.selectbox("Unidad", opciones, label_visibility="collapsed")
    else:
        selected_unit = st.text_input("UNIT #", value="563580", label_visibility="collapsed")

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

# ==================== CAPTURA DE IMAGEN ====================
st.subheader("📸 Captura del número de serie")

imagen = st.camera_input("📷 Toma la foto directamente con la cámara", key="camara")

if imagen is None:
    uploaded = st.file_uploader("📤 O sube una foto desde la galería", type=["jpg", "jpeg", "png"])
    if uploaded:
        imagen = uploaded

if imagen is not None:
    st.image(imagen, caption="Imagen capturada", use_column_width=True)
    
    with st.spinner("🔍 Procesando con Inteligencia Artificial..."):
        img_bytes = imagen.getvalue()
        pil_image = Image.open(io.BytesIO(img_bytes))
        if "reader" not in st.session_state:
            st.session_state.reader = easyocr.Reader(['en', 'es'], gpu=False)
        resultados = st.session_state.reader.readtext(pil_image, detail=0)
        texto_extraido = " ".join(resultados).strip().upper()
    
    st.success(f"**Serie detectada:** {texto_extraido}")
    valor_final = st.text_input("Confirma o corrige el número de serie", value=texto_extraido)

    if st.button("💾 GUARDAR EN BASE DE DATOS", type="primary", use_container_width=True):
        try:
            cursor = conn.cursor()
            columna = campos[campo_seleccionado]

            if is_new:
                nuevo_n = len(df) + 100
                cursor.execute(f"INSERT INTO `unidades` (`N`, `UNIT #`, {columna.replace('`','')}) VALUES (%s, %s, %s)",
                             (nuevo_n, selected_unit, valor_final))
                st.success(f"✅ Nueva unidad {selected_unit} creada correctamente")
            else:
                query = f"UPDATE `unidades` SET {columna} = %s WHERE `UNIT #` = %s"
                cursor.execute(query, (valor_final, selected_unit))
                st.success(f"✅ Guardado correctamente en {campo_seleccionado}")

            conn.commit()
            st.rerun()
        except Exception as e:
            st.error(f"Error al guardar: {e}")
        finally:
            cursor.close()

# ==================== TABLA ====================
st.divider()
st.subheader("📊 Tabla actual de unidades")
if df.empty:
    st.info("No hay unidades registradas todavía. La primera se creará al guardar.")
else:
    st.dataframe(df, use_container_width=True, height=500)

conn.close()
st.caption("Carrier Transicold • Sistema de Escaneo de Series • México")