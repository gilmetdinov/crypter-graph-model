"""CLI-прогон 12 сценариев. Запуск: python -m app.experiments.run_scenarios"""

from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from app.graph.optimizer import Constraints, MultiLevelOptimizer, Weights


def _load_scenarios() -> list[dict[str, Any]]:
    """Загружает сценарии из scenarios.yaml рядом с этим модулем."""
    yaml_path = Path(__file__).parent / "scenarios.yaml"
    with yaml_path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["scenarios"]


def run_all(graph: Any, repo: Any) -> list[dict[str, Any]]:
    """Прогоняет все сценарии и возвращает список результатов."""
    scenarios = _load_scenarios()
    results: list[dict[str, Any]] = []

    for scenario in scenarios:
        c = scenario["constraints"]
        w = scenario["weights"]

        constraints = Constraints(
            t_max=float(c["t_max"]),
            s_min=float(c["s_min"]),
            d_max=float(c["d_max"]),
        )
        weights = Weights(
            w1=float(w["w1"]),
            w2=float(w["w2"]),
            w3=float(w["w3"]),
        )

        t_start = time.perf_counter()
        opt_result = MultiLevelOptimizer(graph, repo).optimize(constraints, weights)
        algo_ms = (time.perf_counter() - t_start) * 1000

        # Получить layer_choices через assembler-совместимый маппинг
        from app.builder.assembler import CrypterAssembler

        assembled = CrypterAssembler(graph).assemble(opt_result)
        lc = assembled.layer_choices

        m = opt_result.metrics
        log_first = opt_result.log[0] if opt_result.log else ""

        results.append(
            {
                "name": scenario["name"],
                "level": opt_result.level,
                "enc": lc["encryption"],
                "comp": lc["compression"],
                "obf": lc["obfuscation"],
                "t": m.t,
                "s": m.s,
                "e": m.e,
                "d": m.d,
                "penalty": opt_result.penalty,
                "algo_ms": round(algo_ms, 3),
                "log_first": log_first,
            }
        )

    return results


def write_report(results: list[dict[str, Any]], out_dir: Path) -> Path:
    """Пишет scenarios_report.md и scenarios_raw.json в out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)

    # JSON
    json_path = out_dir / "scenarios_raw.json"
    json_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Markdown
    today = date.today().isoformat()
    lines: list[str] = [
        "# Результаты тестовых прогонов алгоритма подбора",
        "",
        f"Дата: {today}",
        "База данных: 120 конфигураций",
        "",
        "| № | Сценарий | Ур. | Шифрование | Компрессия | Обфускация | T (мс) | S | D | Штраф | Алг. (мс) |",
        "|---|----------|-----|-----------|-----------|-----------|--------|---|---|-------|-----------|",
    ]

    for idx, r in enumerate(results, start=1):
        row = (
            f"| {idx} "
            f"| {r['name']} "
            f"| {r['level']} "
            f"| {r['enc']} "
            f"| {r['comp']} "
            f"| {r['obf']} "
            f"| {r['t']:.2f} "
            f"| {r['s']:.2f} "
            f"| {r['d']:.2f} "
            f"| {r['penalty']:.3f} "
            f"| {r['algo_ms']:.1f} |"
        )
        lines.append(row)

    md_path = out_dir / "scenarios_report.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return md_path


if __name__ == "__main__":
    from pathlib import Path

    from app.db.seed import init_db_if_needed
    from app.graph.model import CrypterGraph

    graph = CrypterGraph.from_json(Path("data/graph_calibration.json"))
    repo = init_db_if_needed(Path("app/db/crypters.db"))
    results = run_all(graph, repo)
    out_dir = Path("data/runs")
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = write_report(results, out_dir)
    print(f"Отчёт сохранён: {report_path}")
    for r in results:
        status = "✓" if r["penalty"] == 0 else f"P={r['penalty']:.3f}"
        print(f"  [{r['level']}] {r['name'][:40]:<40} {status}")
    repo.close()
