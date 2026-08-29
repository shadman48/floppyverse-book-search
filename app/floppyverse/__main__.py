import sys

from PySide6.QtWidgets import QApplication

from .ui import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Floppyverse Book Search")
    app.setOrganizationName("Floppyverse")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

