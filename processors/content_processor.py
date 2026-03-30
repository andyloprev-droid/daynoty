"""
Content Processor - Summarize and paraphrase news articles with Claude (ALL OUTPUT IN ENGLISH)
"""
import logging
from typing import Optional, Dict, List
import re
from anthropic import Anthropic
import config

logger = logging.getLogger(__name__)


class ContentProcessor:
    """Process news content with Claude API - ALL OUTPUT IN ENGLISH"""

    def __init__(self):
        self.client = Anthropic(api_key=config.CLAUDE_API_KEY)
        self.model = config.CLAUDE_MODEL
        self.max_tokens = config.CLAUDE_MAX_TOKENS

    def summarize_news(self, title: str, original_text: str) -> Optional[Dict]:
        """
        Summarize and paraphrase news with Claude

        Args:
            title: News title
            original_text: Original article text

        Returns:
            Dict with:
            - summary: Paraphrased text (IN ENGLISH)
            - key_points: Key points list (IN ENGLISH)
            - is_original: bool (detect if too similar to original)
        """
        if not original_text or len(original_text) < config.MIN_ARTICLE_LENGTH:
            logger.warning(f"Text too short to process: {title[:50]}")
            return None

        try:
            prompt = self._create_summarize_prompt(title, original_text)

            message = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = message.content[0].text

            # Parsear respuesta
            result = self._parse_response(response_text, original_text)

            logger.info(f"News summarized: {title[:50]}")
            return result

        except Exception as e:
            logger.error(f"Error processing with Claude: {e}")
            return None

    def _create_summarize_prompt(self, title: str, text: str) -> str:
        """Create prompt for Claude - ALL OUTPUT IN ENGLISH"""

        # Limit input text
        truncated_text = text[: config.MAX_ARTICLE_LENGTH]

        return f"""You have a news article about: {title}. Your task:

1. Read and fully understand the content
2. Write a summary of 2-3 paragraphs that:
   - Keeps ALL important original information
   - Uses DIFFERENT words and structure (natural paraphrase)
   - Is interesting and easy to read
   - Is NOT a literal copy-paste

3. Extract 3-5 key points

ORIGINAL TEXT:
{truncated_text}

RESPOND IN THIS EXACT FORMAT:
---SUMMARY---
[Your paraphrased summary here]

---KEY POINTS---
- Point 1
- Point 2
- Point 3

Include nothing else, only the summary and key points. ALL RESPONSES MUST BE IN ENGLISH."""

    def _parse_response(self, response: str, original_text: str) -> Dict:
        """Parse Claude's response"""

        # Extract sections
        summary = ""
        key_points = []

        if "---SUMMARY---" in response:
            parts = response.split("---KEY POINTS---")
            if len(parts) >= 1:
                summary_part = parts[0].replace("---SUMMARY---", "").strip()
                summary = summary_part.strip()

            if len(parts) >= 2:
                points_part = parts[1].strip()
                # Extract points
                lines = points_part.split("\n")
                for line in lines:
                    line = line.strip()
                    if line.startswith("-"):
                        point = line[1:].strip()
                        if point:
                            key_points.append(point)

        # If parsing failed, use fallback
        if not summary:
            summary = response[:300]
            key_points = self._extract_key_points_fallback(original_text)

        # Detect if too similar to original (possible copy-paste)
        is_original = not self._is_too_similar(summary, original_text)

        return {
            "summary": summary,
            "key_points": key_points,
            "is_original": is_original,
        }

    def _extract_key_points_fallback(self, text: str) -> List[str]:
        """Extract key points if Claude fails (fallback)"""
        # Use first sentences as key points
        sentences = re.split(r"[.!?]+", text)
        points = []
        for sentence in sentences[:3]:
            sentence = sentence.strip()
            if sentence and len(sentence) > 20:
                points.append(sentence[:80] + "...")
        return points[:3]

    def _is_too_similar(self, summary: str, original: str, threshold: float = 0.75) -> bool:
        """
        Detectar si el resumen es demasiado similar al original

        Args:
            summary: Texto resumido
            original: Texto original
            threshold: Umbral de similitud (0-1)

        Returns:
            True si es demasiado similar (copypaste)
        """
        # Convertir a minúsculas y palabras
        summary_words = set(summary.lower().split())
        original_words = set(original.lower().split())

        # Calcular similitud simple (palabras coincidentes)
        if not original_words:
            return False

        overlap = len(summary_words & original_words) / len(original_words)
        return overlap > threshold

    def get_token_estimate(self, text: str) -> int:
        """
        Estimar tokens (aproximado: 1 token ≈ 4 caracteres)
        """
        return len(text) // 4
