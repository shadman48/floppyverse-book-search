from concurrent.futures import ThreadPoolExecutor, as_completed

from .base import BookSource
from ..models import BookResult


class LibriVoxSource(BookSource):
    name = "LibriVox"
    endpoint = "https://librivox.org/api/feed/audiobooks/"

    def search(self, query: str, limit: int = 30) -> list[BookResult]:
        # Search title, author and genre; merge by LibriVox id before conversion.
        found, errors = {}, []

        def fetch(field):
            return self.get_json(self.endpoint, params={field: f"^{query}", "format": "json", "extended": "1", "limit": limit})

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(fetch, field): field for field in ("title", "author", "genre")}
            for future in as_completed(futures):
                try:
                    data = future.result()
                    for book in data.get("books", []) if isinstance(data, dict) else []:
                        found[str(book.get("id") or book.get("url_librivox"))] = book
                except Exception as exc:
                    errors.append(exc)
        if not found and errors:
            raise errors[-1]
        books = list(found.values())[:limit]
        results = []
        for book in books:
            authors = []
            for author in book.get("authors") or []:
                name = " ".join(filter(None, [author.get("first_name"), author.get("last_name")])).strip()
                if name:
                    authors.append(name)
            sections = book.get("sections") or []
            results.append(BookResult(
                title=book.get("title") or "Untitled",
                authors=authors,
                source=self.name,
                media_type="audiobook",
                formats=["MP3"],
                cover_url=book.get("url_cover"),
                open_url=book.get("url_librivox"),
                download_url=book.get("url_zip_file"),
                duration=book.get("totaltime"),
                chapters=len(sections) or None,
                description=book.get("description"),
                identifier=str(book.get("id", "")) or None,
            ))
        return results
