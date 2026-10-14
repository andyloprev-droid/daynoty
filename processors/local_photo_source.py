"""
Fuente local: fotos numeradas (1.jpg, 2.jpg, ...) en una carpeta del PC.

Para cada foto nueva:
1. GPT (vision) lee el texto de la imagen, dice donde esta y si ataca a un grupo protegido
2. Se recorta el texto y queda solo la foto
3. Se reescribe el mensaje (mismo sentido, otras palabras)
4. Se arma la imagen con el marco y se sube a Cloud Storage
5. Se escribe la descripcion y se guarda en Firestore (dashboard)
"""
import base64
import hashlib
import io
import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
from PIL import Image

import config
from database.firestore_client import NewsDatabase
from processors.content_processor import SYSTEM_PROMPT, ContentProcessor
from processors.image_processor import ImageProcessor

logger = logging.getLogger(__name__)

PROCESSED_FILE = "dashboard-processed.json"

ANALYZE_PROMPT = """You are analyzing a social media image that has a text caption/banner plus a photo or illustration.

Return ONLY a JSON object with these keys:
- "original_text": the exact caption text written on the image (empty string if none)
- "text_location": one of "top", "bottom", "none" (where the caption banner/box is)
- "photo_top_pct": number 0-100, approximate % from the top where the photo/illustration (without the caption) starts
- "photo_bottom_pct": number 0-100, approximate % from the top where the photo/illustration ends
- "targeted_group": who the caption criticizes or attacks, in a few words (e.g. "Democrats", "Muslims", "a suspect", "none").
- "targeted_group_type": exactly one of: "religion", "race", "ethnicity", "national_origin", "sexual_orientation", "gender", "disability", "political_party", "politician", "ideology", "government", "individual", "none". Judge the caption text only, not the appearance of people in the photo. Use "individual" for a specific person accused of something.
- "hate_reason": one short sentence explaining the criticism, or empty string.
- "rewritten_text": the caption rewritten with slightly different wording but the SAME message and tone, in English, max 160 characters, plain text, keep selective CAPS for 1-3 emphasis words if the original uses caps.
- "topic": one short sentence describing what the post is about."""

DESCRIPTION_INSTRUCTIONS = """This post comes from an image (an opinion meme), NOT a news article.
Write the caption about the topic below following your structure.
IMPORTANT: do not invent specific facts, statistics, names, dates, quotes or events that are not given here.
Keep it to general opinion and widely known context.
Never use another page's name (e.g. Raging Americans, Right Side Broadcasting) as a hashtag."""


class LocalPhotoSource:
    """Procesa fotos numeradas de una carpeta local y las sube al dashboard."""

    def __init__(self, folder: str):
        self.folder = folder
        self.work_dir = os.path.join(folder, "work")
        os.makedirs(self.work_dir, exist_ok=True)
        self.processed_path = os.path.join(self.work_dir, PROCESSED_FILE)
        self.content = ContentProcessor()
        self.images = ImageProcessor()
        self.db = NewsDatabase()

    # ---------- estado ----------
    def _load_processed(self) -> Dict:
        if os.path.exists(self.processed_path):
            with open(self.processed_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"items": {}}

    def _save_processed(self, state: Dict) -> None:
        tmp = self.processed_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.processed_path)

    def _numbered_photos(self) -> List[str]:
        files = []
        for name in os.listdir(self.folder):
            m = re.fullmatch(r"(\d+)\.(jpe?g|png|webp)", name, re.IGNORECASE)
            if m:
                files.append((int(m.group(1)), os.path.join(self.folder, name)))
        return [p for _, p in sorted(files)]

    # ---------- IA ----------
    def _analyze(self, image_bytes: bytes) -> Optional[Dict]:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img.thumbnail((1024, 1024))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode()
        try:
            resp = self.content.client.chat.completions.create(
                model=self.content.model,
                max_tokens=500,
                response_format={"type": "json_object"},
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": ANALYZE_PROMPT},
                        {"type": "image_url",
                         "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    ],
                }],
            )
            return json.loads(resp.choices[0].message.content)
        except Exception as e:
            logger.error(f"Error analizando imagen: {e}")
            return None

    def _describe(self, text: str, topic: str) -> Optional[str]:
        user_message = (
            f"{DESCRIPTION_INSTRUCTIONS}\n\n"
            f"Post message: {text}\nTopic: {topic}"
        )
        try:
            resp = self.content.client.chat.completions.create(
                model=self.content.model,
                max_tokens=self.content.max_tokens,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error escribiendo descripcion: {e}")
            return None

    PROTECTED_TYPES = {
        "religion", "race", "ethnicity", "national_origin",
        "sexual_orientation", "gender", "disability",
    }

    @classmethod
    def _attacks_protected_group(cls, info: Dict) -> bool:
        group_type = (info.get("targeted_group_type") or "none").strip().lower()
        return group_type in cls.PROTECTED_TYPES

    # ---------- recorte ----------
    @staticmethod
    def _row_uniformity(img: Image.Image) -> np.ndarray:
        """Fraccion de pixeles de cada fila que comparten el color dominante."""
        small = img.convert("RGB").resize((256, img.height))
        q = (np.asarray(small) // 32).astype(np.int32)
        codes = q[:, :, 0] * 64 + q[:, :, 1] * 8 + q[:, :, 2]
        out = np.empty(codes.shape[0])
        for y, row in enumerate(codes):
            out[y] = np.bincount(row, minlength=512).max() / row.size
        return out

    @staticmethod
    def _find_edge(uni: np.ndarray, limit: int) -> Optional[int]:
        """Desde el inicio de uni (lado del texto): los espacios entre renglones
        son filas casi de un solo color. Sigue esa cadena de espacios mientras
        aparezcan cerca unos de otros; donde se corta, empieza la foto."""
        n = len(uni)
        max_gap = int(0.15 * n)
        gaps = [y for y in range(min(limit, n)) if uni[y] >= 0.75]
        if not gaps or gaps[0] > max_gap:
            return None
        last = gaps[0]
        for y in gaps[1:]:
            if y - last > max_gap:
                break
            last = y
        return last + 1

    def _crop_photo(self, image_bytes: bytes, info: Dict) -> bytes:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        w, h = img.size
        loc = (info.get("text_location") or "none").lower()
        top, bottom = 0, h

        try:
            hint_top = int(float(info.get("photo_top_pct", 0)) / 100 * h)
            hint_bottom = int(float(info.get("photo_bottom_pct", 100)) / 100 * h)
        except (TypeError, ValueError):
            hint_top, hint_bottom = 0, h

        if loc in ("top", "bottom"):
            uni = self._row_uniformity(img)
            limit = int(0.7 * h)
            margin = int(0.01 * h)  # pasar el borde/linea del recuadro de texto
            if loc == "top":
                edge = self._find_edge(uni, limit)
                top = edge + margin if edge is not None else hint_top
            else:
                edge = self._find_edge(uni[::-1], limit)
                bottom = h - edge - margin if edge is not None else hint_bottom

        if bottom - top < 0.4 * h:
            logger.warning("Recorte sospechoso, uso la imagen completa")
            top, bottom = 0, h

        out = io.BytesIO()
        img.crop((0, top, w, bottom)).save(out, "JPEG", quality=95)
        return out.getvalue()

    # ---------- flujo ----------
    def process_new(self) -> Dict[str, int]:
        state = self._load_processed()
        stats = {"processed": 0, "skipped": 0, "failed": 0}

        for path in self._numbered_photos():
            with open(path, "rb") as f:
                data = f.read()
            sha = hashlib.sha256(data).hexdigest()
            if sha in state["items"]:
                continue

            name = os.path.basename(path)
            logger.info(f"Foto local nueva: {name}")
            info = self._analyze(data)
            if not info:
                stats["failed"] += 1
                continue

            if self._attacks_protected_group(info):
                reason = f"{info.get('targeted_group', '')}: {info.get('hate_reason', '')}"
                logger.info(f"{name}: descartada (ataca a un grupo protegido) - {reason}")
                state["items"][sha] = {"file": name, "status": "skipped_hate",
                                       "reason": reason,
                                       "at": datetime.now().isoformat()}
                self._save_processed(state)
                stats["skipped"] += 1
                continue

            text = (info.get("rewritten_text") or info.get("original_text") or "").strip()
            if not text:
                stats["failed"] += 1
                continue

            cropped = self._crop_photo(data, info)
            framed = self.images.add_title_overlay(cropped, text)
            image_url = self.images.upload_to_cloud(
                framed, f"{os.path.splitext(name)[0]}.jpg", folder="local_photos"
            )
            description = self._describe(text, info.get("topic", ""))
            if not image_url or not description:
                stats["failed"] += 1
                continue

            doc_id = self.db.save_article({
                "title": text,
                "summary": description,
                "facebook_caption": description,
                "published_to_facebook": False,
                "cloud_image_url": image_url,
                "url_source": f"local-photo:{sha}",
                "source_type": "local_photo",
            })
            if not doc_id:
                stats["failed"] += 1
                continue

            state["items"][sha] = {"file": name, "status": "uploaded", "doc_id": doc_id,
                                   "text": text, "at": datetime.now().isoformat()}
            self._save_processed(state)
            stats["processed"] += 1
            logger.info(f"{name}: subida al dashboard -> {text}")

        return stats
