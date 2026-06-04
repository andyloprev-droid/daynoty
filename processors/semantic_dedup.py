"""
Semantic Dedup - Detectar noticias duplicadas semánticamente usando TF-IDF + coseno.

Captura duplicados que el match exacto no detecta:
- "Trump wins Iowa caucus" vs "Donald Trump victorious in Iowa caucuses"
- Misma historia reportada por múltiples fuentes con titulares distintos
"""
import logging
from typing import List, Dict, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class SemanticDedup:
    """Detector de duplicados semánticos basado en TF-IDF + similitud coseno"""

    def __init__(self, similarity_threshold: float = 0.62):
        """
        Args:
            similarity_threshold: Umbral (0-1) arriba del cual dos textos se
                consideran el mismo artículo. 0.62 balancea precisión y recall
                para titulares de noticias con TF-IDF word + char n-grams.
        """
        self.threshold = similarity_threshold
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.matrix = None
        self.texts: List[str] = []

    @staticmethod
    def _build_doc(title: str, text: str = "") -> str:
        """Construir documento para vectorizar: título + primer párrafo."""
        title = (title or "").strip()
        snippet = (text or "")[:500].strip()
        # Dar más peso al título repitiéndolo
        return f"{title} {title} {snippet}".lower()

    def fit(self, items: List[Dict]) -> None:
        """
        Entrenar el vectorizador con los artículos ya existentes en BD.

        Args:
            items: lista de dicts con 'title' y opcionalmente 'text'/'summary'
        """
        self.texts = [
            self._build_doc(it.get("title", ""), it.get("text") or it.get("summary", ""))
            for it in items
        ]

        if not self.texts:
            self.vectorizer = None
            self.matrix = None
            return

        try:
            # char_wb n-grams capturan variaciones morfológicas
            # (wins/winning, caucus/caucuses) mejor que palabras enteras
            self.vectorizer = TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(3, 5),
                max_features=10000,
                min_df=1,
                lowercase=True,
                sublinear_tf=True,
            )
            self.matrix = self.vectorizer.fit_transform(self.texts)
            logger.info(
                f"SemanticDedup inicializado con {len(self.texts)} documentos existentes"
            )
        except Exception as e:
            logger.warning(f"Error entrenando SemanticDedup: {e}")
            self.vectorizer = None
            self.matrix = None

    def is_duplicate(self, title: str, text: str = "") -> bool:
        """
        Verificar si un artículo es semánticamente duplicado de alguno existente.

        Returns:
            True si existe un artículo con similitud >= threshold
        """
        if self.vectorizer is None or self.matrix is None or self.matrix.shape[0] == 0:
            return False

        try:
            doc = self._build_doc(title, text)
            vec = self.vectorizer.transform([doc])
            sims = cosine_similarity(vec, self.matrix)[0]
            max_sim = float(np.max(sims)) if sims.size > 0 else 0.0

            if max_sim >= self.threshold:
                idx = int(np.argmax(sims))
                logger.debug(
                    f"Dup semántico (sim={max_sim:.2f}): '{title[:50]}' "
                    f"≈ '{self.texts[idx][:50]}'"
                )
                return True
            return False
        except Exception as e:
            logger.debug(f"Error en is_duplicate: {e}")
            return False

    def add(self, title: str, text: str = "") -> None:
        """
        Agregar un artículo recién aceptado al índice para evitar duplicados
        dentro del mismo ciclo de procesamiento.
        """
        if self.vectorizer is None:
            # Primera adición: inicializar vectorizador
            self.fit([{"title": title, "text": text}])
            return

        try:
            from scipy.sparse import vstack
            doc = self._build_doc(title, text)
            new_vec = self.vectorizer.transform([doc])
            self.matrix = vstack([self.matrix, new_vec])
            self.texts.append(doc)
        except Exception as e:
            logger.debug(f"Error agregando doc al índice semántico: {e}")
