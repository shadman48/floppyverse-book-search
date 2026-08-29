from __future__ import annotations

from dataclasses import dataclass, field
import re
import unicodedata


@dataclass(slots=True)
class BookResult:
    title: str
    authors: list[str]
    source: str
    media_type: str
    formats: list[str] = field(default_factory=list)
    cover_url: str | None = None
    open_url: str | None = None
    download_url: str | None = None
    duration: str | None = None
    chapters: int | None = None
    description: str | None = None
    identifier: str | None = None

    def __post_init__(self) -> None:
        # Some library catalogs expose MARC subfield markers such as "$b"
        # (subtitle) inside otherwise human-readable titles.
        self.title = clean_catalog_text(self.title)
        self.authors = [clean_catalog_text(author) for author in self.authors]

    @property
    def author_text(self) -> str:
        return ", ".join(self.authors) if self.authors else "Unknown author"


def _key_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def clean_catalog_text(value: str) -> str:
    value = re.sub(r"\s*:\s*\$[a-z0-9]\s*", ": ", value, flags=re.IGNORECASE)
    value = re.sub(r"\s*\$[a-z0-9]\s*", " ", value, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", value).strip()


def work_key(item: BookResult) -> tuple[str, str, str]:
    # Media type remains part of the key so an ebook and audiobook of the same work
    # both survive. Source variants of the same medium collapse where practical.
    return (_key_text(item.title), _key_text(item.authors[0] if item.authors else ""), item.media_type)


def deduplicate(items: list[BookResult]) -> list[BookResult]:
    merged: dict[tuple[str, str, str], BookResult] = {}
    for item in items:
        key = work_key(item)
        if not key[0]:
            continue
        current = merged.get(key)
        if current is None:
            merged[key] = item
            continue
        current.formats = sorted(set(current.formats + item.formats))
        if item.source not in current.source.split(" + "):
            current.source += " + " + item.source
        current.cover_url = current.cover_url or item.cover_url
        current.open_url = current.open_url or item.open_url
        current.download_url = current.download_url or item.download_url
        current.duration = current.duration or item.duration
        current.chapters = current.chapters or item.chapters
    return sorted(merged.values(), key=lambda x: (_key_text(x.title), _key_text(x.author_text)))
