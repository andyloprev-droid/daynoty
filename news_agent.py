"""
News Agent - Orquestador principal del sistema de procesamiento de noticias
"""
import logging
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
from scrapers.reuters_scraper import ReutersScraper
from scrapers.cnn_scraper import CNNScraper
from scrapers.bbc_scraper import BBCScraper
from scrapers.fox_scraper import FoxScraper
from scrapers.bloomberg_scraper import BloombergScraper
from scrapers.cnbc_scraper import CNBCScraper
from scrapers.marketwatch_scraper import MarketWatchScraper
from scrapers.wsj_scraper import WSJScraper
from scrapers.base_scraper import Article
# from processors.image_processor import ImageProcessor  # Not needed - Option 3 (no image generation)
from processors.content_processor import ContentProcessor
from database.firestore_client import NewsDatabase
import config

logger = logging.getLogger(__name__)


class NewsAgent:
    """Agente principal que orquesta la extracción y procesamiento de noticias"""

    def __init__(self):
        # Initialize components
        self.scrapers = self._initialize_scrapers()
        # self.image_processor = ImageProcessor()  # Not needed - Option 3 (no image generation)
        self.content_processor = ContentProcessor()
        self.database = NewsDatabase()

        logger.info("NewsAgent initialized (no image generation)")

    def _initialize_scrapers(self):
        """Crear instancias de todos los scrapers"""
        return {
            "reuters": ReutersScraper(),
            "cnn": CNNScraper(),
            "bbc": BBCScraper(),
            "fox": FoxScraper(),
            "bloomberg": BloombergScraper(),
            "cnbc": CNBCScraper(),
            "marketwatch": MarketWatchScraper(),
            "wsj": WSJScraper(),
        }

    def run(self):
        """Ejecutar ciclo completo de procesamiento de noticias"""
        logger.info("=" * 50)
        logger.info(f"INICIO: Ciclo de procesamiento {datetime.now()}")
        logger.info("=" * 50)

        try:
            # 1. Extraer noticias de todas las fuentes
            articles = self._extract_all_articles()
            logger.info(f"Total extraído: {len(articles)} artículos")

            if not articles:
                logger.warning("No hay artículos para procesar")
                return

            # 2. Filtrar duplicados
            new_articles = self._filter_duplicates(articles)
            logger.info(f"Nuevas noticias: {len(new_articles)} (filtrados duplicados)")

            # 3. Procesar cada noticia
            processed_count = 0
            for article in new_articles:
                if self._process_single_article(article):
                    processed_count += 1

            logger.info(f"Total procesadas: {processed_count}/{len(new_articles)}")

            # 4. Resumen de ejecución
            stats = self.database.get_statistics()
            logger.info(f"Estadísticas BD: {stats}")

            logger.info("=" * 50)
            logger.info(f"FIN: Ciclo completado {datetime.now()}")
            logger.info("=" * 50)

        except Exception as e:
            logger.error(f"Error en ciclo de procesamiento: {e}", exc_info=True)

    def _extract_all_articles(self) -> List[Article]:
        """Extraer artículos de todas las fuentes"""
        all_articles = []

        for name, scraper in self.scrapers.items():
            try:
                logger.info(f"Extrayendo de {name}...")
                articles = scraper.extract_articles()
                all_articles.extend(articles)
                logger.info(f"{name}: {len(articles)} artículos")
            except Exception as e:
                logger.error(f"Error en scraper {name}: {e}")

        return all_articles

    def _filter_duplicates(self, articles: List[Article]) -> List[Article]:
        """Filtrar artículos duplicados ya procesados"""
        new_articles = []

        for article in articles:
            if not config.DUPLICATE_CHECK_ENABLED:
                new_articles.append(article)
                continue

            if not self.database.check_duplicate(article.url):
                new_articles.append(article)
            else:
                logger.debug(f"Duplicado encontrado: {article.title[:50]}")

        return new_articles

    def _process_single_article(self, article: Article) -> bool:
        """
        Procesar un artículo individual

        Flujo:
        1. Descargar y procesar imagen original
        2. Resumir contenido con Claude
        3. Guardar en Firestore

        Args:
            article: Artículo a procesar

        Returns:
            True si se procesó exitosamente
        """
        try:
            logger.info(f"Procesando: {article.title[:50]}...")

            # 1. Process original image (disabled - Option 3)
            original_image_url = article.image_url  # Keep original URL
            # if article.image_url:
            #     original_image_url = self.image_processor.process_and_upload(
            #         article.image_url, article.source
            #     )
            #     logger.debug(f"Image saved: {original_image_url[:50]}")

            # 2. Resumir contenido con Claude
            content_result = self.content_processor.summarize_news(
                article.title, article.text
            )

            if not content_result:
                logger.warning(f"No se pudo procesar contenido: {article.title[:50]}")
                return False

            summary = content_result.get("summary", article.text)

            # 3. Preparar datos para guardar
            article_data = {
                "title": article.title,
                "source": article.source,
                "original_text": article.text,
                "summary": summary,
                "key_points": content_result.get("key_points", []),
                "original_image_url": original_image_url,
                "published_date": article.published_date,
                "url_source": article.url,
                "category": self._determine_category(article),
                "is_original_content": content_result.get("is_original", True),
            }

            # 4. Guardar en Firestore
            doc_id = self.database.save_article(article_data)

            if doc_id:
                logger.info(f"✓ Artículo guardado: {article.title[:50]}")
                return True
            else:
                logger.error(f"✗ Error guardando: {article.title[:50]}")
                return False

        except Exception as e:
            logger.error(f"Error procesando artículo {article.title[:50]}: {e}")
            return False

    def _determine_category(self, article: Article) -> str:
        """
        Determinar categoría de noticia (política o economía)

        Args:
            article: Artículo

        Returns:
            Categoría (politics, economy)
        """
        text = (article.title + " " + article.text).lower()

        economy_keywords = [
            "economía", "economy", "stock", "mercado", "market",
            "finanza", "finance", "dinero", "money", "bolsa", "trade"
        ]

        for keyword in economy_keywords:
            if keyword in text:
                return "economy"

        return "politics"

    def get_daily_summary(self) -> Dict:
        """
        Obtener resumen de noticias del día

        Returns:
            Dict con estadísticas y artículos
        """
        today = datetime.now()
        articles = self.database.get_articles_by_date(today)
        stats = self.database.get_statistics()

        return {
            "date": today.isoformat(),
            "total_articles_today": len(articles),
            "total_articles_all_time": stats.get("total_articles", 0),
            "articles_by_source": stats.get("by_source", {}),
            "articles": articles[:10],  # Primeros 10
        }
