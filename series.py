import streamlit as st
import mysql.connector
from mysql.connector import Error
import pandas as pd
from io import BytesIO
from datetime import datetime
import time

# --- CONFIGURACIÓN DE ESTILO ---
st.set_page_config(page_title="Gestión de Refrigeración Tier 1", layout="wide", page_icon="❄️")

def local_css(file_name):
    st.markdown(f'<style>{file_name}</style>', unsafe_allow_html=True)

# CSS para mejorar la interfaz
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    .stDownloadButton>button { width: 100%; border-radius: 5px; background-color: #28a745; color: white; }
    .block-container { padding-top: 2rem; }
    .highlight { background-color: #e1f5fe; padding: 10px; border-radius: 10px; border-left: 5px solid #01579b; }
    </style>
    """, unsafe_allow_html=True)

# --- CLASE DE GESTIÓN DE BASE DE DATOS ---
class DBManager:
    def __init__(self):
        try:
            self.config = {
                'host': st.secrets["mysql"]["host"],
                'user': st.secrets["mysql"]["user"],
                'password': st.secrets["mysql"]["password"],
                'database': st.secrets["mysql"]["database"],
                'raise_on_warnings': True,
                'pool_name': "mypool",
                'pool_size': 5
            }
        except Exception:
            st.error("❌ No se encontraron los Secretos de la Base de Datos.")

    def get_connection(self):
        return mysql.connector.connect(**self.config)

    def inicializar_tablas(self):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS registro_series (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    fecha_registro DATETIME,
                    lote VARCHAR(50),
                    unidad VARCHAR(50),
                    serie VARCHAR(100),
                    operador VARCHAR(100)
                )
            """)
            conn.commit()
            cursor.close()
            conn.close()
        except Error as e:
            st.error(f"Error inicializando DB: {e}")

    def guardar_registro(self, lote, unidad, serie):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            query = "INSERT INTO registro_series (fecha_registro, lote, unidad, serie, operador) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(query, (datetime.now(), lote, unidad, serie, "Admin"))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Error as e:
            st.error(f"Error al guardar: {e}")
            return False

    def obtener_todo(self):
        try:
            conn = self.get_connection()
            df = pd.read_sql("SELECT * FROM registro_series ORDER BY fecha_registro DESC", conn)
            conn.close()
            return df
        except:
            return pd.DataFrame()

db = DBManager()
db.inicializar_tablas()

# --- LÓGICA DE DATOS DEL TABLERO ---
LOTES_DATA = {
    "445": [f"{i:02d}" for i in range(1, 4)],
    "431": [f"{i:02d}" for i in range(1, 3)],
    "426": [f"{i:02d}" for i in range(1, 6)],
    "443": [f"{i:02d}" for i in range(1, 4)],
    "444": [f"{i:02d}" for i in range(1, 3)],
    "425": [f"{i:02d}" for i in range(1, 3)],
    "244": ["01"],
    "458": ["01", "03", "02"],
    "245": ["02"],
    "258": ["04"],
    "405": ["12"],
    "391": [f"{i:02d}" for i in range(1, 7)]
}

# --- ESTADO DE LA SESIÓN ---
if 'step' not in st.session_state:
    st.session_state.step = 1
if 'lote_sel' not in st.session_state:
    st.session_state.lote_sel = ""
if 'unidad_sel' not in st.session_state:
    st.session_state.unidad_sel = ""

def reset_form():
    st.session_state.step = 1
    st.session_state.lote_sel = ""
    st.session_state.unidad_sel = ""
    st.rerun()

# --- SIDEBAR NAVEGACIÓN ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2933/2933753.png", width=100)
    st.title("Control Tier 1")
    opcion = st.radio("Menú Principal", ["📥 Registro Secuencial", "📊 Dashboard y Reportes", "🗄️ Histórico Completo"])
    st.divider()
    if st.button("🔄 Resetear Formulario"):
        reset_form()

# --- MÓDULO 1: REGISTRO SECUENCIAL ---
if opcion == "📥 Registro Secuencial":
    st.header("Entrada de Series")
    
    col1, col2 = st.columns([2, 1])

    with col1:
        with st.expander("Pasos de Llenado", expanded=True):
            # PASO 1: LOTE
            lote = st.selectbox("1. Seleccione el LOTE", [""] + list(LOTES_DATA.keys()), key="lote_box")
            
            if lote:
                st.session_state.lote_sel = lote
                # PASO 2: UNIDAD
                unidad = st.selectbox("2. Seleccione el UNIT NUMBER", [""] + LOTES_DATA[lote], key="unit_box")
                
                if unidad:
                    st.session_state.unidad_sel = unidad
                    # PASO 3: SERIE
                    serie = st.text_input("3. Escanee el Número de Serie", key="serie_input")
                    
                    if st.button("💾 GUARDAR REGISTRO"):
                        if serie:
                            with st.spinner('Guardando...'):
                                exito = db.guardar_registro(lote, unidad, serie)
                                if exito:
                                    st.toast(f"¡Serie {serie} guardada!", icon="✅")
                                    time.sleep(1)
                                    st.rerun()
                        else:
                            st.error("El número de serie es obligatorio.")

    with col2:
        st.info("📌 **Estado Actual**")
        st.write(f"**Lote:** {st.session_state.lote_sel}")
        st.write(f"**Unidad:** {st.session_state.unidad_sel}")
        if st.session_state.lote_sel and st.session_state.unidad_sel:
            st.success("Listo para escanear")

# --- MÓDULO 2: DASHBOARD ---
elif opcion == "📊 Dashboard y Reportes":
    st.header("Métricas y Exportación")
    df = db.obtener_todo()

    if not df.empty:
        # Fila de Métricas
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Registros", len(df))
        m2.metric("Lotes Activos", df['lote'].nunique())
        m3.metric("Series Hoy", len(df[df['fecha_registro'].dt.date == datetime.now().date()]))
        
        # Exportación del Dashboard
        resumen = df.groupby('lote').size().reset_index(name='Cantidad')
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            resumen.to_excel(writer, sheet_name='Resumen_Lotes', index=False)
            df.to_excel(writer, sheet_name='Detalle_Series', index=False)
        
        m4.download_button(
            label="📥 Exportar Excel",
            data=output.getvalue(),
            file_name=f"reporte_refrigeracion_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.divider()
        
        c_izq, c_der = st.columns(2)
        with c_izq:
            st.subheader("Producción por Lote")
            st.bar_chart(resumen.set_index('lote'))
        
        with c_der:
            st.subheader("Últimos Movimientos")
            st.dataframe(df[['lote', 'unidad', 'serie']].head(10), use_container_width=True)
    else:
        st.warning("No hay datos para mostrar el dashboard.")

# --- MÓDULO 3: HISTÓRICO ---
elif opcion == "🗄️ Histórico Completo":
    st.header("Administración de Datos")
    df = db.obtener_todo()
    
    filtro = st.text_input("🔍 Buscar por Serie o Lote")
    if filtro:
        df = df[df.astype(str).apply(lambda x: x.str.contains(filtro, case=False)).any(axis=1)]

    st.dataframe(df, use_container_width=True)
    
    if st.button("🗑️ Limpiar filtros"):
        st.rerun()