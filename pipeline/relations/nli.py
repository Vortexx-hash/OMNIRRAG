"""
NLI Contradiction Detector — Stage 3.3.

Takes chunk pairs and classifies them as "contradiction" or "no-contradiction".
Applies the scope qualifier rule: when both chunks carry different qualifying
roles for the same property, the pair is marked is_scope_difference=True rather
than a hard contradiction.

See SKILLS.md: NLI Scope Qualifier Rule.
"""

from __future__ import annotations

import re
from itertools import combinations

from models.schemas import Chunk, RelationPair
from pipeline.shared.constants import NLI_CONTRADICTION, NLI_NO_CONTRADICTION, SCOPE_QUALIFIERS
from pipeline.shared.helpers import cosine_similarity, chunk_pair_key
from pipeline.relations.ner import NERExtractor, extract_all


# ---------------------------------------------------------------------------
# Rule-based NLI heuristic
# ---------------------------------------------------------------------------

def _strip_scope_qualifiers(text: str) -> str:
    """Remove known scope qualifier words from a predicate string for normalisation."""
    result = text.lower()
    for q in sorted(SCOPE_QUALIFIERS, key=len, reverse=True):
        result = result.replace(q.lower(), "")
    # Collapse extra whitespace
    return re.sub(r'\s+', ' ', result).strip()


def _extract_claims(text: str) -> list[tuple[str, str]]:
    """
    Extract (subject_lower, predicate_lower) pairs from "<Subject> is [the] <predicate>"
    patterns.  The predicate is normalised by stripping scope qualifiers so that
    "constitutional capital of Bolivia" and "administrative capital of Bolivia"
    both normalise to "capital of bolivia" — allowing contradiction detection
    even when qualifiers differ.

    Returns a list of (subject, predicate) tuples, both lowercased and stripped.
    """
    claims: list[tuple[str, str]] = []
    # Captures: <TitleCase subject> is [the] <rest of clause>
    pattern = re.compile(
        r'([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s+(?:is|was|are|were)\s+(?:the\s+)?([^.,;]+)',
        re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        subject = match.group(1).strip().lower()
        predicate = _strip_scope_qualifiers(match.group(2).strip())
        if predicate:
            claims.append((subject, predicate))
    return claims


class _RuleBasedNLIClassifier:
    """
    Simple heuristic NLI classifier that requires no ML model.

    Contradiction detection strategy:
    1. Extract (subject, predicate) claims from each text.
       Predicate = the thing the subject "is", with scope qualifiers stripped.
    2. Build a mapping of predicate → set of subjects from each text.
    3. If the same predicate maps to *different* subjects across the two texts,
       classify as contradiction.
    4. Also check the inverse: same subject, different predicates.
    """

    def classify(self, premise: str, hypothesis: str) -> str:
        claims_a = _extract_claims(premise)
        claims_b = _extract_claims(hypothesis)

        # predicate → set of subjects
        pred_to_subj_a: dict[str, set[str]] = {}
        for subj, pred in claims_a:
            pred_to_subj_a.setdefault(pred, set()).add(subj)

        pred_to_subj_b: dict[str, set[str]] = {}
        for subj, pred in claims_b:
            pred_to_subj_b.setdefault(pred, set()).add(subj)

        # Same predicate, different subjects → contradiction
        for pred in pred_to_subj_a:
            if pred in pred_to_subj_b:
                if pred_to_subj_a[pred].isdisjoint(pred_to_subj_b[pred]):
                    return NLI_CONTRADICTION

        # subject → set of predicates
        subj_to_pred_a: dict[str, set[str]] = {}
        for subj, pred in claims_a:
            subj_to_pred_a.setdefault(subj, set()).add(pred)

        subj_to_pred_b: dict[str, set[str]] = {}
        for subj, pred in claims_b:
            subj_to_pred_b.setdefault(subj, set()).add(pred)

        # Same subject, different predicates → contradiction
        for subj in subj_to_pred_a:
            if subj in subj_to_pred_b:
                if subj_to_pred_a[subj].isdisjoint(subj_to_pred_b[subj]):
                    return NLI_CONTRADICTION

        return NLI_NO_CONTRADICTION


class NLIClassifier:
    """Wraps an NLI backend and returns binary labels for chunk pairs.

    Parameters
    ----------
    model_name:
        When ``None`` (default), the rule-based heuristic is used — no ML
        model is downloaded or loaded.  When a non-None string is passed,
        the classifier attempts to lazy-load a sentence-transformers
        cross-encoder model.  The sentence-transformers library must be
        installed separately; it is an optional dependency.
    """

    def __init__(self, model_name: str | None = None) -> None:
        self._rule_based = _RuleBasedNLIClassifier()
        self._model = None
        self._model_name = model_name

        if model_name is not None:
            self._load_model(model_name)

    def _load_model(self, model_name: str) -> None:
        try:
            from sentence_transformers import CrossEncoder  # type: ignore
            self._model = CrossEncoder(model_name)
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is required for model-based NLI. "
                "Install it with: pip install sentence-transformers"
            ) from exc

    def classify(self, premise: str, hypothesis: str) -> str:
        """
        Return NLI_CONTRADICTION or NLI_NO_CONTRADICTION for the given pair.
        Does not apply the scope qualifier rule — that is handled in build_relation_pairs.
        """
        if self._model is not None:
            # Model-based path: CrossEncoder returns scores for
            # [contradiction, entailment, neutral] — index 0 is contradiction.
            scores = self._model.predict([(premise, hypothesis)])
            label_id = int(scores[0].argmax())
            return NLI_CONTRADICTION if label_id == 0 else NLI_NO_CONTRADICTION

        return self._rule_based.classify(premise, hypothesis)


# ---------------------------------------------------------------------------
# Scope qualifier rule
# ---------------------------------------------------------------------------

def _apply_scope_qualifier_rule(
    raw_label: str,
    qualifiers_a: list[str],
    qualifiers_b: list[str],
    known_qualifiers: list[str],
) -> bool:
    """
    Return True if the pair should be marked as a scope difference.

    Conditions:
    - raw_label is contradiction
    - Both chunks carry at least one qualifier from known_qualifiers
    - The qualifiers are different (they refer to different roles)
    """
    if raw_label != NLI_CONTRADICTION:
        return False

    known_lower = {q.lower() for q in known_qualifiers}

    present_a = {q.lower() for q in qualifiers_a if q.lower() in known_lower}
    present_b = {q.lower() for q in qualifiers_b if q.lower() in known_lower}

    # Both must have qualifiers and those qualifiers must differ
    return bool(present_a) and bool(present_b) and present_a != present_b


# ---------------------------------------------------------------------------
# Public builder
# ---------------------------------------------------------------------------

def build_relation_pairs(
    chunks: list[Chunk],
    nli_classifier: NLIClassifier,
    scope_qualifiers: list[str],
    ner_results: dict[str, dict] | None = None,
) -> list[RelationPair]:
    """
    Construct RelationPair objects for all chunk pairs.

    Parameters
    ----------
    chunks:
        The retrieved chunks to compare.
    nli_classifier:
        Classifier used to obtain raw NLI labels.
    scope_qualifiers:
        List of known scope qualifier strings (from constants.SCOPE_QUALIFIERS).
    ner_results:
        Optional pre-computed NER results (chunk_id → {"entities": [...],
        "qualifiers": [...]}).  When None, NER is run inline using a
        default rule-based extractor to avoid recomputation overhead.
    """
    if ner_results is None:
        extractor = NERExtractor()
        ner_results = extract_all(chunks, extractor)

    pairs: list[RelationPair] = []

    for chunk_a, chunk_b in combinations(chunks, 2):
        raw_label = nli_classifier.classify(chunk_a.text, chunk_b.text)

        ner_a = ner_results.get(chunk_a.id, {"entities": [], "qualifiers": []})
        ner_b = ner_results.get(chunk_b.id, {"entities": [], "qualifiers": []})

        qualifiers_a: list[str] = ner_a.get("qualifiers", [])
        qualifiers_b: list[str] = ner_b.get("qualifiers", [])

        # Compute entity overlap from NER entity lists
        extractor_for_overlap = NERExtractor()
        entity_overlap = extractor_for_overlap.compute_entity_overlap(
            ner_a.get("entities", []),
            ner_b.get("entities", []),
        )

        # All qualifiers seen across both chunks
        all_qualifiers = list(dict.fromkeys(qualifiers_a + qualifiers_b))

        is_scope_diff = _apply_scope_qualifier_rule(
            raw_label, qualifiers_a, qualifiers_b, scope_qualifiers
        )

        sim = cosine_similarity(chunk_a.embedding, chunk_b.embedding)

        key = chunk_pair_key(chunk_a.id, chunk_b.id)
        pairs.append(RelationPair(
            chunk_a_id=key[0],
            chunk_b_id=key[1],
            similarity_score=sim,
            nli_label=raw_label,
            entity_overlap=entity_overlap,
            scope_qualifiers=all_qualifiers,
            is_scope_difference=is_scope_diff,
        ))

    return pairs
