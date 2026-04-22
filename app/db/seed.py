from __future__ import annotations

import random
from pathlib import Path

from app.db.repository import ConfigRecord, ConfigRepository
from app.graph.model import CrypterGraph

_CALIB = Path(__file__).parent.parent.parent / "data" / "graph_calibration.json"

ENC_MAP = {
    "v_XOR": "XOR",
    "v_AES128": "AES128",
    "v_AES256": "AES256",
}
COMP_MAP = {
    "v_nocomp": "nocomp",
    "v_LZ4": "LZ4",
    "v_LZMA": "LZMA",
}
OBF_MAP = {
    "v_noobf": "noobf",
    "v_meta": "meta",
    "v_virt": "virt",
    "v_poly": "poly",
}

_CANONICAL = [
    ConfigRecord(
        enc_layer="XOR",
        comp_layer="nocomp",
        obf_layer="noobf",
        payload_size_kb=64,
        total_time_ms=12.0,
        crypto_strength=0.30,
        avg_entropy=4.2,
        detectability=0.60,
        validated=1,
    ),
    ConfigRecord(
        enc_layer="AES128",
        comp_layer="LZ4",
        obf_layer="noobf",
        payload_size_kb=64,
        total_time_ms=47.0,
        crypto_strength=0.75,
        avg_entropy=7.3,
        detectability=0.40,
        validated=1,
    ),
    ConfigRecord(
        enc_layer="AES256",
        comp_layer="LZMA",
        obf_layer="virt",
        payload_size_kb=64,
        total_time_ms=180.0,
        crypto_strength=1.00,
        avg_entropy=7.9,
        detectability=0.12,
        validated=1,
    ),
    ConfigRecord(
        enc_layer="AES256",
        comp_layer="nocomp",
        obf_layer="meta",
        payload_size_kb=64,
        total_time_ms=89.0,
        crypto_strength=0.80,
        avg_entropy=7.8,
        detectability=0.35,
        validated=1,
    ),
]

_BOUNDARY: list[ConfigRecord] = [
    # 2x минимальная детектируемость
    ConfigRecord(
        enc_layer="AES256",
        comp_layer="LZMA",
        obf_layer="virt",
        payload_size_kb=64,
        total_time_ms=190.0,
        crypto_strength=1.0,
        avg_entropy=7.9,
        detectability=0.05,
        validated=0,
    ),
    ConfigRecord(
        enc_layer="AES256",
        comp_layer="LZMA",
        obf_layer="virt",
        payload_size_kb=64,
        total_time_ms=190.0,
        crypto_strength=1.0,
        avg_entropy=7.9,
        detectability=0.05,
        validated=0,
    ),
    # 2x максимальная скорость
    ConfigRecord(
        enc_layer="XOR",
        comp_layer="nocomp",
        obf_layer="noobf",
        payload_size_kb=4,
        total_time_ms=3.0,
        crypto_strength=0.2,
        avg_entropy=4.2,
        detectability=0.6,
        validated=0,
    ),
    ConfigRecord(
        enc_layer="XOR",
        comp_layer="nocomp",
        obf_layer="noobf",
        payload_size_kb=4,
        total_time_ms=3.0,
        crypto_strength=0.2,
        avg_entropy=4.2,
        detectability=0.6,
        validated=0,
    ),
    # 2x максимальная криптостойкость
    ConfigRecord(
        enc_layer="AES256",
        comp_layer="nocomp",
        obf_layer="poly",
        payload_size_kb=64,
        total_time_ms=100.0,
        crypto_strength=1.0,
        avg_entropy=7.9,
        detectability=0.20,
        validated=0,
    ),
    ConfigRecord(
        enc_layer="AES256",
        comp_layer="nocomp",
        obf_layer="poly",
        payload_size_kb=64,
        total_time_ms=100.0,
        crypto_strength=1.0,
        avg_entropy=7.9,
        detectability=0.20,
        validated=0,
    ),
    # 2x смешанные
    ConfigRecord(
        enc_layer="AES128",
        comp_layer="LZ4",
        obf_layer="meta",
        payload_size_kb=256,
        total_time_ms=80.0,
        crypto_strength=0.85,
        avg_entropy=7.0,
        detectability=0.30,
        validated=0,
    ),
    ConfigRecord(
        enc_layer="AES128",
        comp_layer="LZ4",
        obf_layer="meta",
        payload_size_kb=256,
        total_time_ms=80.0,
        crypto_strength=0.85,
        avg_entropy=7.0,
        detectability=0.30,
        validated=0,
    ),
]


def seed(repo: ConfigRepository, graph: CrypterGraph) -> int:
    """Заполняет репозиторий. Возвращает число вставленных записей."""
    random.seed(42)

    inserted = 0
    sizes = [4, 64, 256]

    for enc_id, enc_name in ENC_MAP.items():
        for comp_id, comp_name in COMP_MAP.items():
            for obf_id, obf_name in OBF_MAP.items():
                path = graph.path_from_layers(enc_id, comp_id, obf_id)
                base = graph.aggregate(path)

                base_t = base.t
                base_s = base.s
                base_e = base.e
                base_d = base.d

                for size in sizes:
                    noise_t = random.gauss(0, 0.02 * base_t)
                    t_scaled = base_t * (1 + (size - 64) / 512) + noise_t
                    t_scaled = max(0.0, t_scaled)

                    avg_entropy = base_e
                    if avg_entropy == 0.0:
                        avg_entropy = random.uniform(3.5, 5.0)

                    noise_d = random.gauss(0, 0.01)
                    d_val = max(0.0, min(1.0, base_d + noise_d))

                    record = ConfigRecord(
                        enc_layer=enc_name,
                        comp_layer=comp_name,
                        obf_layer=obf_name,
                        payload_size_kb=size,
                        total_time_ms=round(t_scaled, 4),
                        crypto_strength=base_s,
                        avg_entropy=round(avg_entropy, 4),
                        detectability=round(d_val, 4),
                        validated=0,
                    )
                    repo.insert(record)
                    inserted += 1

    # 4 канонических записи
    for canonical in _CANONICAL:
        repo.insert(canonical)
        inserted += 1

    # 8 граничных синтетических записей
    for boundary in _BOUNDARY:
        repo.insert(boundary)
        inserted += 1

    return inserted


def init_db_if_needed(db_path: Path) -> ConfigRepository:
    """Если БД не существует или пустая — запускает seed. Возвращает открытый repo."""
    repo = ConfigRepository(db_path)
    if repo.count() == 0:
        graph = CrypterGraph.from_json(_CALIB)
        seed(repo, graph)
    return repo


if __name__ == "__main__":
    from pathlib import Path

    repo = init_db_if_needed(Path(__file__).parent / "crypters.db")
    print(f"Записей в базе: {repo.count()}")
    repo.close()
