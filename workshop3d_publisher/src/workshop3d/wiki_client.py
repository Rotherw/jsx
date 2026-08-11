"""Conservative enrichment from the public Wiki KF2 (Wiki.js).

Search is public GraphQL; page bodies are read from their normal public HTML
pages. A result is used only when the title closely matches the product-folder
name. Network/search failures never block preparing or publishing a product.
"""
from __future__ import annotations

import json
import re
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any
from urllib.parse import quote

from .config import Config


_SEARCH_QUERY = """
query Search($q: String!, $path: String, $locale: String!) {
  pages {
    search(query: $q, path: $path, locale: $locale) {
      results { id title description path locale }
      totalHits
    }
  }
}
""".strip()

_NOISE = {
    "workshop3d", "workshop", "kf2", "model", "models", "miniature",
    "miniatures", "figurka", "figura", "stl", "3mf", "glb", "obj",
    "print", "printable", "druk", "3d", "render", "cover", "final",
    "gotowe", "bundle", "pack", "set", "kroniki", "fallathanu",
}


@dataclass(frozen=True)
class WikiMatch:
    title: str
    description: str
    path: str
    url: str
    excerpt: str
    score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "path": self.path,
            "url": self.url,
            "excerpt": self.excerpt,
            "score": round(self.score, 3),
        }


class WikiKF2Client:
    def __init__(self, config: Config):
        self.base_url = str(config.get("wiki.base_url", "https://wiki.kf2.pl")).rstrip("/")
        self.locale = str(config.get("wiki.locale", "pl"))
        self.timeout = float(config.get("wiki.timeout_seconds", 8))
        self.min_score = float(config.get("wiki.minimum_match_score", 0.78))

    def find(self, folder_name: str) -> WikiMatch | None:
        query_tokens = _tokens(folder_name)
        if not query_tokens:
            return None
        query = " ".join(query_tokens)
        results = self._search(query)
        ranked = sorted(
            ((self._score(query_tokens, item), item) for item in results),
            key=lambda pair: pair[0],
            reverse=True,
        )
        if not ranked or ranked[0][0] < self.min_score:
            return None
        # Ambiguous matches (e.g. a folder named just "smok") are unsafe.
        if len(ranked) > 1 and ranked[0][0] - ranked[1][0] < 0.12:
            return None

        score, item = ranked[0]
        path = str(item.get("path", "")).strip("/")
        if not path:
            return None
        url = f"{self.base_url}/{quote(path, safe='/')}"
        excerpt = self._page_excerpt(url)
        description = _clean_text(str(item.get("description", "")))
        if not excerpt:
            excerpt = description
        return WikiMatch(
            title=str(item.get("title", "")).strip(),
            description=description,
            path=path,
            url=url,
            excerpt=excerpt,
            score=score,
        )

    def _search(self, query: str) -> list[dict[str, Any]]:
        payload = json.dumps({
            "query": _SEARCH_QUERY,
            "variables": {"q": query, "path": "", "locale": self.locale},
        }).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/graphql",
            data=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (OSError, ValueError, urllib.error.URLError):
            return []
        return (((data.get("data") or {}).get("pages") or {}).get("search") or {}).get("results", []) or []

    def _page_excerpt(self, url: str) -> str:
        request = urllib.request.Request(url, headers={"Accept": "text/html"})
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                html = response.read(2_000_000).decode("utf-8", errors="replace")
        except (OSError, urllib.error.URLError):
            return ""
        parser = _ContentsParser()
        try:
            parser.feed(html)
        except Exception:
            return ""
        return _first_sentences(_clean_text(" ".join(parser.parts)), max_chars=650)

    @staticmethod
    def _score(query_tokens: list[str], item: dict[str, Any]) -> float:
        title_tokens = _tokens(str(item.get("title", "")))
        if not title_tokens:
            return 0.0
        q, t = set(query_tokens), set(title_tokens)
        if q == t:
            return 1.0
        overlap = len(q & t)
        coverage = overlap / len(t)
        precision = overlap / len(q)
        score = (0.7 * coverage) + (0.3 * precision)
        # Contiguous title in folder names deserves a small bonus while still
        # requiring token coverage (e.g. "Czerwony Smok 75mm STL").
        q_text, t_text = " ".join(query_tokens), " ".join(title_tokens)
        if t_text and t_text in q_text:
            score += 0.08
        return min(score, 1.0)


def enrich_metadata(metadata: dict[str, Any], match: WikiMatch) -> dict[str, Any]:
    """Attach sourced lore without pretending it was independently verified."""
    metadata["WIKI_KF2"] = match.to_dict()
    source_line = f"Źródło świata: {match.title} — {match.url}"
    pl_parts = [metadata.get("DESCRIPTION_PL", "").rstrip()]
    if match.excerpt:
        pl_parts += ["", "Informacje ze świata Kronik Fallathanu:", match.excerpt]
    pl_parts += ["", source_line]
    metadata["DESCRIPTION_PL"] = "\n".join(part for part in pl_parts if part is not None).strip()

    en_parts = [metadata.get("DESCRIPTION_EN", "").rstrip(), "", "Kroniki Fallathanu source:",
                f"{match.title} — {match.url}"]
    metadata["DESCRIPTION_EN"] = "\n".join(en_parts).strip()
    return metadata


class _ContentsParser(HTMLParser):
    """Extract only Wiki.js' <template slot="contents"> article body."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.skip_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        if tag == "template" and attr.get("slot") == "contents":
            self.depth = 1
            return
        if self.depth:
            if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}:
                self.depth += 1
            if tag in ("script", "style", "nav"):
                self.skip_depth = self.depth

    def handle_endtag(self, tag: str) -> None:
        if not self.depth:
            return
        if self.skip_depth == self.depth:
            self.skip_depth = 0
        self.depth -= 1

    def handle_data(self, data: str) -> None:
        if self.depth and not self.skip_depth and data.strip():
            self.parts.append(data)


def _tokens(value: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    words = re.findall(r"[a-zA-Z0-9]+", normalized.lower())
    return [
        word for word in words
        if len(word) > 1
        and word not in _NOISE
        and not word.isdigit()
        and not re.fullmatch(r"(?:v)?\d+(?:mm|cm|in|inch|scale)?", word)
    ]


def _clean_text(value: str) -> str:
    value = value.replace("¶", " ")
    return re.sub(r"\s+", " ", value).strip()


def _first_sentences(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    cut = value[:max_chars]
    last = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    if last >= int(max_chars * 0.5):
        return cut[: last + 1].strip()
    return cut.rsplit(" ", 1)[0].rstrip(" ,;:") + "…"
