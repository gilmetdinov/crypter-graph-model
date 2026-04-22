from __future__ import annotations

import datetime
import time
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.builder.assembler import CrypterAssembler
from app.db.seed import init_db_if_needed
from app.graph.model import CrypterGraph
from app.graph.optimizer import Constraints, MultiLevelOptimizer, Weights
from app.ui.config_form import ConfigForm
from app.ui.reference_db_widget import ReferenceDbWidget
from app.ui.results_panel import ResultsPanel


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Конструктор криптера")
        self.setMinimumSize(1100, 860)

        # Загрузить граф
        self.graph = CrypterGraph.from_json(Path("data/graph_calibration.json"))

        # Инициализировать БД
        self.repo = init_db_if_needed(Path("app/db/crypters.db"))

        # Создать оптимизатор и сборщик
        self.optimizer = MultiLevelOptimizer(self.graph, self.repo)
        self.assembler = CrypterAssembler(self.graph)

        # Создать виджеты конструктора
        self.config_form = ConfigForm()
        self.results_panel = ResultsPanel()

        # Подключить сигналы
        self.config_form.config_requested.connect(self._on_config_requested)
        self.results_panel.path_highlighted.connect(self._on_path_highlighted)

        tabs = QTabWidget()
        self.setCentralWidget(tabs)

        # Вкладка «Конструктор»
        constructor_tab = self._build_constructor_tab()
        tabs.addTab(constructor_tab, "Конструктор")

        # Вкладка «Граф»
        from app.ui.graph_widget import GraphWidget

        self.graph_widget = GraphWidget(self.graph)
        tabs.addTab(self.graph_widget, "Граф")

        # Вкладка «База эталонных»
        self.reference_db_widget = ReferenceDbWidget(self.repo)
        tabs.addTab(self.reference_db_widget, "База эталонных")

        # Вкладка «Эксперименты»
        from app.ui.experiments_widget import ExperimentsWidget

        self.experiments_widget = ExperimentsWidget(self.graph, self.repo)
        self.experiments_widget.path_selected.connect(self._on_path_highlighted)
        tabs.addTab(self.experiments_widget, "Эксперименты")

        self.statusBar().showMessage("Готов к работе")

    # ------------------------------------------------------------------
    # Построение вкладки «Конструктор»
    # ------------------------------------------------------------------

    def _build_constructor_tab(self) -> QWidget:
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)
        layout.addWidget(self.config_form)
        layout.addWidget(self.results_panel)
        layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)
        return scroll

    # ------------------------------------------------------------------
    # Слоты
    # ------------------------------------------------------------------

    def _on_config_requested(
        self,
        constraints: Constraints,
        weights: Weights,
        payload_path: object,
    ) -> None:
        self.config_form.set_busy("Подбор конфигурации…")
        QApplication.processEvents()

        t0 = time.perf_counter()
        result = self.optimizer.optimize(constraints, weights)
        assembled = self.assembler.assemble(
            result,
            Path(payload_path) if payload_path else None,
        )
        elapsed = (time.perf_counter() - t0) * 1000

        self.results_panel.display(result, assembled)
        self.config_form.set_status(
            f"Готово за {elapsed:.1f} мс · Уровень стратегии: {result.level}"
        )

        # Сохранить JSON результата
        out_dir = Path("data/runs")
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.assembler.export_json(assembled, out_dir / f"result_{ts}.json")

    def _on_path_highlighted(self, node_ids: list) -> None:
        self.graph_widget.highlight(node_ids)
