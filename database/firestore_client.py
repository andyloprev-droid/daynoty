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
        Guardar artículo procesado en Firestore

        Args:
            article_data: Dict con datos del artículo

        Returns:
            ID del documento guardado
        """
        try:
            # Agregar timestamp de procesamiento
            article_data["processed_date"] = datetime.now()

            # Guardar en Firestore
            doc_ref = self.db.collection(self.collection).add(article_data)
            doc_id = doc_ref[1].id

            logger.info(f"Artículo guardado en Firestore: {doc_id}")
            return doc_id

        except Exception as e:
            logger.error(f"Error guardando artículo en Firestore: {e}")
            return None

    def check_duplicate(self, url: str) -> bool:
        """
        Verificar si noticia ya fue procesada

        Args:
            url: URL de la noticia

        Returns:
            True si ya existe
        """
        try:
            query = self.db.collection(self.collection).where(
                "url_source", "==", url
            ).limit(1)

            docs = query.stream()
            return len(list(docs)) > 0

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
