from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, List, Optional

from app.graph.model import CrypterGraph, Node, PathMetrics


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class Constraints:
    t_max: float
    s_min: float
    d_max: float


@dataclass
class Weights:
    w1: float = 1.0  # приоритет скорости
    w2: float = 1.0  # приоритет криптостойкости
    w3: float = 1.0  # приоритет скрытности


@dataclass
class OptimizationResult:
    level: int  # 1, 2 или 3
    path: List[Node]
    metrics: object  # PathMetrics
    source: str  # "db" или "synthesized"
    penalty: float  # 0 на уровнях 1-2
    log: List[str]  # строки лога на русском
    record_id: Optional[int] = None  # если из БД


# ---------------------------------------------------------------------------
# Маппинги слоёв
# ---------------------------------------------------------------------------

_ENC_MAP: dict[str, str] = {
    "XOR": "v_XOR",
    "AES128": "v_AES128",
    "AES256": "v_AES256",
}

_COMP_MAP: dict[str, str] = {
    "nocomp": "v_nocomp",
    "LZ4": "v_LZ4",
    "LZMA": "v_LZMA",
}

_OBF_MAP: dict[str, str] = {
    "noobf": "v_noobf",
    "meta": "v_meta",
    "virt": "v_virt",
    "poly": "v_poly",
}

# Обратные маппинги: node_id → название слоя
_NODE_TO_ENC: dict[str, str] = {v: k for k, v in _ENC_MAP.items()}
_NODE_TO_COMP: dict[str, str] = {v: k for k, v in _COMP_MAP.items()}
_NODE_TO_OBF: dict[str, str] = {v: k for k, v in _OBF_MAP.items()}


def _path_label(path: List[Node]) -> str:
    """Возвращает строку вида 'XOR/nocomp/noobf' для пути."""
    enc = next((n.id for n in path if n.id in _NODE_TO_ENC), "?")
    comp = next((n.id for n in path if n.id in _NODE_TO_COMP), "?")
    obf = next((n.id for n in path if n.id in _NODE_TO_OBF), "?")
    return f"{_NODE_TO_ENC.get(enc, enc)}/{_NODE_TO_COMP.get(comp, comp)}/{_NODE_TO_OBF.get(obf, obf)}"


# ---------------------------------------------------------------------------
# Оптимизатор
# ---------------------------------------------------------------------------


class MultiLevelOptimizer:
    def __init__(self, graph: CrypterGraph, repo: Any) -> None:
        """
        repo — объект с методами:
          find_by_constraints(t_max, s_min, d_max) -> list
          all() -> list
        """
        self._graph = graph
        self._repo = repo

    def optimize(
        self, constraints: Constraints, weights: Weights
    ) -> OptimizationResult:
        t_start = time.perf_counter()
        log: List[str] = []

        result = self._level1(constraints, weights, log)
        if result is not None:
            elapsed = (time.perf_counter() - t_start) * 1000
            log.append(f"Время работы алгоритма: {elapsed:.1f}мс")
            result.log = log
            return result

        result = self._level2(constraints, weights, log)
        if result is not None:
            elapsed = (time.perf_counter() - t_start) * 1000
            log.append(f"Время работы алгоритма: {elapsed:.1f}мс")
            result.log = log
            return result

        result = self._level3(constraints, weights, log)
        elapsed = (time.perf_counter() - t_start) * 1000
        log.append(f"Время работы алгоритма: {elapsed:.1f}мс")
        result.log = log
        return result

    # ------------------------------------------------------------------
    # Уровень 1 — поиск в БД
    # ------------------------------------------------------------------

    def _level1(
        self,
        constraints: Constraints,
        weights: Weights,
        log: List[str],
    ) -> Optional[OptimizationResult]:
        records = self._repo.find_by_constraints(
            constraints.t_max, constraints.s_min, constraints.d_max
        )
        if not records:
            return None

        # Берём запись с минимальным total_time_ms
        best = min(records, key=lambda r: r.total_time_ms)

        enc_node = _ENC_MAP[best.enc_layer]
        comp_node = _COMP_MAP[best.comp_layer]
        obf_node = _OBF_MAP[best.obf_layer]

        path = self._graph.path_from_layers(enc_node, comp_node, obf_node)
        metrics = self._graph.aggregate(path)

        label = f"{best.enc_layer}/{best.comp_layer}/{best.obf_layer}"
        log.append(
            f"Уровень 1: найдено {len(records)} конфигураций в базе эталонных. "
            f"Выбрана: {label}, T={best.total_time_ms:.1f}мс"
        )

        return OptimizationResult(
            level=1,
            path=path,
            metrics=metrics,
            source="db",
            penalty=0.0,
            log=log,
            record_id=best.id,
        )

    # ------------------------------------------------------------------
    # Уровень 2 — модульная сборка по DAG
    # ------------------------------------------------------------------

    def _level2(
        self,
        constraints: Constraints,
        weights: Weights,
        log: List[str],
    ) -> Optional[OptimizationResult]:
        log.append("Уровень 1: совпадений в БД не найдено.")

        all_paths = list(self._graph.all_paths())
        valid: List[tuple[List[Node], PathMetrics]] = []

        for path in all_paths:
            m = self._graph.aggregate(path)
            if (
                m.t <= constraints.t_max
                and m.s >= constraints.s_min
                and m.d <= constraints.d_max
            ):
                valid.append((path, m))

        if not valid:
            return None

        # Минимальное время
        best_path, best_metrics = min(valid, key=lambda x: x[1].t)
        label = _path_label(best_path)

        log.append(
            f"Уровень 2: модульная сборка. Найдено {len(valid)} допустимых путей. "
            f"Выбран с минимальным временем: {label}, T={best_metrics.t:.1f}мс"
        )

        return OptimizationResult(
            level=2,
            path=best_path,
            metrics=best_metrics,
            source="synthesized",
            penalty=0.0,
            log=log,
            record_id=None,
        )

    # ------------------------------------------------------------------
    # Уровень 3 — компромиссный выбор
    # ------------------------------------------------------------------

    def _level3(
        self,
        constraints: Constraints,
        weights: Weights,
        log: List[str],
    ) -> OptimizationResult:
        log.append(
            "Уровень 2: нет путей, удовлетворяющих всем ограничениям."
        )

        all_paths = list(self._graph.all_paths())

        def penalty(m: PathMetrics) -> float:
            return (
                weights.w1 * max(0.0, m.t - constraints.t_max)
                + weights.w2 * max(0.0, constraints.s_min - m.s)
                + weights.w3 * max(0.0, m.d - constraints.d_max)
            )

        scored: List[tuple[List[Node], PathMetrics, float]] = []
        for path in all_paths:
            m = self._graph.aggregate(path)
            p = penalty(m)
            scored.append((path, m, p))

        # tie-breaker: при равном штрафе — меньшая D(P)
        best_path, best_metrics, min_penalty = min(
            scored, key=lambda x: (x[2], x[1].d)
        )

        label = _path_label(best_path)

        # Формируем список нарушений
        violations: List[str] = []
        if best_metrics.t > constraints.t_max:
            violations.append(
                f"Время: {best_metrics.t:.1f} > {constraints.t_max:.1f} мс"
            )
        if best_metrics.s < constraints.s_min:
            violations.append(
                f"Стойкость: {best_metrics.s:.2f} < {constraints.s_min:.2f}"
            )
        if best_metrics.d > constraints.d_max:
            violations.append(
                f"Детектируемость: {best_metrics.d:.2f} > {constraints.d_max:.2f}"
            )

        violation_str = (
            ", ".join(violations) if violations else "нет нарушений"
        )

        log.append(
            f"Уровень 3: компромиссный выбор. Минимальный штраф: P={min_penalty:.3f}. "
            f"Выбрана: {label}\n  Нарушения: [{violation_str}]"
        )

        return OptimizationResult(
            level=3,
            path=best_path,
            metrics=best_metrics,
            source="synthesized",
            penalty=min_penalty,
            log=log,
            record_id=None,
        )
