"""
Query Normalizer — Stage 0.

Strips filler words, normalises phrasing, extracts entities/property/intent,
and encodes the normalised query into a dense vector.

Entity extraction here is intentionally rule-based (proper-noun detection).
Full NER over retrieved chunks is handled by pipeline/relations/ner.py in Phase 2.
"""

from __future__ import annotations

from models.schemas import Query
from pipeline.shared.types import EmbedderProtocol

_FILLER_WORDS: frozenset[str] = frozenset({
    "what", "is", "the", "a", "an", "of", "in", "at", "on",
    "are", "was", "were", "be", "been", "being", "have", "has",
    "do", "does", "did", "will", "would", "could", "should",
    "tell", "me", "please", "can", "you",
})

_KNOWN_PROPERTIES: dict[str, str] = {
    "capital": "capital",
    "population": "population",
    "area": "area",
    "president": "president",
    "prime minister": "prime minister",
    "language": "language",
    "currency": "currency",
    "location": "location",
    "founder": "founder",
    "year": "year",
    "flag": "flag",
    "border": "border",
}

_INTENT_MAP: dict[str, str] = {
    "what": "factual lookup",
    "which": "factual lookup",
    "who": "factual lookup",
    "where": "factual lookup",
    "when": "factual lookup",
    "why": "causal",
    "how": "procedural",
    "list": "enumeration",
}


class QueryNormalizer:
    """Converts a raw user query into a structured Query object."""

    def __init__(self, embedder: EmbedderProtocol) -> None:
        self._embedder = embedder

    def normalize(self, raw: str) -> Query:
        """Return a fully populated Query from a raw question string."""
        normalized = self._normalize_text(raw)
        entities = self._extract_entities(raw)
        property_ = self._extract_property(raw.lower())
        intent = self._extract_intent(raw.lower())
        vector = self._embedder.encode(normalized)
        return Query(
            raw=raw,
            normalized=normalized,
            entities=entities,
            property=property_,
            intent=intent,
            vector=vector,
        )

    def _normalize_text(self, raw: str) -> str:
        """Strip trailing punctuation, remove filler words."""
        text = raw.rstrip("?!.,")
        tokens = text.split()
        meaningful = [t for t in tokens if t.lower() not in _FILLER_WORDS]
        return " ".join(meaningful).strip()

    def _extract_entities(self, text: str) -> list[dict]:
        """Detect capitalised proper nouns not at sentence-initial position.

        Returns [{"text": str, "label": "ENTITY"}]. Phase 2 NER provides
        richer extraction over retrieved chunks.
        """
        tokens = text.split()
        entities: list[dict] = []
        seen: set[str] = set()
        for i, token in enumerate(tokens):
            word = token.rstrip("?!.,;:'\"")
            if (
                word
                and word[0].isupper()
                and word.lower() not in _FILLER_WORDS
                and word not in seen
                and i > 0  # skip sentence-opening capitalisation
            ):
                seen.add(word)
                entities.append({"text": word, "label": "ENTITY"})
        return entities

    def _extract_property(self, text: str) -> str:
        """Return the first matching known property phrase, or 'unknown'."""
        for phrase, label in _KNOWN_PROPERTIES.items():
            if phrase in text:
                return label
        return "unknown"

    def _extract_intent(self, text: str) -> str:
        """Classify intent from the leading question word."""
        first_word = text.split()[0] if text.split() else ""
        return _INTENT_MAP.get(first_word, "factual lookup")
