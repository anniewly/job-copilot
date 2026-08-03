from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from models import Fact


def default_db_path() -> Path:
    return Path(os.getenv("JOB_COPILOT_DB", "data/job_copilot.db"))


@contextmanager
def connection(db_path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    path = Path(db_path) if db_path else default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: str | Path | None = None) -> None:
    with connection(db_path) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact_type TEXT NOT NULL,
            title TEXT NOT NULL,
            organization TEXT NOT NULL DEFAULT '',
            start_date TEXT,
            end_date TEXT,
            content TEXT NOT NULL,
            skills_json TEXT NOT NULL DEFAULT '[]',
            metrics_json TEXT NOT NULL DEFAULT '[]',
            confirmed INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL DEFAULT '',
            jd_text TEXT NOT NULL,
            jd_analysis_json TEXT,
            match_report_json TEXT,
            status TEXT NOT NULL DEFAULT 'Interested',
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
            kind TEXT NOT NULL,
            version INTEGER NOT NULL,
            content_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(job_id, kind, version)
        );
        """)


def get_setting(key: str, db_path: str | Path | None = None) -> str | None:
    with connection(db_path) as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None


def set_setting(key: str, value: str, db_path: str | Path | None = None) -> None:
    with connection(db_path) as conn:
        conn.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )


def save_fact(fact: Fact, db_path: str | Path | None = None) -> int:
    with connection(db_path) as conn:
        cur = conn.execute(
            """INSERT INTO facts
            (fact_type,title,organization,start_date,end_date,content,skills_json,metrics_json,confirmed)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (fact.fact_type.value, fact.title, fact.organization,
             fact.start_date.isoformat() if fact.start_date else None,
             fact.end_date.isoformat() if fact.end_date else None,
             fact.content, json.dumps(fact.skills, ensure_ascii=False),
             json.dumps(fact.metrics, ensure_ascii=False), int(fact.confirmed)),
        )
        return int(cur.lastrowid)


def list_facts(confirmed_only: bool = False, db_path: str | Path | None = None) -> list[Fact]:
    query = "SELECT * FROM facts" + (" WHERE confirmed = 1" if confirmed_only else "") + " ORDER BY id DESC"
    with connection(db_path) as conn:
        rows = conn.execute(query).fetchall()
    return [
        Fact(
            id=r["id"], fact_type=r["fact_type"], title=r["title"],
            organization=r["organization"], start_date=r["start_date"],
            end_date=r["end_date"], content=r["content"],
            skills=json.loads(r["skills_json"]), metrics=json.loads(r["metrics_json"]),
            confirmed=bool(r["confirmed"]), created_at=r["created_at"],
        ) for r in rows
    ]


def set_fact_confirmed(fact_id: int, confirmed: bool, db_path: str | Path | None = None) -> None:
    with connection(db_path) as conn:
        conn.execute("UPDATE facts SET confirmed=? WHERE id=?", (int(confirmed), fact_id))


def delete_fact(fact_id: int, db_path: str | Path | None = None) -> None:
    with connection(db_path) as conn:
        conn.execute("DELETE FROM facts WHERE id=?", (fact_id,))


def save_job(company: str, title: str, url: str, jd_text: str, analysis_json: str,
             match_json: str, db_path: str | Path | None = None) -> int:
    with connection(db_path) as conn:
        cur = conn.execute(
            """INSERT INTO jobs(company,title,url,jd_text,jd_analysis_json,match_report_json)
            VALUES(?,?,?,?,?,?)""", (company, title, url, jd_text, analysis_json, match_json))
        return int(cur.lastrowid)


def list_jobs(db_path: str | Path | None = None) -> list[dict]:
    with connection(db_path) as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM jobs ORDER BY updated_at DESC").fetchall()]


def update_job_status(job_id: int, status: str, notes: str, db_path: str | Path | None = None) -> None:
    with connection(db_path) as conn:
        conn.execute(
            "UPDATE jobs SET status=?, notes=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (status, notes, job_id),
        )


def list_materials(job_id: int, db_path: str | Path | None = None) -> list[dict]:
    with connection(db_path) as conn:
        rows = conn.execute(
            "SELECT id, kind, version, created_at FROM materials WHERE job_id=? ORDER BY id DESC",
            (job_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def save_material(job_id: int, kind: str, content_json: str,
                  db_path: str | Path | None = None) -> int:
    with connection(db_path) as conn:
        version = conn.execute(
            "SELECT COALESCE(MAX(version),0)+1 FROM materials WHERE job_id=? AND kind=?",
            (job_id, kind),
        ).fetchone()[0]
        cur = conn.execute(
            "INSERT INTO materials(job_id,kind,version,content_json) VALUES(?,?,?,?)",
            (job_id, kind, version, content_json),
        )
        return int(cur.lastrowid)

