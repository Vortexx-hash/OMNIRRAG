"""
Document chunker — runs at upload time only.

Splits a document into semantically coherent pieces using one of four strategies.
Default strategy is SEMANTIC. All strategies return a list of non-empty strings.
"""

from __future__ import annotations

import re
from enum import Enum


class ChunkingStrategy(Enum):
    SEMANTIC = "semantic"
    CHARACTER = "character"
    OVERLAP = "overlap"
    HYBRID = "hybrid"


class Chunker:
    """Splits document text into chunks according to the chosen strategy."""

    # Sentences longer than this trigger further splitting inside _semantic_chunk
    _MAX_PARAGRAPH_CHARS: int = 500

    def chunk(
        self,
        text: str,
        strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC,
        chunk_size: int = 300,
        overlap_size: int = 50,
    ) -> list[str]:
        """Return a list of non-empty text chunks for the given document."""
        if strategy is ChunkingStrategy.SEMANTIC:
            return self._semantic_chunk(text)
        if strategy is ChunkingStrategy.CHARACTER:
            return self._char_chunk(text, chunk_size)
        if strategy is ChunkingStrategy.OVERLAP:
            return self._overlap_chunk(text, chunk_size, overlap_size)
        if strategy is ChunkingStrategy.HYBRID:
            return self._hybrid_chunk(text, chunk_size, overlap_size)
        raise ValueError(f"Unknown strategy: {strategy}")

    def _semantic_chunk(self, text: str) -> list[str]:
        """Split at paragraph boundaries (double newline).

        Paragraphs exceeding _MAX_PARAGRAPH_CHARS are further split at sentence
        boundaries to keep chunk sizes manageable.
        """
        raw_paragraphs = re.split(r"\n{2,}", text.strip())
        sentence_end = re.compile(r"(?<=[.!?])\s+")
        chunks: list[str] = []

        for para in raw_paragraphs:
            para = para.strip()
            if not para:
                continue
            if len(para) <= self._MAX_PARAGRAPH_CHARS:
                chunks.append(para)
            else:
                # Split overlong paragraph at sentence boundaries
                sentences = sentence_end.split(para)
                segment = ""
                for sentence in sentences:
                    candidate = (segment + " " + sentence).strip() if segment else sentence
                    if segment and len(candidate) > self._MAX_PARAGRAPH_CHARS:
                        chunks.append(segment.strip())
                        segment = sentence
                    else:
                        segment = candidate
                if segment:
                    chunks.append(segment.strip())

        return [c for c in chunks if c]

    def _char_chunk(self, text: str, chunk_size: int) -> list[str]:
        """Split into fixed-size character windows. Last chunk may be shorter."""
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

    def _overlap_chunk(self, text: str, chunk_size: int, overlap_size: int) -> list[str]:
        """Split into fixed-size windows with shared overlap between adjacent chunks."""
        if overlap_size >= chunk_size:
            raise ValueError("overlap_size must be smaller than chunk_size")
        step = chunk_size - overlap_size
        chunks: list[str] = []
        i = 0
        while i < len(text):
            chunk = text[i : i + chunk_size]
            if chunk:
                chunks.append(chunk)
            i += step
        return chunks

    def _hybrid_chunk(self, text: str, chunk_size: int, overlap_size: int) -> list[str]:
        """Semantic paragraph splits; apply overlap chunking within oversized paragraphs."""
        paragraphs = self._semantic_chunk(text)
        chunks: list[str] = []
        for para in paragraphs:
            if len(para) <= chunk_size:
                chunks.append(para)
            else:
                chunks.extend(self._overlap_chunk(para, chunk_size, overlap_size))
        return chunks
