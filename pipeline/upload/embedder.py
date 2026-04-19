"""
Embedder — encodes text into dense vectors.

Used at upload time to encode chunks and at query time to encode user queries.
The same model instance must be shared between both uses to ensure vectors
occupy the same embedding space.

Concrete implementation wraps sentence-transformers with lazy model loading.
Query-time code should depend on EmbedderProtocol (pipeline/shared/types.py),
not this class directly, to preserve the module boundary in CLAUDE.md.
"""

from __future__ import annotations


class Embedder:
    """sentence-transformers wrapper with lazy model loading.

    The underlying model is downloaded and loaded on the first encode call,
    not at construction time, to avoid blocking the process startup.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self._model_name = model_name
        self._model = None  # loaded lazily on first use

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is required: pip install sentence-transformers"
            ) from exc
        self._model = SentenceTransformer(self._model_name)

    def encode(self, text: str) -> list[float]:
        """Encode a single text string into a dense vector."""
        self._ensure_model()
        return self._model.encode(text, convert_to_numpy=True).tolist()

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        """Encode a list of texts. Returns vectors in the same order as input."""
        self._ensure_model()
        return self._model.encode(texts, convert_to_numpy=True).tolist()
