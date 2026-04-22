from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QDoubleSpinBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from app.graph.optimizer import Constraints, Weights


class ConfigForm(QWidget):
    config_requested = pyqtSignal(object, object, object)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._syncing: bool = False
        self._build_ui()

    # ------------------------------------------------------------------
    # Построение интерфейса
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(10)

        root.addWidget(self._build_constraints_group())
        root.addWidget(self._build_weights_group())
        root.addLayout(self._build_payload_row())

        self._run_btn = QPushButton("Подобрать конфигурацию")
        font = self._run_btn.font()
        font.setBold(True)
        self._run_btn.setFont(font)
        self._run_btn.setFixedHeight(36)
        self._run_btn.clicked.connect(self._on_run_clicked)
        root.addWidget(self._run_btn)

        self._status_label = QLabel("")
        self._status_label.setAlignment(Qt.AlignLeft)
        root.addWidget(self._status_label)

        root.addStretch()

    def _build_constraints_group(self) -> QGroupBox:
        group = QGroupBox("Ограничения")
        layout = QVBoxLayout(group)

        # Макс. время выполнения
        self._t_max = QDoubleSpinBox()
        self._t_max.setMinimum(1.0)
        self._t_max.setMaximum(10000.0)
        self._t_max.setValue(200.0)
        self._t_max.setSingleStep(10.0)
        self._t_max.setSuffix(" мс")
        self._t_max.setDecimals(0)
        layout.addWidget(QLabel("Макс. время выполнения (мс):"))
        layout.addWidget(self._t_max)

        # Мин. криптостойкость
        self._s_min = QDoubleSpinBox()
        self._s_min.setMinimum(0.0)
        self._s_min.setMaximum(1.0)
        self._s_min.setValue(0.5)
        self._s_min.setSingleStep(0.05)
        self._s_min.setDecimals(2)
        layout.addWidget(QLabel("Мин. криптостойкость:"))
        layout.addWidget(self._s_min)

        # Макс. детектируемость
        self._d_max = QDoubleSpinBox()
        self._d_max.setMinimum(0.0)
        self._d_max.setMaximum(1.0)
        self._d_max.setValue(0.5)
        self._d_max.setSingleStep(0.05)
        self._d_max.setDecimals(2)
        layout.addWidget(QLabel("Макс. детектируемость:"))
        layout.addWidget(self._d_max)

        return group

    def _build_weights_group(self) -> QGroupBox:
        group = QGroupBox("Приоритеты")
        layout = QVBoxLayout(group)

        self._w1_spin, self._w1_slider = self._make_weight_row(
            "Приоритет скорости (w₁):", layout
        )
        self._w2_spin, self._w2_slider = self._make_weight_row(
            "Приоритет стойкости (w₂):", layout
        )
        self._w3_spin, self._w3_slider = self._make_weight_row(
            "Приоритет скрытности (w₃):", layout
        )

        return group

    def _make_weight_row(
        self, label_text: str, parent_layout: QVBoxLayout
    ) -> tuple[QDoubleSpinBox, QSlider]:
        parent_layout.addWidget(QLabel(label_text))

        row = QHBoxLayout()

        spin = QDoubleSpinBox()
        spin.setMinimum(0.1)
        spin.setMaximum(10.0)
        spin.setValue(1.0)
        spin.setSingleStep(0.1)
        spin.setDecimals(1)
        spin.setFixedWidth(80)
        row.addWidget(spin)

        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(1)
        slider.setMaximum(100)
        slider.setValue(10)
        slider.setTickInterval(10)
        slider.setTickPosition(QSlider.TicksBelow)
        row.addWidget(slider)

        parent_layout.addLayout(row)

        # Синхронизация
        spin.valueChanged.connect(
            lambda v, sl=slider, sp=spin: self._sync_spin_to_slider(v, sl, sp)
        )
        slider.valueChanged.connect(
            lambda v, sl=slider, sp=spin: self._sync_slider_to_spin(v, sl, sp)
        )

        return spin, slider

    def _sync_spin_to_slider(
        self, value: float, slider: QSlider, spin: QDoubleSpinBox
    ) -> None:
        if self._syncing:
            return
        self._syncing = True
        try:
            slider.setValue(round(value * 10))
        finally:
            self._syncing = False

    def _sync_slider_to_spin(
        self, value: int, slider: QSlider, spin: QDoubleSpinBox
    ) -> None:
        if self._syncing:
            return
        self._syncing = True
        try:
            spin.setValue(value / 10.0)
        finally:
            self._syncing = False

    def _build_payload_row(self) -> QHBoxLayout:
        row = QHBoxLayout()

        self._payload_edit = QLineEdit()
        self._payload_edit.setReadOnly(True)
        self._payload_edit.setPlaceholderText("Путь к PE-файлу (опционально)")
        row.addWidget(self._payload_edit)

        browse_btn = QPushButton("Обзор…")
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self._on_browse_clicked)
        row.addWidget(browse_btn)

        return row

    # ------------------------------------------------------------------
    # Слоты
    # ------------------------------------------------------------------

    def _on_browse_clicked(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Выбрать PE-файл",
            "",
            "EXE файлы (*.exe);;Все файлы (*)",
        )
        if path:
            self._payload_edit.setText(path)

    def _on_run_clicked(self) -> None:
        constraints = Constraints(
            t_max=self._t_max.value(),
            s_min=self._s_min.value(),
            d_max=self._d_max.value(),
        )
        weights = Weights(
            w1=self._w1_spin.value(),
            w2=self._w2_spin.value(),
            w3=self._w3_spin.value(),
        )
        payload_text = self._payload_edit.text().strip()
        payload_path: Optional[str] = payload_text if payload_text else None

        self.config_requested.emit(constraints, weights, payload_path)

    # ------------------------------------------------------------------
    # Статус-лейбл
    # ------------------------------------------------------------------

    def set_status(self, msg: str) -> None:
        font = self._status_label.font()
        font.setItalic(False)
        self._status_label.setFont(font)
        self._status_label.setText(msg)

    def set_busy(self, msg: str) -> None:
        font = self._status_label.font()
        font.setItalic(True)
        self._status_label.setFont(font)
        self._status_label.setText(msg)

    def clear_status(self) -> None:
        self._status_label.setText("")
