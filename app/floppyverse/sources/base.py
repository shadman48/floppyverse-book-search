from __future__ import annotations

from abc import ABC, abstractmethod
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..models import BookResult


class SourceError(RuntimeError):
    pass


class BookSource(ABC):
    name: str
    timeout = (4, 12)

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "FloppyverseBookSearch/1.0 (desktop catalog client)"})
        retry = Retry(total=1, connect=1, read=0, backoff_factor=0.35,
                      status_forcelist=(429, 500, 502, 503, 504), allowed_methods=("GET",))
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    def get_json(self, url: str, **kwargs):
        try:
            response = self.session.get(url, timeout=self.timeout, **kwargs)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            raise SourceError(f"{self.name}: {exc}") from exc

    @abstractmethod
    def search(self, query: str, limit: int = 30) -> list[BookResult]:
        raise NotImplementedError
