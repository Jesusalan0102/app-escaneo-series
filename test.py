import streamlit as st
import mysql.connector
import os

st.title("Diagnóstico de conexión")

config = {
    "host": "bmffi0bgsqnener2omcu-mysql.services.clever-cloud.com",
    "database": "bmffi0bgsqnener2omcu",
    "user": "uo8vbdsnvm2ojwta",
    "password": "aXSKib5oxXDEwjlozeQP",
    "port": 3306,
    "connection_timeout": 10
}

try:
    st.write("Intentando conectar...")
    conn = mysql.connector.connect(**config)
    st.success("✅ Conectado exitosamente!")
    conn.close()
except Exception as e:
    st.error(f"Error: {e}")
    st.info("Esto confirma que Streamlit Cloud no puede acceder a Clever Cloud.")
