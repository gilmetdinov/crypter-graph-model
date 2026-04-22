from __future__ import annotations

from pathlib import Path

import pytest

from app.db.repository import ConfigRecord, ConfigRepository
from app.db.seed import init_db_if_needed


def _make_record(
    enc: str = "XOR",
    comp: str = "nocomp",
    obf: str = "noobf",
    kb: int = 64,
    t: float = 10.0,
    s: float = 0.5,
    e: float = 5.0,
    d: float = 0.4,
    validated: int = 0,
) -> ConfigRecord:
    return ConfigRecord(
        enc_layer=enc,
        comp_layer=comp,
        obf_layer=obf,
        payload_size_kb=kb,
        total_time_ms=t,
        crypto_strength=s,
        avg_entropy=e,
        detectability=d,
        validated=validated,
    )


@pytest.fixture()
def repo(tmp_path: Path) -> ConfigRepository:
    db = tmp_path / "test.db"
    r = ConfigRepository(db)
    yield r
    r.close()


def test_insert_and_count(repo: ConfigRepository) -> None:
    assert repo.count() == 0
    repo.insert(_make_record(t=10.0))
    repo.insert(_make_record(enc="AES256", t=50.0))
    assert repo.count() == 2


def test_find_by_constraints(repo: ConfigRepository) -> None:
    # record 1: fast, strong, low detect
    repo.insert(_make_record(enc="XOR", t=20.0, s=0.3, d=0.2))
    # record 2: slow, very strong, very low detect
    repo.insert(_make_record(enc="AES256", t=150.0, s=1.0, d=0.1))
    # record 3: medium, weak, high detect
    repo.insert(_make_record(enc="AES128", t=60.0, s=0.5, d=0.7))

    # only record 1 satisfies t<=100, s>=0.3, d<=0.3
    results = repo.find_by_constraints(t_max=100.0, s_min=0.3, d_max=0.3)
    assert len(results) == 1
    assert results[0].enc_layer == "XOR"

    # records 1 and 2 satisfy s>=0.3 and d<=0.3, but record 2 fails t<=100
    results2 = repo.find_by_constraints(t_max=200.0, s_min=0.3, d_max=0.3)
    assert len(results2) == 2

    # limit test
    results3 = repo.find_by_constraints(t_max=200.0, s_min=0.0, d_max=1.0, limit=2)
    assert len(results3) == 2


def test_seed_count(tmp_path: Path) -> None:
    db = tmp_path / "seeded.db"
    repo = init_db_if_needed(db)
    count = repo.count()
    repo.close()
    assert count == 120


def test_validated_count(tmp_path: Path) -> None:
    db = tmp_path / "validated.db"
    repo = init_db_if_needed(db)
    records = repo.all()
    validated = [r for r in records if r.validated == 1]
    repo.close()
    assert len(validated) == 4
