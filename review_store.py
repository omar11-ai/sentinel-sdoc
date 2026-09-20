"""Reviewer round-trip store — the audit backbone (blueprint §8).

Two append-only tables:
  reviews       one row per reviewer action (confirm / correct / reject_flag /
                unresolvable), with the version the action applied to
  audit_events  one row per state change (entity, event, actor, before, after)

The original extraction is NEVER mutated. A correction is an overlay: the
stored documents gain a reviewer-corrected value, the comparison re-runs, and
the verdict is recomputed — never overwritten. SQLite keeps the prelim
single-file and dependency-free; the production path (managed Postgres) is
documented in ARCHITECTURE.md.
"""
from __future__ import annotations

import datetime
import json
import sqlite3
import threading

_LOCK = threading.Lock()
_CONN: sqlite3.Connection | None = None


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def init(path: str = "review_store.db") -> None:
    global _CONN
    _CONN = sqlite3.connect(path, check_same_thread=False)
    _CONN.row_factory = sqlite3.Row
    _CONN.executescript(
        """
        CREATE TABLE IF NOT EXISTS reviews (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            email_id   TEXT NOT NULL,
            version    INTEGER NOT NULL,
            reviewer   TEXT NOT NULL,
            action     TEXT NOT NULL,
            field      TEXT,
            old_value  TEXT,
            new_value  TEXT,
            reason_note TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit_events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            entity_id   TEXT NOT NULL,
            event       TEXT NOT NULL,
            actor       TEXT NOT NULL,
            before      TEXT,
            after       TEXT,
            created_at  TEXT NOT NULL
        );
        """
    )
    _CONN.commit()


def _require() -> sqlite3.Connection:
    if _CONN is None:
        init()
    return _CONN  # type: ignore[return-value]


def log_review(email_id: str, version: int, reviewer: str, action: str,
               field: str | None = None, old_value: str | None = None,
               new_value: str | None = None, reason_note: str | None = None) -> int:
    with _LOCK:
        c = _require()
        cur = c.execute(
            "INSERT INTO reviews (email_id, version, reviewer, action, field, old_value,"
            " new_value, reason_note, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (email_id, version, reviewer, action, field, old_value, new_value,
             reason_note, _now()),
        )
        c.commit()
        return int(cur.lastrowid or 0)


def log_audit(entity_type: str, entity_id: str, event: str, actor: str,
              before: object, after: object) -> int:
    with _LOCK:
        c = _require()
        cur = c.execute(
            "INSERT INTO audit_events (entity_type, entity_id, event, actor, before,"
            " after, created_at) VALUES (?,?,?,?,?,?,?)",
            (entity_type, entity_id, event, actor,
             json.dumps(before, ensure_ascii=False) if before is not None else None,
             json.dumps(after, ensure_ascii=False) if after is not None else None,
             _now()),
        )
        c.commit()
        return int(cur.lastrowid or 0)


def history(email_id: str, limit: int = 100) -> list[dict]:
    with _LOCK:
        c = _require()
        rows = c.execute(
            "SELECT * FROM reviews WHERE email_id = ? ORDER BY id DESC LIMIT ?",
            (email_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def audit_for(email_id: str, limit: int = 100) -> list[dict]:
    with _LOCK:
        c = _require()
        rows = c.execute(
            "SELECT * FROM audit_events WHERE entity_type = 'email' AND entity_id = ?"
            " ORDER BY id DESC LIMIT ?",
            (email_id, limit),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        for k in ("before", "after"):
            try:
                d[k] = json.loads(d[k]) if d[k] is not None else None
            except Exception:
                pass
        out.append(d)
    return out


def recent_audit(limit: int = 200) -> list[dict]:
    with _LOCK:
        c = _require()
        rows = c.execute(
            "SELECT * FROM audit_events ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        for k in ("before", "after"):
            try:
                d[k] = json.loads(d[k]) if d[k] is not None else None
            except Exception:
                pass
        out.append(d)
    return out


def version_for(email_id: str) -> int:
    """Optimistic-concurrency version = number of recorded actions so far."""
    with _LOCK:
        c = _require()
        row = c.execute(
            "SELECT COUNT(*) AS n FROM reviews WHERE email_id = ?", (email_id,)
        ).fetchone()
    return int(row["n"]) if row else 0


def all_reviews_asc() -> list[dict]:
    """Every review in application order — used to replay overlays at startup."""
    with _LOCK:
        c = _require()
        rows = c.execute("SELECT * FROM reviews ORDER BY id ASC").fetchall()
    return [dict(r) for r in rows]
