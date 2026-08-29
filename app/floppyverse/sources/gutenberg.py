from urllib.parse import quote

from .base import BookSource
from ..models import BookResult


class GutenbergSource(BookSource):
    name = "Project Gutenberg"
    endpoint = "https://gutendex.com/books/"

    def search(self, query: str, limit: int = 30) -> list[BookResult]:
        data = self.get_json(self.endpoint, params={"search": query})
        results = []
        for book in data.get("results", [])[:limit]:
            formats = book.get("formats") or {}
            download = self._best_download(formats)
            book_id = str(book.get("id", ""))
            results.append(BookResult(
                title=book.get("title") or "Untitled",
                authors=[a.get("name", "") for a in book.get("authors", []) if a.get("name")],
                source=self.name,
                media_type="ebook",
                formats=self._format_names(formats),
                cover_url=formats.get("image/jpeg"),
                open_url=f"https://www.gutenberg.org/ebooks/{quote(book_id)}" if book_id else None,
                download_url=download,
                identifier=book_id or None,
            ))
        return results

    @staticmethod
    def _best_download(formats: dict) -> str | None:
        for mime in ("application/epub+zip", "application/x-mobipocket-ebook", "text/html", "text/plain; charset=utf-8", "application/pdf"):
            value = formats.get(mime)
            if value and not value.endswith(".zip"):
                return value
        return None

    @staticmethod
    def _format_names(formats: dict) -> list[str]:
        labels = {
            "application/epub+zip": "EPUB", "application/x-mobipocket-ebook": "Kindle",
            "text/html": "HTML", "text/plain; charset=utf-8": "Text", "application/pdf": "PDF",
        }
        return [label for mime, label in labels.items() if formats.get(mime)]

