"""
Configuraciones del Agente de Noticias
"""
import os
from dotenv import load_dotenv

load_dotenv(override=True)

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
# NOTA: Muchas fuentes (Reuters, Bloomberg, MarketWatch, WSJ) requieren JavaScript o
# tienen protecciones anti-scraping. BBC y Fox News funcionan mejor.
# NewsAPI es una alternativa para obtener más volumen de artículos.
SCRAPERS = {
    "reuters": {
        "url": "https://www.reuters.com/politics/",
        "enabled": True,
        "selectors": {
            "article": "[data-testid='Link']",
            "title": "h3, h2, a",
            "text": "p, span[class*='text']",
            "image": "img[class*='image']",
            "date": "time, span[class*='date']"
        }
    },
    "cnn": {
        "url": "https://www.cnn.com/politics",
        "enabled": True,
        "selectors": {
            "article": "[class*='container'], article",
            "title": "span[class*='headline'], h2, h3",
            "text": "p[class*='text'], p, span[class*='description']",
            "image": "img[class*='image']",
            "date": "span[class*='timestamp'], time"
        }
    },
    "bbc": {
        "url": "https://www.bbc.com/news/politics",
        "enabled": True,
        "selectors": {
            "article": "[data-testid='internal-link']",
            "title": "h2, h3, a",
            "text": "p[class*='summary'], p, div[class*='text']",
            "image": "img[class*='image']",
            "date": "time, span[class*='date']"
        }
    },
    "fox": {
        "url": "https://www.foxnews.com/politics",
        "enabled": True,
        "selectors": {
            "article": "article, [class*='article']",
            "title": "h2, h3, span[class*='title'], a",
            "text": "p[class*='text'], p, div[class*='summary']",
            "image": "img[class*='image'], img",
            "date": "span[class*='date'], time"
        }
    },
    "bloomberg": {
        "url": "https://www.bloomberg.com/politics",
        "enabled": False,
        "requires_javascript": True,
        "selectors": {
            "article": "article, [class*='story']",
            "title": "h2, h3, a",
            "text": "p[class*='text'], p",
            "image": "img[class*='image']",
            "date": "time, span[class*='date']"
        }
    },
    "cnbc": {
        "url": "https://www.cnbc.com/politics/",
        "enabled": False,
        "selectors": {
            "article": "article, [class*='article']",
            "title": "h2, h3, a",
            "text": "p[class*='text'], p, span[class*='summary']",
            "image": "img[class*='image']",
            "date": "span[class*='date'], time"
        }
    },
    "marketwatch": {
        "url": "https://www.marketwatch.com/",
        "enabled": False,
        "selectors": {
            "article": "article, [class*='article']",
            "title": "h2, h3, a",
            "text": "p, span[class*='text']",
            "image": "img[class*='image']",
            "date": "time, span[class*='date']"
        }
    },
    "wsj": {
        "url": "https://www.wsj.com/news/politics",
        "enabled": False,
        "requires_login": False,
        "selectors": {
            "article": "article, [class*='article']",
            "title": "h2, h3, a",
            "text": "p, span[class*='text']",
            "image": "img[class*='image']",
            "date": "time, span[class*='date']"
        }
    },
    "newsmax": {
        "url": "https://www.newsmax.com/politics",
        "enabled": True,
        "selectors": {
            "article": "article, [class*='story'], [class*='article-item']",
            "title": "h2, h3, a[href*='/news/']",
            "text": "p[class*='text'], p, div[class*='summary']",
            "image": "img[class*='image'], img",
            "date": "span[class*='date'], time, [class*='timestamp']"
        }
    },
    "theamericanconservative": {
        "url": "https://www.theamericanconservative.com/politics/",
        "enabled": True,
        "selectors": {
            "article": "article, [class*='post'], [class*='article']",
            "title": "h2, h3, a",
            "text": "p[class*='text'], p, div[class*='summary']",
            "image": "img[class*='image'], img",
            "date": "span[class*='date'], time"
        }
    },
    "realclearpolitics": {
        "url": "https://www.realclearpolitics.com/",
        "enabled": True,
        "selectors": {
            "article": "article, [class*='article'], [class*='story']",
            "title": "h2, h3, a",
            "text": "p[class*='text'], p, span",
            "image": "img[class*='image'], img",
            "date": "span[class*='date'], time"
        }
    },
    "townhall": {
        "url": "https://townhall.com/politics",
        "enabled": True,
        "selectors": {
            "article": "article, [class*='article-item'], [class*='story']",
            "title": "h2, h3, a",
            "text": "p[class*='text'], p, div[class*='summary']",
            "image": "img[class*='image'], img",
            "date": "span[class*='date'], time"
        }
    },
    "dailywire": {
        "url": "https://www.dailywire.com/news",
        "enabled": True,
        "selectors": {
            "article": "article, [class*='article-card'], [class*='story']",
            "title": "h2, h3, a",
            "text": "p[class*='text'], p, span[class*='description']",
            "image": "img[class*='image'], img",
            "date": "span[class*='date'], time, [class*='timestamp']"
        }
    },
    "washingtonexaminer": {
        "url": "https://www.washingtonexaminer.com/politics",
        "enabled": True,
        "selectors": {
            "article": "article, [class*='article'], [class*='post-item']",
            "title": "h2, h3, a",
            "text": "p[class*='text'], p, div[class*='summary']",
            "image": "img[class*='image'], img",
            "date": "span[class*='date'], time"
        }
    },
    "nationalreview": {
        "url": "https://www.nationalreview.com/politics/",
        "enabled": True,
        "selectors": {
            "article": "article, [class*='article'], [class*='story']",
            "title": "h2, h3, a",
            "text": "p[class*='text'], p, span[class*='summary']",
            "image": "img[class*='image'], img",
            "date": "span[class*='date'], time"
        }
    },
    "theblaze": {
        "url": "https://www.theblaze.com/news",
        "enabled": True,
        "selectors": {
            "article": "article, [class*='article-item'], [class*='story-card']",
            "title": "h2, h3, a",
            "text": "p[class*='text'], p, div[class*='summary']",
            "image": "img[class*='image'], img",
            "date": "span[class*='date'], time"
        }
    },
    "epochtimes": {
        "url": "https://www.theepochtimes.com/c-us-news",
        "enabled": True,
        "selectors": {
            "article": "article, [class*='article'], [class*='item']",
            "title": "h2, h3, a",
            "text": "p[class*='text'], p, span[class*='summary']",
            "image": "img[class*='image'], img",
            "date": "span[class*='date'], time"
        }
    },
    "redstate": {
        "url": "https://www.redstate.com/",
        "enabled": True,
        "selectors": {
            "article": "article, [class*='post'], [class*='article-item']",
            "title": "h2, h3, a",
            "text": "p[class*='text'], p, div[class*='summary']",
            "image": "img[class*='image'], img",
            "date": "span[class*='date'], time, [class*='published']"
        }
    },
    "hotair": {
        "url": "https://hotair.com/",
        "enabled": True,
        "selectors": {
            "article": "article, [class*='post'], [class*='item']",
            "title": "h2, h3, a",
            "text": "p[class*='text'], p, div[class*='excerpt']",
            "image": "img[class*='image'], img",
            "date": "span[class*='date'], time"
        }
    },
    "powerline": {
        "url": "https://www.powerlineblog.com/",
        "enabled": True,
        "selectors": {
            "article": "article, [class*='post'], [class*='entry']",
            "title": "h2, h3, a",
            "text": "p[class*='text'], p, div[class*='entry-content']",
            "image": "img[class*='image'], img",
            "date": "span[class*='date'], time"
        }
    },
    "americanthinker": {
        "url": "https://www.americanthinker.com/",
        "enabled": True,
        "selectors": {
            "article": "article, [class*='article'], [class*='post']",
            "title": "h2, h3, a",
            "text": "p[class*='text'], p, div[class*='summary']",
            "image": "img[class*='image'], img",
            "date": "span[class*='date'], time"
        }
    },
    "conservativereview": {
        "url": "https://www.conservativereview.com/news/politics",
        "enabled": True,
        "selectors": {
            "article": "article, [class*='article'], [class*='story']",
            "title": "h2, h3, a",
            "text": "p[class*='text'], p, span[class*='summary']",
            "image": "img[class*='image'], img",
            "date": "span[class*='date'], time"
        }
    },
    "investopedia": {
        "url": "https://www.investopedia.com/markets",
        "enabled": True,
        "selectors": {
            "article": "article, [class*='article'], [class*='story']",
            "title": "h2, h3, a",
            "text": "p[class*='text'], p, span[class*='summary']",
            "image": "img[class*='image'], img",
            "date": "span[class*='date'], time, [class*='timestamp']"
        }
    },
    "seeking_alpha": {
        "url": "https://seekingalpha.com/market-news",
        "enabled": True,
        "selectors": {
            "article": "article, [class*='article'], [class*='news-item']",
            "title": "h2, h3, a",
            "text": "p[class*='text'], p, span[class*='summary']",
            "image": "img[class*='image'], img",
            "date": "span[class*='date'], time"
        }
    },
    "investors_business_daily": {
        "url": "https://www.investors.com/news/",
        "enabled": True,
        "selectors": {
            "article": "article, [class*='article'], [class*='item']",
            "title": "h2, h3, a",
            "text": "p[class*='text'], p, span[class*='summary']",
            "image": "img[class*='image'], img",
            "date": "span[class*='date'], time"
        }
    },
    "zero_hedge": {
        "url": "https://www.zerohedge.com/",
        "enabled": True,
        "selectors": {
            "article": "article, [class*='article'], [class*='item']",
            "title": "h2, h3, a",
            "text": "p[class*='text'], p, span[class*='summary']",
            "image": "img[class*='image'], img",
            "date": "span[class*='date'], time"
        }
    },
    "benzinga": {
        "url": "https://www.benzinga.com/news",
        "enabled": True,
        "selectors": {
            "article": "article, [class*='article'], [class*='post']",
            "title": "h2, h3, a",
            "text": "p[class*='text'], p, span[class*='summary']",
            "image": "img[class*='image'], img",
            "date": "span[class*='date'], time"
        }
    },
    "breitbart": {
        "url": "https://www.breitbart.com/economy/",
        "enabled": True,
        "selectors": {
            "article": "article, [class*='article'], [class*='post']",
            "title": "h2, h3, a",
            "text": "p[class*='text'], p, span[class*='summary']",
            "image": "img[class*='image'], img",
            "date": "span[class*='date'], time"
        }
    },
    "business_insider": {
        "url": "https://www.businessinsider.com/",
        "enabled": True,
        "selectors": {
            "article": "article, [class*='article'], [class*='item']",
            "title": "h2, h3, a",
            "text": "p[class*='text'], p, span[class*='summary']",
            "image": "img[class*='image'], img",
            "date": "span[class*='date'], time"
        }
    },
    "stock_market_news": {
        "url": "https://www.cnbc.com/finance/",
        "enabled": True,
        "selectors": {
            "article": "article, [class*='article'], [class*='news-item']",
            "title": "h2, h3, a",
            "text": "p[class*='text'], p, span[class*='summary']",
            "image": "img[class*='image'], img",
            "date": "span[class*='date'], time"
        }
    },
    "tradingview": {
        "url": "https://www.tradingview.com/news/",
        "enabled": True,
        "selectors": {
            "article": "article, [class*='article'], [class*='item']",
            "title": "h2, h3, a",
            "text": "p[class*='text'], p, span[class*='summary']",
            "image": "img[class*='image'], img",
            "date": "span[class*='date'], time"
        }
    },
    "fool_com": {
        "url": "https://www.fool.com/investing/",
        "enabled": True,
        "selectors": {
            "article": "article, [class*='article'], [class*='post']",
            "title": "h2, h3, a",
            "text": "p[class*='text'], p, span[class*='summary']",
            "image": "img[class*='image'], img",
            "date": "span[class*='date'], time"
        }
    }
}

# ============ NewsAPI Configuration ============
# Obtener API key gratis en https://newsapi.org/register
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "demo")  # Replace with your key for production
NEWSAPI_ENABLED = os.getenv("NEWSAPI_ENABLED", "True").lower() == "true"
NEWSAPI_KEYWORDS = "politics economy"  # Palabras clave para buscar
NEWSAPI_LANGUAGE = "en"

# ============ RSS Feeds Configuration ============
# NOTA: Todos estos feeds fueron VERIFICADOS y funcionan.
# Mayormente republicanos/conservadores + fuentes de economia de EE.UU.
RSS_FEEDS = [
    # ===== POLITICA - REPUBLICANOS / CONSERVADORES =====
    {"name": "Fox News Politics", "url": "http://feeds.foxnews.com/foxnews/politics", "enabled": True, "category": "politics"},
    {"name": "National Review", "url": "https://www.nationalreview.com/feed/", "enabled": True, "category": "politics"},
    {"name": "Washington Examiner", "url": "https://www.washingtonexaminer.com/feed/", "enabled": True, "category": "politics"},
    {"name": "The American Conservative", "url": "https://www.theamericanconservative.com/feed/", "enabled": True, "category": "politics"},
    {"name": "The Federalist", "url": "https://thefederalist.com/feed/", "enabled": True, "category": "politics"},
    {"name": "Hot Air", "url": "https://hotair.com/feed", "enabled": True, "category": "politics"},
    {"name": "PJ Media", "url": "https://pjmedia.com/feed/", "enabled": True, "category": "politics"},
    {"name": "RedState", "url": "https://redstate.com/feed/", "enabled": True, "category": "politics"},
    {"name": "American Greatness", "url": "https://amgreatness.com/feed/", "enabled": True, "category": "politics"},
    {"name": "Washington Times Politics", "url": "https://www.washingtontimes.com/rss/headlines/news/politics/", "enabled": True, "category": "politics"},
    {"name": "CBN News", "url": "https://www1.cbn.com/cbnnews/us/feed", "enabled": True, "category": "politics"},
    {"name": "The Daily Caller", "url": "https://dailycaller.com/feed/", "enabled": True, "category": "politics"},
    {"name": "PowerLine Blog", "url": "https://www.powerlineblog.com/feed", "enabled": True, "category": "politics"},
    {"name": "Legal Insurrection", "url": "https://legalinsurrection.com/feed/", "enabled": True, "category": "politics"},
    {"name": "Newsbusters", "url": "https://www.newsbusters.org/rss.xml", "enabled": True, "category": "politics"},
    {"name": "Western Journal", "url": "https://www.westernjournal.com/feed/", "enabled": True, "category": "politics"},
    {"name": "Washington Free Beacon", "url": "https://freebeacon.com/feed/", "enabled": True, "category": "politics"},
    {"name": "American Thinker", "url": "https://www.americanthinker.com/index.xml", "enabled": True, "category": "politics"},
    {"name": "Just the News", "url": "https://justthenews.com/rss.xml", "enabled": True, "category": "politics"},
    # ===== ECONOMIA - BOLSA DE VALORES / MERCADOS (pocas, solo lo importante) =====
    {"name": "CNBC Markets", "url": "https://www.cnbc.com/id/10000664/device/rss/rss.html", "enabled": True, "category": "economy"},
    {"name": "MarketWatch Markets", "url": "https://feeds.content.dowjones.io/public/rss/mw_marketpulse", "enabled": True, "category": "economy"},
]

# ============ Filtros por Categoría ============
# Límite de artículos de economía por ciclo (pocas, solo importantes)
MAX_ECONOMY_ARTICLES_PER_CYCLE = 8

# ============ Filtro de Viralidad ============
# Score mínimo (1-10, combinacion 60% viralidad + 40% importancia).
# 6 = noticias importantes con buen potencial viral.
MIN_VIRALITY_SCORE = 6

# Maximo de noticias a procesar por ciclo (las TOP por score combinado).
MAX_ARTICLES_PER_CYCLE = 10

# Palabras clave para filtrar noticias políticas (solo se aceptan si contienen alguna)
POLITICS_KEYWORDS = [
    "trump", "biden", "harris", "vance", "republican", "democrat", "gop",
    "congress", "senate", "house", "white house", "election", "vote", "voter",
    "campaign", "president", "governor", "supreme court", "scotus", "bill",
    "legislat", "policy", "immigration", "border", "pentagon", "doj", "fbi",
    "cia", "constitution", "administration", "federal", "capitol", "obama",
    "clinton", "desantis", "pelosi", "mcconnell", "schumer", "kamala",
    "conservative", "liberal", "progressive", "left-wing", "right-wing",
    "impeach", "filibuster", "primary", "caucus", "ballot", "lawmaker",
    "senator", "representative", "congressman", "congresswoman", "politic",
    "second amendment", "first amendment", "woke", "cancel", "abortion",
    "transgender", "dei", "marxis", "communis", "socialis",
]

# Palabras clave para filtrar noticias de economía (solo bolsa / mercados importantes)
ECONOMY_KEYWORDS = [
    "stock", "stocks", "market", "markets", "nasdaq", "dow", "s&p", "s and p",
    "wall street", "shares", "share price", "earnings", "bond", "bonds",
    "yield", "fed", "federal reserve", "interest rate", "rate cut", "rate hike",
    "inflation", "cpi", "gdp", "ipo", "bull market", "bear market", "trading",
    "trader", "dividend", "nyse", "treasury", "index", "indexes", "futures",
    "recession", "rally", "selloff", "sell-off", "volatility", "vix",
    "etf", "hedge fund", "portfolio", "investor", "equity", "equities",
]

# ============ Procesamiento de Contenido ============
MIN_ARTICLE_LENGTH = 200  # Mínimo caracteres para procesar
MAX_ARTICLE_LENGTH = 5000  # Máximo caracteres a procesar
SUMMARY_TARGET_LENGTH = 300  # Palabras objetivo para resumen

# ============ Full Article Extraction ============
EXTRACT_FULL_ARTICLES = True
FULL_ARTICLE_TIMEOUT = 15  # Segundos para descargar página de artículo

# ============ Image Processing ============
ENABLE_IMAGE_PROCESSING = True
IMAGE_MAX_WIDTH = 1200
IMAGE_QUALITY = 85
IMAGE_BUCKET_FOLDER = "article_images"

# ============ Generación de Imágenes ============
# NOTA: Generación de imágenes DESHABILITADA (Opción 3 - Económica)
# Las noticias usarán las imágenes originales de las fuentes
# Si deseas activar DALL-E en el futuro, descomentar image_generator en news_agent.py
# DALL_E_MODEL = "dall-e-3"
# DALL_E_SIZE = "1024x1024"
# DALL_E_QUALITY = "standard"

# ============ OpenAI Configuration (ChatGPT) ============
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # barato y rapido
CLAUDE_MAX_TOKENS = 900  # Caption Facebook en ingles (hook + body + CTA + hashtags)

# ============ Claude Configuration (legacy, ya no se usa) ============
CLAUDE_MODEL = "claude-haiku-4-5-20251001"

# ============ Base de Datos ============
DB_BATCH_SIZE = 50  # Guardar en lotes
DUPLICATE_CHECK_ENABLED = True

# ============ Scheduling ============
SCHEDULER_INTERVAL_MINUTES = 30  # Ejecutar cada 30 minutos (noticias más frescas)
SCHEDULER_TIMEZONE = "America/New_York"  # Zona horaria EST

# ============ Logging ============
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = "logs/news_agent.log"

# ============ Ambiente ============
ENV = os.getenv("ENV", "development")  # development, production
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# ============ Validations ============
if not all([OPENAI_API_KEY, GOOGLE_CLOUD_PROJECT, GOOGLE_APPLICATION_CREDENTIALS]):
    raise ValueError(
        "Missing configuration: OPENAI_API_KEY, GOOGLE_CLOUD_PROJECT, GOOGLE_APPLICATION_CREDENTIALS in .env"
    )
