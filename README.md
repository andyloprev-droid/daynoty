# Agente de Extracción y Procesamiento de Noticias

Sistema automatizado que extrae, procesa y enriquece noticias de política y economía de EE.UU. en tiempo real.

## Características

- ✅ **Web Scraping**: Extracción de 8 fuentes principales (Reuters, CNN, BBC, Fox, Bloomberg, CNBC, MarketWatch, WSJ)
- ✅ **Paráfrasis Inteligente**: Resúmenes con Claude evitando copypaste
- ✅ **Extracción de Imágenes**: Descarga y procesamiento de imágenes originales
- ✅ **Base de Datos**: Almacenamiento en Google Cloud Firestore
- ✅ **Ejecución Programada**: Cada hora, 24/7
- ✅ **Cloud Ready**: Deployment en Google Cloud Run
- 💡 **Opción Económica**: Sin generación de imágenes con DALL-E (Opción 3)

## Requisitos

- Python 3.10+
- Credenciales de Google Cloud
- API Key de OpenAI (DALL-E)
- API Key de Anthropic (Claude)

## Instalación

### 1. Clonar y configurar

```bash
git clone <repo-url>
cd news-agent
```

### 2. Crear entorno virtual

```bash
python -m venv venv

# En Windows
venv\Scripts\activate

# En Linux/Mac
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar credenciales

Copiar `.env.example` a `.env` y llenar valores:

```bash
cp .env.example .env
```

**Variables necesarias en `.env`:**

```env
OPENAI_API_KEY=sk-...
CLAUDE_API_KEY=sk-ant-...
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_KEY_PATH=/path/to/service-account-key.json
CLOUD_STORAGE_BUCKET=your-bucket-name
```

### 5. Crear bucket en Google Cloud

```bash
gsutil mb gs://your-bucket-name
```

## Uso

### Ejecutar una sola vez

```bash
python main.py --run-once
```

### Ejecutar programado (cada hora)

```bash
python main.py --schedule
```

### Ver resumen del día

```bash
python main.py --summary
```

### Modo prueba (logging detallado)

```bash
python main.py --test-mode
```

## Estructura de Carpetas

```
news-agent/
├── scrapers/                 # Web scrapers para cada fuente
│   ├── base_scraper.py      # Clase abstracta base
│   ├── reuters_scraper.py   # Scraper Reuters
│   └── ...                  # Otros scrapers
├── processors/              # Procesamiento de contenido
│   ├── content_processor.py # Resúmenes con Claude
│   ├── image_processor.py   # Procesamiento de imágenes
│   └── image_generator.py   # Generación con DALL-E
├── database/                # Interacción con Firestore
│   └── firestore_client.py  # Cliente Firestore
├── config.py                # Configuraciones
├── news_agent.py            # Orquestador principal
├── main.py                  # Punto de entrada
├── requirements.txt         # Dependencias
└── Dockerfile               # Contenedor Docker
```

## Flujo de Procesamiento

```
1. WEB SCRAPING
   └→ Extraer de 8 fuentes (Reuters, CNN, BBC, Fox, Bloomberg, CNBC, MarketWatch, WSJ)

2. FILTRADO DE DUPLICADOS
   └→ Verificar en Firestore si ya fue procesada

3. PROCESAMIENTO DE CONTENIDO
   ├→ Descargar y procesar imagen original
   └→ Resumir/parafrasear con Claude (evitar copypaste)

4. ALMACENAMIENTO
   └→ Guardar en Firestore + Google Cloud Storage

5. LOGGING
   └→ Registrar en Cloud Logging
```

**Nota**: Generación de imágenes con DALL-E deshabilitada (Opción 3 - Económica)

## Configuración Avanzada

### Cambiar frecuencia de ejecución

En `.env`:
```env
SCHEDULER_INTERVAL_MINUTES=30  # Ejecutar cada 30 minutos
```

### Ajustar nivel de logging

```env
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR
```

### Cambiar zona horaria

```env
SCHEDULER_TIMEZONE=America/Los_Angeles
```

## Monitoreo

### Ver logs locales

```bash
tail -f logs/news_agent.log
```

### Ver logs en Cloud

```bash
gcloud logging read "resource.type=cloud_run_job" --limit 50
```

### Ver estadísticas

Las estadísticas se guardan automáticamente en Firestore. Acceder vía:
- Google Cloud Console → Firestore
- Colección: `noticias`

## Costos Estimados

**Con 100-300 noticias/día (SIN generación de imágenes):**

| Servicio | Costo/mes |
|----------|-----------|
| Claude API (resúmenes) | $5-10 |
| Google Cloud Storage (imágenes originales) | $0.50-1 |
| Firestore (almacenamiento) | $0.50-1 |
| **Total** | **$6-12/mes** |

**Nota**: Si en el futuro decides activar DALL-E, el costo sería +$60-300/mes según volumen.

## Troubleshooting

### Error: "No module named 'anthropic'"

```bash
pip install anthropic
```

### Error: "Google Cloud credentials not found"

Verificar:
1. Variable `GOOGLE_CLOUD_KEY_PATH` en `.env`
2. Archivo JSON existe
3. Permisos de lectura en el archivo

### Imágenes no se generan

- Verificar saldo en OpenAI
- Revisar logs: `tail logs/news_agent.log`
- Probar manualmente: `python -c "from openai import OpenAI; print('OK')"`

### Noticias no se guardan

- Verificar Firestore existe en Google Cloud
- Comprobar permisos de Firebase
- Ver logs de Firestore en Cloud Console

## API Resultados

Acceder a noticias procesadas:

```python
from database.firestore_client import NewsDatabase

db = NewsDatabase()

# Obtener artículos recientes
articles = db.get_latest_articles(limit=10)

# Búsqueda por fecha
from datetime import datetime
today_articles = db.get_articles_by_date(datetime.now())

# Estadísticas
stats = db.get_statistics()
```

## Deployment en Google Cloud

### 1. Build y push de imagen

```bash
docker build -t gcr.io/YOUR_PROJECT/news-agent .
docker push gcr.io/YOUR_PROJECT/news-agent
```

### 2. Deploy en Cloud Run

```bash
gcloud run deploy news-agent \
  --image gcr.io/YOUR_PROJECT/news-agent \
  --platform managed \
  --region us-central1 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=YOUR_PROJECT" \
  --service-account=news-agent@YOUR_PROJECT.iam.gserviceaccount.com
```

### 3. Programar con Cloud Scheduler

```bash
gcloud scheduler jobs create app-engine news-agent-hourly \
  --schedule="0 * * * *" \
  --time-zone="America/New_York" \
  --http-method=POST \
  --uri="https://YOUR_CLOUD_RUN_URL/run"
```

## Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork del repositorio
2. Crear rama para feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push a rama (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

## Licencia

MIT License - ver LICENSE.md

## Soporte

Para reportar issues o sugerencias, abrir un issue en el repositorio.

---

**Última actualización**: 2026-03-27
