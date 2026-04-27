#!/bin/bash
# clevercloud/python_post_build.sh
# Este script corre ANTES de iniciar la app en Clever Cloud

# Crear la carpeta de configuración de Streamlit
mkdir -p ~/.streamlit

# Generar el secrets.toml desde las variables de entorno de Clever Cloud
cat > ~/.streamlit/secrets.toml << EOF
[db]
host     = "${STREAMLIT_SECRETS_DB_HOST}"
database = "${STREAMLIT_SECRETS_DB_DATABASE}"
user     = "${STREAMLIT_SECRETS_DB_USER}"
password = "${STREAMLIT_SECRETS_DB_PASSWORD}"
port     = ${STREAMLIT_SECRETS_DB_PORT}
EOF

echo "✅ secrets.toml generado correctamente"
echo "✅ Host: ${STREAMLIT_SECRETS_DB_HOST}"
