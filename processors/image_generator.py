"""
Image Generator - Generar imágenes con DALL-E
"""
import logging
from typing import Optional
import requests
from openai import OpenAI
import config

logger = logging.getLogger(__name__)


class ImageGenerator:
    """Generar imágenes con OpenAI DALL-E basadas en noticias"""

    def __init__(self):
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.DALL_E_MODEL
        self.size = config.DALL_E_SIZE
        self.quality = config.DALL_E_QUALITY

    def generate_image_from_news(
        self, title: str, summary: str, original_image_url: Optional[str] = None
    ) -> Optional[str]:
        """
        Generar imagen con DALL-E basada en noticia

        Args:
            title: Título de la noticia
            summary: Resumen/descripción
            original_image_url: URL de imagen original para referencia

        Returns:
            URL de la imagen generada o None
        """
        try:
            prompt = self._create_prompt(title, summary)

            # Si hay imagen original, usar vision para referencia
            if original_image_url:
                image_url = self._generate_with_reference(prompt, original_image_url)
            else:
                image_url = self._generate_without_reference(prompt)

            if image_url:
                logger.info(f"Imagen generada para: {title[:50]}")
                return image_url
            else:
                logger.warning(f"No se pudo generar imagen para: {title[:50]}")
                return None

        except Exception as e:
            logger.error(f"Error generando imagen con DALL-E: {e}")
            return None

    def _create_prompt(self, title: str, summary: str) -> str:
        """Crear prompt para DALL-E"""

        # Limitar resumen
        summary_excerpt = summary[:200]

        return f"""Crea una imagen profesional e informativa en formato CUADRADO (1:1) que represente esta noticia:

TÍTULO: {title}

DESCRIPCIÓN: {summary_excerpt}

Requisitos:
- Estilo moderno y profesional para noticias
- Formato cuadrado (1:1)
- Incluye elementos visuales relevantes al tema
- Colores vibrantes pero profesionales
- Sin texto en la imagen
- Alta calidad y resolución
- Apto para visualización en redes sociales

NO incluyas:
- Personas específicas identificables
- Logos de marcas
- Texto
- Watermarks"""

    def _generate_with_reference(
        self, prompt: str, original_image_url: str
    ) -> Optional[str]:
        """
        Generar imagen usando referencia visual (vision)

        Para DALL-E-3 con referencia, combinamos el prompt con descripción
        de la imagen original
        """
        try:
            # Crear prompt mejorado con contexto visual
            enhanced_prompt = (
                f"{prompt}\n\n"
                f"Utiliza como inspiración visual esta imagen: {original_image_url}\n"
                f"(Usa solo el estilo y contexto visual, no reproduzcas la imagen)"
            )

            response = self.client.images.generate(
                model=self.model,
                prompt=enhanced_prompt,
                size=self.size,
                quality=self.quality,
                n=1,
            )

            if response.data and len(response.data) > 0:
                return response.data[0].url

        except Exception as e:
            logger.warning(f"Error generando con referencia: {e}")

        # Fallback a generación sin referencia
        return self._generate_without_reference(prompt)

    def _generate_without_reference(self, prompt: str) -> Optional[str]:
        """
        Generar imagen sin referencia visual
        """
        try:
            response = self.client.images.generate(
                model=self.model,
                prompt=prompt,
                size=self.size,
                quality=self.quality,
                n=1,
            )

            if response.data and len(response.data) > 0:
                return response.data[0].url

        except Exception as e:
            logger.error(f"Error generando imagen: {e}")

        return None

    def download_and_save_image(self, image_url: str, filepath: str) -> bool:
        """
        Descargar y guardar imagen generada localmente

        Args:
            image_url: URL de la imagen
            filepath: Ruta local donde guardar

        Returns:
            True si se guardó exitosamente
        """
        try:
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()

            with open(filepath, "wb") as f:
                f.write(response.content)

            logger.info(f"Imagen guardada en: {filepath}")
            return True

        except Exception as e:
            logger.error(f"Error descargando imagen: {e}")
            return False
