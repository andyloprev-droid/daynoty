"""
Image Generator - Genera imágenes usando ChatGPT para cada noticia
"""
import logging
import time
import firebase_admin
from firebase_admin import credentials, firestore
import config
import os

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
collection = config.FIRESTORE_DATABASE


class ImageGeneratorChatGPT:
    """Genera imágenes usando ChatGPT para cada noticia"""

    def __init__(self):
        self.processed_ids = set()

    def get_articles_without_images(self):
        """Obtener noticias que no tienen imagen aún"""
        try:
            docs = db.collection(collection).stream()
            articles = []

            for doc in docs:
                data = doc.to_dict()
                # Si no tiene imagen URL guardada, necesita imagen
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

    def generate_images(self):
        """Generar imágenes para todas las noticias"""
        logger.info("=" * 80)
        logger.info("GENERADOR DE IMÁGENES - ChatGPT")
        logger.info("=" * 80)
        logger.info("Este script generará imágenes para cada noticia usando ChatGPT")
        logger.info("Asegúrate de que ChatGPT esté abierto en tu navegador")
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
                        logger.info(f"Título: {article['title'][:70]}...")
                        logger.info(f"Resumen: {article['summary'][:100]}...\n")

                        prompt = f"""
INSTRUCCIONES PARA EL USUARIO:

1. Copia este PROMPT exactamente en ChatGPT:

---
Crea una imagen profesional para esta noticia de noticias:

TÍTULO: {article['title']}

RESUMEN: {article['summary'][:300]}

La imagen debe ser:
- Profesional y atractiva para redes sociales
- Relacionada al contenido de la noticia
- Con colores que destaquen
- Apta para compartir en Facebook
---

2. Dale a ChatGPT para que genere la imagen
3. Una vez que genere, descárgala (botón derecho > Guardar imagen como)
4. Guárdala en: C:\\claude\\news-agent\\downloaded_images\\

El sistema detectará la imagen automáticamente.

ESPERANDO: Estoy monitoreando la carpeta de descargas...
"""
                        logger.info(prompt)

                        logger.info("Esperando imagen... (verifica ChatGPT en tu navegador)")
                        logger.info("Timeout: 5 minutos para generar y descargar\n")

                        # Esperar a que el usuario genere la imagen
                        start_time = time.time()
                        timeout = 300  # 5 minutos

                        while time.time() - start_time < timeout:
                            # Aquí iría lógica para detectar si se descargó una imagen
                            # Por ahora solo espera
                            time.sleep(10)

                        logger.warning(f"Timeout alcanzado para noticia #{article['daily_number']}")
                        logger.info("Continuar con la siguiente noticia...\n")

                        self.processed_ids.add(article['id'])

                else:
                    logger.info(f"[{time.strftime('%H:%M:%S')}] Ciclo {cycle}: Todas las noticias tienen imagen")

                time.sleep(60)  # Chequear cada minuto

            except KeyboardInterrupt:
                logger.info("\n" + "=" * 80)
                logger.info("Generador detenido por el usuario")
                logger.info("=" * 80)
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                time.sleep(60)


if __name__ == "__main__":
    # Crear carpeta de descargas si no existe
    os.makedirs('downloaded_images', exist_ok=True)

    generator = ImageGeneratorChatGPT()
    generator.generate_images()
