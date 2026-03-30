# 🚀 Guía de Configuración Paso a Paso

Este documento te guía para configurar completamente el Agente de Noticias.

**Tiempo total: 30-45 minutos**

---

## Paso 1️⃣: Obtener API Key de Claude

**Tiempo: 5 min**

1. Ve a https://console.anthropic.com/keys
2. Si no tienes cuenta, crea una (o inicia sesión)
3. Haz clic en **"Create Key"**
4. Dale un nombre (ej: "news-agent")
5. **Copia la key** (aparece una sola vez, guárdala)

**Guardar**: `CLAUDE_API_KEY = sk-ant-XXXXX...`

---

## Paso 2️⃣: Crear Google Cloud Project

**Tiempo: 10 min**

### 2a. Crear proyecto

1. Ve a https://console.cloud.google.com
2. Haz clic en el selector de proyecto (arriba izquierda)
3. Haz clic en **"NEW PROJECT"**
4. Nombre: `news-agent`
5. Click en **"CREATE"**
6. Espera ~1 min a que se cree

### 2b. Habilitar servicios requeridos

1. En la barra de búsqueda, escribe: **Firestore**
2. Haz clic en **"Cloud Firestore"**
3. Haz clic en **"Create Database"**
4. Selecciona región: `us-central1` (o la más cercana)
5. Modo: **"Start in production mode"**
6. Haz clic en **"Create"**
7. Espera a que se cree

**Repite para Cloud Storage:**
1. Busca: **Cloud Storage**
2. Haz clic en **"Create Bucket"**
3. Nombre: `news-agent-bucket-TUSUARIO` (debe ser único globalmente)
4. Ubicación: `us-central1`
5. Haz clic en **"Create"**

**Guardar**: `CLOUD_STORAGE_BUCKET = news-agent-bucket-TUSUARIO`

---

## Paso 3️⃣: Crear Service Account

**Tiempo: 10 min**

### 3a. Crear la cuenta de servicio

1. En Google Cloud Console, ve a **IAM & Admin** → **Service Accounts**
2. Haz clic en **"CREATE SERVICE ACCOUNT"**
3. Nombre: `news-agent-service`
4. Descripción: `Service account para News Agent`
5. Haz clic en **"CREATE AND CONTINUE"**

### 3b. Asignar permisos

En la sección "Grant this service account access to project":

1. Haz clic en **"Select a role"**
2. Busca y selecciona: **"Cloud Datastore User"** (para Firestore)
3. Haz clic en **"ADD ANOTHER ROLE"**
4. Selecciona: **"Storage Admin"** (para Cloud Storage)
5. Haz clic en **"CONTINUE"**
6. Haz clic en **"DONE"**

### 3c. Descargar credenciales JSON

1. Ve a **IAM & Admin** → **Service Accounts**
2. Haz clic en el email de `news-agent-service`
3. Ve a la pestaña **"KEYS"**
4. Haz clic en **"ADD KEY"** → **"Create new key"**
5. Selecciona **"JSON"**
6. Haz clic en **"CREATE"**
7. Se descargará un archivo JSON automáticamente

**Guardar**: Guarda este archivo en una carpeta segura (ej: `C:\Users\TUSUARIO\credentials\gcloud-key.json`)

**Guardar**: `GOOGLE_CLOUD_KEY_PATH = C:\Users\TUSUARIO\credentials\gcloud-key.json`

---

## Paso 4️⃣: Obtener Project ID

**Tiempo: 2 min**

1. En Google Cloud Console (inicio)
2. Mira el **Project ID** (arriba en el header, junto al nombre)
3. Copia el ID

**Guardar**: `GOOGLE_CLOUD_PROJECT = XXXXX` (sin comillas)

---

## Paso 5️⃣: Configurar archivo .env

**Tiempo: 5 min**

1. Abre el archivo **`.env.example`** en tu editor de texto
2. Guárdalo como **`.env`** (en la misma carpeta)
3. Llena los valores:

```env
# ============ API Keys ============
CLAUDE_API_KEY=sk-ant-XXXXX...       # De Paso 1
GOOGLE_CLOUD_PROJECT=news-agent-12345  # De Paso 4
GOOGLE_CLOUD_KEY_PATH=C:\Users\TUSUARIO\credentials\gcloud-key.json  # De Paso 3
CLOUD_STORAGE_BUCKET=news-agent-bucket-tusuario  # De Paso 2

# ============ El resto puede quedarse igual ============
REQUEST_TIMEOUT=10
MAX_RETRIES=3
RETRY_DELAY=2
SCHEDULER_INTERVAL_MINUTES=60
SCHEDULER_TIMEZONE=America/New_York
LOG_LEVEL=INFO
ENV=production
DEBUG=False
```

**⚠️ IMPORTANTE**: No versiones este archivo (ya está en `.gitignore`)

---

## Paso 6️⃣: Instalar dependencias

**Tiempo: 10 min**

Abre terminal/cmd en la carpeta del proyecto:

```bash
# Crear entorno virtual
python -m venv venv

# Activar (Windows)
venv\Scripts\activate

# Activar (Linux/Mac)
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

---

## Paso 7️⃣: Test Local

**Tiempo: 10 min**

### 7a. Test modo debug

```bash
python main.py --test-mode
```

Esto debe:
- ✅ Extraer noticias de las 8 fuentes
- ✅ Procesar algunos artículos
- ✅ Guardar en Firestore
- ✅ Ver logs detallados

Si hay errores, verás el detalle en los logs.

### 7b. Ver resumen

```bash
python main.py --summary
```

Debe mostrar noticias del día procesadas.

---

## Paso 8️⃣: Deployment en Google Cloud (OPCIONAL)

**Tiempo: 15 min**

Si todo funciona localmente, ahora desplegamos a Google Cloud para que corra 24/7:

### 8a. Build imagen Docker

```bash
docker build -t gcr.io/PROJECT_ID/news-agent .
```

Reemplaza `PROJECT_ID` con tu project ID de Google Cloud.

### 8b. Push a Container Registry

```bash
docker push gcr.io/PROJECT_ID/news-agent
```

### 8c. Deploy en Cloud Run

```bash
gcloud run deploy news-agent \
  --image gcr.io/PROJECT_ID/news-agent \
  --platform managed \
  --region us-central1 \
  --memory 512Mi \
  --timeout 600
```

### 8d. Programar ejecución cada hora

```bash
gcloud scheduler jobs create app-engine news-agent-hourly \
  --schedule="0 * * * *" \
  --time-zone="America/New_York" \
  --http-method=POST \
  --uri="https://YOUR_CLOUD_RUN_URL/run" 2>/dev/null || true
```

---

## ✅ Checklist Final

Antes de ejecutar:

- [ ] ✅ Tengo API Key de Claude
- [ ] ✅ Creé Google Cloud Project
- [ ] ✅ Habilitéé Firestore y Cloud Storage
- [ ] ✅ Creé Service Account y descargué JSON
- [ ] ✅ Configuré archivo `.env`
- [ ] ✅ Instalé dependencias con `pip install -r requirements.txt`
- [ ] ✅ Ejecuté test local: `python main.py --test-mode`

---

## 🚨 Troubleshooting

### Error: "No module named 'anthropic'"
```bash
pip install anthropic
```

### Error: "Google Cloud credentials not found"
- Verifica ruta en `GOOGLE_CLOUD_KEY_PATH`
- Comprueba que el archivo JSON existe
- Prueba ruta absoluta (no relativa)

### Error: "Firestore database not found"
- Ve a Google Cloud Console
- Verifica que Firestore está creada
- Comprueba el nombre en config.py

### Error: "Cloud Storage bucket not found"
- Ve a Google Cloud Console → Cloud Storage
- Verifica nombre exacto del bucket
- Asegúrate de permisos en Service Account

### Noticias no se extraen
```bash
python main.py --test-mode
```
Ver logs detallados para identificar problema en scrapers.

---

## 📞 Soporte

Si algo no funciona:
1. Lee el error en los logs
2. Revisa el archivo `logs/news_agent.log`
3. Abre un issue en el repositorio

---

**¡Listo! Ya tienes todo configurado.** 🎉

Ejecuta regularmente con:
```bash
python main.py --schedule
```

O déjalo corriendo 24/7 en Google Cloud Run.
