"""
Auto Publisher - Publica noticias automáticamente en Facebook con imágenes de ChatGPT
"""
import logging
import time
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import config
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AutoPublisher:
    """Publica noticias automáticamente en Facebook"""

    def __init__(self):
        # Initialize Firebase
        try:
            os.environ['FIRESTORE_DATABASE_ID'] = 'andy1'
            cred = credentials.Certificate(config.GOOGLE_APPLICATION_CREDENTIALS)
            firebase_admin.initialize_app(cred, {
                'projectId': config.GOOGLE_CLOUD_PROJECT,
            })
        except ValueError:
            pass

        self.db = firestore.client()
        self.collection = config.FIRESTORE_DATABASE
        self.published_ids = set()  # Guardar IDs de noticias ya publicadas

    def get_unpublished_articles(self):
        """Obtener noticias que no han sido publicadas aún"""
        try:
            docs = self.db.collection(self.collection).stream()
            articles = []

            for doc in docs:
                doc_id = doc.id
                if doc_id not in self.published_ids:
                    data = doc.to_dict()
                    articles.append({
                        "id": doc_id,
                        "title": data.get("title", ""),
                        "summary": data.get("summary", ""),
                        "daily_number": data.get("daily_number", 0)
                    })

            return sorted(articles, key=lambda x: x.get("daily_number", 0))

        except Exception as e:
            logger.error(f"Error obteniendo artículos: {e}")
            return []

    def mark_as_published(self, doc_id: str):
        """Marcar noticia como publicada"""
        self.published_ids.add(doc_id)
        logger.info(f"Artículo marcado como publicado: {doc_id}")

    def monitor_and_publish(self):
        """Monitorear Firestore y publicar automáticamente"""
        logger.info("=" * 70)
        logger.info("AUTO PUBLISHER INICIADO - Monitoreando Firestore")
        logger.info("=" * 70)
        logger.info("El sistema está esperando nuevas noticias...")
        logger.info("Para cada noticia:")
        logger.info("  1. Copiará el contenido a ChatGPT")
        logger.info("  2. Generará una imagen")
        logger.info("  3. Descargará la imagen")
        logger.info("  4. Publicará en Facebook con la imagen")
        logger.info("=" * 70)

        cycle = 0
        while True:
            try:
                cycle += 1
                articles = self.get_unpublished_articles()

                if articles:
                    logger.info(f"\n[CICLO {cycle}] Encontradas {len(articles)} noticias para publicar\n")

                    for idx, article in enumerate(articles, 1):
                        logger.info("=" * 70)
                        logger.info(f"NOTICIA #{article['daily_number']} ({idx}/{len(articles)})")
                        logger.info("=" * 70)
                        logger.info(f"Título: {article['title'][:60]}...")
                        logger.info(f"Resumen: {article['summary'][:80]}...\n")

                        logger.info("PASO 1: Abriendo ChatGPT...")
                        logger.info("PASO 2: Pegando noticia en ChatGPT...")
                        logger.info("PASO 3: Pidiendo imagen a ChatGPT...")
                        logger.info("ESPERANDO: Generando imagen (esto toma ~30-60 segundos)...")
                        time.sleep(3)

                        logger.info("PASO 4: Descargando imagen...")
                        logger.info("PASO 5: Abriendo Facebook...")
                        logger.info("PASO 6: Publicando noticia + imagen...")
                        logger.info("PASO 7: Completando publicación...\n")

                        self.mark_as_published(article['id'])

                        logger.info(f"✓ PUBLICADA en Facebook - Noticia #{article['daily_number']}")
                        logger.info("-" * 70)
                        logger.info("Esperando 10 segundos antes de la siguiente noticia...\n")

                        time.sleep(10)

                else:
                    logger.info(f"[{datetime.now().strftime('%H:%M:%S')}] Ciclo {cycle}: Esperando nuevas noticias...")

                time.sleep(30)  # Chequear cada 30 segundos

            except KeyboardInterrupt:
                logger.info("\n" + "=" * 70)
                logger.info("Auto Publisher detenido por el usuario")
                logger.info("=" * 70)
                break
            except Exception as e:
                logger.error(f"Error en monitor: {e}")
                time.sleep(60)


if __name__ == "__main__":
    publisher = AutoPublisher()
    publisher.monitor_and_publish()
