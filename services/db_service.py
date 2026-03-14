"""
db_service.py – SQLite para histórico de análises.
"""
import sqlite3
import json
import os
from datetime import datetime

DB_PATH = "data/shrimpscan.db"

def init_db():
    os.makedirs("data", exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at  TEXT    NOT NULL,
            type        TEXT    NOT NULL,
            filename    TEXT,
            summary     TEXT,
            result_json TEXT
        )
    """)
    con.commit()
    con.close()

def save_analysis(analysis_type: str, filename: str, result: dict):
    # Cria sumário textual (sem imagem base64 para economizar espaço)
    summary_keys = ["count","stats","swim_index","swim_class","overall_score",
                    "status","stage","batch_quality","size_mean_mm","processing_time_s"]
    summary = {k: result[k] for k in summary_keys if k in result}
    result_clean = {k: v for k, v in result.items()
                    if k not in ("annotated_image", "preview_frames")}
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        "INSERT INTO analyses (created_at, type, filename, summary, result_json) VALUES (?,?,?,?,?)",
        (datetime.utcnow().isoformat(), analysis_type, filename,
         json.dumps(summary, ensure_ascii=False),
         json.dumps(result_clean, ensure_ascii=False))
    )
    con.commit()
    row_id = cur.lastrowid
    con.close()
    return row_id

def get_history(limit: int = 50, analysis_type: str = None):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    if analysis_type:
        cur.execute("SELECT id,created_at,type,filename,summary FROM analyses WHERE type=? ORDER BY id DESC LIMIT ?",
                    (analysis_type, limit))
    else:
        cur.execute("SELECT id,created_at,type,filename,summary FROM analyses ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    con.close()
    return [{"id": r[0], "created_at": r[1], "type": r[2], "filename": r[3],
             "summary": json.loads(r[4])} for r in rows]

def get_stats():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT type, COUNT(*) FROM analyses GROUP BY type")
    by_type = dict(cur.fetchall())
    cur.execute("SELECT COUNT(*) FROM analyses")
    total = cur.fetchone()[0]
    cur.execute("""
        SELECT DATE(created_at) as d, COUNT(*) FROM analyses
        WHERE created_at >= DATE('now','-7 days')
        GROUP BY d ORDER BY d
    """)
    recent_7d = [{"date": r[0], "count": r[1]} for r in cur.fetchall()]
    con.close()
    return {"total": total, "by_type": by_type, "recent_7d": recent_7d}

def delete_analysis(analysis_id: int):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("DELETE FROM analyses WHERE id=?", (analysis_id,))
    con.commit()
    deleted = cur.rowcount
    con.close()
    return deleted > 0

def get_full_result(analysis_id: int) -> dict:
    """Retorna o resultado completo (JSON) de uma análise pelo ID."""
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT result_json FROM analyses WHERE id=?", (analysis_id,))
    row = cur.fetchone()
    con.close()
    if row is None:
        return None
    return json.loads(row[0])

def export_csv() -> str:
    import csv, io
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("SELECT id,created_at,type,filename,summary FROM analyses ORDER BY id DESC")
    rows = cur.fetchall()
    con.close()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id","created_at","type","filename","summary"])
    for r in rows:
        w.writerow(r)
    return buf.getvalue()
