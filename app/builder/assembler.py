from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.graph.model import CrypterGraph
from app.graph.optimizer import OptimizationResult

# ---------------------------------------------------------------------------
# Маппинги node_id → человекочитаемое имя для layer_choices
# ---------------------------------------------------------------------------

_NODE_TO_HUMAN: dict[str, str] = {
    "v_XOR": "XOR",
    "v_AES128": "AES128",
    "v_AES256": "AES256",
    "v_nocomp": "nocomp",
    "v_LZ4": "LZ4",
    "v_LZMA": "LZMA",
    "v_noobf": "noobf",
    "v_meta": "meta",
    "v_virt": "virt",
    "v_poly": "poly",
}

_ENC_IDS = {"v_XOR", "v_AES128", "v_AES256"}
_COMP_IDS = {"v_nocomp", "v_LZ4", "v_LZMA"}
_OBF_IDS = {"v_noobf", "v_meta", "v_virt", "v_poly"}


# ---------------------------------------------------------------------------
# AssembledConfig
# ---------------------------------------------------------------------------


@dataclass
class AssembledConfig:
    path_nodes: List[str]
    layer_choices: Dict[str, str]  # {"encryption": "AES256", ...}
    predicted_metrics: Any  # PathMetrics
    source: str
    level: int
    penalty: float
    payload: Optional[Dict[str, Any]] = None  # {"path": str, "size_bytes": int}


# ---------------------------------------------------------------------------
# CrypterAssembler
# ---------------------------------------------------------------------------


class CrypterAssembler:
    def __init__(self, graph: CrypterGraph) -> None:
        self._graph = graph

    def assemble(
        self,
        result: OptimizationResult,
        payload_path: Optional[Path] = None,
    ) -> AssembledConfig:
        path = result.path

        # Восстановить выборы слоёв из узлов пути
        enc_choice = next(
            (_NODE_TO_HUMAN[n.id] for n in path if n.id in _ENC_IDS), "unknown"
        )
        comp_choice = next(
            (_NODE_TO_HUMAN[n.id] for n in path if n.id in _COMP_IDS), "unknown"
        )
        obf_choice = next(
            (_NODE_TO_HUMAN[n.id] for n in path if n.id in _OBF_IDS), "unknown"
        )

        layer_choices: Dict[str, str] = {
            "encryption": enc_choice,
            "compression": comp_choice,
            "obfuscation": obf_choice,
        }

        path_nodes = [n.id for n in path]

        payload: Optional[Dict[str, Any]] = None
        if payload_path is not None:
            payload = {
                "path": str(payload_path),
                "size_bytes": payload_path.stat().st_size,
            }

        return AssembledConfig(
            path_nodes=path_nodes,
            layer_choices=layer_choices,
            predicted_metrics=result.metrics,
            source=result.source,
            level=result.level,
            penalty=result.penalty,
            payload=payload,
        )

    def export_json(self, cfg: AssembledConfig, path: Path) -> None:
        m = cfg.predicted_metrics
        data = {
            "version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "level": cfg.level,
            "path": cfg.path_nodes,
            "layers": cfg.layer_choices,
            "predicted_metrics": {
                "t": m.t,
                "s": m.s,
                "e": m.e,
                "d": m.d,
            },
            "penalty": cfg.penalty,
            "source": cfg.source,
            "payload": cfg.payload,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Demo entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    graph = CrypterGraph.from_json(Path("data/graph_calibration.json"))
    paths = list(graph.all_paths())

    demo_result = OptimizationResult(
        level=1,
        path=paths[0],
        metrics=graph.aggregate(paths[0]),
        source="demo",
        penalty=0.0,
        log=["Демо-запуск"],
        record_id=None,
    )

    assembler = CrypterAssembler(graph)
    cfg = assembler.assemble(demo_result)

    out = Path("data/runs")
    out.mkdir(parents=True, exist_ok=True)
    assembler.export_json(cfg, out / "demo.json")
    print("JSON экспортирован в data/runs/demo.json")
