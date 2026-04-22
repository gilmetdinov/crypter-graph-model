from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from app.graph.model import CrypterGraph
from app.graph.optimizer import Constraints, MultiLevelOptimizer, Weights

CALIB = Path(__file__).parent.parent.parent / "data" / "graph_calibration.json"


# ---------------------------------------------------------------------------
# Заглушка репозитория (изолирована от app.db)
# ---------------------------------------------------------------------------


@dataclass
class FakeRecord:
    id: int
    enc_layer: str
    comp_layer: str
    obf_layer: str
    payload_size_kb: int
    total_time_ms: float
    crypto_strength: float
    avg_entropy: float
    detectability: float
    validated: int = 0


class FakeRepo:
    def __init__(self, records: list[FakeRecord]) -> None:
        self._records = records

    def find_by_constraints(
        self,
        t_max: float,
        s_min: float,
        d_max: float,
        limit: int | None = None,
    ) -> list[FakeRecord]:
        return [
            r
            for r in self._records
            if r.total_time_ms <= t_max
            and r.crypto_strength >= s_min
            and r.detectability <= d_max
        ]

    def all(self) -> list[FakeRecord]:
        return list(self._records)


# ---------------------------------------------------------------------------
# Фикстуры
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def graph() -> CrypterGraph:
    return CrypterGraph.from_json(CALIB)


_CRYPTER_A = FakeRecord(
    id=1,
    enc_layer="XOR",
    comp_layer="nocomp",
    obf_layer="noobf",
    payload_size_kb=100,
    total_time_ms=12.0,
    crypto_strength=0.3,
    avg_entropy=4.2,
    detectability=0.6,
    validated=1,
)


# ---------------------------------------------------------------------------
# Тесты
# ---------------------------------------------------------------------------


def test_level1_found(graph: CrypterGraph) -> None:
    """Запись криптера A удовлетворяет ограничениям → уровень 1."""
    repo = FakeRepo([_CRYPTER_A])
    optimizer = MultiLevelOptimizer(graph, repo)
    result = optimizer.optimize(
        Constraints(t_max=20.0, s_min=0.0, d_max=1.0),
        Weights(),
    )
    assert result.level == 1
    assert result.source == "db"
    assert result.record_id == 1
    assert result.penalty == pytest.approx(0.0)


def test_level2_synthesized(graph: CrypterGraph) -> None:
    """Пустой репозиторий — оптимизатор находит путь по DAG (уровень 2)."""
    repo = FakeRepo([])
    optimizer = MultiLevelOptimizer(graph, repo)
    # XOR/nocomp/noobf: t≈9 мс, s=0.2, d=0.9 — удовлетворяет t_max=15, s_min=0.2, d_max=1.0
    result = optimizer.optimize(
        Constraints(t_max=15.0, s_min=0.2, d_max=1.0),
        Weights(),
    )
    assert result.level == 2
    assert result.source == "synthesized"
    assert result.penalty == pytest.approx(0.0)


def test_level3_compromise(graph: CrypterGraph) -> None:
    """Невыполнимые ограничения → уровень 3, штраф > 0."""
    repo = FakeRepo([])
    optimizer = MultiLevelOptimizer(graph, repo)
    result = optimizer.optimize(
        Constraints(t_max=1.0, s_min=1.0, d_max=0.0),
        Weights(),
    )
    assert result.level == 3
    assert result.source == "synthesized"
    assert result.penalty > 0.0


def test_log_not_empty(graph: CrypterGraph) -> None:
    """Лог всегда непустой список строк."""
    for repo, c in [
        (FakeRepo([_CRYPTER_A]), Constraints(t_max=20.0, s_min=0.0, d_max=1.0)),
        (FakeRepo([]), Constraints(t_max=15.0, s_min=0.2, d_max=1.0)),
        (FakeRepo([]), Constraints(t_max=1.0, s_min=1.0, d_max=0.0)),
    ]:
        optimizer = MultiLevelOptimizer(graph, repo)
        result = optimizer.optimize(c, Weights())
        assert isinstance(result.log, list)
        assert len(result.log) > 0
        for entry in result.log:
            assert isinstance(entry, str)


def test_level3_tiebreaker(graph: CrypterGraph) -> None:
    """При равных штрафах выбирается путь с меньшей D(P)."""
    repo = FakeRepo([])
    optimizer = MultiLevelOptimizer(graph, repo)

    # Все веса = 0 → все пути имеют нулевой штраф → tie-breaker по D(P)
    result = optimizer.optimize(
        Constraints(t_max=0.0, s_min=0.0, d_max=0.0),
        Weights(w1=0.0, w2=0.0, w3=0.0),
    )
    assert result.level == 3

    # При нулевом штрафе у всех путей tie-breaker выбирает минимальную D(P)
    all_paths = list(graph.all_paths())
    best_d = min(graph.aggregate(p).d for p in all_paths)

    assert result.metrics.d == pytest.approx(best_d)  # type: ignore[union-attr]
