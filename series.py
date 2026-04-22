# ==================== IMPORTS ====================
import streamlit as st
import pandas as pd
import mysql.connector
import plotly.express as px
from datetime import datetime
import io
import pytz
import os
from uuid import uuid4
from PIL import Image
from streamlit_autorefresh import st_autorefresh

# ==================== CONFIG ====================
st.set_page_config(page_title="Carrier Panel", layout="wide")
st_autorefresh(interval=30 * 1000, key="refresh")

UPLOAD_FOLDER = "evidencias"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

tijuana_tz = pytz.timezone('America/Tijuana')

# ==================== DB ====================
@st.cache_resource
def get_db():
    return mysql.connector.connect(**st.secrets["db"], autocommit=True)

def read(q, p=None):
    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute(q, p or ())
        r = cur.fetchall()
        cur.close()
        return r
    except Exception as e:
        st.error(e)
        return []

def write(q, p=None):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(q, p or ())
        cur.close()
        return True
    except Exception as e:
        st.error(e)
        return False

# ==================== SAVE IMAGE ====================
def save_evidencia(file, tarea):
    try:
        img = Image.open(file).convert("RGB")
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=70)

        name = f"{uuid4()}.jpg"
        path = os.path.join(UPLOAD_FOLDER, name)

        with open(path, "wb") as f:
            f.write(buffer.getvalue())

        write("INSERT INTO evidencias (unit_number, nombre_archivo, contenido, tecnico) VALUES (%s,%s,%s,%s)",
              (tarea['unidad'], name, buffer.getvalue(), tarea['tecnico']))
        return True
    except Exception as e:
        st.error(e)
        return False

# ==================== SESSION ====================
if "login" not in st.session_state:
    st.session_state.update({"login": False, "user": "", "role": ""})

# ==================== LOGIN ====================
if not st.session_state.login:
    u = st.text_input("Usuario")
    p = st.text_input("Password", type="password")

    if st.button("Login"):
        r = read("SELECT * FROM users WHERE username=%s AND password=%s", (u, p))
        if r:
            st.session_state.login = True
            st.session_state.user = r[0]['username']
            st.session_state.role = r[0]['role']
            st.rerun()
        else:
            st.error("Error")
    st.stop()

# ==================== MENU ====================
menu = st.sidebar.selectbox("Menu", ["Mis Tareas"])

# ==================== MIS TAREAS ====================
if menu == "Mis Tareas":
    tareas = read("SELECT * FROM asignaciones WHERE tecnico=%s AND estado IN ('pendiente','en_proceso')",
                  (st.session_state.user,))

    for t in tareas:
        with st.expander(f"Unidad {t['unidad']} - {t['actividad_id']}"):

            if t['estado'] == 'pendiente':
                if st.button("Iniciar", key=f"i{t['id']}"):
                    write("UPDATE asignaciones SET estado='en_proceso' WHERE id=%s", (t['id'],))
                    st.rerun()

            elif t['actividad_id'].lower() == "evidencia":
                with st.form(f"form_{t['id']}"):

                    fotos = st.file_uploader("Sube fotos", accept_multiple_files=True)

                    if st.form_submit_button("Guardar"):
                        if fotos:
                            prog = st.progress(0)

                            for i, f in enumerate(fotos):
                                if f.size < 5*1024*1024:
                                    save_evidencia(f, t)
                                prog.progress((i+1)/len(fotos))

                            write("UPDATE asignaciones SET estado='completada' WHERE id=%s", (t['id'],))
                            st.success("Completado")
                            st.rerun()
                        else:
                            st.warning("Sube algo")

            else:
                if st.button("Terminar", key=f"f{t['id']}"):
                    write("UPDATE asignaciones SET estado='completada' WHERE id=%s", (t['id'],))
                    st.rerun()
