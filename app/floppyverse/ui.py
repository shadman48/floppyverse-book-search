from __future__ import annotations

from functools import partial

import requests
from PySide6.QtCore import QByteArray, QThreadPool, Qt, QTimer, QUrl, QRunnable, Signal, QSize
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (QButtonGroup, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget)

from .models import BookResult, deduplicate
from .sources import ALL_SOURCES
from .workers import SearchWorker

STYLE = """
QWidget { background:#11151c; color:#e8edf5; font-family:'Segoe UI'; font-size:14px; }
QMainWindow { background:#0c1016; }
QLineEdit { background:#1b2230; border:1px solid #354055; border-radius:9px; padding:11px 13px; font-size:16px; }
QLineEdit:focus { border-color:#6aa9ff; }
QPushButton { background:#232c3b; border:1px solid #3a465b; border-radius:8px; padding:8px 13px; }
QPushButton:hover { background:#303c50; } QPushButton:checked,QPushButton#primary { background:#2671d9; border-color:#5597ef; }
QPushButton:disabled { color:#778090; background:#191e28; }
QFrame#card { background:#171d27; border:1px solid #293345; border-radius:11px; }
QLabel#title { font-size:17px; font-weight:600; } QLabel#muted { color:#9ca9ba; }
QLabel#badge { color:#bcd8ff; background:#223551; border-radius:5px; padding:3px 7px; }
QScrollArea { border:none; }
"""


class CoverWorker(QRunnable):
    def __init__(self, url: str, signal):
        super().__init__()
        self.url, self.signal = url, signal

    def run(self):
        try:
            response = requests.get(self.url, timeout=(3, 8), headers={"User-Agent": "FloppyverseBookSearch/1.0"})
            response.raise_for_status()
            if len(response.content) <= 5_000_000:
                self.signal.emit(QByteArray(response.content))
        except requests.RequestException:
            pass


class WrappedLabel(QLabel):
    """A wrapping label that always reserves the full rendered text height."""

    def __init__(self, text="", parent=None, extra_height=4):
        super().__init__(text, parent)
        self._extra_height = extra_height
        self.setWordWrap(True)
        policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)

    def heightForWidth(self, width):
        margins = self.contentsMargins()
        available = max(1, width - margins.left() - margins.right())
        bounds = self.fontMetrics().boundingRect(
            0, 0, available, 100_000,
            int(Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop), self.text()
        )
        return bounds.height() + margins.top() + margins.bottom() + self._extra_height

    def sizeHint(self):
        hint = super().sizeHint()
        return QSize(hint.width(), self.heightForWidth(max(1, self.width())))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        needed = self.heightForWidth(event.size().width())
        if self.minimumHeight() != needed or self.maximumHeight() != needed:
            self.setFixedHeight(needed)
            self.updateGeometry()


class ResultCard(QFrame):
    cover_ready = Signal(QByteArray)

    def __init__(self, item: BookResult, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        row = QHBoxLayout(self); row.setContentsMargins(14, 14, 14, 14); row.setSpacing(14)
        self.cover = QLabel("📖" if item.media_type == "ebook" else "🎧")
        self.cover.setAlignment(Qt.AlignCenter); self.cover.setFixedSize(76, 108)
        self.cover.setStyleSheet("background:#222b39;border-radius:6px;font-size:28px;")
        row.addWidget(self.cover)
        text = QVBoxLayout()
        self.title_label = WrappedLabel(item.title); self.title_label.setObjectName("title"); text.addWidget(self.title_label)
        self.author_label = WrappedLabel(item.author_text); self.author_label.setObjectName("muted"); text.addWidget(self.author_label)
        details = [item.source, " / ".join(item.formats) or item.media_type.title()]
        if item.duration: details.append(item.duration)
        if item.chapters: details.append(f"{item.chapters} chapters")
        self.meta_label = WrappedLabel("  •  ".join(details), extra_height=8); self.meta_label.setObjectName("badge")
        self.meta_label.setMaximumWidth(620); text.addWidget(self.meta_label); text.addStretch()
        actions = QHBoxLayout(); actions.setAlignment(Qt.AlignLeft)
        for label, url in (("Open", item.open_url), ("Download", item.download_url)):
            button = QPushButton(label); button.setEnabled(bool(url))
            button.setToolTip("Opens in your browser" if url else "No direct file supplied by this catalog")
            button.clicked.connect(partial(self._visit, url)); actions.addWidget(button)
        text.addLayout(actions); row.addLayout(text, 1)
        self.cover_ready.connect(self._set_cover)
        if item.cover_url: QThreadPool.globalInstance().start(CoverWorker(item.cover_url, self.cover_ready))

    @staticmethod
    def _visit(url):
        if url: QDesktopServices.openUrl(QUrl(url))

    def _set_cover(self, data):
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            self.cover.setPixmap(pixmap.scaled(self.cover.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("Floppyverse Book Search"); self.resize(980, 760); self.setMinimumSize(720, 540)
        self.setStyleSheet(STYLE); self.pool = QThreadPool(self); self.pool.setMaxThreadCount(6)
        self.results = []; self.pending = set(); self.errors = {}; self.search_generation = 0; self._build_ui()

    def _build_ui(self):
        root = QWidget(); outer = QVBoxLayout(root); outer.setContentsMargins(24, 20, 24, 18)
        heading = QLabel("Floppyverse Book Search"); heading.setStyleSheet("font-size:25px;font-weight:700;"); outer.addWidget(heading)
        subtitle = QLabel("Find free, public-domain and openly available ebooks and audiobooks"); subtitle.setObjectName("muted"); outer.addWidget(subtitle)
        search_row = QHBoxLayout(); self.query = QLineEdit(); self.query.setPlaceholderText("Search by title, author, or subject…")
        self.query.returnPressed.connect(self.start_search); search_row.addWidget(self.query, 1)
        self.search_button = QPushButton("Search"); self.search_button.setObjectName("primary"); self.search_button.clicked.connect(self.start_search)
        search_row.addWidget(self.search_button); outer.addLayout(search_row)
        filters = QHBoxLayout()
        self.type_buttons = self._filter_group(filters, [("All", "all"), ("Ebooks", "ebook"), ("Audiobooks", "audiobook")])
        filters.addSpacing(18)
        self.source_buttons = self._filter_group(filters, [("All sources", "all"), ("Gutenberg", "Project Gutenberg"), ("LibriVox", "LibriVox"), ("Internet Archive", "Internet Archive")])
        filters.addStretch(); outer.addLayout(filters)
        self.status = QLabel("Ready — try “H. G. Wells”, “Frankenstein”, or “science fiction”."); self.status.setObjectName("muted"); self.status.setWordWrap(True); outer.addWidget(self.status)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); self.results_host = QWidget(); self.results_layout = QVBoxLayout(self.results_host)
        self.results_layout.setContentsMargins(0, 6, 8, 6); self.results_layout.setSpacing(10); self.results_layout.addStretch(); scroll.setWidget(self.results_host)
        outer.addWidget(scroll, 1); self.setCentralWidget(root); QTimer.singleShot(0, self.query.setFocus)

    def _filter_group(self, layout, choices):
        group = QButtonGroup(self); group.setExclusive(True)
        for index, (label, value) in enumerate(choices):
            button = QPushButton(label); button.setCheckable(True); button.setProperty("filter_value", value); button.setChecked(index == 0)
            button.clicked.connect(self.render_results); group.addButton(button); layout.addWidget(button)
        return group

    def start_search(self):
        query = self.query.text().strip()
        if len(query) < 2: self.status.setText("Enter at least two characters to search."); return
        self.search_generation += 1; generation = self.search_generation; self.results = []; self.errors = {}
        self.pending = {source.name for source in ALL_SOURCES}; self.search_button.setEnabled(False)
        self.status.setText("Searching Project Gutenberg, LibriVox, and Internet Archive…"); self.render_results()
        for source in ALL_SOURCES:
            worker = SearchWorker(source, query)
            worker.signals.succeeded.connect(lambda name, items, g=generation: self._received(g, items))
            worker.signals.failed.connect(lambda name, error, g=generation: self._failed(g, name, error))
            worker.signals.finished.connect(lambda name, g=generation: self._finished(g, name)); self.pool.start(worker)

    def _received(self, generation, items):
        if generation == self.search_generation: self.results = deduplicate(self.results + items); self.render_results()

    def _failed(self, generation, name, error):
        if generation == self.search_generation: self.errors[name] = error

    def _finished(self, generation, name):
        if generation != self.search_generation: return
        self.pending.discard(name)
        if self.pending: self.status.setText(f"Found {len(self.results)} results — still searching {', '.join(sorted(self.pending))}…")
        else:
            self.search_button.setEnabled(True); suffix = f" {len(self.errors)} source(s) could not be reached." if self.errors else " All sources completed."
            self.status.setText(f"Found {len(self.results)} unique results.{suffix}"); self.status.setToolTip("\n".join(self.errors.values()))
        self.render_results()

    @staticmethod
    def _selected(group):
        button = group.checkedButton(); return button.property("filter_value") if button else "all"

    def render_results(self):
        while self.results_layout.count() > 1:
            item = self.results_layout.takeAt(0); widget = item.widget()
            if widget: widget.deleteLater()
        kind, source = self._selected(self.type_buttons), self._selected(self.source_buttons)
        visible = [item for item in self.results if (kind == "all" or item.media_type == kind) and (source == "all" or source in item.source.split(" + "))]
        if not visible and not self.pending:
            empty = QLabel("No matching results. Try a broader title, author, or subject."); empty.setAlignment(Qt.AlignCenter); empty.setObjectName("muted")
            self.results_layout.insertWidget(0, empty)
        else:
            for item in visible: self.results_layout.insertWidget(self.results_layout.count() - 1, ResultCard(item))
