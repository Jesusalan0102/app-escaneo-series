import os
import pathlib
import subprocess
import sys

# Crear secrets.toml desde variables de entorno de Clever Cloud
p = pathlib.Path.home() / ".streamlit"
p.mkdir(exist_ok=True)

secrets = """[db]
host     = "{host}"
database = "{database}"
user     = "{user}"
password = "{password}"
port     = {port}
""".format(
    host     = os.environ.get("STREAMLIT_SECRETS_DB_HOST", ""),
    database = os.environ.get("STREAMLIT_SECRETS_DB_DATABASE", ""),
    user     = os.environ.get("STREAMLIT_SECRETS_DB_USER", ""),
    password = os.environ.get("STREAMLIT_SECRETS_DB_PASSWORD", ""),
    port     = os.environ.get("STREAMLIT_SECRETS_DB_PORT", "3306"),
)

(p / "secrets.toml").write_text(secrets)
print("secrets.toml creado en:", p / "secrets.toml")

# Arrancar Streamlit
os.execv(sys.executable, [
    sys.executable, "-m", "streamlit", "run", "series.py",
    "--server.port", "9000",
    "--server.address", "0.0.0.0",
    "--server.headless", "true"
])
