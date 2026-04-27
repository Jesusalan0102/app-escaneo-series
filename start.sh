#!/bin/bash
# Crear secrets.toml en AMBAS rutas que Streamlit busca
mkdir -p ~/.streamlit
cat > ~/.streamlit/secrets.toml << SECRETS
[db]
host     = "${STREAMLIT_SECRETS_DB_HOST}"
database = "${STREAMLIT_SECRETS_DB_DATABASE}"
user     = "${STREAMLIT_SECRETS_DB_USER}"
password = "${STREAMLIT_SECRETS_DB_PASSWORD}"
port     = ${STREAMLIT_SECRETS_DB_PORT}
SECRETS

# También en la ruta del app si existe
APP_DIR=$(find /home/bas -maxdepth 1 -name "app_*" -type d 2>/dev/null | head -1)
if [ -n "$APP_DIR" ]; then
    mkdir -p "$APP_DIR/.streamlit"
    cp ~/.streamlit/secrets.toml "$APP_DIR/.streamlit/secrets.toml"
    echo "✅ secrets.toml copiado a $APP_DIR/.streamlit/"
fi

echo "✅ secrets.toml creado en ~/.streamlit/"
echo "🚀 Iniciando Streamlit..."
python3 -m streamlit run series.py --server.port 9000 --server.address 0.0.0.0 --server.headless true
