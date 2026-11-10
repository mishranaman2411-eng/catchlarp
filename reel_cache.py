#!/usr/bin/env python3
"""Lightweight SQLite cache and creator trust-scoring helper for CatchLARP."""

from __future__ import annotations

from contextlib import closing
from pathlib import Path
import re
import sqlite3
from typing import Any
from urllib.parse import urlsplit


DEFAULT_DB_PATH = Path("reel_cache.db")

_INSTAGRAM_HOSTS = frozenset({
    "instagram.com",
    "www.instagram.com",
    "m.instagram.com",
})

_RESERVED_SEGMENTS = frozenset({
    "share",
    "explore",
    "accounts",
    "stories",
    "direct",
    "about",
    "developer",
    "legal",
})

_REEL_PATH_RE = re.compile(
    r"^/(?:(?P<user>[A-Za-z0-9._]+)/)?(?P<kind>reel|reels|p)/(?P<shortcode>[A-Za-z0-9_-]+)(?:/embed)?/?$",
    re.IGNORECASE,
)

_SHORTCODE_RE = re.compile(r"^[A-Za-z0-9_-]+$")

_CREATE_REEL_CACHE_SQL = """
CREATE TABLE IF NOT EXISTS reel_cache (
    reel_id TEXT PRIMARY KEY,
    creator_handle TEXT,
    transcript TEXT NOT NULL,
    is_larp INTEGER NOT NULL CHECK (is_larp IN (0, 1)),
    verdict_text TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

_CREATE_CREATORS_SQL = """
CREATE TABLE IF NOT EXISTS creators (
    handle TEXT PRIMARY KEY,
    total_checks INTEGER NOT NULL DEFAULT 0,
    larp_count INTEGER NOT NULL DEFAULT 0,
    legit_count INTEGER NOT NULL DEFAULT 0,
    trust_score REAL NOT NULL DEFAULT 100.0,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

_CREATE_DAILY_USAGE_SQL = """
CREATE TABLE IF NOT EXISTS user_daily_usage (
    user_id TEXT,
    usage_date TEXT DEFAULT (DATE('now')),
    check_count INTEGER DEFAULT 1,
    PRIMARY KEY (user_id, usage_date)
);
"""


def sanitize_creator_handle(raw_handle: str | None) -> str:
    """Normalize a creator handle to canonical @handle format."""
    if not isinstance(raw_handle, str):
        return "@unknown"
    stripped = raw_handle.strip().lstrip("@")
    if not stripped:
        return "@unknown"
    cleaned = re.sub(r"[^A-Za-z0-9._]+", "_", stripped).strip("._").lower()
    return f"@{cleaned}" if cleaned else "@unknown"


def extract_reel_shortcode(reel_url_or_id: str) -> str:
    """Extract the unique Reel shortcode from an Instagram URL or validate a bare shortcode."""
    if not isinstance(reel_url_or_id, str):
        raise ValueError("reel_id must be a string URL or shortcode.")

    candidate = reel_url_or_id.strip()
    if len(candidate) >= 2 and candidate[0] == candidate[-1] and candidate[0] in ("'", '"'):
        candidate = candidate[1:-1].strip()

    if not candidate:
        raise ValueError("reel_id cannot be empty.")

    looks_like_url = any(ch in candidate for ch in ("/", ":", "?", "#", "."))
    if not looks_like_url:
        if _SHORTCODE_RE.match(candidate):
            return candidate
        raise ValueError(f"Invalid Reel shortcode: '{candidate}'.")

    normalized = f"https:{candidate}" if candidate.startswith("//") else candidate
    parsed = urlsplit(normalized)
    if not parsed.scheme:
        parsed = urlsplit(f"https://{candidate}")

    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme '{parsed.scheme}' for Instagram Reel.")

    host = (parsed.hostname or "").lower()
    if host not in _INSTAGRAM_HOSTS:
        raise ValueError("Invalid URL: expected an instagram.com Reel link.")

    match = _REEL_PATH_RE.match(parsed.path or "")
    if not match:
        raise ValueError("Invalid Instagram Reel URL: could not extract reel shortcode.")

    user = match.group("user")
    kind = match.group("kind").lower()
    shortcode = match.group("shortcode")

    if user and user.lower() in _RESERVED_SEGMENTS:
        raise ValueError("Invalid Instagram Reel URL: unsupported Instagram path.")

    if not user and kind == "reels" and shortcode.lower() == "audio":
        raise ValueError("Instagram audio library links (/reels/audio/) do not have a reel shortcode.")

    return shortcode


def _normalize_is_larp(is_larp: int | bool) -> int:
    """Validate and coerce is_larp to integer 0 or 1."""
    if isinstance(is_larp, bool):
        return int(is_larp)
    if isinstance(is_larp, int) and is_larp in (0, 1):
        return is_larp
    raise ValueError("is_larp must be a boolean or integer (0 or 1).")


def _compute_trust_score(legit_count: int, total_checks: int) -> float:
    """Compute creator trust score percentage safely handling division by zero."""
    if total_checks <= 0:
        return 100.0
    return round((legit_count / total_checks) * 100, 1)


def _connect(db_path: str | Path) -> sqlite3.Connection:
    """Open a SQLite connection, creating parent directories for file-backed databases."""
    target = str(db_path)
    if target != ":memory:" and not target.startswith("file:"):
        Path(target).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Create tables and migrate older reel_cache tables missing creator_handle."""
    conn.execute(_CREATE_REEL_CACHE_SQL)
    conn.execute(_CREATE_CREATORS_SQL)
    conn.execute(_CREATE_DAILY_USAGE_SQL)
    existing_cols = {
        row["name"] for row in conn.execute("PRAGMA table_info(reel_cache)").fetchall()
    }
    if "creator_handle" not in existing_cols:
        conn.execute("ALTER TABLE reel_cache ADD COLUMN creator_handle TEXT")


def init_db(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    """Create the reel_cache and creators tables if they do not already exist."""
    with closing(_connect(db_path)) as conn:
        with conn:
            _ensure_schema(conn)


def _apply_creator_delta(
    conn: sqlite3.Connection,
    handle: str,
    delta_total: int,
    delta_larp: int,
    delta_legit: int,
) -> tuple[int, int, int, float]:
    """Adjust a creator's aggregate counters and recompute trust_score within an open txn."""
    conn.execute(
        """
        INSERT OR IGNORE INTO creators (handle, total_checks, larp_count, legit_count, trust_score)
        VALUES (?, 0, 0, 0, 100.0)
        """,
        (handle,),
    )
    row = conn.execute(
        "SELECT total_checks, larp_count, legit_count FROM creators WHERE handle = ?",
        (handle,),
    ).fetchone()

    total_checks = max(0, int(row["total_checks"]) + delta_total)
    larp_count = max(0, int(row["larp_count"]) + delta_larp)
    legit_count = max(0, int(row["legit_count"]) + delta_legit)
    trust_score = _compute_trust_score(legit_count, total_checks)

    conn.execute(
        """
        UPDATE creators
        SET total_checks = ?,
            larp_count = ?,
            legit_count = ?,
            trust_score = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE handle = ?
        """,
        (total_checks, larp_count, legit_count, trust_score, handle),
    )
    return total_checks, larp_count, legit_count, trust_score


def record_audit(
    reel_id: str,
    creator_handle: str,
    is_larp: int | bool,
    verdict_text: str,
    transcript: str,
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    """Persist a Reel audit and atomically update creator trust scoring in one transaction."""
    shortcode = extract_reel_shortcode(reel_id)
    handle = sanitize_creator_handle(creator_handle)
    is_larp_int = _normalize_is_larp(is_larp)

    if not isinstance(transcript, str):
        raise ValueError("transcript must be a string.")
    if not isinstance(verdict_text, str) or not verdict_text.strip():
        raise ValueError("verdict_text must be a non-empty string.")

    with closing(_connect(db_path)) as conn:
        with conn:
            _ensure_schema(conn)
            existing = conn.execute(
                "SELECT creator_handle, is_larp FROM reel_cache WHERE reel_id = ?",
                (shortcode,),
            ).fetchone()

            conn.execute(
                """
                INSERT INTO reel_cache (reel_id, creator_handle, transcript, is_larp, verdict_text, created_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(reel_id) DO UPDATE SET
                    creator_handle = excluded.creator_handle,
                    transcript = excluded.transcript,
                    is_larp = excluded.is_larp,
                    verdict_text = excluded.verdict_text,
                    created_at = CURRENT_TIMESTAMP
                """,
                (shortcode, handle, transcript, is_larp_int, verdict_text),
            )

            new_larp = 1 if is_larp_int == 1 else 0
            new_legit = 0 if is_larp_int == 1 else 1

            if existing is None:
                total_checks, larp_count, legit_count, trust_score = _apply_creator_delta(
                    conn, handle, 1, new_larp, new_legit
                )
            else:
                prev_handle = sanitize_creator_handle(existing["creator_handle"])
                prev_larp = 1 if int(existing["is_larp"]) == 1 else 0
                prev_legit = 0 if prev_larp == 1 else 1

                if prev_handle == handle:
                    total_checks, larp_count, legit_count, trust_score = _apply_creator_delta(
                        conn,
                        handle,
                        0,
                        new_larp - prev_larp,
                        new_legit - prev_legit,
                    )
                else:
                    if existing["creator_handle"]:
                        _apply_creator_delta(conn, prev_handle, -1, -prev_larp, -prev_legit)
                    total_checks, larp_count, legit_count, trust_score = _apply_creator_delta(
                        conn, handle, 1, new_larp, new_legit
                    )

    return {
        "reel_id": shortcode,
        "creator_handle": handle,
        "is_larp": bool(is_larp_int),
        "total_checks": total_checks,
        "larp_count": larp_count,
        "legit_count": legit_count,
        "trust_score": trust_score,
    }


def get_cached_verdict(
    reel_id: str,
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any] | None:
    """Look up a cached Reel verdict by URL or shortcode, returning None if not cached."""
    shortcode = extract_reel_shortcode(reel_id)
    with closing(_connect(db_path)) as conn:
        with conn:
            _ensure_schema(conn)
            row = conn.execute(
                """
                SELECT reel_id, creator_handle, transcript, is_larp, verdict_text, created_at
                FROM reel_cache
                WHERE reel_id = ?
                """,
                (shortcode,),
            ).fetchone()

    if row is None:
        return None

    return {
        "reel_id": row["reel_id"],
        "creator_handle": row["creator_handle"] or "@unknown",
        "transcript": row["transcript"],
        "is_larp": bool(row["is_larp"]),
        "verdict_text": row["verdict_text"],
        "created_at": row["created_at"],
    }


def save_cached_verdict(
    reel_id: str,
    transcript: str,
    is_larp: int | bool,
    verdict_text: str,
    *,
    creator_handle: str | None = None,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> str:
    """Insert or update a cached Reel verdict keyed by shortcode and return the shortcode."""
    shortcode = extract_reel_shortcode(reel_id)
    is_larp_int = _normalize_is_larp(is_larp)
    handle = sanitize_creator_handle(creator_handle) if creator_handle is not None else None

    if not isinstance(transcript, str):
        raise ValueError("transcript must be a string.")
    if not isinstance(verdict_text, str) or not verdict_text.strip():
        raise ValueError("verdict_text must be a non-empty string.")

    with closing(_connect(db_path)) as conn:
        with conn:
            _ensure_schema(conn)
            conn.execute(
                """
                INSERT INTO reel_cache (reel_id, creator_handle, transcript, is_larp, verdict_text, created_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(reel_id) DO UPDATE SET
                    creator_handle = COALESCE(excluded.creator_handle, reel_cache.creator_handle),
                    transcript = excluded.transcript,
                    is_larp = excluded.is_larp,
                    verdict_text = excluded.verdict_text,
                    created_at = CURRENT_TIMESTAMP
                """,
                (shortcode, handle, transcript, is_larp_int, verdict_text),
            )

    return shortcode


def list_cached_verdicts(
    limit: int = 50,
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> list[dict[str, Any]]:
    """Return recent cached Reel audits ordered newest-first."""
    safe_limit = max(1, min(int(limit), 200))
    with closing(_connect(db_path)) as conn:
        with conn:
            _ensure_schema(conn)
            rows = conn.execute(
                """
                SELECT reel_id, creator_handle, transcript, is_larp, verdict_text, created_at
                FROM reel_cache
                ORDER BY created_at DESC, rowid DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()

    return [
        {
            "reel_id": row["reel_id"],
            "creator_handle": row["creator_handle"] or "@unknown",
            "transcript": row["transcript"],
            "is_larp": bool(row["is_larp"]),
            "verdict_text": row["verdict_text"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def get_larpking_leaderboard(
    limit: int = 10,
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, list[dict[str, Any]]]:
    """Return top flagged creators and verified legit creators from the creators table."""
    safe_limit = max(1, min(int(limit), 100))
    with closing(_connect(db_path)) as conn:
        with conn:
            _ensure_schema(conn)
            flagged_rows = conn.execute(
                """
                SELECT handle, total_checks, larp_count, legit_count, trust_score, updated_at
                FROM creators
                WHERE total_checks > 0 AND larp_count > 0
                ORDER BY trust_score ASC, total_checks DESC, handle ASC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()

            legit_rows = conn.execute(
                """
                SELECT handle, total_checks, larp_count, legit_count, trust_score, updated_at
                FROM creators
                WHERE total_checks > 0 AND legit_count > 0
                ORDER BY trust_score DESC, total_checks DESC, handle ASC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()

    def _to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "handle": row["handle"],
            "total_checks": int(row["total_checks"]),
            "larp_count": int(row["larp_count"]),
            "legit_count": int(row["legit_count"]),
            "trust_score": float(row["trust_score"]),
            "updated_at": row["updated_at"],
        }

    return {
        "flagged_creators": [_to_dict(row) for row in flagged_rows],
        "legit_creators": [_to_dict(row) for row in legit_rows],
    }


def get_cache_stats(*, db_path: str | Path = DEFAULT_DB_PATH) -> dict[str, int]:
    """Return summary counts and SQLite file size in bytes for reel_cache."""
    with closing(_connect(db_path)) as conn:
        with conn:
            _ensure_schema(conn)
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    COALESCE(SUM(CASE WHEN is_larp = 1 THEN 1 ELSE 0 END), 0) AS larp_count,
                    COALESCE(SUM(CASE WHEN is_larp = 0 THEN 1 ELSE 0 END), 0) AS real_count
                FROM reel_cache
                """
            ).fetchone()

    target = Path(db_path)
    db_bytes = target.stat().st_size if str(db_path) != ":memory:" and target.is_file() else 0
    return {
        "total": int(row["total"]),
        "larp_count": int(row["larp_count"]),
        "real_count": int(row["real_count"]),
        "db_bytes": int(db_bytes),
    }


def clear_cached_verdicts(*, db_path: str | Path = DEFAULT_DB_PATH) -> int:
    """Delete all rows from reel_cache and creators and return removed audit count."""
    with closing(_connect(db_path)) as conn:
        with conn:
            _ensure_schema(conn)
            cursor = conn.execute("DELETE FROM reel_cache")
            conn.execute("DELETE FROM creators")
            return int(cursor.rowcount or 0)


def check_user_quota(
    user_id: str,
    daily_limit: int = 20,
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> tuple[bool, int]:
    """Return (allowed, current_usage) for user_id against daily_limit for UTC today."""
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("user_id must be a non-empty string.")
    clean_uid = user_id.strip()

    with closing(_connect(db_path)) as conn:
        with conn:
            _ensure_schema(conn)
            row = conn.execute(
                """
                SELECT check_count
                FROM user_daily_usage
                WHERE user_id = ? AND usage_date = DATE('now')
                """,
                (clean_uid,),
            ).fetchone()

    current_usage = int(row["check_count"]) if row is not None and row["check_count"] is not None else 0
    return (current_usage < daily_limit, current_usage)


def increment_user_quota(
    user_id: str,
    *,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> None:
    """Insert or increment user_id's check_count for the current UTC date."""
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("user_id must be a non-empty string.")
    clean_uid = user_id.strip()

    with closing(_connect(db_path)) as conn:
        with conn:
            _ensure_schema(conn)
            conn.execute(
                """
                INSERT INTO user_daily_usage (user_id, usage_date, check_count)
                VALUES (?, DATE('now'), 1)
                ON CONFLICT(user_id, usage_date) DO UPDATE SET
                    check_count = user_daily_usage.check_count + 1
                """,
                (clean_uid,),
            )


if __name__ == "__main__":
    init_db()
    print(f"Initialized SQLite tables 'reel_cache' and 'creators' in {DEFAULT_DB_PATH}")
