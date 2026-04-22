import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from app.ui.main_window import MainWindow

DB_PATH = Path(__file__).parent / "db" / "crypters.db"
CALIBRATION_PATH = Path(__file__).parent.parent / "data" / "graph_calibration.json"


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
