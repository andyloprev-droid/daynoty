"""
CNN Scraper
"""
import logging
from typing import List
from .base_scraper import BaseScraper, Article

logger = logging.getLogger(__name__)


class CNNScraper(BaseScraper):
    """Scraper para CNN (política y economía)"""

    def __init__(self):
        super().__init__(
            source_name="CNN",
            base_url="https://www.cnn.com"
        )

    def extract_articles(self) -> List[Article]:
        """Extraer artículos de CNN"""
        articles = []

        # Scraping de política
        politics_html = self.fetch_page("https://www.cnn.com/us/politics")
        if politics_html:
            articles.extend(self._extract_from_html(politics_html, "politics"))

        # Scraping de negocios/economía
        business_html = self.fetch_page("https://www.cnn.com/business")
        if business_html:
            articles.extend(self._extract_from_html(business_html, "business"))

        articles = self.filter_valid_articles(articles)
        logger.info(f"CNN: Extraídos {len(articles)} artículos")
        return articles

    def _extract_from_html(self, html: str, category: str) -> List[Article]:
        """Extraer artículos de HTML"""
        soup = self.parse_html(html)
        articles = []

        # CNN usa article tags
        article_elements = soup.find_all("article")

        for element in article_elements:
            try:
                # Extraer título
                title_elem = element.find(["h2", "h3"])
                if not title_elem:
                    continue
                title = self.clean_text(title_elem.get_text())

                # Extraer URL
                link = element.find("a")
                if not link:
                    continue
                url = link.get("href")
                if not url:
                    continue
                url = self.normalize_url(url)

                # Extraer descripción
                desc_elem = element.find("p")
                text = self.clean_text(desc_elem.get_text()) if desc_elem else title

                # Extraer imagen
                image_url = None
                img = element.find("img")
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
                    source="CNN",
                )

                articles.append(article)

            except Exception as e:
                logger.debug(f"Error procesando elemento CNN: {e}")
                continue

        return articles
