"""
Generic Scraper - Scraper genérico para cualquier sitio de noticias
"""
import re
from datetime import datetime
from scrapers.base_scraper import BaseScraper, Article
import logging
import requests
from config import USER_AGENT

logger = logging.getLogger(__name__)


class GenericScraper(BaseScraper):
    """Scraper genérico que funciona con cualquier sitio configurado"""

    def __init__(self, source_name: str, config: dict):
        """
        Inicializar scraper genérico

        Args:
            source_name: Nombre de la fuente
            config: Configuración con URL y selectores
        """
        super().__init__(source_name, config.get("url", ""))
        self.url = config.get("url")
        self.selectors = config.get("selectors", {})

    def _create_session(self):
        """Crear sesión de requests con headers de navegador"""
        session = requests.Session()
        session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
        })
        return session

    def extract_articles(self) -> list:
        """Extraer artículos del sitio (SOLO noticias de hoy)"""
        try:
            logger.info(f"{self.source_name}: Descargando {self.url}...")

            html = self.fetch_page(self.url)
            if not html:
                return []

            soup = self.parse_html(html)
            articles = []
            today = datetime.now().date()
            skipped_old = 0

            # Buscar artículos usando selector
            article_selector = self.selectors.get("article")
            if not article_selector:
                logger.warning(f"{self.source_name}: No hay selector para artículos")
                return []

            article_elements = soup.select(article_selector)[:10]  # Máximo 10

            for element in article_elements:
                try:
                    # Extraer título
                    title_selector = self.selectors.get("title")
                    title_elem = element.select_one(title_selector) if title_selector else None
                    title = title_elem.get_text(strip=True) if title_elem else ""

                    if not title or len(title) < 10:
                        continue

                    # Extraer URL
                    link_elem = element.find("a", href=True)
                    url = link_elem.get("href", "") if link_elem else ""
                    if url and not url.startswith("http"):
                        url = self.url.split("/news")[0] + url

                    # Extraer texto/descripción
                    text_selector = self.selectors.get("text")
                    text_elem = element.select_one(text_selector) if text_selector else None
                    text = text_elem.get_text(strip=True) if text_elem else title

                    # Extraer imagen
                    image_selector = self.selectors.get("image")
                    image_elem = element.select_one(image_selector) if image_selector else None
                    image_url = image_elem.get("src", "") if image_elem else ""

                    if image_url and not image_url.startswith("http"):
                        image_url = self.url.split("/news")[0] + image_url

                    # Intentar extraer fecha de publicacion del elemento/URL
                    # Si la encontramos y NO es hoy, descartar.
                    # Si no la encontramos, aceptar (confiar en que el front-page
                    # muestra contenido reciente).
                    pub_date = self._extract_date_from_element(element, url)
                    if pub_date and pub_date != today:
                        skipped_old += 1
                        continue

                    # Crear artículo
                    article = Article(
                        title=title,
                        text=text,
                        url=url,
                        image_url=image_url,
                        published_date=datetime.combine(pub_date, datetime.min.time()) if pub_date else datetime.now(),
                        source=self.source_name
                    )

                    articles.append(article)

                except Exception as e:
                    logger.debug(f"{self.source_name}: Error procesando artículo: {e}")
                    continue

            if skipped_old:
                logger.info(
                    f"{self.source_name}: Extraidos {len(articles)} articulos "
                    f"(descartados {skipped_old} por no ser de hoy)"
                )
            else:
                logger.info(f"{self.source_name}: Extraidos {len(articles)} articulos")
            return articles

        except Exception as e:
            logger.error(f"{self.source_name}: Error: {e}")
            return []

    def _extract_date_from_element(self, element, url: str = ""):
        """
        Intenta extraer la fecha de publicacion de un elemento de la lista
        o de la URL. Devuelve un date o None si no la encuentra.
        """
        try:
            # 1) <time datetime="2026-04-15T...">
            time_elem = element.find("time")
            if time_elem:
                dt_attr = time_elem.get("datetime") or time_elem.get("pubdate")
                if dt_attr:
                    parsed = self._parse_date_string(dt_attr)
                    if parsed:
                        return parsed
                # texto del time tambien puede tener la fecha
                txt = time_elem.get_text(" ", strip=True)
                if txt:
                    parsed = self._parse_date_string(txt)
                    if parsed:
                        return parsed

            # 2) class/atributo que contenga "date", "time" o "published"
            for el in element.find_all(
                True,
                attrs={"class": lambda c: c and any(
                    k in " ".join(c).lower() for k in ["date", "time", "published", "timestamp"]
                )},
            ):
                txt = el.get_text(" ", strip=True)
                if txt:
                    parsed = self._parse_date_string(txt)
                    if parsed:
                        return parsed
                for attr_name in ["datetime", "data-date", "data-published", "title"]:
                    val = el.get(attr_name)
                    if val:
                        parsed = self._parse_date_string(val)
                        if parsed:
                            return parsed

            # 3) URL suele incluir /YYYY/MM/DD/ o similar
            if url:
                m = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", url)
                if m:
                    try:
                        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date()
                    except ValueError:
                        pass

            return None
        except Exception:
            return None

    def _parse_date_string(self, text: str):
        """Intentar parsear una fecha de un string en varios formatos."""
        if not text:
            return None
        text = text.strip()
        # Formatos mas comunes
        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%d %B %Y",
            "%d %b %Y",
        ]
        # Si trae timezone tipo +00:00 o Z, quitarlo para el parser simple
        iso_match = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", text)
        if iso_match:
            try:
                return datetime.strptime(iso_match.group(1), "%Y-%m-%dT%H:%M:%S").date()
            except ValueError:
                pass
        # Palabras relativas
        lower = text.lower()
        if "today" in lower or "hoy" in lower or "hours ago" in lower or "minutes ago" in lower or "just now" in lower:
            return datetime.now().date()
        if "yesterday" in lower or "ayer" in lower:
            # Devolver ayer para que pase el filtro como "no es hoy"
            from datetime import timedelta
            return (datetime.now() - timedelta(days=1)).date()
        # "X days ago" con X >= 1
        m_days_ago = re.search(r"(\d+)\s*(day|days|d)\s*ago", lower)
        if m_days_ago:
            from datetime import timedelta
            days = int(m_days_ago.group(1))
            if days >= 1:
                return (datetime.now() - timedelta(days=days)).date()
        for fmt in formats:
            try:
                return datetime.strptime(text[:len(fmt)+5], fmt).date()
            except (ValueError, TypeError):
                continue
        return None
