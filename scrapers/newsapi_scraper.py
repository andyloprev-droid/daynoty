"""
NewsAPI Scraper - Obtener noticias de 40,000+ fuentes usando NewsAPI.org
"""
import logging
from typing import List, Optional
import requests
from datetime import datetime, timedelta
from scrapers.base_scraper import Article

logger = logging.getLogger(__name__)


class NewsAPIScraper:
    """Scraper que utiliza la API de NewsAPI.org"""

    def __init__(self, api_key: str):
        """
        Inicializar scraper NewsAPI

        Args:
            api_key: API key de NewsAPI.org (obtener gratis en https://newsapi.org)
        """
        self.api_key = api_key
        self.base_url = "https://newsapi.org/v2/everything"
        self.source_name = "NewsAPI"

    def extract_articles(self, keywords: str = "politics economy", language: str = "en", sort_by: str = "publishedAt") -> List[Article]:
        """
        Extraer artículos de NewsAPI

        Args:
            keywords: Palabras clave para buscar (default: política y economía)
            language: Idioma (default: inglés)
            sort_by: Ordenar por (publishedAt, relevancy, popularity)

        Returns:
            Lista de artículos
        """
        try:
            # Fecha para obtener últimas 24 horas
            from_date = (datetime.now() - timedelta(days=1)).isoformat()

            params = {
                "q": keywords,
                "language": language,
                "sortBy": sort_by,
                "apiKey": self.api_key,
                "pageSize": 30,  # Máximo recomendado
                "from": from_date,
            }

            logger.info(f"{self.source_name}: Buscando '{keywords}'...")

            response = requests.get(self.base_url, params=params, timeout=15)
            response.raise_for_status()

            data = response.json()

            if data.get("status") != "ok":
                error_msg = data.get("message", "Error desconocido")
                logger.error(f"{self.source_name}: Error API - {error_msg}")
                return []

            articles = []
            for item in data.get("articles", []):
                try:
                    article = Article(
                        title=item.get("title", ""),
                        text=item.get("description", "") or item.get("content", ""),
                        url=item.get("url", ""),
                        image_url=item.get("urlToImage"),
                        published_date=self._parse_date(item.get("publishedAt")),
                        source=item.get("source", {}).get("name", "NewsAPI"),
                    )

                    # Validar artículo
                    if article.title and article.text and len(article.text) > 50:
                        articles.append(article)

                except Exception as e:
                    logger.debug(f"{self.source_name}: Error parseando artículo: {e}")
                    continue

            logger.info(f"{self.source_name}: Extraídos {len(articles)} artículos")
            return articles

        except requests.exceptions.RequestException as e:
            logger.error(f"{self.source_name}: Error descargando: {e}")
            return []
        except Exception as e:
            logger.error(f"{self.source_name}: Error: {e}")
            return []

    def _parse_date(self, date_str: Optional[str]) -> datetime:
        """Parsear fecha ISO 8601"""
        if not date_str:
            return datetime.now()
        try:
            # NewsAPI usa formato ISO 8601
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            return datetime.now()
