from .gutenberg import GutenbergSource
from .internet_archive import InternetArchiveSource
from .librivox import LibriVoxSource

ALL_SOURCES = (GutenbergSource(), LibriVoxSource(), InternetArchiveSource())

