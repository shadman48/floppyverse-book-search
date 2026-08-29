import unittest
from floppyverse.models import BookResult, deduplicate
from floppyverse.sources.gutenberg import GutenbergSource
from floppyverse.sources.internet_archive import InternetArchiveSource

class ModelTests(unittest.TestCase):
    def test_removes_marc_subfield_markers(self):
        item = BookResult("The red planet : $b a science fiction novel", ["Writer, A. $c editor"], "Catalog", "ebook")
        self.assertEqual(item.title, "The red planet: a science fiction novel")
        self.assertEqual(item.authors, ["Writer, A. editor"])

    def test_deduplicates_same_work_and_medium(self):
        a = BookResult("Frankenstein", ["Mary Shelley"], "Project Gutenberg", "ebook", ["EPUB"])
        b = BookResult("Frankenstein!", ["Mary Shelley"], "Internet Archive", "ebook", ["PDF"])
        c = BookResult("Frankenstein", ["Mary Shelley"], "LibriVox", "audiobook", ["MP3"])
        result = deduplicate([a, b, c]); self.assertEqual(len(result), 2)
        ebook = next(x for x in result if x.media_type == "ebook"); self.assertEqual(ebook.formats, ["EPUB", "PDF"])

    def test_gutenberg_prefers_epub(self):
        formats = {"text/html": "a.html", "application/epub+zip": "a.epub"}
        self.assertEqual(GutenbergSource._best_download(formats), "a.epub")

    def test_archive_audio_conversion(self):
        item = InternetArchiveSource()._convert({"identifier":"abc", "title":"A", "mediatype":"audio", "format":["VBR MP3"]})
        self.assertEqual(item.media_type, "audiobook"); self.assertIn("MP3", item.formats)

if __name__ == "__main__": unittest.main()
