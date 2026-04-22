from __future__ import annotations

from typing import List, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QAbstractScrollArea,
    QGroupBox,
    QHeaderView,
    QPlainTextEdit,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.builder.assembler import AssembledConfig
from app.graph.optimizer import OptimizationResult

# ---------------------------------------------------------------------------
# Локализация выборов слоёв
# ---------------------------------------------------------------------------

_ENC_LABELS: dict[str, str] = {
    "XOR": "XOR",
    "AES128": "AES-128 CBC",
    "AES256": "AES-256 CBC",
}

_COMP_LABELS: dict[str, str] = {
    "nocomp": "Без компрессии",
    "LZ4": "LZ4",
    "LZMA": "LZMA",
}

_OBF_LABELS: dict[str, str] = {
    "noobf": "Без обфускации",
    "meta": "Метаморфизм",
    "virt": "Виртуализация",
    "poly": "Полиморфизм",
}

_LAYER_NAMES: list[str] = [
    "Чтение PE",
    "Шифрование",
    "Компрессия",
    "Обфускация",
    "Генерация stub",
    "Выполнение",
]

_METRIC_ROWS: list[str] = [
    "Суммарное время (мс)",
    "Криптостойкость S(P)",
    "Средняя энтропия E(P)",
    "Детектируемость D(P)",
]


def _dash_if_zero(value: float, fmt: str = ".2f") -> str:
    return "—" if value == 0.0 else format(value, fmt)


def _fit_table(widget: QAbstractScrollArea) -> None:
    """Make the table/tree expand to show all rows — no internal scrollbar."""
    widget.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
    widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
    widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)


class ResultsPanel(QWidget):
    path_highlighted = pyqtSignal(list)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._build_ui()

    # ------------------------------------------------------------------
    # Построение интерфейса
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)
        root.addWidget(self._build_path_group())
        root.addWidget(self._build_metrics_group())
        root.addWidget(self._build_details_group())
        root.addWidget(self._build_log_group())

    def _build_path_group(self) -> QGroupBox:
        group = QGroupBox("Выбранный путь")
        layout = QVBoxLayout(group)

        self._path_table = QTableWidget(6, 2)
        self._path_table.setHorizontalHeaderLabels(["Слой", "Алгоритм"])
        self._path_table.verticalHeader().setVisible(False)
        self._path_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._path_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._path_table.setAlternatingRowColors(True)
        _fit_table(self._path_table)

        # Заполнить слои
        for i, name in enumerate(_LAYER_NAMES):
            self._path_table.setItem(i, 0, QTableWidgetItem(name))
            self._path_table.setItem(i, 1, QTableWidgetItem("—"))

        layout.addWidget(self._path_table)
        return group

    def _build_metrics_group(self) -> QGroupBox:
        group = QGroupBox("Прогнозируемые характеристики")
        layout = QVBoxLayout(group)

        self._metrics_table = QTableWidget(4, 2)
        self._metrics_table.setHorizontalHeaderLabels(["Характеристика", "Значение"])
        self._metrics_table.verticalHeader().setVisible(False)
        self._metrics_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._metrics_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._metrics_table.setAlternatingRowColors(True)
        _fit_table(self._metrics_table)

        for i, name in enumerate(_METRIC_ROWS):
            self._metrics_table.setItem(i, 0, QTableWidgetItem(name))
            self._metrics_table.setItem(i, 1, QTableWidgetItem("—"))

        layout.addWidget(self._metrics_table)
        return group

    def _build_details_group(self) -> QGroupBox:
        group = QGroupBox("Детализация узлов")
        layout = QVBoxLayout(group)

        self._details_tree = QTreeWidget()
        self._details_tree.setColumnCount(5)
        self._details_tree.setHeaderLabels(["Узел", "t (мс)", "s", "e", "d"])
        self._details_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self._details_tree.setRootIsDecorated(False)
        self._details_tree.setAlternatingRowColors(True)
        _fit_table(self._details_tree)

        layout.addWidget(self._details_tree)
        return group

    def _build_log_group(self) -> QGroupBox:
        group = QGroupBox("Лог работы алгоритма")
        layout = QVBoxLayout(group)

        self._log_edit = QPlainTextEdit()
        self._log_edit.setReadOnly(True)
        self._log_edit.setMinimumHeight(100)

        mono_font = QFont("Monospace")
        mono_font.setStyleHint(QFont.Monospace)
        mono_font.setPointSize(9)
        self._log_edit.setFont(mono_font)

        layout.addWidget(self._log_edit)
        return group

    # ------------------------------------------------------------------
    # Публичный API
    # ------------------------------------------------------------------

    def display(self, result: OptimizationResult, assembled: AssembledConfig) -> None:
        self._fill_path_table(assembled)
        self._fill_metrics_table(result.metrics)
        self._fill_details_tree(result)
        self._fill_log(result)

        node_ids: List[str] = [n.id for n in result.path]
        self.path_highlighted.emit(node_ids)

    def clear(self) -> None:
        for i in range(6):
            item = self._path_table.item(i, 1)
            if item:
                item.setText("—")

        for i in range(4):
            item = self._metrics_table.item(i, 1)
            if item:
                item.setText("—")

        self._details_tree.clear()
        self._log_edit.clear()

    # ------------------------------------------------------------------
    # Вспомогательные методы заполнения
    # ------------------------------------------------------------------

    def _fill_path_table(self, assembled: AssembledConfig) -> None:
        choices = assembled.layer_choices
        enc_label = _ENC_LABELS.get(
            choices.get("encryption", ""), choices.get("encryption", "—")
        )
        comp_label = _COMP_LABELS.get(
            choices.get("compression", ""), choices.get("compression", "—")
        )
        obf_label = _OBF_LABELS.get(
            choices.get("obfuscation", ""), choices.get("obfuscation", "—")
        )

        algo_values = [
            "Чтение PE",
            enc_label,
            comp_label,
            obf_label,
            "Генерация stub",
            "Выполнение",
        ]

        for i, layer_name in enumerate(_LAYER_NAMES):
            self._path_table.item(i, 0).setText(layer_name)
            self._path_table.item(i, 1).setText(algo_values[i])

    def _fill_metrics_table(self, metrics: object) -> None:
        m = metrics
        e_text = f"{m.e:.2f} бит/байт" if m.e > 0 else "—"
        values = [
            f"{m.t:.1f}",
            f"{m.s:.2f}",
            e_text,
            f"{m.d:.2f}",
        ]
        for i, val in enumerate(values):
            self._metrics_table.item(i, 1).setText(val)

    def _fill_details_tree(self, result: OptimizationResult) -> None:
        self._details_tree.clear()
        for node in result.path:
            item = QTreeWidgetItem()
            item.setText(0, node.label)
            item.setText(1, f"{node.t:.1f}")
            item.setText(2, _dash_if_zero(node.s))
            item.setText(3, _dash_if_zero(node.e))
            item.setText(4, _dash_if_zero(node.d))
            item.setTextAlignment(1, Qt.AlignRight | Qt.AlignVCenter)
            item.setTextAlignment(2, Qt.AlignRight | Qt.AlignVCenter)
            item.setTextAlignment(3, Qt.AlignRight | Qt.AlignVCenter)
            item.setTextAlignment(4, Qt.AlignRight | Qt.AlignVCenter)
            self._details_tree.addTopLevelItem(item)

    def _fill_log(self, result: OptimizationResult) -> None:
        self._log_edit.setPlainText("\n".join(result.log))
