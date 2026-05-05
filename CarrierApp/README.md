# Carrier Transicold — APK WebView

APK nativo de Android que carga la app de Streamlit. Las actualizaciones
se aplican automáticamente sin reinstalar: solo actualiza el servidor.

---

## Paso 1 — Cambiar la URL de tu app

Edita este archivo:
```
app/src/main/java/com/carrier/transicold/MainActivity.java
```

Busca esta línea y pon tu URL real:
```java
private static final String APP_URL = "https://tu-app.railway.app";
```

---

## Paso 2 — Subir a GitHub

1. Crea un repositorio nuevo en github.com (puede ser privado)
2. Sube todos estos archivos tal como están

---

## Paso 3 — Obtener el APK

1. Ve a tu repositorio en GitHub
2. Haz clic en la pestaña **Actions**
3. Verás el workflow "Build APK" corriendo automáticamente
4. Cuando termine (2-3 minutos), haz clic en el workflow completado
5. Baja hasta **Artifacts** y descarga **CarrierTransicold-APK**
6. Descomprime el .zip — adentro está el **app-debug.apk**

---

## Instalar en el celular

1. Copia el APK al celular (por USB, WhatsApp, Google Drive, etc.)
2. En el celular: Ajustes → Seguridad → Activar "Fuentes desconocidas"
3. Abre el APK y acepta la instalación

---

## Cómo funciona la actualización automática

```
Tú editas tu código Python
        ↓
Haces push/deploy a Railway o Render
        ↓
Los técnicos abren la app en su celular
        ↓
Ven los cambios al instante — sin tocar el APK
```

El APK solo se reinstala si cambias algo de la app nativa (nombre, ícono, URL).
