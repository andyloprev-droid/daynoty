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
from scrapers.generic_scraper import GenericScraper
from scrapers.newsapi_scraper import NewsAPIScraper
from scrapers.rss_scraper import RSSFeedScraper
from scrapers.base_scraper import Article
from processors.image_processor import ImageProcessor
from processors.content_processor import ContentProcessor
from processors.semantic_dedup import SemanticDedup
from database.firestore_client import NewsDatabase
import config

logger = logging.getLogger(__name__)


class NewsAgent:
    """Agente principal que orquesta la extracción y procesamiento de noticias"""

    def __init__(self):
        # Initialize components
        self.scrapers = self._initialize_scrapers()
        self.image_processor = ImageProcessor()
        self.content_processor = ContentProcessor()
        self.database = NewsDatabase()
        self.last_cleanup_date = None  # Para detectar cambio de día

        logger.info("NewsAgent initialized with full article processing")

    def _initialize_scrapers(self):
        """Crear instancias de todos los scrapers"""
        scrapers = {
            "reuters": ReutersScraper(),
            "cnn": CNNScraper(),
            "bbc": BBCScraper(),
            "fox": FoxScraper(),
            "bloomberg": BloombergScraper(),
            "cnbc": CNBCScraper(),
            "marketwatch": MarketWatchScraper(),
            "wsj": WSJScraper(),
        }

        # Agregar scrapers genéricos para nuevas fuentes
        for name, cfg in config.SCRAPERS.items():
            if cfg.get("enabled") and name not in scrapers:
                try:
                    scrapers[name] = GenericScraper(name.replace("_", " ").title(), cfg)
                except Exception as e:
                    logger.warning(f"Error inicializando scraper {name}: {e}")

        # Agregar NewsAPI si está habilitado
        if config.NEWSAPI_ENABLED and config.NEWSAPI_KEY != "demo":
            try:
                scrapers["newsapi"] = NewsAPIScraper(config.NEWSAPI_KEY)
                logger.info("NewsAPI scraper inicializado")
            except Exception as e:
                logger.warning(f"Error inicializando NewsAPI: {e}")

        # Agregar RSS feeds + mapa de categorías por nombre de fuente
        self.source_categories = {}
        for feed in config.RSS_FEEDS:
            if feed.get("enabled"):
                try:
                    scraper_name = f"rss_{feed['name'].replace(' ', '_').lower()}"
                    scrapers[scraper_name] = RSSFeedScraper(feed["url"], feed["name"])
                    self.source_categories[feed["name"]] = feed.get("category", "politics")
                except Exception as e:
                    logger.warning(f"Error inicializando RSS feed {feed['name']}: {e}")

        return scrapers

    def run(self):
        """Ejecutar ciclo completo de procesamiento de noticias"""
        logger.info("=" * 50)
        logger.info(f"INICIO: Ciclo de procesamiento {datetime.now()}")
        logger.info("=" * 50)

        # Nota: La limpieza diaria ahora se maneja por cron a la 1 AM hora Miami
        # (ver main.py daily_cleanup_job)

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

            # 3. Filtrar por potencial de viralidad + importancia (60/40)
            if new_articles:
                scored = self.content_processor.score_virality_batch(new_articles)
                min_score = getattr(config, "MIN_VIRALITY_SCORE", 7)
                max_articles = getattr(config, "MAX_ARTICLES_PER_CYCLE", 8)
                viral_articles = [(art, s) for art, s in scored if s >= min_score]
                filtered_out = len(scored) - len(viral_articles)
                if filtered_out:
                    logger.info(
                        f"Score: {len(viral_articles)} pasan (>= {min_score}), "
                        f"{filtered_out} descartadas por bajo score"
                    )
                # Limitar a las TOP MAX_ARTICLES_PER_CYCLE (ordenadas por score)
                viral_articles = viral_articles[:max_articles]
                logger.info(
                    f"TOP {len(viral_articles)} noticias del dia (cap {max_articles}):"
                )
                for art, s in viral_articles:
                    logger.info(f"  [{s}/10] {art.title[:80]}")
                new_articles = [art for art, s in viral_articles]

            # 4. Procesar cada noticia
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
        """Extraer artículos de todas las fuentes, con filtros por categoría"""
        politics_articles = []
        economy_articles = []

        for name, scraper in self.scrapers.items():
            try:
                logger.info(f"Extrayendo de {name}...")
                articles = scraper.extract_articles()
                logger.info(f"{name}: {len(articles)} artículos")

                for article in articles:
                    category = self.source_categories.get(article.source, "politics")
                    if category == "economy":
                        if self._matches_keywords(article, config.ECONOMY_KEYWORDS):
                            economy_articles.append(article)
                    else:
                        if self._matches_keywords(article, config.POLITICS_KEYWORDS):
                            politics_articles.append(article)
            except Exception as e:
                logger.error(f"Error en scraper {name}: {e}")

        # Limitar economía a los N más recientes/importantes
        max_econ = getattr(config, "MAX_ECONOMY_ARTICLES_PER_CYCLE", 8)
        if len(economy_articles) > max_econ:
            # Ordenar por fecha descendente (más recientes primero)
            economy_articles.sort(
                key=lambda a: a.published_date or datetime.min, reverse=True
            )
            economy_articles = economy_articles[:max_econ]

        logger.info(
            f"Filtrado por categoría: {len(politics_articles)} políticas, "
            f"{len(economy_articles)} economía (cap {max_econ})"
        )
        return politics_articles + economy_articles

    def _matches_keywords(self, article: Article, keywords: List[str]) -> bool:
        """Verificar si el artículo contiene alguna palabra clave de la categoría"""
        text = ((article.title or "") + " " + (article.text or "")).lower()
        return any(kw in text for kw in keywords)

    def _filter_duplicates(self, articles: List[Article]) -> List[Article]:
        """
        Filtrar duplicados en dos niveles:
        1) Exacto: URL / título normalizado (rápido)
        2) Semántico: TF-IDF + coseno sobre título + resumen
        """
        if not config.DUPLICATE_CHECK_ENABLED:
            return articles

        # 1) Cache de coincidencias exactas
        cache = self.database.load_existing_index()

        # 2) Índice semántico inicializado con los artículos existentes
        sem_dedup = SemanticDedup(similarity_threshold=0.45)
        sem_dedup.fit(cache.get("items", []))

        new_articles = []
        exact_dups = 0
        semantic_dups = 0

        for article in articles:
            # Check rápido por URL/título exacto
            if self.database.check_duplicate(article.url, article.title, cache=cache):
                exact_dups += 1
                continue

            # Check semántico (captura mismo evento reportado por varias fuentes)
            if sem_dedup.is_duplicate(article.title, article.text):
                semantic_dups += 1
                logger.debug(f"Dup semántico descartado: {article.title[:60]}")
                continue

            # Agregar a ambos caches para bloquear duplicados dentro del mismo batch
            norm_url = self.database._normalize_url(article.url) if article.url else ""
            norm_title = self.database._normalize_title(article.title) if article.title else ""
            if norm_url:
                cache["urls"].add(norm_url)
            if norm_title:
                cache["titles"].add(norm_title)
            sem_dedup.add(article.title, article.text)

            new_articles.append(article)

        logger.info(
            f"Dedup: {exact_dups} exactos + {semantic_dups} semánticos descartados "
            f"de {len(articles)} | {len(new_articles)} nuevos"
        )
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

            # 1. Generar pregunta de encuesta para overlay de imagen
            poll_question = ""
            try:
                poll_question = self.content_processor.generate_poll_question(
                    article.title, article.text
                )
                logger.info(f"Poll: {poll_question}")
            except Exception as e:
                logger.warning(f"Error generando poll: {e}")
                poll_question = article.title

            # 2. Process and upload image to Cloud Storage
            original_image_url = article.image_url
            cloud_image_url = None

            if article.image_url:
                try:
                    cloud_image_url = self.image_processor.process_and_upload(
                        article.image_url, article.source,
                        title=poll_question or article.title,
                    )
                    logger.debug(f"Imagen guardada en Cloud: {cloud_image_url[:50]}")
                except Exception as e:
                    logger.warning(f"Error procesando imagen: {e}")
                    # Continue without image

            # 2. Resumir contenido con Claude
            content_result = self.content_processor.summarize_news(
                article.title, article.text
            )

            if not content_result:
                logger.warning(f"No se pudo procesar contenido: {article.title[:50]}")
                return False

            summary = content_result.get("summary", article.text)
            facebook_caption = content_result.get("facebook_caption", "")

            # 3. Preparar datos para guardar - TITULO, RESUMEN, IMAGEN Y URL
            article_data = {
                "title": article.title,
                "summary": summary,
                "facebook_caption": facebook_caption,  # Caption optimizado para Facebook en ES
                "published_to_facebook": False,  # Flag para el publisher futuro
                "cloud_image_url": cloud_image_url,  # URL de imagen en Google Cloud
                "url_source": article.url,  # URL del artículo original (para detectar duplicados)
            }

            # 4. Guardar en Firestore
            doc_id = self.database.save_article(article_data)

            if doc_id:
                daily_num = article_data.get("daily_number", "?")
                logger.info(f"[Noticia #{daily_num}] Artículo guardado: {article.title[:50]}")
                return True
            else:
                logger.error(f"Error guardando: {article.title[:50]}")
                return False

        except Exception as e:
            logger.error(f"Error procesando artículo {article.title[:50]}: {e}")
            return False

    def _check_and_cleanup_daily(self):
        """
        Verificar si es un nuevo día y borrar noticias del día anterior
        para mantener limpio el proyecto
        """
        try:
            today = datetime.now().date()

            # Si es el primer ciclo o cambió la fecha
            if self.last_cleanup_date is None or self.last_cleanup_date != today:
                if self.last_cleanup_date is not None:  # No limpiar en la primera ejecución
                    logger.info("=" * 50)
                    logger.info("LIMPIEZA DIARIA: Borrando artículos del día anterior")
                    logger.info("=" * 50)
                    deleted = self.database.delete_all_articles()
                    logger.info(f"✓ Se borraron {deleted} artículos. El proyecto está limpio para el nuevo día")
                    logger.info("=" * 50)

                self.last_cleanup_date = today

        except Exception as e:
            logger.error(f"Error en limpieza diaria: {e}")

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
