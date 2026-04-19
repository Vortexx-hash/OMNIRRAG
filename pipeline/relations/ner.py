"""
NER — Named Entity Recognition & Entity Overlap — Stage 3.4.

Extracts named entities and scope qualifiers from chunk text.
Computes entity overlap between chunk pairs to identify whether
apparent contradictions are true conflicts or role distinctions.

Rule-based implementation — no external NLP libraries required.
"""

from __future__ import annotations

import re

from models.schemas import Chunk
from pipeline.shared.constants import SCOPE_QUALIFIERS


# Built-in gazetteers — extend as needed without adding ML dependencies.
_KNOWN_COUNTRIES: set[str] = {
    "Bolivia", "Brazil", "Argentina", "Chile", "Peru", "Colombia", "Venezuela",
    "Ecuador", "Paraguay", "Uruguay", "Guyana", "Suriname", "Panama",
    "United States", "United Kingdom", "Canada", "Mexico", "France", "Germany",
    "Spain", "Italy", "Portugal", "Russia", "China", "Japan", "India",
    "Australia", "New Zealand", "South Africa", "Nigeria", "Egypt",
    "Saudi Arabia", "Iran", "Iraq", "Turkey", "Indonesia", "Pakistan",
    "Bangladesh", "Afghanistan", "Kenya", "Ethiopia", "Ghana",
}

_KNOWN_CITIES: set[str] = {
    "Sucre", "La Paz", "Santa Cruz", "Cochabamba", "Oruro", "Potosi",
    "Brasilia", "Rio de Janeiro", "São Paulo", "Buenos Aires", "Santiago",
    "Lima", "Bogota", "Caracas", "Quito", "Asuncion", "Montevideo",
    "Washington", "New York", "Los Angeles", "London", "Paris", "Berlin",
    "Madrid", "Rome", "Moscow", "Beijing", "Tokyo", "Delhi", "Mumbai",
    "Sydney", "Cairo", "Lagos", "Nairobi", "Pretoria", "Cape Town",
    "Toronto", "Mexico City", "Jakarta", "Islamabad", "Dhaka",
    "Tehran", "Baghdad", "Ankara", "Riyadh",
}


class NERExtractor:
    """Rule-based named entity extractor — no ML dependencies.

    Detects countries, cities, scope qualifiers, and generic capitalised
    proper nouns from text using gazetteers and simple heuristics.

    ``model_name`` is accepted for interface compatibility but is currently
    ignored; the implementation is always rule-based.
    """

    def __init__(self, model_name: str | None = None) -> None:
        # model_name reserved for future ML extension; ignored here.
        self._scope_qualifiers = SCOPE_QUALIFIERS

    def extract(self, text: str) -> list[dict]:
        """
        Return entities as [{"text": str, "label": str}].
        Labels: COUNTRY, CITY, QUALIFIER, ENTITY.
        """
        entities: list[dict] = []
        seen: set[str] = set()

        def _add(surface: str, label: str) -> None:
            if surface not in seen:
                seen.add(surface)
                entities.append({"text": surface, "label": label})

        # --- Countries ---
        for country in _KNOWN_COUNTRIES:
            if re.search(r'\b' + re.escape(country) + r'\b', text):
                _add(country, "COUNTRY")

        # --- Cities ---
        for city in _KNOWN_CITIES:
            if re.search(r'\b' + re.escape(city) + r'\b', text):
                _add(city, "CITY")

        # --- Scope qualifiers (multi-word phrases before single-word) ---
        lower_text = text.lower()
        for qualifier in sorted(self._scope_qualifiers, key=len, reverse=True):
            if qualifier.lower() in lower_text:
                _add(qualifier, "QUALIFIER")

        # --- Generic capitalised proper nouns (fallback) ---
        # Match sequences of Title-Cased words not already captured.
        for match in re.finditer(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', text):
            surface = match.group(1)
            if surface not in seen:
                _add(surface, "ENTITY")

        return entities

    def detect_scope_qualifiers(self, entities: list[dict]) -> list[str]:
        """
        Return qualifier surface forms found in the entity list.
        Cross-references against SCOPE_QUALIFIERS from constants.
        """
        qualifier_set = {q.lower() for q in self._scope_qualifiers}
        return [
            e["text"]
            for e in entities
            if e["label"] == "QUALIFIER" or e["text"].lower() in qualifier_set
        ]

    def compute_entity_overlap(
        self,
        entities_a: list[dict],
        entities_b: list[dict],
    ) -> list[str]:
        """Return the list of entity surface forms shared by both chunks."""
        texts_b = {e["text"] for e in entities_b}
        seen: set[str] = set()
        overlap: list[str] = []
        for e in entities_a:
            surface = e["text"]
            if surface in texts_b and surface not in seen:
                seen.add(surface)
                overlap.append(surface)
        return overlap


def extract_all(chunks: list[Chunk], extractor: NERExtractor) -> dict[str, dict]:
    """
    Run NER on all chunks. Returns chunk_id → {"entities": [...], "qualifiers": [...]}.
    """
    results: dict[str, dict] = {}
    for chunk in chunks:
        entities = extractor.extract(chunk.text)
        qualifiers = extractor.detect_scope_qualifiers(entities)
        results[chunk.id] = {"entities": entities, "qualifiers": qualifiers}
    return results
