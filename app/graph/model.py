from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import reduce
from pathlib import Path
from typing import Iterator

import networkx as nx

LAYER_ORDER = ["L1", "L2", "L3", "L4", "L5", "L6"]

NODE_LAYERS: dict[str, str] = {
    "v_read": "L1",
    "v_XOR": "L2",
    "v_AES128": "L2",
    "v_AES256": "L2",
    "v_nocomp": "L3",
    "v_LZ4": "L3",
    "v_LZMA": "L3",
    "v_noobf": "L4",
    "v_meta": "L4",
    "v_virt": "L4",
    "v_poly": "L4",
    "v_stubgen": "L5",
    "v_exec": "L6",
}

NODE_LABELS: dict[str, str] = {
    "v_read": "Чтение PE",
    "v_XOR": "XOR",
    "v_AES128": "AES-128 CBC",
    "v_AES256": "AES-256 CBC",
    "v_nocomp": "Без компрессии",
    "v_LZ4": "LZ4",
    "v_LZMA": "LZMA",
    "v_noobf": "Без обфускации",
    "v_meta": "Метаморфизм",
    "v_virt": "Виртуализация",
    "v_poly": "Полиморфизм",
    "v_stubgen": "Генерация stub",
    "v_exec": "Выполнение",
}

LAYER_LABELS: dict[str, str] = {
    "L1": "Чтение файла",
    "L2": "Шифрование",
    "L3": "Компрессия",
    "L4": "Обфускация",
    "L5": "Внедрение",
    "L6": "Выполнение",
}


@dataclass
class Node:
    id: str
    layer: str
    t: float
    s: float
    e: float
    d: float

    @property
    def label(self) -> str:
        return NODE_LABELS.get(self.id, self.id)


@dataclass
class Edge:
    src: str
    dst: str
    w: float


@dataclass
class PathMetrics:
    t: float
    s: float
    e: float
    d: float


class CrypterGraph:
    def __init__(self, nodes: list[Node], edges: list[Edge]) -> None:
        self._nodes: dict[str, Node] = {n.id: n for n in nodes}
        self._edges: dict[tuple[str, str], Edge] = {(e.src, e.dst): e for e in edges}
        self._adj: dict[str, list[str]] = {n: [] for n in self._nodes}
        for e in edges:
            self._adj[e.src].append(e.dst)

    @classmethod
    def from_json(cls, path: Path) -> "CrypterGraph":
        data = json.loads(path.read_text(encoding="utf-8"))
        nodes = [
            Node(
                id=node_id,
                layer=NODE_LAYERS[node_id],
                t=attrs["t"],
                s=attrs["s"],
                e=attrs["e"],
                d=attrs["d"],
            )
            for node_id, attrs in data["nodes"].items()
        ]
        edges = [
            Edge(src=e["from"], dst=e["to"], w=e["w"]) for e in data["edges"]
        ]
        return cls(nodes, edges)

    def node(self, node_id: str) -> Node:
        return self._nodes[node_id]

    def nodes_in_layer(self, layer: str) -> list[Node]:
        return [n for n in self._nodes.values() if n.layer == layer]

    def successors(self, node_id: str) -> list[Node]:
        return [self._nodes[dst] for dst in self._adj.get(node_id, [])]

    def edge(self, src: str, dst: str) -> Edge | None:
        return self._edges.get((src, dst))

    def all_paths(self) -> Iterator[list[Node]]:
        start = self._nodes["v_read"]
        yield from self._dfs([start])

    def _dfs(self, current_path: list[Node]) -> Iterator[list[Node]]:
        last = current_path[-1]
        nexts = self.successors(last.id)
        if not nexts:
            yield list(current_path)
            return
        for nxt in nexts:
            yield from self._dfs(current_path + [nxt])

    def aggregate(self, path: list[Node]) -> PathMetrics:
        t = sum(n.t for n in path)
        for i in range(len(path) - 1):
            e = self.edge(path[i].id, path[i + 1].id)
            if e:
                t += e.w

        s = max(n.s for n in path)

        non_zero_e = [n.e for n in path if n.e > 0]
        avg_e = sum(non_zero_e) / len(non_zero_e) if non_zero_e else 0.0

        d = 1.0 - reduce(lambda acc, n: acc * (1.0 - n.d), path, 1.0)

        return PathMetrics(t=round(t, 4), s=s, e=round(avg_e, 4), d=round(d, 4))

    def path_from_layers(
        self, enc: str, comp: str, obf: str
    ) -> list[Node]:
        """Build path by layer choices (enc/comp/obf node IDs)."""
        return [
            self._nodes["v_read"],
            self._nodes[enc],
            self._nodes[comp],
            self._nodes[obf],
            self._nodes["v_stubgen"],
            self._nodes["v_exec"],
        ]

    def underlying_nx(self) -> nx.DiGraph:
        g = nx.DiGraph()
        for n in self._nodes.values():
            g.add_node(n.id, layer=n.layer, label=n.label, t=n.t, s=n.s, e=n.e, d=n.d)
        for e in self._edges.values():
            g.add_edge(e.src, e.dst, w=e.w)
        return g
