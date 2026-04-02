"""Regex-based parser for Obsidian-style link syntax in note content.

Supported syntax:
    [[Note Title]]                          → link to note by title
    [[note:uuid]]                           → link to note by ID
    [[doc:uuid|Display Name]]               → link to document
    [[artifact:uuid|Display Name]]          → link to artifact
    [label](url)                            → standard markdown URL/media
    [label](url?t=120)                      → video with timestamp (seconds)
    [label](url#page=3)                     → slide/PDF with page number
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from urllib.parse import urlparse, parse_qs

_UUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"

_INTERNAL_BY_ID = re.compile(
    rf"\[\[(?P<type>note|doc|artifact):(?P<id>{_UUID})(?:\|(?P<label>[^\]]+))?\]\]"
)

_NOTE_BY_TITLE = re.compile(
    r"\[\[(?P<title>[^\]:|\]]+)\]\]"
)

_MARKDOWN_LINK = re.compile(
    r"\[(?P<label>[^\]]+)\]\((?P<url>[^)]+)\)"
)

# Map short type names to canonical target_type values
_TYPE_MAP = {
    "note": "note",
    "doc": "document",
    "artifact": "artifact",
}


@dataclass
class ParsedLink:
    """A single link extracted from note content."""
    label: str
    target_type: str  # note | document | artifact | media | url
    target_id: Optional[str] = None  # UUID string for internal links
    target_url: Optional[str] = None  # URL for external links
    position: int = 0  # char offset of the match start
    media_meta: Optional[Dict] = field(default_factory=lambda: None)


def _extract_media_meta(url: str) -> Optional[Dict]:
    """Extract video timestamp or page number from URL query/fragment."""
    meta: Dict = {}

    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    # Handle malformed double-? URLs like "?v=abc?t=120"
    # where the second ? should be &
    if not qs.get("t") and "?t=" in url:
        # Try parsing the part after the last ?t=
        idx = url.rfind("?t=")
        if idx >= 0:
            raw_t = url[idx + 3:].split("&")[0].split("#")[0].rstrip(")")
            try:
                meta["timestamp_start"] = int(raw_t)
            except ValueError:
                meta["timestamp_start"] = raw_t

    # ?t=120 or ?t=1m30s  (we store raw seconds)
    if "t" in qs and "timestamp_start" not in meta:
        raw = qs["t"][0]
        try:
            meta["timestamp_start"] = int(raw)
        except ValueError:
            meta["timestamp_start"] = raw

    # #page=3
    if parsed.fragment:
        for part in parsed.fragment.split("&"):
            if part.startswith("page="):
                try:
                    meta["page_number"] = int(part.split("=", 1)[1])
                except ValueError:
                    pass

    return meta if meta else None


def _classify_url(url: str) -> str:
    """Classify a URL as 'media' or 'url' based on its content."""
    lower = url.lower()
    media_hosts = ("youtube.com", "youtu.be", "vimeo.com", "dailymotion.com")
    media_exts = (".mp4", ".mp3", ".wav", ".webm", ".ogg", ".m4a", ".mov", ".avi")

    parsed = urlparse(lower)
    if any(host in (parsed.netloc or "") for host in media_hosts):
        return "media"
    if any(parsed.path.endswith(ext) for ext in media_exts):
        return "media"
    return "url"


def extract_links(content: str) -> List[ParsedLink]:
    """Parse note content and return all embedded links.

    The function scans for three syntax patterns in order:
    1. Internal links by ID:  ``[[type:uuid|Label]]``
    2. Note links by title:   ``[[Note Title]]``
    3. Markdown links:        ``[label](url)``

    Returns a list of ParsedLink objects sorted by position.
    """
    if not content:
        return []

    links: List[ParsedLink] = []
    # Track matched spans to avoid double-matching
    matched_spans: set = set()

    # 1) Internal links by ID
    for m in _INTERNAL_BY_ID.finditer(content):
        matched_spans.add((m.start(), m.end()))
        link_type = _TYPE_MAP.get(m.group("type"), "url")
        label = m.group("label") or m.group("id")
        links.append(ParsedLink(
            label=label,
            target_type=link_type,
            target_id=m.group("id"),
            position=m.start(),
        ))

    # 2) Note links by title — skip spans already matched by pattern 1
    for m in _NOTE_BY_TITLE.finditer(content):
        if any(m.start() >= s and m.end() <= e for s, e in matched_spans):
            continue
        matched_spans.add((m.start(), m.end()))
        links.append(ParsedLink(
            label=m.group("title"),
            target_type="note",
            position=m.start(),
        ))

    # 3) Markdown links
    for m in _MARKDOWN_LINK.finditer(content):
        if any(m.start() >= s and m.end() <= e for s, e in matched_spans):
            continue
        url = m.group("url")
        target_type = _classify_url(url)
        media_meta = _extract_media_meta(url)
        links.append(ParsedLink(
            label=m.group("label"),
            target_type=target_type,
            target_url=url,
            position=m.start(),
            media_meta=media_meta,
        ))

    links.sort(key=lambda lnk: lnk.position)
    return links
