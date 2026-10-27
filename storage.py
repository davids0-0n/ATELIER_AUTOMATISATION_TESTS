"""
Stockage des runs dans une base SQLite (un simple fichier runs.db).
"""
import json
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runs.db")


def _connexion():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            api             TEXT NOT NULL,
            timestamp       TEXT NOT NULL,
            passed          INTEGER NOT NULL,
            failed          INTEGER NOT NULL,
            error_rate      REAL,
            latency_ms_avg  REAL,
            latency_ms_p95  REAL,
            available       INTEGER NOT NULL,
            verdict         TEXT,
            details_json    TEXT NOT NULL
        )
    """)
    return conn


def save_run(run):
    """Enregistre un run et renvoie son identifiant."""
    s = run["summary"]
    with _connexion() as conn:
        cur = conn.execute(
            """INSERT INTO runs (api, timestamp, passed, failed, error_rate,
                                 latency_ms_avg, latency_ms_p95, available, verdict, details_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (run["api"], run["timestamp"], s["passed"], s["failed"], s["error_rate"],
             s["latency_ms_avg"], s["latency_ms_p95"], int(s["available"]), s["verdict"],
             json.dumps(run, ensure_ascii=False)),
        )
        return cur.lastrowid


def list_runs(limite=50):
    """Les derniers runs (le plus récent en premier), en version complète."""
    with _connexion() as conn:
        lignes = conn.execute(
            "SELECT id, details_json FROM runs ORDER BY id DESC LIMIT ?", (limite,)
        ).fetchall()
    runs = []
    for ligne in lignes:
        run = json.loads(ligne["details_json"])
        run["id"] = ligne["id"]
        runs.append(run)
    return runs


def last_run():
    runs = list_runs(1)
    return runs[0] if runs else None
