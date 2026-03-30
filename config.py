"""
Configuraciones del Agente de Noticias
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ============ API Keys ============
CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY")  # Using ANTHROPIC_API_KEY from .env
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")  # Path to JSON credentials

# ============ Google Cloud ============
FIRESTORE_DATABASE = os.getenv("FIRESTORE_DATABASE", "noticias")
CLOUD_STORAGE_BUCKET = os.getenv("CLOUD_STORAGE_BUCKET")

# ============ Configuración de Scraping ============
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "10"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY = int(os.getenv("RETRY_DELAY", "2"))

# User Agent para evitar bloqueos
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# ============ Scrapers Configuración ============
SCRAPERS = {
    "reuters": {
        "url": "https://www.reuters.com/politics/",
        "enabled": True,
        "selectors": {
            "article": "article",
            "title": "h3, h2",
            "text": "p",
            "image": "img",
            "date": "time"
        }
    },
    "cnn": {
        "url": "https://www.cnn.com/us/politics",
        "enabled": True,
        "selectors": {
            "article": "article",
            "title": "h2, h3",
            "text": "p",
            "image": "img",
            "date": "span[class*='date']"
        }
    },
    "bbc": {
        "url": "https://www.bbc.com/news/world/us_and_canada",
        "enabled": True,
        "selectors": {
            "article": "article",
            "title": "h2, h3",
            "text": "p",
            "image": "img",
            "date": "time"
        }
    },
    "fox": {
        "url": "https://www.foxnews.com/politics",
        "enabled": True,
        "selectors": {
            "article": "article",
            "title": "h2, h3",
            "text": "p",
            "image": "img",
            "date": "span[data-testid*='date']"
        }
    },
    "bloomberg": {
        "url": "https://www.bloomberg.com/politics",
        "enabled": True,
        "requires_javascript": True,
        "selectors": {
            "article": "article",
            "title": "h2, h3",
            "text": "p",
            "image": "img",
            "date": "time"
        }
    },
    "cnbc": {
        "url": "https://www.cnbc.com/politics/",
        "enabled": True,
        "selectors": {
            "article": "article",
            "title": "h2, h3",
            "text": "p",
            "image": "img",
            "date": "span[class*='date']"
        }
    },
    "marketwatch": {
        "url": "https://www.marketwatch.com/",
        "enabled": True,
        "selectors": {
            "article": "article",
            "title": "h2, h3",
            "text": "p",
            "image": "img",
            "date": "time"
        }
    },
    "wsj": {
        "url": "https://www.wsj.com/news/politics",
        "enabled": True,
        "requires_login": False,  # Solo contenido libre
        "selectors": {
            "article": "article",
            "title": "h2, h3",
            "text": "p",
            "image": "img",
            "date": "time"
        }
    }
}

# ============ Procesamiento de Contenido ============
MIN_ARTICLE_LENGTH = 200  # Mínimo caracteres para procesar
MAX_ARTICLE_LENGTH = 5000  # Máximo caracteres a procesar
SUMMARY_TARGET_LENGTH = 300  # Palabras objetivo para resumen

# ============ Generación de Imágenes ============
# NOTA: Generación de imágenes DESHABILITADA (Opción 3 - Económica)
# Las noticias usarán las imágenes originales de las fuentes
# Si deseas activar DALL-E en el futuro, descomentar image_generator en news_agent.py
# DALL_E_MODEL = "dall-e-3"
# DALL_E_SIZE = "1024x1024"
# DALL_E_QUALITY = "standard"

# ============ Claude Configuration ============
CLAUDE_MODEL = "claude-3-5-sonnet-20241022"
CLAUDE_MAX_TOKENS = 1000

# ============ Base de Datos ============
DB_BATCH_SIZE = 50  # Guardar en lotes
DUPLICATE_CHECK_ENABLED = True

# ============ Scheduling ============
SCHEDULER_INTERVAL_MINUTES = 60  # Ejecutar cada hora
SCHEDULER_TIMEZONE = "America/New_York"  # Zona horaria EST

# ============ Logging ============
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = "logs/news_agent.log"

# ============ Ambiente ============
ENV = os.getenv("ENV", "development")  # development, production
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# ============ Validations ============
if not all([CLAUDE_API_KEY, GOOGLE_CLOUD_PROJECT, GOOGLE_APPLICATION_CREDENTIALS]):
    raise ValueError(
        "Missing configuration: ANTHROPIC_API_KEY, GOOGLE_CLOUD_PROJECT, GOOGLE_APPLICATION_CREDENTIALS in .env"
    )
