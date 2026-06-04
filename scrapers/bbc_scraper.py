"""
BBC Scraper
"""
import logging
from typing import List
from .base_scraper import BaseScraper, Article
from utils.article_extractor import ArticleExtractor

logger = logging.getLogger(__name__)


class BBCScraper(BaseScraper):
    """Scraper para BBC"""

    def __init__(self):
        super().__init__(
            source_name="BBC",
            base_url="https://www.bbc.com"
        )
        self.article_extractor = ArticleExtractor()

    def extract_articles(self) -> List[Article]:
        """Extraer artículos de BBC"""
        articles = []

        # BBC US & Canada (incluye política y economía)
        html = self.fetch_page("https://www.bbc.com/news/world/us_and_canada")
        if html:
            articles.extend(self._extract_from_html(html))

        # Enriquecer artículos con contenido completo
        for article in articles:
            logger.debug(f"Obteniendo contenido completo para: {article.title[:50]}")

            # Extraer contenido completo de la página del artículo
            full_content = self.article_extractor.extract_full_content(
                article.url, "BBC"
            )
            if full_content and len(full_content) > 200:
                article.text = full_content
                logger.debug(f"Contenido completo obtenido: {len(full_content)} chars")

            # Extraer imagen principal del artículo
            feature_image = self.article_extractor.extract_feature_image(
                article.url, "BBC"
            )
            if feature_image:
                article.image_url = feature_image
                logger.debug(f"Imagen obtenida: {feature_image[:50]}")

        articles = self.filter_valid_articles(articles)
        logger.info(f"BBC: Extraídos {len(articles)} artículos")
        return articles

    def _extract_from_html(self, html: str) -> List[Article]:
        """Extraer artículos de HTML"""
        soup = self.parse_html(html)
        articles = []

        # BBC usa article elements
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

                # Extraer descripción/resumen (múltiples párrafos si es posible)
                text_parts = []

                # Buscar párrafo de descripción principal
                desc_elem = element.find("p")
                if desc_elem:
                    text_parts.append(self.clean_text(desc_elem.get_text()))

                # Buscar otros párrafos o divs con contenido
                for p in element.find_all("p"):
                    p_text = self.clean_text(p.get_text())
                    if p_text and p_text not in text_parts and len(p_text) > 20:
                        text_parts.append(p_text)
                        if len(text_parts) >= 3:  # Limitar a 3 párrafos máximo
                            break

                text = " ".join(text_parts) if text_parts else title

                # Si el texto es muy corto, buscar en divs con clases comunes
                if len(text) < 200:
                    for div in element.find_all("div", class_=True):
                        if any(cls in str(div.get("class")) for cls in ["summary", "description", "text"]):
                            div_text = self.clean_text(div.get_text())
                            if len(div_text) > len(text):
                                text = div_text
                                break

                # Extraer imagen
                image_url = None
                img = element.find("img")
                if img:
                    image_url = img.get("src") or img.get("data-src")
                    if image_url:
                        image_url = self.normalize_url(image_url)

                article = Article(
                    title=title,
                    text=text,
                    url=url,
                    image_url=image_url,
                    source="BBC",
                )

                articles.append(article)

            except Exception as e:
                logger.debug(f"Error procesando elemento BBC: {e}")
                continue

        return articles
