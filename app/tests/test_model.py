from pathlib import Path

import pytest

from app.graph.model import CrypterGraph, PathMetrics

CALIB = Path(__file__).parent.parent.parent / "data" / "graph_calibration.json"


@pytest.fixture(scope="module")
def graph() -> CrypterGraph:
    return CrypterGraph.from_json(CALIB)


def test_node_and_edge_counts(graph: CrypterGraph):
    assert len(graph._nodes) == 13
    assert len(graph._edges) == 29


def test_all_paths_count(graph: CrypterGraph):
    paths = list(graph.all_paths())
    assert len(paths) == 36


def test_all_paths_length(graph: CrypterGraph):
    for path in graph.all_paths():
        assert len(path) == 6


def test_aggregate_crypter_a(graph: CrypterGraph):
    # Криптер A: XOR / nocomp / noobf
    path = graph.path_from_layers("v_XOR", "v_nocomp", "v_noobf")
    m = graph.aggregate(path)
    # t = v_read(1) + v_XOR(2) + v_nocomp(0) + v_noobf(0) + v_stubgen(3) + v_exec(1)
    #   + edges: read→XOR(0) + XOR→nocomp(0) + nocomp→noobf(0) + noobf→stubgen(0) + stubgen→exec(2)
    assert abs(m.t - 9) < 1  # 9 мс base (+2 edge on stubgen→exec) = 11
    assert m.s == pytest.approx(0.2)
    # d: noobf=0.9, others 0 → D(P) = 1-(1*1*(1-0.9)*1*1) = 1-0.1 = 0.9
    assert m.d == pytest.approx(0.9)


def test_aggregate_crypter_c(graph: CrypterGraph):
    # Криптер C: AES-256 / LZMA / virt
    path = graph.path_from_layers("v_AES256", "v_LZMA", "v_virt")
    m = graph.aggregate(path)
    # t = 1+8+35+45+3+1 + edges: 0+40+8+5+2 = 93+55 = 148
    assert m.t == pytest.approx(148.0)
    assert m.s == pytest.approx(1.0)
    assert m.d == pytest.approx(1.0 - (1 - 0.15))  # only virt contributes d


def test_layer_nodes(graph: CrypterGraph):
    assert len(graph.nodes_in_layer("L2")) == 3
    assert len(graph.nodes_in_layer("L4")) == 4
    assert len(graph.nodes_in_layer("L1")) == 1
    assert len(graph.nodes_in_layer("L6")) == 1


def test_underlying_nx(graph: CrypterGraph):
    g = graph.underlying_nx()
    assert g.number_of_nodes() == 13
    assert g.number_of_edges() == 29
