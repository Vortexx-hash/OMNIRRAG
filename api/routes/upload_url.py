"""
URL upload route — fetches a web page, extracts its text, and ingests it
through the same upload pipeline as text/PDF documents.

Edge cases handled:
- Invalid / unreachable URL          → HTTP 502
- SSL certificate errors             → HTTP 502
- Request timeout (15 s)             → HTTP 408
- Non-HTML content types             → HTTP 422
- HTTP 4xx / 5xx from remote server  → mirrors status code
- Response too large (> 2 MB)        → HTTP 413
- No extractable text after cleaning → HTTP 422
- Encoding detection failures        → falls back to utf-8 with replace
- Redirect loops                     → requests raises TooManyRedirects → 502
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import api.state as state
from api.schemas import UploadResponse
from api.state import get_pipeline
from pipeline.upload.chunker import ChunkingStrategy

router = APIRouter(tags=["upload"])

_MAX_BYTES = 2 * 1024 * 1024  # 2 MB
_FETCH_TIMEOUT = 15            # seconds
_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; RAGPipelineBot/1.0; +research-purposes)"
    ),
    "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Tags whose entire subtree should be removed before text extraction
_STRIP_TAGS = {
    "script", "style", "noscript", "nav", "footer", "header",
    "aside", "form", "button", "iframe", "svg", "figure",
    "meta", "link", "head",
}

# Domains / patterns that signal a higher-credibility source type
_DOMAIN_TIER: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\.gov(\.[a-z]{2})?$"), "government"),
    (re.compile(r"(pubmed|ncbi\.nlm|nih\.gov|clinicaltrials|cochrane|bmj\.com|"
                r"nejm\.org|thelancet|jamanetwork|nature\.com|science\.org|"
                r"cell\.com|springer|wiley|tandfonline|sagepub|frontiersin|"
                r"plos|arxiv|biorxiv|medrxiv|ssrn)"), "peer_reviewed"),
    (re.compile(r"\.(edu|ac\.[a-z]{2})$"), "academic"),
]


class UploadUrlRequest(BaseModel):
    url: str
    doc_id: str
    source_type: str = "unverified"
    chunking_strategy: str = "semantic"
    title: Optional[str] = None
    author: Optional[str] = None


def _suggest_source_type(url: str) -> str:
    """Heuristically infer source type from the domain."""
    try:
        hostname = urlparse(url).hostname or ""
    except Exception:
        return "unverified"
    for pattern, stype in _DOMAIN_TIER:
        if pattern.search(hostname):
            return stype
    return "unverified"


def _fetch_and_extract(url: str) -> tuple[str, str]:
    """
    Fetch *url* and return (clean_text, page_title).

    Raises HTTPException on every failure.
    """
    # ── Fetch ────────────────────────────────────────────────────────────────
    try:
        resp = requests.get(
            url,
            headers=_REQUEST_HEADERS,
            timeout=_FETCH_TIMEOUT,
            stream=True,
            allow_redirects=True,
        )
    except requests.exceptions.SSLError as exc:
        raise HTTPException(502, detail=f"SSL error fetching URL: {exc}") from exc
    except requests.exceptions.ConnectionError as exc:
        raise HTTPException(502, detail=f"Cannot reach URL: {exc}") from exc
    except requests.exceptions.Timeout:
        raise HTTPException(408, detail=f"URL fetch timed out after {_FETCH_TIMEOUT}s")
    except requests.exceptions.TooManyRedirects:
        raise HTTPException(502, detail="URL resulted in too many redirects")
    except requests.exceptions.RequestException as exc:
        raise HTTPException(502, detail=f"Request error: {exc}") from exc

    # Mirror remote HTTP errors
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=resp.status_code,
            detail=f"Remote server returned HTTP {resp.status_code}",
        )

    # ── Content-type check ───────────────────────────────────────────────────
    content_type = resp.headers.get("Content-Type", "").lower()
    if not any(t in content_type for t in ("text/html", "text/plain", "application/xhtml")):
        raise HTTPException(
            422,
            detail=(
                f"Unsupported content type '{content_type}'. "
                "Only HTML and plain-text pages are supported."
            ),
        )

    # ── Size guard ───────────────────────────────────────────────────────────
    chunks: list[bytes] = []
    total = 0
    for chunk in resp.iter_content(chunk_size=65536):
        total += len(chunk)
        if total > _MAX_BYTES:
            raise HTTPException(
                413,
                detail=f"Page exceeds the {_MAX_BYTES // (1024*1024)} MB size limit",
            )
        chunks.append(chunk)
    raw_bytes = b"".join(chunks)

    # ── Decode ───────────────────────────────────────────────────────────────
    encoding = resp.encoding or "utf-8"
    try:
        html = raw_bytes.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        html = raw_bytes.decode("utf-8", errors="replace")

    # Plain-text shortcut
    if "text/plain" in content_type:
        text = html.strip()
        if not text:
            raise HTTPException(422, detail="Page contains no extractable text")
        return text, url

    # ── Parse HTML ───────────────────────────────────────────────────────────
    soup = BeautifulSoup(html, "lxml")

    # Extract page title before stripping tags
    title_tag = soup.find("title")
    page_title = title_tag.get_text(strip=True) if title_tag else ""

    # Remove boilerplate subtrees
    for tag in soup.find_all(_STRIP_TAGS):
        tag.decompose()

    # Prefer <main> or <article>, fall back to <body>
    main = soup.find("main") or soup.find("article") or soup.find("body")
    if main is None:
        main = soup

    # Collect text: join block-level elements with newlines
    lines: list[str] = []
    for element in main.descendants:
        if hasattr(element, "name") and element.name in {
            "p", "h1", "h2", "h3", "h4", "h5", "h6",
            "li", "td", "th", "blockquote", "pre", "dt", "dd",
        }:
            txt = element.get_text(separator=" ", strip=True)
            if txt:
                lines.append(txt)

    text = "\n\n".join(lines)

    # Remove excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    if len(text) < 100:
        raise HTTPException(
            422,
            detail=(
                "Could not extract meaningful text from the page. "
                "The page may be JavaScript-rendered, paywalled, or contain only images."
            ),
        )

    return text, page_title


@router.post("/upload/url", response_model=UploadResponse)
def upload_url(body: UploadUrlRequest) -> UploadResponse:
    """
    Fetch a web page, extract its text, and ingest it through the RAG pipeline.
    """
    text, page_title = _fetch_and_extract(body.url)

    pipeline = get_pipeline()

    strategy_map = {
        "semantic": ChunkingStrategy.SEMANTIC,
        "character": ChunkingStrategy.CHARACTER,
        "overlap": ChunkingStrategy.OVERLAP,
        "hybrid": ChunkingStrategy.HYBRID,
    }
    strategy = strategy_map.get(body.chunking_strategy, ChunkingStrategy.SEMANTIC)

    source_metadata: dict = {
        "source_type": body.source_type,
        "url": body.url,
    }
    if body.title or page_title:
        source_metadata["title"] = body.title or page_title
    if body.author:
        source_metadata["author"] = body.author

    chunk_ids = pipeline.upload(
        text=text,
        source_metadata=source_metadata,
        doc_id=body.doc_id,
        strategy=strategy,
    )

    state.add_document({
        "doc_id": body.doc_id,
        "title": body.title or page_title or body.url,
        "source_type": body.source_type,
        "chunks_stored": len(chunk_ids),
        "chunk_ids": chunk_ids,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    })

    return UploadResponse(
        doc_id=body.doc_id,
        chunks_stored=len(chunk_ids),
        chunk_ids=chunk_ids,
    )


@router.get("/upload/url/suggest-source-type")
def suggest_source_type(url: str) -> dict:
    """Return a heuristic source_type suggestion for the given URL."""
    return {"suggested_source_type": _suggest_source_type(url)}
