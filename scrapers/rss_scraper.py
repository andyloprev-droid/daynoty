"""
RSS Scraper - Obtener noticias de RSS feeds públicos
"""
import logging
from typing import List, Optional
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from scrapers.base_scraper import Article
import feedparser

logger = logging.getLogger(__name__)


class RSSFeedScraper:
    """Scraper para RSS feeds públicos"""

    def __init__(self, feed_url: str, source_name: str):
        """
        Inicializar scraper RSS

        Args:
            feed_url: URL del feed RSS
            source_name: Nombre de la fuente
        """
        self.feed_url = feed_url
        self.source_name = source_name

    def extract_articles(self) -> List[Article]:
        """
        Extraer artículos de un feed RSS

        Returns:
            Lista de artículos
        """
        try:
            logger.info(f"{self.source_name}: Descargando feed RSS...")

            # Usar feedparser para parsear el feed
            feed = feedparser.parse(self.feed_url)

            if feed.get("bozo"):
                logger.warning(f"{self.source_name}: Feed malformado, intentando procesar...")

            articles = []
            max_articles = 20  # Límite por feed
            skipped_old = 0
            skipped_nodate = 0

            for entry in feed.get("entries", [])[:max_articles]:
                try:
                    # Extraer información del entry
                    title = entry.get("title", "")

                    # Obtener descripción o contenido
                    summary = entry.get("summary", "")
                    content = entry.get("content")
                    if isinstance(content, list) and content:
                        content = content[0].get("value", "")

                    text = content or summary or ""

                    # Limpiar HTML de la descripción si es necesario
                    if text:
                        soup = BeautifulSoup(text, "html.parser")
                        text = soup.get_text(strip=True)

                    url = entry.get("link", "")

                    # Extraer imagen - preferir la de mayor resolución disponible
                    image_url = self._pick_best_image(entry)

                    # Parsear fecha publicada del feed (puede ser None si el feed
                    # no la trae o no se puede parsear)
                    published_date = self._parse_rss_date(entry.get("published"))

                    today = datetime.now().date()

                    # Pre-filtro rapido: si el RSS ya dice que NO es de hoy, descartar
                    # sin bajar la pagina completa.
                    if published_date is not None and published_date.date() != today:
                        skipped_old += 1
                        continue

                    # Decidir si hace falta bajar la pagina del articulo:
                    #  - texto corto
                    #  - falta imagen
                    #  - falta fecha fiable (RSS no la dio)
                    need_text = len(text) < 400
                    need_image = not image_url
                    need_date = published_date is None
                    page_date = None
                    if url and (need_text or need_image or need_date):
                        page_image, page_text, page_date = self._fetch_page_extras(
                            url, want_text=need_text
                        )
                        if need_image and page_image:
                            image_url = page_image
                        if need_text and page_text and len(page_text) > len(text):
                            text = page_text
                        if need_date and page_date:
                            published_date = page_date

                    # Si tras todos los intentos no hay fecha fiable -> descartar
                    if published_date is None:
                        skipped_nodate += 1
                        continue

                    # Revalidar con la fecha obtenida de la pagina (si cambio)
                    if published_date.date() != today:
                        skipped_old += 1
                        continue

                    if title and text and len(text) > 50:
                        article = Article(
                            title=title,
                            text=text,
                            url=url,
                            image_url=image_url,
                            published_date=published_date,
                            source=self.source_name,
                        )
                        articles.append(article)

                except Exception as e:
                    logger.debug(f"{self.source_name}: Error parseando entry: {e}")
                    continue

            if skipped_old or skipped_nodate:
                logger.info(
                    f"{self.source_name}: Extraidos {len(articles)} articulos "
                    f"(descartados {skipped_old} por no ser de hoy, "
                    f"{skipped_nodate} por no tener fecha fiable)"
                )
            else:
                logger.info(f"{self.source_name}: Extraidos {len(articles)} articulos")
            return articles

        except Exception as e:
            logger.error(f"{self.source_name}: Error descargando feed: {e}")
            return []

    def _fetch_page_extras(
        self, url: str, want_text: bool = True
    ) -> tuple:
        """
        Descargar la pagina del articulo UNA sola vez y devolver
        (og_image_url, body_text, published_date). Cualquiera puede ser None.
        """
        try:
            resp = requests.get(
                url,
                timeout=8,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
            resp.raise_for_status()
            # Leer hasta 300KB: suficiente para meta tags + cuerpo del articulo
            html = resp.text[:300000]
            soup = BeautifulSoup(html, "html.parser")

            # 1) og:image / twitter:image
            image_url = None
            for prop in ["og:image", "twitter:image", "twitter:image:src"]:
                tag = soup.find("meta", attrs={"property": prop}) or soup.find(
                    "meta", attrs={"name": prop}
                )
                if tag and tag.get("content"):
                    image_url = tag["content"]
                    break

            # 1b) Fecha de publicacion desde meta tags (mas autoritativa que RSS)
            published_date = None
            for prop in [
                "article:published_time",
                "og:article:published_time",
                "datePublished",
                "pubdate",
                "publishdate",
                "article:published",
            ]:
                tag = soup.find("meta", attrs={"property": prop}) or soup.find(
                    "meta", attrs={"name": prop}
                )
                if tag and tag.get("content"):
                    try:
                        val = tag["content"].strip()
                        # Soporta con y sin timezone
                        val = val.replace("Z", "+00:00")
                        published_date = datetime.fromisoformat(val)
                        break
                    except Exception:
                        continue
            # Fallback: <time datetime="...">
            if not published_date:
                t = soup.find("time")
                if t and t.get("datetime"):
                    try:
                        val = t["datetime"].strip().replace("Z", "+00:00")
                        published_date = datetime.fromisoformat(val)
                    except Exception:
                        pass

            # 2) Cuerpo del articulo (solo si se pide)
            body_text = None
            if want_text:
                # Remover basura comun
                for bad in soup.find_all(
                    ["script", "style", "nav", "header", "footer", "aside", "form"]
                ):
                    bad.decompose()

                # Estrategia: buscar <article> o contenedor principal
                candidates = []
                article_tag = soup.find("article")
                if article_tag:
                    candidates.append(article_tag)
                for sel in [
                    {"name": "div", "attrs": {"class": lambda c: c and "article" in c.lower()}},
                    {"name": "div", "attrs": {"class": lambda c: c and "entry-content" in c.lower()}},
                    {"name": "div", "attrs": {"class": lambda c: c and "post-content" in c.lower()}},
                    {"name": "div", "attrs": {"class": lambda c: c and "story" in c.lower()}},
                    {"name": "main", "attrs": {}},
                ]:
                    try:
                        found = soup.find(**sel)
                        if found:
                            candidates.append(found)
                    except Exception:
                        continue

                best_text = ""
                for cand in candidates:
                    paragraphs = cand.find_all("p")
                    text = " ".join(
                        p.get_text(" ", strip=True) for p in paragraphs
                    )
                    if len(text) > len(best_text):
                        best_text = text

                # Fallback: todos los <p> de la pagina
                if len(best_text) < 300:
                    paragraphs = soup.find_all("p")
                    text = " ".join(
                        p.get_text(" ", strip=True) for p in paragraphs
                    )
                    if len(text) > len(best_text):
                        best_text = text

                body_text = best_text if len(best_text) > 100 else None

            return (image_url, body_text, published_date)
        except Exception:
            return (None, None, None)

    def _pick_best_image(self, entry) -> Optional[str]:
        """
        Elegir la imagen de mayor resolución disponible en un entry RSS.
        Prioriza media_content > enclosures > media_thumbnail > image.
        """
        candidates = []

        # media_content: puede venir con width/height
        for mc in entry.get("media_content", []) or []:
            url = mc.get("url")
            if not url:
                continue
            try:
                w = int(mc.get("width", 0) or 0)
                h = int(mc.get("height", 0) or 0)
            except (ValueError, TypeError):
                w = h = 0
            candidates.append((w * h, url))

        # enclosures (imágenes adjuntas)
        for enc in entry.get("enclosures", []) or []:
            t = (enc.get("type") or "").lower()
            if "image" in t and enc.get("href"):
                candidates.append((0, enc["href"]))

        # media_thumbnail (generalmente baja resolución, último recurso)
        for mt in entry.get("media_thumbnail", []) or []:
            url = mt.get("url")
            if url:
                try:
                    w = int(mt.get("width", 0) or 0)
                    h = int(mt.get("height", 0) or 0)
                except (ValueError, TypeError):
                    w = h = 0
                candidates.append((w * h, url))

        # Campo image legacy
        if entry.get("image") and isinstance(entry["image"], dict):
            href = entry["image"].get("href")
            if href:
                candidates.append((0, href))

        # Buscar <img> en el contenido HTML como último recurso
        content_html = ""
        if entry.get("content"):
            c = entry["content"]
            if isinstance(c, list) and c:
                content_html = c[0].get("value", "")
        if not content_html:
            content_html = entry.get("summary", "")
        if content_html:
            try:
                soup = BeautifulSoup(content_html, "html.parser")
                for img in soup.find_all("img"):
                    src = img.get("src")
                    if src:
                        try:
                            w = int(img.get("width", 0) or 0)
                            h = int(img.get("height", 0) or 0)
                        except (ValueError, TypeError):
                            w = h = 0
                        candidates.append((w * h, src))
            except Exception:
                pass

        if not candidates:
            return None

        # Preferir la de mayor resolución conocida; si todas son 0, tomar la primera
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    def _parse_rss_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """
        Parsear fecha de feed RSS. Devuelve None si no se puede parsear
        para que el filtro estricto decida si buscar en la pagina del articulo
        o descartar.
        """
        if not date_str:
            return None
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except Exception:
            try:
                return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except Exception:
                return None
