"""
Base Scraper - Clase abstracta para scrapers de noticias
"""
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
import time
from config import REQUEST_TIMEOUT, MAX_RETRIES, RETRY_DELAY, USER_AGENT

logger = logging.getLogger(__name__)


class Article:
    """Modelo de artículo extraído"""

    def __init__(
        self,
        title: str,
        text: str,
        url: str,
        image_url: Optional[str] = None,
        published_date: Optional[datetime] = None,
        source: Optional[str] = None,
    ):
        self.title = title
        self.text = text
        self.url = url
        self.image_url = image_url
        self.published_date = published_date or datetime.now()
        self.source = source

    def __repr__(self):
        return f"Article(title='{self.title[:50]}...', source='{self.source}')"

    def is_valid(self) -> bool:
        """Validar que el artículo tenga información mínima"""
        return bool(self.title and self.text and len(self.text) > 100)


class BaseScraper(ABC):
    """Clase abstracta para scrapers de noticias"""

    def __init__(self, source_name: str, base_url: str):
        self.source_name = source_name
        self.base_url = base_url
        self.session = requests.Session()

        # Configurar headers para simular navegador real
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        })

    def fetch_page(self, url: str) -> Optional[str]:
        """Descargar página HTML con reintentos"""
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.get(url, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                logger.warning(
                    f"{self.source_name}: Intento {attempt + 1}/{MAX_RETRIES} fallido para {url}: {e}"
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (2 ** attempt))  # Exponential backoff
                else:
                    logger.error(f"{self.source_name}: Error descargando {url}: {e}")
                    return None
        return None

    def parse_html(self, html: str) -> BeautifulSoup:
        """Parsear HTML a BeautifulSoup"""
        return BeautifulSoup(html, "html.parser")

    @abstractmethod
    def extract_articles(self) -> List[Article]:
        """Extraer artículos - debe implementarse en subclases"""
        pass

    def clean_text(self, text: str) -> str:
        """Limpiar texto extraído"""
        if not text:
            return ""
        # Remover espacios múltiples y saltos de línea
        text = " ".join(text.split())
        # Remover caracteres especiales problemáticos
        text = text.replace("\xa0", " ")
        return text.strip()

    def safe_extract(self, element, selector: str, attribute: Optional[str] = None) -> Optional[str]:
        """
        Extraer texto o atributo de un elemento de forma segura

        Args:
            element: Elemento BeautifulSoup
            selector: Selector CSS
            attribute: Atributo a extraer (None = text)

        Returns:
            Valor extraído o None
        """
        try:
            found = element.select_one(selector)
            if found:
                if attribute:
                    return found.get(attribute)
                else:
                    return self.clean_text(found.get_text())
        except Exception as e:
            logger.debug(f"Error extrayendo con selector '{selector}': {e}")
        return None

    def filter_valid_articles(self, articles: List[Article]) -> List[Article]:
        """Filtrar artículos válidos"""
        valid = [a for a in articles if a.is_valid()]
        if len(valid) != len(articles):
            logger.warning(
                f"{self.source_name}: Filtraron {len(articles) - len(valid)} artículos inválidos"
            )
        return valid

    def normalize_url(self, url: str) -> str:
        """Normalizar URL relativa a absoluta si es necesario"""
        if url.startswith("http"):
            return url
        if url.startswith("/"):
            return self.base_url + url
        return self.base_url + "/" + url
