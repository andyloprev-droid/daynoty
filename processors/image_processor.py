"""
Image Processor - Procesar y subir imágenes a Google Cloud
"""
import logging
import io
import os
import hashlib
import textwrap
from typing import Optional, Tuple
from datetime import datetime, timedelta
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
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

    def optimize_image(self, image_bytes: bytes, target_size: int = 1080) -> Optional[bytes]:
        """
        Optimizar imagen a formato cuadrado 1:1 de tamaño fijo (1080x1080 por defecto).

        - Si la imagen es más pequeña, la upscala con LANCZOS.
        - Si es más grande, la downscala.
        - Siempre aplica center-crop a 1:1.

        Args:
            image_bytes: Bytes de la imagen original
            target_size: Tamaño final del lado (px)

        Returns:
            Bytes de la imagen optimizada 1:1
        """
        try:
            img = Image.open(io.BytesIO(image_bytes))

            # Convertir a RGB si tiene alpha channel o es paleta
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")

            orig_w, orig_h = img.size

            # 1) Redimensionar para que el lado MENOR iguale target_size
            #    Esto asegura que podemos recortar al cuadrado sin barras.
            scale = target_size / min(orig_w, orig_h)
            new_w = int(round(orig_w * scale))
            new_h = int(round(orig_h * scale))
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # 2) Center-crop a cuadrado target_size x target_size
            left = (new_w - target_size) // 2
            top = (new_h - target_size) // 2
            img = img.crop((left, top, left + target_size, top + target_size))

            # Guardar como JPEG de alta calidad
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=90, optimize=True)
            optimized_bytes = output.getvalue()

            if len(optimized_bytes) > self.max_size:
                output = io.BytesIO()
                img.save(output, format="JPEG", quality=75, optimize=True)
                optimized_bytes = output.getvalue()

            logger.debug(
                f"Imagen 1:1 {target_size}x{target_size}: "
                f"{orig_w}x{orig_h} → {len(optimized_bytes)} bytes"
            )
            return optimized_bytes

        except Exception as e:
            logger.error(f"Error optimizando imagen: {e}")
            return None

    @staticmethod
    def _wrap_text_by_pixels(text: str, font, max_width_px: int, draw) -> list:
        """
        Wrap de texto por píxeles reales (no por caracteres).
        Garantiza que cada línea quepa en max_width_px con la fuente dada.
        No trunca: devuelve todas las palabras, aunque sean muchas líneas.
        """
        words = text.split()
        if not words:
            return []
        lines = []
        current = words[0]
        for w in words[1:]:
            tentative = current + " " + w
            bbox = draw.textbbox((0, 0), tentative, font=font)
            if (bbox[2] - bbox[0]) <= max_width_px:
                current = tentative
            else:
                lines.append(current)
                current = w
        lines.append(current)
        return lines

    @staticmethod
    def _find_font(bold: bool = True) -> Optional[str]:
        """Buscar fuente sans-serif bold disponible."""
        if bold:
            candidates = [
                "C:/Windows/Fonts/arialbd.ttf",
                "C:/Windows/Fonts/ariblk.ttf",
                "C:/Windows/Fonts/seguisb.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            ]
        else:
            candidates = [
                "C:/Windows/Fonts/arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ]
        for path in candidates:
            try:
                ImageFont.truetype(path, 20)
                return path
            except (OSError, IOError):
                continue
        return None

    def _make_gradient_bar(self, width: int, height: int) -> Image.Image:
        """Barra horizontal con gradiente azul (azul oscuro → azul brillante → azul oscuro)."""
        bar = Image.new("RGB", (width, height), (20, 50, 130))
        draw = ImageDraw.Draw(bar)
        bright_blue = (52, 120, 220)
        dark_blue = (15, 40, 110)
        for x in range(width):
            t = x / max(1, width - 1)
            t_mirror = abs(t - 0.5) * 2  # 1 en bordes, 0 en centro
            # Centro = azul brillante, bordes = azul oscuro
            r = int(bright_blue[0] + (dark_blue[0] - bright_blue[0]) * t_mirror)
            g = int(bright_blue[1] + (dark_blue[1] - bright_blue[1]) * t_mirror)
            b = int(bright_blue[2] + (dark_blue[2] - bright_blue[2]) * t_mirror)
            draw.line([(x, 0), (x, height)], fill=(r, g, b))
        return bar

    def _make_anti_dem_badge(self, size: int = 220) -> Image.Image:
        """Badge circular azul con burro Demócrata tachado por X roja."""
        # RGBA para transparencia fuera del círculo
        badge = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(badge)

        # Círculo azul Demócrata (#1F4FA0 aprox)
        blue = (31, 79, 160, 255)
        draw.ellipse([(0, 0), (size, size)], fill=blue)

        # "Burro" simplificado: cuerpo blanco con 3 estrellitas rojas pequeñas.
        # Como dibujar un burro realista con PIL es muy complejo, usamos una
        # silueta estilizada que evoque el logo demócrata.
        white = (255, 255, 255, 255)
        red_star = (199, 29, 58, 255)

        # Cuerpo del burro (cuerpo + cuello + cabeza simplificados)
        cx, cy = size // 2, size // 2
        s = size / 100.0  # factor de escala

        # Cuerpo (rectángulo redondeado)
        body_box = [
            (cx - 32 * s, cy - 5 * s),
            (cx + 28 * s, cy + 18 * s),
        ]
        draw.rounded_rectangle(body_box, radius=int(8 * s), fill=white)

        # Cabeza (círculo a la derecha)
        head_r = 14 * s
        head_cx = cx + 30 * s
        head_cy = cy - 5 * s
        draw.ellipse(
            [(head_cx - head_r, head_cy - head_r),
             (head_cx + head_r, head_cy + head_r)],
            fill=white,
        )
        # Hocico/orejas simplificadas (pequeño rectángulo arriba de cabeza)
        ear_w = 8 * s
        ear_h = 14 * s
        draw.rounded_rectangle(
            [(head_cx - ear_w / 2 - 2 * s, head_cy - head_r - ear_h + 2 * s),
             (head_cx + ear_w / 2 - 2 * s, head_cy - head_r + 4 * s)],
            radius=int(3 * s),
            fill=white,
        )

        # 4 patas (rectángulos verticales bajo el cuerpo)
        leg_w = 6 * s
        leg_h = 18 * s
        leg_y_top = cy + 16 * s
        for offset in (-26, -10, 6, 22):
            lx = cx + offset * s
            draw.rectangle(
                [(lx, leg_y_top), (lx + leg_w, leg_y_top + leg_h)],
                fill=white,
            )

        # Cola pequeña hacia atrás
        tail_box = [
            (cx - 38 * s, cy - 2 * s),
            (cx - 30 * s, cy + 10 * s),
        ]
        draw.rectangle(tail_box, fill=white)

        # 3 estrellitas rojas en el cuerpo (representan la bandera del logo)
        for sx in (-18, -4, 10):
            star_cx = cx + sx * s
            star_cy = cy + 6 * s
            r = 3 * s
            draw.ellipse(
                [(star_cx - r, star_cy - r), (star_cx + r, star_cy + r)],
                fill=red_star,
            )

        # X roja gigante encima de todo
        x_color = (220, 30, 40, 255)
        x_thickness = max(8, int(size * 0.07))
        margin = int(size * 0.12)
        draw.line(
            [(margin, margin), (size - margin, size - margin)],
            fill=x_color, width=x_thickness,
        )
        draw.line(
            [(size - margin, margin), (margin, size - margin)],
            fill=x_color, width=x_thickness,
        )

        return badge

    def add_title_overlay(self, image_bytes: bytes, title: str) -> Optional[bytes]:
        """
        Plantilla tipo redes sociales:
            ┌────────────────────────────────┐
            │                                │
            │           FOTO                 │   (top, ~56% alto)
            │                                │
            ├──[ gradiente rojo↔morado ]─────┤
            │           [BADGE]              │   (badge sobre la barra)
            ├────────────────────────────────┤
            │   TEXTO PREGUNTA NEGRO         │   (panel gris claro)
            │                                │
            └────────────────────────────────┘
        """
        # Si existe el marco MAGA, usar esa plantilla
        frame_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "assets", "frame.png",
        )
        if os.path.exists(frame_path):
            result = self._apply_frame_template(image_bytes, title, frame_path)
            if result:
                return result

        try:
            # ===== Dimensiones canónicas =====
            CANVAS_W = 1080
            PHOTO_MIN_H = 600   # altura minima de foto (rellena con padding si es muy ancha)
            PHOTO_MAX_H = 1500  # altura maxima de foto (recorte vertical solo si es muy alta)
            BAR_H = 40
            PANEL_H = 550
            BADGE_SIZE = 230
            PANEL_BG = (240, 239, 236)  # gris claro estilo papel

            # ===== 1) Foto: ajustar al ancho 1080, conservando proporcion =====
            photo = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            ow, oh = photo.size

            # WATERMARK STRIP: recortar zonas tipicas de marca de agua antes de escalar
            # - Borde inferior (4%): logos de canal, creditos de agencia (Getty, AP, Reuters)
            # - Esquina inferior derecha extra: muchas agencias ponen su logo ahi
            crop_bottom = int(oh * 0.04)
            if crop_bottom > 0:
                photo = photo.crop((0, 0, ow, oh - crop_bottom))
                ow, oh = photo.size

            # Escalar para que el ancho sea 1080
            scale = CANVAS_W / ow
            new_w = CANVAS_W
            new_h = int(round(oh * scale))
            photo = photo.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # Decidir altura final del area de foto
            if new_h < PHOTO_MIN_H:
                # Foto muy "panoramica" / corta: agregamos padding gris arriba y abajo
                # para llegar al minimo (asi el badge no queda muy arriba)
                photo_h = PHOTO_MIN_H
                pad_total = PHOTO_MIN_H - new_h
                pad_top = pad_total // 2
                photo_panel = Image.new("RGB", (CANVAS_W, photo_h), PANEL_BG)
                photo_panel.paste(photo, (0, pad_top))
                photo = photo_panel
            elif new_h > PHOTO_MAX_H:
                # Foto muy alta: center-crop vertical hasta el max
                top = (new_h - PHOTO_MAX_H) // 2
                photo = photo.crop((0, top, CANVAS_W, top + PHOTO_MAX_H))
                photo_h = PHOTO_MAX_H
            else:
                photo_h = new_h

            # ===== 2) Canvas final con altura dinamica =====
            CANVAS_H = photo_h + BAR_H + PANEL_H
            PHOTO_H = photo_h
            canvas = Image.new("RGB", (CANVAS_W, CANVAS_H), PANEL_BG)
            canvas.paste(photo, (0, 0))

            # ===== 3) Barra de gradiente =====
            bar = self._make_gradient_bar(CANVAS_W, BAR_H)
            canvas.paste(bar, (0, PHOTO_H))

            # ===== 4) Texto en el panel inferior (auto-fit) =====
            font_path = self._find_font(bold=True)
            usable_w = CANVAS_W - 80  # 40 px de padding a cada lado
            temp_draw = ImageDraw.Draw(canvas)

            # Buscar el font_size mas grande que quepa en <= 5 lineas
            font = None
            lines = []
            font_size = 64
            for candidate in range(72, 28, -2):
                try:
                    f = (ImageFont.truetype(font_path, candidate)
                         if font_path else ImageFont.load_default())
                except (OSError, IOError):
                    f = ImageFont.load_default()
                cand_lines = self._wrap_text_by_pixels(title, f, usable_w, temp_draw)
                # Estimar alto del texto
                lh = int(candidate * 1.18)
                total_h = lh * len(cand_lines)
                if len(cand_lines) <= 5 and total_h <= PANEL_H - 60:
                    font = f
                    font_size = candidate
                    lines = cand_lines
                    break
            if font is None:
                try:
                    font = (ImageFont.truetype(font_path, 32)
                            if font_path else ImageFont.load_default())
                except (OSError, IOError):
                    font = ImageFont.load_default()
                font_size = 32
                lines = self._wrap_text_by_pixels(title, font, usable_w, temp_draw)[:6]

            line_height = int(font_size * 1.18)
            total_text_h = line_height * len(lines)
            panel_top = PHOTO_H + BAR_H
            # Centrado vertical en el panel
            text_y = panel_top + (PANEL_H - total_text_h) // 2

            draw = ImageDraw.Draw(canvas)
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                tw = bbox[2] - bbox[0]
                # Alinear a la izquierda con padding de 40 px (estilo plantilla)
                x = 40
                # Si es muy corto, igual a la izquierda - mas natural
                draw.text((x, text_y), line, font=font, fill=(15, 15, 15))
                text_y += line_height

            # (Sin badge — diseño limpio sin marca de agua)

            output = io.BytesIO()
            canvas.save(output, format="JPEG", quality=92, optimize=True)

            logger.info(f"Plantilla aplicada: {title[:50]}")
            return output.getvalue()

        except Exception as e:
            logger.error(f"Error aplicando plantilla: {e}", exc_info=True)
            return image_bytes

    def _apply_frame_template(
        self, image_bytes: bytes, title: str, frame_path: str
    ) -> Optional[bytes]:
        """
        Plantilla con marco MAGA (1254x1254):
            ┌──────── MAKE AMERICA GREAT AGAIN ────────┐
            │   ┌──────────────────────────────┐       │
            │   │            FOTO              │       │  (completa, sin recorte)
            │   └──────────────────────────────┘       │
            │   TEXTO PREGUNTA (azul marino)           │
            └──────────────────────────────────────────┘
        """
        try:
            canvas = Image.open(frame_path).convert("RGB")
            W, H = canvas.size

            # Area util dentro del marco (debajo del logo, dentro de las lineas rojas)
            LEFT, RIGHT = 70, W - 70
            TOP, BOTTOM = 160, H - 120
            BOX_W = RIGHT - LEFT
            PHOTO_MAX_H = 750
            BORDER = 6
            NAVY = (27, 45, 92)

            # ===== 1) Foto completa (contain) =====
            photo = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            ow, oh = photo.size
            crop_bottom = int(oh * 0.04)
            if crop_bottom > 0:
                photo = photo.crop((0, 0, ow, oh - crop_bottom))
                ow, oh = photo.size

            max_w = BOX_W - 2 * BORDER
            max_h = PHOTO_MAX_H - 2 * BORDER
            scale = min(max_w / ow, max_h / oh)
            pw, ph = int(ow * scale), int(oh * scale)
            photo = photo.resize((pw, ph), Image.Resampling.LANCZOS)

            px = LEFT + (BOX_W - pw) // 2
            py = TOP
            draw = ImageDraw.Draw(canvas)
            draw.rectangle(
                [px - BORDER, py - BORDER, px + pw + BORDER - 1, py + ph + BORDER - 1],
                fill=NAVY,
            )
            canvas.paste(photo, (px, py))

            # ===== 2) Texto debajo de la foto (auto-fit) =====
            text_top = py + ph + BORDER + 22
            text_area_h = BOTTOM - text_top
            font_path = self._find_font(bold=True)

            font, lines, font_size = None, [], 32
            for candidate in range(68, 26, -2):
                try:
                    f = (ImageFont.truetype(font_path, candidate)
                         if font_path else ImageFont.load_default())
                except (OSError, IOError):
                    f = ImageFont.load_default()
                cand = self._wrap_text_by_pixels(title, f, BOX_W, draw)
                if int(candidate * 1.18) * len(cand) <= text_area_h and len(cand) <= 6:
                    font, lines, font_size = f, cand, candidate
                    break
            if font is None:
                try:
                    font = (ImageFont.truetype(font_path, 28)
                            if font_path else ImageFont.load_default())
                except (OSError, IOError):
                    font = ImageFont.load_default()
                font_size = 28
                lines = self._wrap_text_by_pixels(title, font, BOX_W, draw)[:6]

            line_h = int(font_size * 1.18)
            y = text_top + max(0, (text_area_h - line_h * len(lines)) // 2)
            for line in lines:
                draw.text((LEFT, y), line, font=font, fill=NAVY)
                y += line_h

            output = io.BytesIO()
            canvas.save(output, format="JPEG", quality=92, optimize=True)
            logger.info(f"Plantilla marco aplicada: {title[:50]}")
            return output.getvalue()

        except Exception as e:
            logger.error(f"Error aplicando marco: {e}", exc_info=True)
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

            # Generar signed URL (válido por 7 días)
            try:
                url = blob.generate_signed_url(
                    version="v4",
                    expiration=timedelta(days=7),
                    method="GET"
                )
            except Exception as e:
                # Si falla signed URL, intentar hacer público
                logger.debug(f"Error generando signed URL: {e}")
                try:
                    blob.make_public()
                    url = blob.public_url
                except:
                    # Fallback: URL directa (puede no funcionar sin autenticación)
                    url = f"https://storage.googleapis.com/{self.bucket.name}/{blob_path}"

            logger.info(f"Imagen subida a {url}")
            return url

        except Exception as e:
            logger.error(f"Error subiendo imagen a Cloud Storage: {e}")
            return None

    def process_and_upload(
        self, image_url: str, source_name: str, title: Optional[str] = None
    ) -> Optional[str]:
        """
        Proceso completo: descargar → validar → optimizar → agregar titulo → subir

        Args:
            image_url: URL de la imagen original
            source_name: Nombre de la fuente (para carpeta)
            title: Titulo opcional para incrustar en la imagen

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

        # Si vamos a aplicar plantilla, NO recortamos a cuadrado: la plantilla
        # se encarga de respetar la proporcion original. Solo optimizamos si
        # NO hay titulo (uso aislado de la imagen).
        if title:
            optimized = self.add_title_overlay(image_bytes, title)
        else:
            optimized = self.optimize_image(image_bytes)
            if not optimized:
                return None

        # Obtener nombre de archivo
        filename = image_url.split("/")[-1].split("?")[0][:50]
        if not filename.endswith((".jpg", ".jpeg", ".png", ".webp")):
            filename += ".jpg"

        # Subir
        return self.upload_to_cloud(optimized, filename, folder=f"original_images/{source_name}")
