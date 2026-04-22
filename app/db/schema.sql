CREATE TABLE IF NOT EXISTS configurations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    enc_layer       TEXT NOT NULL,
    comp_layer      TEXT NOT NULL,
    obf_layer       TEXT NOT NULL,
    payload_size_kb INTEGER NOT NULL,
    total_time_ms   REAL NOT NULL,
    crypto_strength REAL NOT NULL,
    avg_entropy     REAL NOT NULL,
    detectability   REAL NOT NULL,
    validated       INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_cfg_metrics ON configurations
    (total_time_ms, crypto_strength, detectability);
