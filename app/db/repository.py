from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


@dataclass
class ConfigRecord:
    enc_layer: str
    comp_layer: str
    obf_layer: str
    payload_size_kb: int
    total_time_ms: float
    crypto_strength: float
    avg_entropy: float
    detectability: float
    validated: int = 0
    id: Optional[int] = field(default=None)


class ConfigRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        schema = _SCHEMA_PATH.read_text(encoding="utf-8")
        self._conn.executescript(schema)
        self._conn.commit()

    def insert(self, record: ConfigRecord) -> int:
        cursor = self._conn.execute(
            """
            INSERT INTO configurations
                (enc_layer, comp_layer, obf_layer, payload_size_kb,
                 total_time_ms, crypto_strength, avg_entropy, detectability, validated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.enc_layer,
                record.comp_layer,
                record.obf_layer,
                record.payload_size_kb,
                record.total_time_ms,
                record.crypto_strength,
                record.avg_entropy,
                record.detectability,
                record.validated,
            ),
        )
        self._conn.commit()
        return cursor.lastrowid

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM configurations").fetchone()
        return row[0]

    def all(self) -> List[ConfigRecord]:
        rows = self._conn.execute(
            "SELECT * FROM configurations ORDER BY id"
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def find_by_constraints(
        self,
        t_max: float,
        s_min: float,
        d_max: float,
        limit: Optional[int] = None,
    ) -> List[ConfigRecord]:
        query = """
            SELECT * FROM configurations
            WHERE total_time_ms <= ?
              AND crypto_strength >= ?
              AND detectability <= ?
            ORDER BY total_time_ms ASC
        """
        params: list = [t_max, s_min, d_max]
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_record(r) for r in rows]

    def get_by_layers(self, enc: str, comp: str, obf: str) -> List[ConfigRecord]:
        rows = self._conn.execute(
            """
            SELECT * FROM configurations
            WHERE enc_layer = ? AND comp_layer = ? AND obf_layer = ?
            ORDER BY id
            """,
            (enc, comp, obf),
        ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "ConfigRepository":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> ConfigRecord:
        return ConfigRecord(
            id=row["id"],
            enc_layer=row["enc_layer"],
            comp_layer=row["comp_layer"],
            obf_layer=row["obf_layer"],
            payload_size_kb=row["payload_size_kb"],
            total_time_ms=row["total_time_ms"],
            crypto_strength=row["crypto_strength"],
            avg_entropy=row["avg_entropy"],
            detectability=row["detectability"],
            validated=row["validated"],
        )
