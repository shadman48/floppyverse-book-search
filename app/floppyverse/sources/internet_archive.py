from __future__ import annotations

from urllib.parse import quote

from .base import BookSource
from ..models import BookResult


class InternetArchiveSource(BookSource):
    name = "Internet Archive"
    endpoint = "https://archive.org/advancedsearch.php"

    def search(self, query: str, limit: int = 30) -> list[BookResult]:
        safe = query.replace('"', " ").strip()
        expression = f'(title:("{safe}") OR creator:("{safe}") OR subject:("{safe}")) AND mediatype:(texts OR audio)'
        params = {
            "q": expression, "fl[]": ["identifier", "title", "creator", "mediatype", "format", "description"],
            "rows": limit, "page": 1, "output": "json", "sort[]": "downloads desc",
        }
        data = self.get_json(self.endpoint, params=params)
        docs = (data.get("response") or {}).get("docs", [])
        return [self._convert(doc) for doc in docs if doc.get("identifier")]

    def _convert(self, doc: dict) -> BookResult:
        identifier = str(doc["identifier"])
        formats = doc.get("format") or []
        if isinstance(formats, str):
            formats = [formats]
        media_type = "audiobook" if doc.get("mediatype") == "audio" else "ebook"
        creator = doc.get("creator") or []
        if isinstance(creator, str):
            creator = [creator]
        labels = self._labels(formats, media_type)
        return BookResult(
            title=doc.get("title") or "Untitled", authors=creator, source=self.name,
            media_type=media_type, formats=labels,
            cover_url=f"https://archive.org/services/img/{quote(identifier)}",
            open_url=f"https://archive.org/details/{quote(identifier)}",
            # IA file names require a metadata call; the item page is the safe rights-aware download destination.
            download_url=None, description=self._description(doc.get("description")), identifier=identifier,
        )

    @staticmethod
    def _description(value) -> str | None:
        if isinstance(value, list):
            value = value[0] if value else None
        return value if isinstance(value, str) else None

    @staticmethod
    def _labels(formats: list[str], media_type: str) -> list[str]:
        wanted = ["EPUB", "PDF", "DjVu", "Text", "M4B", "MP3", "Ogg Vorbis"]
        found = [label for label in wanted if any(label.lower() in str(fmt).lower() for fmt in formats)]
        return found[:5] or (["Audio"] if media_type == "audiobook" else ["Text"])

