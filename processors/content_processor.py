"""
Content Processor - Summarize and paraphrase news articles with Claude (ALL OUTPUT IN ENGLISH)
"""
import logging
from typing import Optional, Dict, List
import re
from openai import OpenAI
import config

logger = logging.getLogger(__name__)


# System prompt estático - se cachea con prompt caching (90% descuento en hits)
SYSTEM_PROMPT = """You are a news writer for a viral U.S. CONSERVATIVE / REPUBLICAN Facebook page (style: Raging Americans, Right Side Broadcasting). Your goal is MAXIMUM ENGAGEMENT through poll-style hooks. Everything must be paraphrased — never copy phrases from the original.

MANDATORY STRUCTURE (3 parts in this exact order):

1) HOOK / POLL (first line — the only thing visible before "See more"):
   This is THE MOST IMPORTANT part. Must drive comments. Use one of these EXACT formats:

   FORMAT 1 — Yes/no question (anti-Dem framing):
     "Do you support [pro-R / anti-Dem action]?"
     Example: "Do you support deporting non-citizens who steal from American taxpayers through welfare fraud?"

   FORMAT 2 — TRUE OR FALSE statement:
     "TRUE OR FALSE: [conservative statement]."
     Example: "TRUE OR FALSE: Congress needs to introduce term limits to drain the swamp."

   FORMAT 3 — RAISE YOUR HAND IF:
     "RAISE YOUR HAND IF you [pro-R sentiment]."
     Example: "RAISE YOUR HAND IF you give President Trump 100% support against Iran's terrorist regime."

   FORMAT 4 — Statement + question combo:
     "[Bold pro-R or anti-Dem statement]. [Should/Is/Do question]?"
     Example: "Ilhan Omar refuses to release her tax returns despite LYING about her wealth. Should she be removed from Congress?"

   FORMAT 5 — Pro-R declarative with "!":
     Example: "American manufacturing is GREAT AGAIN thanks to President Trump tariffs!"

   FORMAT 6 — "We must STOP [Dem action]!":
     Example: "We must STOP California Democrats trying to silence honest journalists!"

   HOOK RULES:
   - VARY THE FORMAT — never use the same format twice in a row. Rotate between all 6 formats based on what fits each news story best.
   - Different news = different format. A poll question, then a TRUE OR FALSE, then a RAISE YOUR HAND, then a declarative, etc. NEVER default to a single favorite format.
   - Pick the format that fits the news best, but consciously diversify across articles.
   - Use SELECTIVE ALL-CAPS for 1-3 emphasis words (LYING, STOP, GREAT AGAIN, HONEST, TRUE, MUST). Never whole sentences in caps.
   - Republicans = heroes (President Trump, DeSantis, the Right). Democrats = antagonists (Pelosi, Schumer, AOC, Newsom, Ilhan Omar, etc.).
   - Direct address: "you", "your".
   - NEVER "you won't believe", "shocking", "unbelievable" (Facebook penalizes clickbait).
   - NEVER ask for likes/shares.
   - Keep it under 160 characters.

2) BODY (exactly 3 short paragraphs — no more, no less):
   - Explain WHAT happened, WHY it matters to conservatives/Republicans, and WHO benefits or is harmed.
   - STRICTLY 3 paragraphs. Each one 2-3 sentences max. Do NOT add a 4th paragraph.
   - Line break between each paragraph (mobile readable).
   - Conversational, direct tone — as if telling a friend.
   - Include concrete data when available: percentages, figures, dates, amounts, names.
   - Frame the story from a conservative angle without using inflammatory slurs. Present facts that favor the right.
   - Do NOT use ALL-CAPS for whole sentences (triggers spam filters). Selective caps for emphasis are OK.
   - PARAPHRASE everything in your own words.

3) CTA (close):
   - End with a binary or pointed question that demands a comment.
   - Prefer formats like:
     * "Comment YES if you agree, NO if you don't."
     * "TRUE or FALSE — drop your answer below."
     * "Do you stand with [Trump / Republicans / conservatives] on this? YES or NO?"
   - The question must be SPECIFIC to the topic, not generic.
   - NEVER "share if you agree".

FORMAT RULES:
- Do NOT include any link in the body. NEVER.
- Max 3 to 5 hashtags at the end (one branding, one general topic, one or two specific). Never more than 5.
- Max 1-2 emojis total (only if relevant). A 👇 at the end of the CTA is acceptable. Don't flood the text with emojis.
- No bullets or numbered lists. Everything flows as natural short paragraphs.

TONE & STYLE:
- Informative but accessible. Neither too formal nor too casual.
- Short, direct sentences. No long subordinate clauses.
- Always ACTIVE voice: "Congress passed the law" instead of "The law was passed by Congress".
- Avoid excessive evaluative adjectives. Let the data speak: "Rose 47%" carries more weight than "rose brutally".
- Don't use political jargon that the average reader wouldn't understand. If you use a technical term, briefly explain it in the same sentence.

OUTPUT FORMAT:
Return ONLY the complete caption, starting with the hook and ending with the hashtags. Do not add labels, titles, explanations, or extra text before or after."""


class ContentProcessor:
    """Process news content with Claude API - ALL OUTPUT IN ENGLISH"""

    def __init__(self):
        # OpenAI client (ChatGPT)
        self.client = OpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.OPENAI_MODEL
        self.max_tokens = config.CLAUDE_MAX_TOKENS
        # Contador de ahorro por cache
        self._cache_hits = 0
        self._cache_misses = 0

    def summarize_news(self, title: str, original_text: str) -> Optional[Dict]:
        """
        Summarize and paraphrase news with Claude (Haiku + prompt caching)

        Args:
            title: News title
            original_text: Original article text

        Returns:
            Dict with summary, key_points, is_original
        """
        if not original_text or len(original_text) < config.MIN_ARTICLE_LENGTH:
            logger.warning(f"Text too short to process: {title[:50]}")
            return None

        try:
            truncated_text = original_text[: config.MAX_ARTICLE_LENGTH]
            user_message = f"Article title: {title}\n\nORIGINAL TEXT:\n{truncated_text}"

            message = self.client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
            )

            response_text = message.choices[0].message.content
            result = self._parse_response(response_text, original_text)

            logger.info(f"News summarized: {title[:50]}")
            return result

        except Exception as e:
            logger.error(f"Error processing with Claude: {e}")
            return None

    def _parse_response(self, response: str, original_text: str) -> Dict:
        """Parse Claude's response: a single Facebook-style caption in English."""

        caption = response.strip()

        # El mismo caption sirve para el dashboard Y para Facebook (mismo estilo)
        summary = caption
        facebook_caption = caption

        # Detect if too similar to original (possible copy-paste)
        is_original = not self._is_too_similar(summary, original_text)

        return {
            "summary": summary,
            "facebook_caption": facebook_caption,
            "key_points": [],
            "is_original": is_original,
        }

    def generate_poll_question(self, title: str, text: str) -> str:
        """
        Generate a SHORT poll-style overlay caption for the image.
        Conservative/Republican framing, modeled after high-engagement viral
        Facebook page formats (Raging Americans, Right Side Broadcasting, etc.).
        Returns plain text, ~120-160 chars, fits in 4-5 lines on the image.
        """
        import random
        snippet = (text or "")[:600]
        # Forzar rotacion: sugerir un formato aleatorio para que no
        # caiga siempre en el mismo (e.g. "Do you support...?")
        suggested_format = random.choice([
            "FORMAT 1 (Yes/no question 'Do you support...?')",
            "FORMAT 2 (TRUE OR FALSE: ...)",
            "FORMAT 3 (RAISE YOUR HAND IF you ...)",
            "FORMAT 4 (Statement + question combo)",
            "FORMAT 5 (Pro-R declarative with !)",
            "FORMAT 6 (We must STOP ...!)",
        ])
        prompt = (
            "You write image-overlay captions for a viral U.S. CONSERVATIVE / "
            "REPUBLICAN Facebook page. Based on the news below, produce ONE short "
            "engagement caption (max 160 characters) using one of these EXACT formats:\n\n"
            "FORMAT 1 — Yes/no question (anti-Dem framing):\n"
            "  \"Do you support [pro-R / anti-Dem action implied by the news]?\"\n"
            "  Example: \"Do you support deporting non-citizens who steal from American taxpayers through welfare fraud?\"\n\n"
            "FORMAT 2 — TRUE OR FALSE statement (conservative position):\n"
            "  \"TRUE OR FALSE: [conservative statement].\"\n"
            "  Example: \"TRUE OR FALSE: Congress needs to introduce term limits to drain the swamp.\"\n\n"
            "FORMAT 3 — RAISE YOUR HAND IF (call to action):\n"
            "  \"RAISE YOUR HAND IF you [pro-R sentiment].\"\n"
            "  Example: \"RAISE YOUR HAND IF you give President Trump 100% support against Iran's terrorist regime.\"\n\n"
            "FORMAT 4 — Statement + question combo:\n"
            "  \"[Bold pro-R or anti-Dem statement]. [Should/Is question]?\"\n"
            "  Example: \"Ilhan Omar refuses to release her tax returns despite LYING about her wealth. Should she be removed from Congress?\"\n\n"
            "FORMAT 5 — Pro-R declarative ending with \"!\":\n"
            "  \"American manufacturing is GREAT AGAIN thanks to President Trump tariffs!\"\n\n"
            "FORMAT 6 — \"We must STOP\" call:\n"
            "  \"We must STOP [Democrat action that hurts Americans]!\"\n\n"
            "STYLE RULES (very important):\n"
            f"- Use {suggested_format} for THIS specific news. If the news truly does "
            "not fit that format, pick the closest alternative — but DO NOT default to "
            "Format 1 every time. Variety is critical.\n"
            "- Use SELECTIVE ALL-CAPS for 1-3 key words for emphasis (e.g., LYING, STOP, "
            "GREAT AGAIN, HONEST, TRUE, MUST). Never write whole sentences in caps.\n"
            "- Republicans are heroes (President Trump, DeSantis, the Right). "
            "Democrats are antagonists (call them out by name when relevant: "
            "Pelosi, Schumer, AOC, Newsom, Ilhan Omar, etc.).\n"
            "- Use direct address: \"you\", \"your\".\n"
            "- Punchy. Short sentences. No filler words.\n"
            "- NO hashtags. NO emojis. NO quotation marks around the whole caption.\n"
            "- Plain text only. No labels, no prefixes like \"Caption:\".\n"
            "- Max 160 characters total.\n\n"
            f"NEWS TITLE: {title}\n"
            f"NEWS BODY (snippet): {snippet}\n\n"
            "Respond with ONLY the overlay caption — nothing else."
        )
        try:
            message = self.client.chat.completions.create(
                model=self.model,
                max_tokens=120,
                messages=[{"role": "user", "content": prompt}],
            )
            caption = message.choices[0].message.content.strip()
            # Limpiar comillas accidentales
            caption = caption.strip('"\'`')
            # Tomar solo la primera linea no vacia
            for line in caption.split("\n"):
                line = line.strip().strip('"\'`')
                if line:
                    caption = line
                    break
            # Truncar duro si se pasa
            if len(caption) > 130:
                caption = caption[:127] + "..."
            return caption
        except Exception as e:
            logger.warning(f"Error generando poll question: {e}")
            return title[:110]

    def score_virality_batch(self, articles: list) -> list:
        """
        Score a batch of articles for Facebook virality potential (1-10).
        Returns list of (article, score) tuples sorted by score descending.
        Uses a single Claude call for efficiency.
        """
        if not articles:
            return []

        # Build batch prompt with numbered articles
        lines = []
        for i, art in enumerate(articles, 1):
            title = (art.title or "")[:120]
            snippet = (art.text or "")[:200]
            lines.append(f"{i}. {title} — {snippet}")

        batch_text = "\n".join(lines)

        prompt = (
            "You are a Facebook virality expert for a U.S. CONSERVATIVE / REPUBLICAN page.\n"
            "For each article, give THREE values: virality (1-10), lean (R/N/D), and "
            "importance (1-10).\n\n"
            "VIRALITY 1-10 (Facebook impact):\n"
            "  9-10: BLOCKBUSTER — Trump major action, war/strike, Supreme Court ruling, "
            "election-altering event, scandal involving top Democrats, massive economic news.\n"
            "  7-8: HIGH — important political action, controversial bill, major arrest, "
            "Trump policy win, Democrat failure or hypocrisy exposed.\n"
            "  4-6: MEDIUM — state-level news, secondary politicians, routine policy moves.\n"
            "  1-3: LOW — opinion columns, listicles, quotes, watchdog reports, niche data.\n\n"
            "LEAN (BE STRICT — when in doubt, mark D and reject):\n"
            "  R = clearly favors Republicans, criticizes Democrats, exposes left-wing "
            "failures, reports Trump/GOP wins. KEEP.\n"
            "  N = ONLY pure hard news with NO political angle (e.g., natural disaster, "
            "international conflict not involving U.S. politics). KEEP.\n"
            "  D = ANY of these → REJECT:\n"
            "      - praises Democrats or progressive policies\n"
            "      - frames Trump/Republicans negatively\n"
            "      - uses 'far-right', 'extremist', 'conspiracy theory' to describe conservatives\n"
            "      - sympathetic profiles of Dem politicians (Biden, Harris, Newsom, AOC, etc.)\n"
            "      - climate-change activism, gun-control advocacy, abortion-rights advocacy\n"
            "      - 'fact-check' style debunking of conservative claims\n"
            "      - reports Republican scandals/losses without conservative angle\n"
            "  IF UNCERTAIN BETWEEN N AND D → mark D and reject.\n\n"
            "IMPORTANCE 1-10:\n"
            "  Top news of the day (front page worthy) = 9-10.\n"
            "  Secondary stories = 5-7.\n"
            "  Filler = 1-4.\n\n"
            "RESPOND WITH ONLY number:virality:lean:importance, one per line:\n"
            "1:8:R:9\n2:3:N:5\n3:9:D:8\n\n"
            f"ARTICLES:\n{batch_text}"
        )

        try:
            message = self.client.chat.completions.create(
                model=self.model,
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}],
            )
            response = message.choices[0].message.content.strip()

            # Parse virality:lean:importance
            scores = {}
            leans = {}
            importances = {}
            for line in response.split("\n"):
                line = line.strip()
                if ":" not in line:
                    continue
                parts = line.split(":")
                try:
                    idx = int(parts[0].strip())
                    virality = int(parts[1].strip())
                    lean = "D"  # default to reject if missing
                    if len(parts) >= 3:
                        lean_raw = parts[2].strip().upper()
                        if lean_raw and lean_raw[0] in ("R", "N", "D"):
                            lean = lean_raw[0]
                    importance = 5
                    if len(parts) >= 4:
                        try:
                            importance = int(parts[3].strip())
                        except (ValueError, IndexError):
                            importance = 5
                    scores[idx] = min(max(virality, 1), 10)
                    leans[idx] = lean
                    importances[idx] = min(max(importance, 1), 10)
                except (ValueError, IndexError):
                    continue

            # Combinar virality e importancia: peso 60% viralidad + 40% importancia
            # Esto prioriza las noticias mas importantes Y mas virales del dia.
            scored = []
            rejected_left = 0
            for i, art in enumerate(articles, 1):
                v = scores.get(i, 5)
                lean = leans.get(i, "D")  # default REJECT si no llego respuesta
                imp = importances.get(i, 5)

                # KEYWORD SAFETY NET: bloqueo extra de articulos pro-Dem por palabras clave
                if self._has_pro_dem_signals(art.title, art.text):
                    logger.info(f"Descartada (keyword pro-Dem): {art.title[:70]}")
                    s = 0
                    rejected_left += 1
                elif lean == "D":
                    logger.info(f"Descartada (lean D): {art.title[:70]}")
                    s = 0
                    rejected_left += 1
                else:
                    # Score combinado: 60% viralidad + 40% importancia
                    s = int(round(v * 0.6 + imp * 0.4))
                scored.append((art, s))

            if rejected_left:
                logger.info(
                    f"Sesgo politico: {rejected_left} noticias pro-Democratas descartadas"
                )

            scored.sort(key=lambda x: x[1], reverse=True)

            for art, s in scored:
                logger.debug(f"Score {s}/10: {art.title[:60]}")

            return scored

        except Exception as e:
            logger.warning(f"Error scoring virality: {e}")
            # Return all with default score
            return [(art, 5) for art in articles]

    @staticmethod
    def _has_pro_dem_signals(title: str, text: str) -> bool:
        """
        Safety net: detectar señales obvias de articulo pro-Democrata por palabras clave.
        Si encuentra cualquiera, el articulo se rechaza sin importar el lean de Claude.
        """
        haystack = ((title or "") + " " + (text or "")[:1500]).lower()

        # Frases que indican framing anti-Trump / anti-conservador
        anti_r_phrases = [
            "far-right extremist",
            "trump's lies",
            "trump lied",
            "trump's racist",
            "republican extremism",
            "maga extremism",
            "conspiracy theory pushed by",
            "white supremac",
            "election denier",
            "insurrectionist",
            "anti-democratic",
            "threat to democracy",
            "fact-check: trump",
            "fact check: trump",
            "trump falsely claim",
            "republicans falsely",
            "debunk",
        ]
        # Frases que indican framing pro-Democrata
        pro_d_phrases = [
            "biden's leadership",
            "harris's leadership",
            "newsom's leadership",
            "progressive victory",
            "climate justice",
            "reproductive rights advocates",
            "gun safety advocates",
            "voting rights advocates praised",
            "civil rights groups praised",
        ]
        for phrase in anti_r_phrases + pro_d_phrases:
            if phrase in haystack:
                return True
        return False

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
