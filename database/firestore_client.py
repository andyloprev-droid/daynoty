"""
Firestore Client - Interacción con base de datos Firestore
"""
import logging
from typing import Optional, List, Dict
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import config

logger = logging.getLogger(__name__)


class NewsDatabase:
    """Cliente para Firestore - almacenar y recuperar noticias"""

    def __init__(self):
        # Initialize Firebase
        try:
            import os
            os.environ['FIRESTORE_DATABASE_ID'] = 'andy1'

            cred = credentials.Certificate(config.GOOGLE_APPLICATION_CREDENTIALS)
            firebase_admin.initialize_app(cred, {
                'projectId': config.GOOGLE_CLOUD_PROJECT,
            })
        except ValueError:
            # Already initialized
            pass

        self.db = firestore.client()
        self.collection = config.FIRESTORE_DATABASE

    def save_article(self, article_data: Dict) -> Optional[str]:
        """
        Guardar artículo procesado en Firestore con número de día

        Args:
            article_data: Dict con datos del artículo

        Returns:
            ID del documento guardado
        """
        try:
            # Agregar timestamp de procesamiento
            article_data["processed_date"] = datetime.now()

            # Obtener número consecutivo del día
            daily_number = self._get_next_daily_number()
            article_data["daily_number"] = daily_number

            # Guardar en Firestore
            doc_ref = self.db.collection(self.collection).add(article_data)
            doc_id = doc_ref[1].id

            logger.info(f"Artículo #{daily_number} guardado en Firestore: {doc_id}")
            return doc_id

        except Exception as e:
            logger.error(f"Error guardando artículo en Firestore: {e}")
            return None

    def _get_next_daily_number(self) -> int:
        """
        Obtener el siguiente número consecutivo para el día

        Returns:
            Número consecutivo del día
        """
        try:
            today = datetime.now().date()
            start_date = datetime(today.year, today.month, today.day)
            end_date = datetime(today.year, today.month, today.day, 23, 59, 59)

            query = (
                self.db.collection(self.collection)
                .where("processed_date", ">=", start_date)
                .where("processed_date", "<=", end_date)
                .order_by("daily_number", direction=firestore.Query.DESCENDING)
                .limit(1)
            )

            docs = list(query.stream())

            if docs:
                last_number = docs[0].to_dict().get("daily_number", 0)
                return last_number + 1
            else:
                return 1

        except Exception as e:
            logger.warning(f"Error obteniendo número consecutivo: {e}")
            return 1

    @staticmethod
    def _normalize_title(title: str) -> str:
        """Normalizar titulo para comparacion (lowercase, sin puntuacion, trim)"""
        if not title:
            return ""
        import re
        normalized = title.lower().strip()
        # Remover puntuacion y caracteres especiales
        normalized = re.sub(r'[^\w\s]', '', normalized)
        # Colapsar espacios multiples
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Normalizar URL para comparacion (sin query params, trailing slash)"""
        if not url:
            return ""
        # Remover query string
        url = url.split('?')[0].split('#')[0]
        # Remover trailing slash
        url = url.rstrip('/')
        return url.lower()

    def load_existing_index(self) -> dict:
        """
        Pre-cargar TODOS los titulos y URLs existentes en memoria.
        Tambien devuelve 'items' con title+summary para dedup semantica.

        Returns:
            Dict con 'urls', 'titles' (sets normalizados) y 'items' (lista)
        """
        try:
            urls = set()
            titles = set()
            items = []

            docs = self.db.collection(self.collection).stream()
            for doc in docs:
                data = doc.to_dict()
                url = data.get('url_source', '')
                title = data.get('title', '')
                summary = data.get('summary', '')

                if url:
                    urls.add(self._normalize_url(url))
                if title:
                    titles.add(self._normalize_title(title))
                if title:
                    items.append({'title': title, 'text': summary})

            logger.info(
                f"Cache de duplicados cargado: {len(urls)} URLs, "
                f"{len(titles)} titulos, {len(items)} items semanticos"
            )
            return {'urls': urls, 'titles': titles, 'items': items}

        except Exception as e:
            logger.warning(f"Error cargando indice de duplicados: {e}")
            return {'urls': set(), 'titles': set(), 'items': []}

    def check_duplicate(self, url: str, title: str = None, cache: dict = None) -> bool:
        """
        Verificar si noticia ya fue procesada (por URL o titulo normalizado)

        Args:
            url: URL de la noticia
            title: Titulo de la noticia
            cache: Dict con 'urls' y 'titles' pre-cargados (opcional, mas rapido)

        Returns:
            True si ya existe
        """
        # Si hay cache en memoria, usarlo (mucho mas rapido)
        if cache is not None:
            norm_url = self._normalize_url(url) if url else ''
            norm_title = self._normalize_title(title) if title else ''

            if norm_url and norm_url in cache.get('urls', set()):
                return True
            if norm_title and norm_title in cache.get('titles', set()):
                return True
            return False

        # Fallback: query directa a Firestore
        try:
            if url:
                query = self.db.collection(self.collection).where(
                    "url_source", "==", url
                ).limit(1)
                docs = list(query.stream())
                if docs:
                    return True

            if title:
                query = self.db.collection(self.collection).where(
                    "title", "==", title
                ).limit(1)
                docs = list(query.stream())
                if docs:
                    return True

            return False

        except Exception as e:
            logger.warning(f"Error verificando duplicado: {e}")
            return False

    def get_articles_by_date(self, date: datetime) -> List[Dict]:
        """
        Obtener artículos de un día específico

        Args:
            date: Fecha

        Returns:
            Lista de artículos
        """
        try:
            start_date = datetime(date.year, date.month, date.day)
            end_date = datetime(date.year, date.month, date.day, 23, 59, 59)

            query = (
                self.db.collection(self.collection)
                .where("processed_date", ">=", start_date)
                .where("processed_date", "<=", end_date)
                .order_by("processed_date", direction=firestore.Query.DESCENDING)
            )

            docs = query.stream()
            articles = []
            for doc in docs:
                articles.append({"id": doc.id, **doc.to_dict()})

            return articles

        except Exception as e:
            logger.warning(f"Error obteniendo artículos por fecha: {e}")
            return []

    def get_latest_articles(self, limit: int = 50) -> List[Dict]:
        """
        Obtener artículos más recientes

        Args:
            limit: Cantidad de artículos

        Returns:
            Lista de artículos
        """
        try:
            query = (
                self.db.collection(self.collection)
                .order_by("processed_date", direction=firestore.Query.DESCENDING)
                .limit(limit)
            )

            docs = query.stream()
            articles = []
            for doc in docs:
                articles.append({"id": doc.id, **doc.to_dict()})

            return articles

        except Exception as e:
            logger.warning(f"Error obteniendo artículos recientes: {e}")
            return []

    def update_status(self, doc_id: str, status: str) -> bool:
        """
        Actualizar estado de procesamiento

        Args:
            doc_id: ID del documento
            status: Nuevo estado

        Returns:
            True si se actualizó
        """
        try:
            self.db.collection(self.collection).document(doc_id).update(
                {"status": status, "status_date": datetime.now()}
            )
            logger.info(f"Estado actualizado para {doc_id}: {status}")
            return True

        except Exception as e:
            logger.error(f"Error actualizando estado: {e}")
            return False

    def bulk_save_articles(self, articles: List[Dict]) -> int:
        """
        Guardar múltiples artículos en batch

        Args:
            articles: Lista de artículos

        Returns:
            Cantidad guardada
        """
        batch = self.db.batch()
        count = 0

        try:
            for article in articles:
                article["processed_date"] = datetime.now()
                doc_ref = self.db.collection(self.collection).document()
                batch.set(doc_ref, article)
                count += 1

                # Firestore tiene límite de 500 operaciones por batch
                if count % 500 == 0:
                    batch.commit()
                    batch = self.db.batch()

            # Guardar lo que quede
            batch.commit()
            logger.info(f"Guardados {count} artículos en batch")
            return count

        except Exception as e:
            logger.error(f"Error en batch save: {e}")
            return count

    def get_article_by_id(self, doc_id: str) -> Optional[Dict]:
        """
        Obtener artículo específico

        Args:
            doc_id: ID del documento

        Returns:
            Datos del artículo o None
        """
        try:
            doc = self.db.collection(self.collection).document(doc_id).get()
            if doc.exists:
                return {"id": doc.id, **doc.to_dict()}
            return None

        except Exception as e:
            logger.warning(f"Error obteniendo artículo: {e}")
            return None

    def search_articles(self, keyword: str) -> List[Dict]:
        """
        Buscar artículos por palabra clave (búsqueda simple)

        Args:
            keyword: Palabra a buscar

        Returns:
            Lista de artículos coincidentes
        """
        try:
            # Nota: Para búsqueda completa de texto, Firestore requiere Algolia o Elasticsearch
            # Esta es una búsqueda simple en campo title
            query = self.db.collection(self.collection).where(
                "title", ">=", keyword
            ).where("title", "<", keyword + "~")

            docs = query.stream()
            articles = []
            for doc in docs:
                articles.append({"id": doc.id, **doc.to_dict()})

            return articles

        except Exception as e:
            logger.warning(f"Error buscando artículos: {e}")
            return []

    def get_statistics(self) -> Dict:
        """
        Obtener estadísticas de noticias almacenadas

        Returns:
            Dict con estadísticas
        """
        try:
            all_docs = self.db.collection(self.collection).stream()

            sources = {}
            total = 0

            for doc in all_docs:
                total += 1
                data = doc.to_dict()
                source = data.get("source", "Unknown")
                sources[source] = sources.get(source, 0) + 1

            return {
                "total_articles": total,
                "by_source": sources,
                "timestamp": datetime.now(),
            }

        except Exception as e:
            logger.warning(f"Error obteniendo estadísticas: {e}")
            return {}

    def delete_all_articles(self) -> int:
        """
        Borrar TODAS las noticias de la colección (limpieza diaria)

        Returns:
            Cantidad de artículos eliminados
        """
        try:
            all_docs = self.db.collection(self.collection).stream()
            batch = self.db.batch()
            count = 0

            for doc in all_docs:
                batch.delete(doc.reference)
                count += 1

                # Firestore tiene límite de 500 operaciones por batch
                if count % 500 == 0:
                    batch.commit()
                    batch = self.db.batch()

            # Borrar lo que quede
            batch.commit()
            logger.info(f"Se borraron {count} artículos de Firestore")
            return count

        except Exception as e:
            logger.error(f"Error borrando artículos: {e}")
            return 0
