from __future__ import annotations

from PyQt5.QtWidgets import QVBoxLayout, QWidget
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from app.graph.model import CrypterGraph
from app.graph.visualizer import GraphVisualizer


class GraphWidget(QWidget):
    """PyQt5 widget that embeds a matplotlib canvas with the DAG visualizer."""

    def __init__(self, graph: CrypterGraph) -> None:
        super().__init__()

        self._visualizer = GraphVisualizer(graph)
        self._figure = Figure(figsize=(16, 6.5), tight_layout=True)
        self._ax = self._figure.add_subplot(111)
        self._canvas = FigureCanvas(self._figure)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas)

        self._visualizer.render(self._ax)

    def highlight(self, path_node_ids: list[str]) -> None:
        """Re-render the graph with the given path highlighted."""
        self._visualizer.render(self._ax, highlighted_path=path_node_ids)
        self._canvas.draw()

    def clear_highlight(self) -> None:
        """Re-render the graph without any path highlighted."""
        self._visualizer.render(self._ax)
        self._canvas.draw()
