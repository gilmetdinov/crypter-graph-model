from __future__ import annotations

from typing import List

from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtCore import Qt

from app.db.repository import ConfigRecord, ConfigRepository


class NumericTableWidgetItem(QTableWidgetItem):
    def __init__(self, value: float, fmt: str = "{:.2f}"):
        super().__init__(fmt.format(value))
        self._value = value

    def __lt__(self, other: "NumericTableWidgetItem") -> bool:
        try:
            return self._value < other._value
        except AttributeError:
            return super().__lt__(other)


_COLUMNS = [
    "ID",
    "Шифрование",
    "Компрессия",
    "Обфускация",
    "Payload (КБ)",
    "T (мс)",
    "S",
    "E",
    "D",
    "Validated",
]


class ReferenceDbWidget(QWidget):
    def __init__(self, repo: ConfigRepository) -> None:
        super().__init__()
        self.repo = repo
        self._all_records: List[ConfigRecord] = []

        self._build_ui()
        self._load_data()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(6)

        # --- Filter panel ---
        filter_box = QGroupBox("Фильтры")
        filter_layout = QHBoxLayout(filter_box)
        filter_layout.setSpacing(10)

        filter_layout.addWidget(QLabel("Шифрование:"))
        self._cb_enc = QComboBox()
        self._cb_enc.addItems(["Все", "XOR", "AES128", "AES256"])
        filter_layout.addWidget(self._cb_enc)

        filter_layout.addWidget(QLabel("Компрессия:"))
        self._cb_comp = QComboBox()
        self._cb_comp.addItems(["Все", "nocomp", "LZ4", "LZMA"])
        filter_layout.addWidget(self._cb_comp)

        filter_layout.addWidget(QLabel("Обфускация:"))
        self._cb_obf = QComboBox()
        self._cb_obf.addItems(["Все", "noobf", "meta", "virt", "poly"])
        filter_layout.addWidget(self._cb_obf)

        self._chk_validated = QCheckBox("Только валидированные")
        self._chk_validated.setChecked(False)
        filter_layout.addWidget(self._chk_validated)

        filter_layout.addStretch()

        self._cb_enc.currentIndexChanged.connect(self._apply_filters)
        self._cb_comp.currentIndexChanged.connect(self._apply_filters)
        self._cb_obf.currentIndexChanged.connect(self._apply_filters)
        self._chk_validated.stateChanged.connect(self._apply_filters)

        root_layout.addWidget(filter_box)

        # --- Table ---
        self._table = QTableWidget()
        self._table.setColumnCount(len(_COLUMNS))
        self._table.setHorizontalHeaderLabels(_COLUMNS)
        self._table.setSortingEnabled(True)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionsClickable(True)
        self._table.verticalHeader().setVisible(False)

        root_layout.addWidget(self._table, stretch=1)

        # --- Status bar ---
        self._status_label = QLabel("Показано: 0 / 0 записей")
        root_layout.addWidget(self._status_label)

    def _load_data(self) -> None:
        self._all_records = self.repo.all()
        self._apply_filters()

    def _apply_filters(self) -> None:
        enc_filter = self._cb_enc.currentText()
        comp_filter = self._cb_comp.currentText()
        obf_filter = self._cb_obf.currentText()
        only_validated = self._chk_validated.isChecked()

        filtered: List[ConfigRecord] = []
        for rec in self._all_records:
            if enc_filter != "Все" and rec.enc_layer != enc_filter:
                continue
            if comp_filter != "Все" and rec.comp_layer != comp_filter:
                continue
            if obf_filter != "Все" and rec.obf_layer != obf_filter:
                continue
            if only_validated and rec.validated != 1:
                continue
            filtered.append(rec)

        # Rebuild table
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)

        for rec in filtered:
            row = self._table.rowCount()
            self._table.insertRow(row)

            # ID
            id_item = NumericTableWidgetItem(float(rec.id or 0), fmt="{:.0f}")
            id_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 0, id_item)

            # enc_layer
            self._table.setItem(row, 1, QTableWidgetItem(rec.enc_layer))

            # comp_layer
            self._table.setItem(row, 2, QTableWidgetItem(rec.comp_layer))

            # obf_layer
            self._table.setItem(row, 3, QTableWidgetItem(rec.obf_layer))

            # payload_size_kb
            payload_item = NumericTableWidgetItem(
                float(rec.payload_size_kb), fmt="{:.0f}"
            )
            payload_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._table.setItem(row, 4, payload_item)

            # total_time_ms  — 1 decimal place
            t_item = NumericTableWidgetItem(rec.total_time_ms, fmt="{:.1f}")
            t_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._table.setItem(row, 5, t_item)

            # crypto_strength — 2 decimal places
            s_item = NumericTableWidgetItem(rec.crypto_strength, fmt="{:.2f}")
            s_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._table.setItem(row, 6, s_item)

            # avg_entropy — 2 decimal places
            e_item = NumericTableWidgetItem(rec.avg_entropy, fmt="{:.2f}")
            e_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._table.setItem(row, 7, e_item)

            # detectability — 2 decimal places
            d_item = NumericTableWidgetItem(rec.detectability, fmt="{:.2f}")
            d_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self._table.setItem(row, 8, d_item)

            # validated — checkmark or empty
            val_text = "✓" if rec.validated == 1 else ""
            val_item = QTableWidgetItem(val_text)
            val_item.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(row, 9, val_item)

        self._table.setSortingEnabled(True)

        total = len(self._all_records)
        shown = len(filtered)
        self._status_label.setText(f"Показано: {shown} / {total} записей")

    def refresh(self) -> None:
        self._load_data()
