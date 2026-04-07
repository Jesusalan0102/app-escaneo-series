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
    st.title("🔐 Iniciar Sesión")
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    
    if st.button("Ingresar", type="primary"):
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
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
            st.error(f"Error de conexión: {str(e)}")
    st.stop()

# ==================== APLICACIÓN PRINCIPAL ====================
st.title("📷 Escaneo de Series - Clever Cloud")
st.markdown(f"**Técnico:** {st.session_state.username} | {datetime.now().strftime('%d/%m/%Y %H:%M')}")

try:
    conn = get_db_connection()
    df = pd.read_sql("SELECT * FROM `unidades` ORDER BY `N`", conn)
except:
    df = pd.DataFrame(columns=['N', 'UNIT #', 'VIN NUMBER', 'REEFER SERIAL NDUG7CN0-AH-A', 
                               'REEFER MODEL ST', 'ENGINE SERIAL', 'COMPRESSOR SERIAL', 'CARB'])

# ==================== AGREGAR NUEVA UNIDAD ====================
with st.expander("➕ Agregar Nueva Unidad Manualmente", expanded=False):
    st.subheader("Nueva Unidad")
    col_a, col_b = st.columns(2)
    with col_a:
        new_unit = st.text_input("UNIT #", value="563580")
        new_vin = st.text_input("VIN NUMBER", value="3H3V532KXXJ0420XX")
    with col_b:
        new_reefer = st.text_input("REEFER SERIAL NDUG7CN0-AH-A", value="")
        new_model = st.text_input("REEFER MODEL ST", value="X4 7700")
    
    if st.button("💾 Guardar Nueva Unidad"):
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO `unidades` 
                (`N`, `UNIT #`, `VIN NUMBER`, `REEFER SERIAL NDUG7CN0-AH-A`, `REEFER MODEL ST`)
                VALUES (%s, %s, %s, %s, %s)
            """, (int(new_unit)+100, new_unit, new_vin, new_reefer, new_model))
            conn.commit()
            st.success(f"✅ Nueva unidad {new_unit} agregada correctamente!")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

# ==================== TABLA ACTUAL ====================
st.subheader("📊 Tabla actual")
if df.empty:
    st.warning("⚠️ Aún no hay unidades registradas. Agrega una arriba o empieza a escanear.")
else:
    st.dataframe(df, use_container_width=True)

# ==================== SELECCIÓN DE UNIDAD Y CAMPO ====================
col1, col2 = st.columns(2)

with col1:
    if not df.empty:
        unidad = st.selectbox(
            "Selecciona la Unidad",
            options=df["UNIT #"].astype(str).tolist(),
            format_func=lambda x: f"Unidad {x}"
        )
    else:
        unidad = st.text_input("Ingresa UNIT # para escanear", value="563580")

with col2:
    campos = {
        "VIN NUMBER": "`VIN NUMBER`",
        "REEFER SERIAL NDUG7CN0-AH-A": "`REEFER SERIAL NDUG7CN0-AH-A`",
        "ENGINE SERIAL": "`ENGINE SERIAL`",
        "COMPRESSOR SERIAL": "`COMPRESSOR SERIAL`",
        "CARB": "`CARB`"
    }
    operacion = st.selectbox("Campo a actualizar", options=list(campos.keys()))

# ==================== ESCANEO CON CÁMARA + IA ====================
st.subheader("📸 Escanea la serie")
st.caption("Apunta la cámara al número de serie impreso")

imagen = st.camera_input("Capturar foto", key="camera")

if imagen is not None:
    st.image(imagen, caption="Foto capturada", use_column_width=True)
    
    with st.spinner("🔍 Leyendo con Inteligencia Artificial..."):
        img_bytes = imagen.getvalue()
        pil_image = Image.open(io.BytesIO(img_bytes))
        
        if "reader" not in st.session_state:
            st.session_state.reader = easyocr.Reader(['en', 'es'], gpu=False)
        
        resultados = st.session_state.reader.readtext(pil_image, detail=0)
        texto_extraido = " ".join(resultados).strip().upper()
    
    st.success(f"**Serie detectada:** {texto_extraido}")
    serie_confirmada = st.text_input("Confirma o corrige el número", value=texto_extraido)
    
    if st.button("💾 Guardar en Clever Cloud", type="primary"):
        try:
            cursor = conn.cursor()
            columna = campos[operacion]
            
            # Si la unidad no existe, crearla automáticamente
            if df.empty or str(unidad) not in df["UNIT #"].astype(str).values:
                cursor.execute(f"""
                    INSERT INTO `unidades` (`N`, `UNIT #`, {columna.replace('`','')})
                    VALUES (%s, %s, %s)
                """, (int(unidad) + 100, unidad, serie_confirmada))
                st.info(f"✅ Unidad {unidad} creada automáticamente")
            else:
                query = f"UPDATE `unidades` SET {columna} = %s WHERE `UNIT #` = %s"
                cursor.execute(query, (serie_confirmada, unidad))
            
            conn.commit()
            st.success(f"✅ ¡Guardado correctamente en {operacion}!")
            st.rerun()
        except Exception as e:
            st.error(f"Error al guardar: {e}")
        finally:
            cursor.close()

# ==================== EXPORTAR A EXCEL ====================
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
st.caption("App de Escaneo de Series • Funciona en celular")