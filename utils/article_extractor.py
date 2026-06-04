"""
Article Extractor - Extraer contenido completo de artículos de noticias
"""
import logging
from typing import Optional
import requests
from bs4 import BeautifulSoup
import time
from config import REQUEST_TIMEOUT, MAX_RETRIES, RETRY_DELAY, USER_AGENT

logger = logging.getLogger(__name__)


class ArticleExtractor:
    """Extrae contenido completo de páginas de artículos"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
        })

    def fetch_page(self, url: str) -> Optional[str]:
        """Descargar página con reintentos"""
        for attempt in range(MAX_RETRIES):
            try:
                response = self.session.get(url, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                logger.debug(f"Intento {attempt + 1}/{MAX_RETRIES} fallido para {url}: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (2 ** attempt))
        return None

    def clean_text(self, text: str) -> str:
        """Limpiar texto"""
        if not text:
            return ""
        text = " ".join(text.split())
        text = text.replace("\xa0", " ")
        return text.strip()

    def extract_full_content(self, url: str, source: str) -> Optional[str]:
        """
        Extrae contenido completo de un artículo

        Args:
            url: URL del artículo
            source: Nombre de la fuente (bbc, fox, etc.)

        Returns:
            Contenido completo del artículo o None
        """
        html = self.fetch_page(url)
        if not html:
            return None

        try:
            soup = BeautifulSoup(html, "html.parser")

            # Buscar párrafos en diferentes ubicaciones según la fuente
            paragraphs = []

            if source.lower() == "bbc":
                # BBC: párrafos dentro de article
                article = soup.find("article")
                if article:
                    for p in article.find_all("p"):
                        text = self.clean_text(p.get_text())
                        if text and len(text) > 20:
                            paragraphs.append(text)
            elif source.lower() == "fox":
                # Fox News: párrafos en main[role='main'] o article
                main = soup.find("main", {"role": "main"})
                if not main:
                    main = soup.find("article")
                if main:
                    for p in main.find_all("p"):
                        text = self.clean_text(p.get_text())
                        if text and len(text) > 20:
                            paragraphs.append(text)
            else:
                # Fallback: buscar todos los párrafos
                for p in soup.find_all("p"):
                    text = self.clean_text(p.get_text())
                    if text and len(text) > 20:
                        paragraphs.append(text)

            # Concatenar párrafos
            if paragraphs:
                full_content = " ".join(paragraphs)
                logger.debug(f"Contenido extraído: {len(full_content)} caracteres")
                return full_content

        except Exception as e:
            logger.warning(f"Error extrayendo contenido de {url}: {e}")

        return None

    def extract_feature_image(self, url: str, source: str) -> Optional[str]:
        """
        Extrae imagen principal de un artículo

        Args:
            url: URL del artículo
            source: Nombre de la fuente

        Returns:
            URL de la imagen o None
        """
        html = self.fetch_page(url)
        if not html:
            return None

        try:
            soup = BeautifulSoup(html, "html.parser")

            # Intentar extraer imagen de meta tags primero
            og_image = soup.find("meta", {"property": "og:image"})
            if og_image and og_image.get("content"):
                logger.debug(f"Imagen encontrada en og:image")
                return og_image.get("content")

            # Selectores por fuente
            selectors = {
                "bbc": [
                    "figure img",
                    "article img:first-of-type",
                    "img[class*='figure']"
                ],
                "fox": [
                    "article img",
                    "figure img",
                    "img[class*='featured']"
                ]
            }

            # Usar selectores de la fuente o defaults
            search_selectors = selectors.get(source.lower(), [
                "img[class*='featured']",
                "article img",
                "figure img"
            ])

            # Buscar imagen
            for selector in search_selectors:
                try:
                    img = soup.select_one(selector)
                    if img:
                        src = img.get("src") or img.get("data-src")
                        if src:
                            # Convertir a URL absoluta si es relativa
                            if src.startswith("http"):
                                logger.debug(f"Imagen encontrada: {src[:50]}...")
                                return src
                            elif src.startswith("/"):
                                # URL relativa
                                from urllib.parse import urljoin
                                absolute_url = urljoin(url, src)
                                logger.debug(f"Imagen relativa convertida: {absolute_url[:50]}...")
                                return absolute_url
                except Exception as e:
                    logger.debug(f"Error con selector '{selector}': {e}")
                    continue

        except Exception as e:
            logger.warning(f"Error extrayendo imagen de {url}: {e}")

        return None
