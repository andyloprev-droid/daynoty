"""
Image Processor - Procesar y subir imágenes a Google Cloud
"""
import logging
import io
import hashlib
from typing import Optional, Tuple
from datetime import datetime
import requests
from PIL import Image
from google.cloud import storage
import config

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Procesar y subir imágenes a Google Cloud Storage"""

    def __init__(self):
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(config.CLOUD_STORAGE_BUCKET)
        self.max_size = 5 * 1024 * 1024  # 5MB
        self.allowed_formats = {"PNG", "JPEG", "WEBP"}

    def download_image(self, url: str, timeout: int = 10) -> Optional[bytes]:
        """
        Descargar imagen desde URL

        Args:
            url: URL de la imagen
            timeout: Timeout en segundos

        Returns:
            Bytes de la imagen o None si falla
        """
        if not url:
            return None

        try:
            response = requests.get(
                url,
                timeout=timeout,
                headers={"User-Agent": config.USER_AGENT},
            )
            response.raise_for_status()

            # Validar tamaño
            if len(response.content) > self.max_size:
                logger.warning(f"Imagen muy grande desde {url}: {len(response.content)} bytes")
                return None

            return response.content

        except requests.RequestException as e:
            logger.warning(f"Error descargando imagen desde {url}: {e}")
            return None

    def validate_image(self, image_bytes: bytes) -> bool:
        """
        Validar que sea una imagen válida

        Args:
            image_bytes: Bytes de la imagen

        Returns:
            True si es válida
        """
        try:
            img = Image.open(io.BytesIO(image_bytes))
            # Validar formato
            if img.format not in self.allowed_formats:
                logger.warning(f"Formato de imagen no soportado: {img.format}")
                return False
            return True
        except Exception as e:
            logger.warning(f"Error validando imagen: {e}")
            return False

    def optimize_image(self, image_bytes: bytes, max_width: int = 1200) -> Optional[bytes]:
        """
        Optimizar imagen (redimensionar, comprimir)

        Args:
            image_bytes: Bytes de la imagen original
            max_width: Ancho máximo en píxeles

        Returns:
            Bytes de la imagen optimizada
        """
        try:
            img = Image.open(io.BytesIO(image_bytes))

            # Redimensionar si es muy grande
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

            # Convertir a RGB si tiene alpha channel
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")

            # Guardar optimizado
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=85, optimize=True)
            optimized_bytes = output.getvalue()

            if len(optimized_bytes) > self.max_size:
                # Si sigue siendo muy grande, reducir calidad
                output = io.BytesIO()
                img.save(output, format="JPEG", quality=70, optimize=True)
                optimized_bytes = output.getvalue()

            logger.debug(
                f"Imagen optimizada: {len(image_bytes)} → {len(optimized_bytes)} bytes"
            )
            return optimized_bytes

        except Exception as e:
            logger.error(f"Error optimizando imagen: {e}")
            return None

    def upload_to_cloud(
        self, image_bytes: bytes, filename: str, folder: str = "original_images"
    ) -> Optional[str]:
        """
        Subir imagen a Google Cloud Storage

        Args:
            image_bytes: Bytes de la imagen
            filename: Nombre del archivo
            folder: Carpeta en el bucket

        Returns:
            URL pública de la imagen o None si falla
        """
        try:
            # Crear nombre de archivo único
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            hash_suffix = hashlib.md5(image_bytes[:100]).hexdigest()[:8]
            blob_path = f"{folder}/{timestamp}_{hash_suffix}_{filename}"

            # Subir a Cloud Storage
            blob = self.bucket.blob(blob_path)
            blob.upload_from_string(image_bytes, content_type="image/jpeg")

            # Hacer público
            blob.make_public()

            url = blob.public_url
            logger.info(f"Imagen subida a {url}")
            return url

        except Exception as e:
            logger.error(f"Error subiendo imagen a Cloud Storage: {e}")
            return None

    def process_and_upload(
        self, image_url: str, source_name: str
    ) -> Optional[str]:
        """
        Proceso completo: descargar → validar → optimizar → subir

        Args:
            image_url: URL de la imagen original
            source_name: Nombre de la fuente (para carpeta)

        Returns:
            URL de la imagen en Cloud Storage o None
        """
        if not image_url:
            return None

        # Descargar
        image_bytes = self.download_image(image_url)
        if not image_bytes:
            return None

        # Validar
        if not self.validate_image(image_bytes):
            return None

        # Optimizar
        optimized = self.optimize_image(image_bytes)
        if not optimized:
            return None

        # Obtener nombre de archivo
        filename = image_url.split("/")[-1].split("?")[0][:50]  # Primeros 50 caracteres
        if not filename.endswith((".jpg", ".jpeg", ".png", ".webp")):
            filename += ".jpg"

        # Subir
        return self.upload_to_cloud(optimized, filename, folder=f"original_images/{source_name}")
