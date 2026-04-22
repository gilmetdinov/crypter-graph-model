from __future__ import annotations

from pathlib import Path
from typing import Any

from PyQt5.QtCore import QObject, QThread, Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.graph.model import CrypterGraph

# Маппинг layer-имени → node_id
_ENC_TO_NODE: dict[str, str] = {
    "XOR": "v_XOR",
    "AES128": "v_AES128",
    "AES256": "v_AES256",
}
_COMP_TO_NODE: dict[str, str] = {
    "nocomp": "v_nocomp",
    "LZ4": "v_LZ4",
    "LZMA": "v_LZMA",
}
_OBF_TO_NODE: dict[str, str] = {
    "noobf": "v_noobf",
    "meta": "v_meta",
    "virt": "v_virt",
    "poly": "v_poly",
}

_COLUMNS = [
    "№",
    "Сценарий",
    "Уровень",
    "Шифрование",
    "Компрессия",
    "Обфускация",
    "T (мс)",
    "S",
    "D",
    "Штраф",
    "Алг. (мс)",
]


class _Worker(QObject):
    finished = pyqtSignal(list)  # list[dict]

    def __init__(self, graph: CrypterGraph, db_path: Path) -> None:
        super().__init__()
        self.graph = graph
        self.db_path = db_path

    def run(self) -> None:
        from app.db.repository import ConfigRepository
        from app.experiments.run_scenarios import run_all

        repo = ConfigRepository(self.db_path)
        try:
            results = run_all(self.graph, repo)
        finally:
            repo.close()
        self.finished.emit(results)


class ExperimentsWidget(QWidget):
    path_selected = pyqtSignal(list)  # list[str] node_ids

    def __init__(self, graph: CrypterGraph, repo: Any) -> None:
        super().__init__()
        self._graph = graph
        self._db_path: Path = repo._db_path
        self._thread: QThread | None = None
        self._worker: _Worker | None = None
        self._results: list[dict[str, Any]] = []
        self._build_ui()

    # ------------------------------------------------------------------
    # Построение интерфейса
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Кнопка запуска
        btn_font = QFont()
        btn_font.setBold(True)
        self._btn_run = QPushButton("▶ Прогнать 12 сценариев")
        self._btn_run.setFont(btn_font)
        self._btn_run.setFixedHeight(36)
        self._btn_run.clicked.connect(self._on_run_clicked)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self._btn_run)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Прогресс-бар
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # marquee
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        # Таблица результатов
        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setHorizontalHeaderLabels(_COLUMNS)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.setSelectionBehavior(self._table.SelectRows)
        self._table.setEditTriggers(self._table.NoEditTriggers)
        self._table.cellClicked.connect(self._on_cell_clicked)
        layout.addWidget(self._table)

        # Метка с путём к отчёту
        self._lbl_report = QLabel()
        self._lbl_report.setVisible(False)
        layout.addWidget(self._lbl_report)

    # ------------------------------------------------------------------
    # Слоты
    # ------------------------------------------------------------------

    def _on_run_clicked(self) -> None:
        self._btn_run.setEnabled(False)
        self._progress.setVisible(True)
        self._table.setRowCount(0)
        self._lbl_report.setVisible(False)

        self._thread = QThread(self)
        self._worker = _Worker(self._graph, self._db_path)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_finished(self, results: list[dict[str, Any]]) -> None:
        self._results = results
        self._fill_table(results)

        # Сохранить отчёт
        from app.experiments.run_scenarios import write_report

        out_dir = Path("data/runs")
        report_path = write_report(results, out_dir)
        self._lbl_report.setText(f"Отчёт сохранён: {report_path}")
        self._lbl_report.setVisible(True)

        self._progress.setVisible(False)
        self._btn_run.setEnabled(True)

    def _fill_table(self, results: list[dict[str, Any]]) -> None:
        self._table.setRowCount(len(results))
        for row, r in enumerate(results):
            values = [
                str(row + 1),
                r["name"],
                str(r["level"]),
                r["enc"],
                r["comp"],
                r["obf"],
                f"{r['t']:.2f}",
                f"{r['s']:.2f}",
                f"{r['d']:.2f}",
                f"{r['penalty']:.3f}",
                f"{r['algo_ms']:.1f}",
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                self._table.setItem(row, col, item)

        self._table.resizeColumnsToContents()
        # Сценарий остаётся растянутым
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

    def _on_cell_clicked(self, row: int, _col: int) -> None:
        if row < 0 or row >= len(self._results):
            return
        r = self._results[row]
        enc_node = _ENC_TO_NODE.get(r["enc"], "v_XOR")
        comp_node = _COMP_TO_NODE.get(r["comp"], "v_nocomp")
        obf_node = _OBF_TO_NODE.get(r["obf"], "v_noobf")
        path_node_ids = [
            "v_read",
            enc_node,
            comp_node,
            obf_node,
            "v_stubgen",
            "v_exec",
        ]
        self.path_selected.emit(path_node_ids)
