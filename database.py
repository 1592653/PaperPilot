"""SQLite database for storing experiments, papers, and knowledge entries."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path


class Database:
    """Persistent storage for research artifacts."""

    def __init__(self, db_path: str = "paperpilot.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                authors TEXT,
                source TEXT,
                abstract TEXT,
                key_findings TEXT,
                methodology TEXT,
                tags TEXT DEFAULT '[]',
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                dataset TEXT,
                model_arch TEXT,
                hyperparams TEXT DEFAULT '{}',
                metrics TEXT DEFAULT '{}',
                code_path TEXT,
                status TEXT DEFAULT 'planned',
                notes TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                source_experiment TEXT,
                tags TEXT DEFAULT '[]',
                created_at TEXT DEFAULT (datetime('now'))
            );
        """)
        self.conn.commit()

    # --- Papers ---
    def add_paper(self, title: str, authors: str = "", source: str = "",
                  abstract: str = "", key_findings: str = "", methodology: str = "",
                  tags: list | None = None) -> int:
        cur = self.conn.execute(
            "INSERT INTO papers (title, authors, source, abstract, key_findings, methodology, tags) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (title, authors, source, abstract, key_findings, methodology, json.dumps(tags or [])),
        )
        self.conn.commit()
        return cur.lastrowid

    def search_papers(self, keyword: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM papers WHERE title LIKE ? OR abstract LIKE ? OR tags LIKE ?",
            (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_recent_papers(self, limit: int = 20) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM papers ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Experiments ---
    def add_experiment(self, name: str, description: str = "", dataset: str = "",
                       model_arch: str = "", hyperparams: dict | None = None) -> int:
        cur = self.conn.execute(
            "INSERT INTO experiments (name, description, dataset, model_arch, hyperparams) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, description, dataset, model_arch, json.dumps(hyperparams or {})),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_experiment(self, exp_id: int, **kwargs) -> None:
        kwargs["updated_at"] = datetime.now().isoformat()
        if "metrics" in kwargs and isinstance(kwargs["metrics"], dict):
            kwargs["metrics"] = json.dumps(kwargs["metrics"])
        if "hyperparams" in kwargs and isinstance(kwargs["hyperparams"], dict):
            kwargs["hyperparams"] = json.dumps(kwargs["hyperparams"])
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [exp_id]
        self.conn.execute(f"UPDATE experiments SET {sets} WHERE id = ?", vals)
        self.conn.commit()

    def get_experiments(self, status: str | None = None, limit: int = 50) -> list[dict]:
        if status:
            rows = self.conn.execute(
                "SELECT * FROM experiments WHERE status = ? ORDER BY updated_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM experiments ORDER BY updated_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_best_experiments(self, metric_key: str, limit: int = 10) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM experiments WHERE metrics != '{}' ORDER BY updated_at DESC", ()
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            metrics = json.loads(d.get("metrics", "{}"))
            if metric_key in metrics:
                d["_sort_val"] = metrics[metric_key]
                results.append(d)
        results.sort(key=lambda x: x["_sort_val"], reverse=True)
        return results[:limit]

    # --- Knowledge ---
    def add_knowledge(self, category: str, title: str, content: str,
                      source_experiment: str = "", tags: list | None = None) -> int:
        cur = self.conn.execute(
            "INSERT INTO knowledge (category, title, content, source_experiment, tags) "
            "VALUES (?, ?, ?, ?, ?)",
            (category, title, content, source_experiment, json.dumps(tags or [])),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_knowledge(self, category: str | None = None) -> list[dict]:
        if category:
            rows = self.conn.execute(
                "SELECT * FROM knowledge WHERE category = ? ORDER BY created_at DESC", (category,)
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM knowledge ORDER BY created_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self.conn.close()
