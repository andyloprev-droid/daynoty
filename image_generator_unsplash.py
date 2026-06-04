"""
Image Generator - Obtiene imágenes gratis de Unsplash basadas en el contenido de cada noticia
"""
import logging
import time
import firebase_admin
from firebase_admin import credentials, firestore, storage
import config
import os
import requests
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Firebase
try:
    os.environ['FIRESTORE_DATABASE_ID'] = 'andy1'
    cred = credentials.Certificate(config.GOOGLE_APPLICATION_CREDENTIALS)
    firebase_admin.initialize_app(cred, {
        'projectId': config.GOOGLE_CLOUD_PROJECT,
    })
except ValueError:
    pass

db = firestore.client()
storage_bucket = storage.bucket(config.CLOUD_STORAGE_BUCKET)
collection = config.FIRESTORE_DATABASE

# Unsplash API (sin clave - limitado pero funciona)
UNSPLASH_API_URL = "https://api.unsplash.com/search/photos"
UNSPLASH_API_KEY = ""  # Usar endpoint sin autenticación para búsquedas simples


class ImageGeneratorUnsplash:
    """Obtiene imágenes de Unsplash para cada noticia"""

    def __init__(self):
        self.processed_ids = set()

    def get_articles_without_images(self):
        """Obtener noticias que no tienen imagen aún"""
        try:
            docs = db.collection(collection).stream()
            articles = []

            for doc in docs:
                data = doc.to_dict()
                # Si no tiene imagen URL guardada
                if not data.get('cloud_image_url') and doc.id not in self.processed_ids:
                    articles.append({
                        'id': doc.id,
                        'title': data.get('title', ''),
                        'summary': data.get('summary', ''),
                        'daily_number': data.get('daily_number', 0)
                    })

            return sorted(articles, key=lambda x: x['daily_number'])

        except Exception as e:
            logger.error(f"Error obteniendo artículos: {e}")
            return []

    def extract_keywords(self, title, summary):
        """Extraer palabras clave para buscar imagen"""
        # Palabras comunes a ignorar
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                      'of', 'with', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                      'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                      'could', 'should', 'may', 'might', 'must', 'can', 'that', 'this',
                      'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'}

        # Combinar título y resumen
        text = (title + " " + summary).lower()

        # Dividir en palabras y filtrar
        words = text.split()
        keywords = [w.replace(',', '').replace('.', '').replace('!', '').replace('?', '')
                   for w in words
                   if w.lower() not in stop_words and len(w) > 3]

        # Retornar las primeras palabras significativas
        return ' '.join(keywords[:3]) if keywords else title[:30]

    def search_image(self, keywords):
        """Buscar imagen usando Unsplash o Pexels"""
        # Primero intentar Pexels (más confiable sin autenticación)
        image_url = self.search_pexels_image(keywords)
        if image_url:
            return image_url

        # Fallback a Unsplash
        return self.search_unsplash_image(keywords)

    def search_pexels_image(self, keywords):
        """Buscar en Pexels (API abierta, muy confiable)"""
        try:
            # Pexels tiene endpoint público sin autenticación para búsquedas simples
            url = "https://www.pexels.com/api/v2/search"
            # Usar headers para simular navegador
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            params = {
                'query': keywords,
                'per_page': 1
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                photos = data.get('photos', [])

                if photos:
                    photo = photos[0]
                    image_url = photo['src']['large']
                    logger.info(f"✓ Imagen encontrada en Pexels")
                    return image_url

        except Exception as e:
            logger.warning(f"Pexels no disponible: {str(e)[:50]}")

        return None

    def search_unsplash_image(self, keywords):
        """Buscar imagen en Unsplash como fallback"""
        try:
            url = "https://api.unsplash.com/search/photos"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            params = {
                'query': keywords,
                'per_page': 1,
                'order_by': 'relevant',
                'client_id': 'YOUR_UNSPLASH_KEY'  # Sin key, funcionará con restricciones
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])

                if results:
                    photo = results[0]
                    if 'urls' in photo:
                        image_url = photo['urls'].get('regular') or photo['urls'].get('small')
                        logger.info(f"✓ Imagen encontrada en Unsplash")
                        return image_url

        except Exception as e:
            logger.warning(f"Unsplash no disponible: {str(e)[:50]}")

        return None

    def upload_image_to_cloud(self, image_url, article_id):
        """Descargar imagen y subirla a Google Cloud Storage"""
        try:
            # Descargar imagen
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()

            # Nombre del archivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"article_images/unsplash_{timestamp}_{article_id[:8]}.jpg"

            # Subir a Cloud Storage
            blob = storage_bucket.blob(filename)
            blob.upload_from_string(response.content, content_type='image/jpeg')

            # Hacer URL pública
            try:
                blob.make_public()
                cloud_url = blob.public_url
            except:
                # Si no funciona make_public, construir URL manual
                cloud_url = f"https://storage.googleapis.com/{config.CLOUD_STORAGE_BUCKET}/{filename}"

            logger.info(f"✓ Imagen guardada en Cloud: {cloud_url[:60]}...")
            return cloud_url

        except Exception as e:
            logger.error(f"Error subiendo imagen: {e}")
            return None

    def update_article_with_image(self, article_id, image_url):
        """Actualizar documento en Firestore con URL de imagen"""
        try:
            db.collection(collection).document(article_id).update({
                'cloud_image_url': image_url,
                'image_source': 'unsplash',
                'image_updated': datetime.now()
            })
            logger.info(f"✓ Firestore actualizado con imagen")
            return True

        except Exception as e:
            logger.error(f"Error actualizando Firestore: {e}")
            return False

    def generate_images(self):
        """Generar imágenes para todas las noticias"""
        logger.info("=" * 80)
        logger.info("GENERADOR DE IMÁGENES - UNSPLASH (GRATIS)")
        logger.info("=" * 80)
        logger.info("Este script obtiene imágenes profesionales GRATIS de Unsplash")
        logger.info("Para cada noticia:")
        logger.info("  1. Extrae palabras clave del título y resumen")
        logger.info("  2. Busca imagen relacionada en Unsplash")
        logger.info("  3. La guarda en Google Cloud Storage")
        logger.info("  4. El dashboard la muestra automáticamente")
        logger.info("=" * 80)

        cycle = 0
        while True:
            try:
                cycle += 1
                articles = self.get_articles_without_images()

                if articles:
                    logger.info(f"\n[CICLO {cycle}] Encontradas {len(articles)} noticias sin imagen\n")

                    for idx, article in enumerate(articles, 1):
                        logger.info("=" * 80)
                        logger.info(f"GENERANDO IMAGEN - Noticia #{article['daily_number']} ({idx}/{len(articles)})")
                        logger.info("=" * 80)
                        logger.info(f"Título: {article['title']}")
                        logger.info(f"Resumen: {article['summary'][:150]}...\n")

                        # Extraer palabras clave
                        keywords = self.extract_keywords(article['title'], article['summary'])
                        logger.info(f"Palabras clave: {keywords}")

                        # Buscar imagen
                        logger.info("Buscando imagen...")
                        image_url = self.search_image(keywords)

                        if image_url:
                            # Subir a Cloud Storage
                            logger.info("Descargando y subiendo a Google Cloud...")
                            cloud_url = self.upload_image_to_cloud(image_url, article['id'])

                            if cloud_url:
                                # Actualizar Firestore
                                self.update_article_with_image(article['id'], cloud_url)
                                logger.info(f"✓ NOTICIA #{article['daily_number']} - IMAGEN COMPLETADA\n")
                            else:
                                logger.error(f"✗ Error subiendo imagen")
                        else:
                            logger.warning(f"✗ No se encontró imagen para esta noticia")

                        self.processed_ids.add(article['id'])
                        time.sleep(2)  # Respetar rate limit de Unsplash

                else:
                    logger.info(f"[{time.strftime('%H:%M:%S')}] Ciclo {cycle}: Todas las noticias tienen imagen")

                logger.info("Esperando 60 segundos antes de chequear nuevas noticias...")
                time.sleep(60)

            except KeyboardInterrupt:
                logger.info("\n" + "=" * 80)
                logger.info("Generador detenido por el usuario")
                logger.info("=" * 80)
                break
            except Exception as e:
                logger.error(f"Error en ciclo: {e}")
                time.sleep(60)


if __name__ == "__main__":
    generator = ImageGeneratorUnsplash()
    generator.generate_images()
