import streamlit as st
import pandas as pd
import mysql.connector
from PIL import Image
import easyocr
import io
from datetime import datetime

# ==================== CONEXIÓN A CLEVER CLOUD ====================
def get_db_connection():
    return mysql.connector.connect(
        host=st.secrets["db"]["host"],
        port=st.secrets["db"]["port"],
        user=st.secrets["db"]["user"],
        password=st.secrets["db"]["password"],
        database=st.secrets["db"]["database"]
    )

# ==================== INICIO DE SESIÓN ====================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

st.set_page_config(page_title="Escaneo Series", page_icon="📷", layout="wide")

if not st.session_state.logged_in:
    st.title("🔐 Iniciar Sesión - Clever Cloud")
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    
    if st.button("Ingresar", type="primary"):
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", 
                          (username, password))
            user = cursor.fetchone()
            conn.close()
            if user:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success(f"✅ Bienvenido, {username}!")
                st.rerun()
            else:
                st.error("❌ Usuario o contraseña incorrectos")
        except Exception as e:
            st.error(f"Error: {e}")
    st.stop()

# ==================== APLICACIÓN PRINCIPAL ====================
st.title("📷 Escaneo de Series - Clever Cloud")
st.markdown(f"**Técnico:** {st.session_state.username} | {datetime.now().strftime('%d/%m/%Y %H:%M')}")

conn = get_db_connection()
df = pd.read_sql("SELECT * FROM `unidades` ORDER BY `N`", conn)

st.subheader("📊 Tabla actual")
st.dataframe(df, use_container_width=True)

# Selección de unidad
col1, col2 = st.columns(2)
with col1:
    unidad = st.selectbox(
        "Selecciona la Unidad",
        options=df["UNIT #"].astype(str).tolist(),
        format_func=lambda x: f"Unidad {x} - VIN: {df.loc[df['UNIT #'].astype(str) == x, 'VIN NUMBER'].values[0]}"
    )

with col2:
    campos = {
        "VIN NUMBER": "`VIN NUMBER`",
        "REEFER SERIAL NDUG7CN0-AH-A": "`REEFER SERIAL NDUG7CN0-AH-A`",
        "ENGINE SERIAL": "`ENGINE SERIAL`",
        "COMPRESSOR SERIAL": "`COMPRESSOR SERIAL`",
        "CARB": "`CARB`"
    }
    operacion = st.selectbox("Campo a actualizar con el escaneo", options=list(campos.keys()))

# ==================== ESCANEO CON CÁMARA + IA ====================
st.subheader("📸 Escanea la serie")
st.caption("Abre la cámara del celular y apunta al número de serie")

imagen = st.camera_input("Capturar foto", key="camera")

if imagen is not None:
    st.image(imagen, caption="Foto capturada", use_column_width=True)
    
    with st.spinner("🔍 Leyendo con Inteligencia Artificial (EasyOCR)..."):
        img_bytes = imagen.getvalue()
        pil_image = Image.open(io.BytesIO(img_bytes))
        
        if "reader" not in st.session_state:
            st.session_state.reader = easyocr.Reader(['en'], gpu=False)
        
        resultados = st.session_state.reader.readtext(pil_image, detail=0)
        texto_extraido = " ".join(resultados).strip().upper()
    
    st.success(f"**Serie detectada:** {texto_extraido}")
    serie_confirmada = st.text_input("Confirma o corrige el número", value=texto_extraido)
    
    if st.button("💾 Guardar en Clever Cloud", type="primary"):
        try:
            cursor = conn.cursor()
            columna_db = campos[operacion]
            query = f"UPDATE `unidades` SET {columna_db} = %s WHERE `UNIT #` = %s"
            cursor.execute(query, (serie_confirmada, unidad))
            conn.commit()
            st.success(f"✅ ¡Guardado correctamente en {operacion} de la unidad {unidad}!")
            st.rerun()
        except Exception as e:
            st.error(f"Error al guardar: {e}")
        finally:
            cursor.close()

# ==================== EXPORTAR EXCEL ====================
st.divider()
if st.button("⬇️ Descargar Excel completo", type="secondary"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Unidades")
    output.seek(0)
    st.download_button(
        label="📥 Descargar archivo .xlsx",
        data=output,
        file_name=f"unidades_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

conn.close()
st.caption("App desarrollada con ❤️ • Funciona en cualquier celular")