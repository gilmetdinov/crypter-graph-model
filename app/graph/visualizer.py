from __future__ import annotations

from collections import defaultdict
from typing import Optional

import matplotlib.axes
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

from app.graph.model import CrypterGraph, LAYER_LABELS, LAYER_ORDER, NODE_LABELS

# Горизонтальные позиции слоёв — широкие промежутки для читаемых рёбер
LAYER_X: dict[str, float] = {
    "L1": 0.0,
    "L2": 2.5,
    "L3": 5.0,
    "L4": 7.5,
    "L5": 10.5,
    "L6": 13.0,
}

_NODE_W = 1.3
_NODE_H = 0.52
_Y_STEP = 1.45

_COLOR_NORMAL_FILL = "#4A90D9"
_COLOR_NORMAL_EDGE = "#2C5F8A"
_COLOR_HL_FILL = "#E05252"
_COLOR_HL_EDGE = "#8B1A1A"
_COLOR_ARROW = "#BBBBBB"
_COLOR_ARROW_HL = "#E05252"
_COLOR_LAYER_LABEL = "#555555"


class GraphVisualizer:
    """Draws a CrypterGraph on a matplotlib Axes using a fixed grid layout."""

    def __init__(self, graph: CrypterGraph) -> None:
        self._graph = graph
        self._pos: dict[str, tuple[float, float]] = {}
        self._precompute_positions()

    def _precompute_positions(self) -> None:
        for layer in LAYER_ORDER:
            nodes = sorted(self._graph.nodes_in_layer(layer), key=lambda n: n.id)
            n = len(nodes)
            x = LAYER_X[layer]
            for i, node in enumerate(nodes):
                y = (i - (n - 1) / 2.0) * _Y_STEP
                self._pos[node.id] = (x, y)

    def _edge_curvatures(self) -> dict[tuple[str, str], float]:
        """Assign arc curvature so parallel edges from same source fan out."""
        by_src: dict[str, list[str]] = defaultdict(list)
        for edge in self._graph._edges.values():
            by_src[edge.src].append(edge.dst)

        curvatures: dict[tuple[str, str], float] = {}
        for src, dsts in by_src.items():
            dsts_sorted = sorted(dsts, key=lambda d: self._pos[d][1])
            n = len(dsts_sorted)
            for i, dst in enumerate(dsts_sorted):
                if n == 1:
                    curvatures[(src, dst)] = 0.0
                else:
                    curvatures[(src, dst)] = (i / (n - 1) - 0.5) * 0.28
        return curvatures

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(
        self,
        ax: matplotlib.axes.Axes,
        highlighted_path: Optional[list[str]] = None,
    ) -> None:
        ax.clear()

        hl_set: set[tuple[str, str]] = set()
        hl_nodes: set[str] = set()
        if highlighted_path:
            hl_nodes = set(highlighted_path)
            for a, b in zip(highlighted_path, highlighted_path[1:]):
                hl_set.add((a, b))

        curvatures = self._edge_curvatures()

        # --- Edges -------------------------------------------------------
        for edge in self._graph._edges.values():
            is_hl = (edge.src, edge.dst) in hl_set
            color = _COLOR_ARROW_HL if is_hl else _COLOR_ARROW
            lw = 2.2 if is_hl else 0.9
            alpha = 1.0 if is_hl else 0.7
            rad = curvatures.get((edge.src, edge.dst), 0.0)

            x0, y0 = self._pos[edge.src]
            x1, y1 = self._pos[edge.dst]

            ax.annotate(
                "",
                xy=(x1 - _NODE_W / 2, y1),
                xytext=(x0 + _NODE_W / 2, y0),
                arrowprops=dict(
                    arrowstyle="->,head_width=0.25,head_length=0.18",
                    color=color,
                    lw=lw,
                    alpha=alpha,
                    connectionstyle=f"arc3,rad={rad}",
                ),
                zorder=2,
            )

            # Метка веса — только ненулевые, с белым фоном
            if edge.w > 0:
                # Смещаем метку чуть в сторону кривизны дуги
                mx = (x0 + _NODE_W / 2 + x1 - _NODE_W / 2) / 2.0
                my = (y0 + y1) / 2.0 + rad * (x1 - x0) * 0.18
                ax.text(
                    mx,
                    my,
                    f"+{edge.w:.0f}мс",
                    fontsize=7.5,
                    color="#333333" if is_hl else "#888888",
                    fontweight="bold" if is_hl else "normal",
                    ha="center",
                    va="center",
                    zorder=4,
                    bbox=dict(
                        boxstyle="round,pad=0.15",
                        facecolor="white",
                        edgecolor="none",
                        alpha=0.85,
                    ),
                )

        # --- Nodes -------------------------------------------------------
        for node_id, (x, y) in self._pos.items():
            is_hl = node_id in hl_nodes
            fill = _COLOR_HL_FILL if is_hl else _COLOR_NORMAL_FILL
            edge_color = _COLOR_HL_EDGE if is_hl else _COLOR_NORMAL_EDGE
            lw = 2.0 if is_hl else 1.2

            patch = FancyBboxPatch(
                (x - _NODE_W / 2, y - _NODE_H / 2),
                _NODE_W,
                _NODE_H,
                boxstyle="round,pad=0.05",
                facecolor=fill,
                edgecolor=edge_color,
                linewidth=lw,
                zorder=5,
            )
            ax.add_patch(patch)

            label = NODE_LABELS.get(node_id, node_id)
            ax.text(
                x,
                y,
                label,
                fontsize=9,
                ha="center",
                va="center",
                color="white",
                fontweight="bold",
                zorder=6,
            )

        # --- Layer labels ------------------------------------------------
        all_ys = list(self._pos.values())
        bottom_y = min(y for _, y in all_ys) if all_ys else 0.0
        label_y = bottom_y - _NODE_H / 2 - 0.55

        for layer, x in LAYER_X.items():
            label = LAYER_LABELS.get(layer, layer)
            ax.text(
                x,
                label_y,
                label,
                ha="center",
                fontsize=8.5,
                color=_COLOR_LAYER_LABEL,
                style="italic",
                zorder=6,
            )

        # --- Axes limits (без equal aspect — граф растягивается по canvas) --
        top_y = max(y for _, y in all_ys) if all_ys else 0.0
        x_min = LAYER_X["L1"] - _NODE_W / 2 - 0.5
        x_max = LAYER_X["L6"] + _NODE_W / 2 + 0.5
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(label_y - 0.4, top_y + _NODE_H / 2 + 0.5)
        ax.axis("off")

        # --- Legend ------------------------------------------------------
        legend_patches = [
            mpatches.Patch(
                facecolor=_COLOR_NORMAL_FILL,
                edgecolor=_COLOR_NORMAL_EDGE,
                label="Обычный узел",
            ),
            mpatches.Patch(
                facecolor=_COLOR_HL_FILL,
                edgecolor=_COLOR_HL_EDGE,
                label="Выбранный путь",
            ),
        ]
        ax.legend(
            handles=legend_patches,
            loc="upper right",
            fontsize=9,
            framealpha=0.9,
        )
