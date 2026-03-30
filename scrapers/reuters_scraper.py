"""
Reuters Scraper
"""
import logging
from typing import List
from .base_scraper import BaseScraper, Article
from datetime import datetime

logger = logging.getLogger(__name__)


class ReutersScraper(BaseScraper):
    """Scraper para Reuters (política y economía)"""

    def __init__(self):
        super().__init__(
            source_name="Reuters",
            base_url="https://www.reuters.com"
        )

    def extract_articles(self) -> List[Article]:
        """Extraer artículos de Reuters"""
        articles = []

        # Scraping de política
        politics_html = self.fetch_page("https://www.reuters.com/politics/")
        if politics_html:
            articles.extend(self._extract_from_html(politics_html, "politics"))

        # Scraping de economía
        economy_html = self.fetch_page("https://www.reuters.com/business/economy/")
        if economy_html:
            articles.extend(self._extract_from_html(economy_html, "economy"))

        articles = self.filter_valid_articles(articles)
        logger.info(f"Reuters: Extraídos {len(articles)} artículos")
        return articles

    def _extract_from_html(self, html: str, category: str) -> List[Article]:
        """Extraer artículos de HTML"""
        soup = self.parse_html(html)
        articles = []

        # Reuters usa divs con clase "item-heading"
        article_elements = soup.find_all("a", {"class": ["heading-link"]})

        for element in article_elements:
            try:
                # Extraer título
                title = self.safe_extract(element, "span")
                if not title:
                    continue

                # Extraer URL
                url = element.get("href")
                if not url:
                    continue
                url = self.normalize_url(url)

                # Extraer descripción (intentar obtener el párrafo asociado)
                parent = element.find_parent("article") or element.find_parent("li")
                text = ""
                if parent:
                    text_elem = parent.find("p", {"class": ["article-text", ""]})
                    if text_elem:
                        text = self.clean_text(text_elem.get_text())

                # Si no hay descripción, usar title como fallback
                if not text:
                    text = title

                # Extraer imagen
                image_url = None
                if parent:
                    img = parent.find("img")
                    if img:
                        image_url = img.get("src") or img.get("data-src")
                        if image_url:
                            image_url = self.normalize_url(image_url)

                # Crear artículo
                article = Article(
                    title=title,
                    text=text,
                    url=url,
                    image_url=image_url,
                    source="Reuters",
                )

                articles.append(article)

            except Exception as e:
                logger.debug(f"Error procesando elemento Reuters: {e}")
                continue

        return articles
