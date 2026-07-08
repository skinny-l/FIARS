"""
queries.py — raw aggregations over case_history. Stdlib sqlite3 only.

Trend/month bucketing uses `created_at` (an ISO timestamp FIARS sets itself
on every insert) rather than the free-text `date` field, which is operator-
entered and inconsistently formatted (see recommend.py's multi-format
parsing for how messy that field can get). created_at answers "when did
FIARS log this case" rather than "when did the fault occur" — close enough
for month-over-month trend shape, and it never fails to parse.
"""
from __future__ import annotations

from datetime import datetime

from .. import db


def _month_of(created_at: str) -> str:
    if not created_at:
        return "unknown"
    try:
        return datetime.fromisoformat(created_at).strftime("%Y-%m")
    except ValueError:
        return "unknown"


def top_labels(path: str, column: str, limit: int = 10) -> list[dict]:
    """Generic top-N over a case_history text column (root_cause, solution, parts)."""
    allowed = {"root_cause", "solution", "parts", "engineer"}
    if column not in allowed:
        raise ValueError(f"column must be one of {allowed}")
    con = db.connect(path)
    rows = con.execute(
        f"""SELECT TRIM({column}) AS label, COUNT(*) AS n
            FROM case_history
            WHERE TRIM(COALESCE({column}, '')) != ''
            GROUP BY label ORDER BY n DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    con.close()
    return [{"label": r["label"], "n": r["n"]} for r in rows]


def mttr_overall(path: str) -> dict:
    con = db.connect(path)
    row = con.execute(
        "SELECT AVG(resolution_time_min) AS mttr, COUNT(*) AS n "
        "FROM case_history WHERE resolution_time_min IS NOT NULL"
    ).fetchone()
    con.close()
    return {"mttr_minutes": round(row["mttr"], 1) if row["mttr"] is not None else None,
            "n": row["n"] or 0}


def mttr_by_month(path: str) -> list[dict]:
    con = db.connect(path)
    rows = con.execute(
        "SELECT created_at, resolution_time_min FROM case_history "
        "WHERE resolution_time_min IS NOT NULL"
    ).fetchall()
    con.close()
    buckets: dict[str, list[float]] = {}
    for r in rows:
        buckets.setdefault(_month_of(r["created_at"]), []).append(r["resolution_time_min"])
    out = [
        {"month": m, "mttr_minutes": round(sum(v) / len(v), 1), "n": len(v)}
        for m, v in buckets.items() if m != "unknown"
    ]
    out.sort(key=lambda x: x["month"])
    return out


def recurrence_rate_overall(path: str) -> dict:
    con = db.connect(path)
    row = con.execute(
        "SELECT AVG(recurrence_flag) AS rate, COUNT(*) AS n FROM case_history"
    ).fetchone()
    con.close()
    return {"rate": round(row["rate"], 4) if row["rate"] is not None else 0.0, "n": row["n"] or 0}


def recurrence_by_resolution(path: str, limit: int = 10, min_n: int = 2) -> list[dict]:
    """Which fixes hold vs. which recur — the doc's 'most valuable view.'"""
    con = db.connect(path)
    rows = con.execute(
        """SELECT TRIM(solution) AS label, COUNT(*) AS n, AVG(recurrence_flag) AS rate
           FROM case_history
           WHERE TRIM(COALESCE(solution, '')) != ''
           GROUP BY label HAVING n >= ? ORDER BY n DESC LIMIT ?""",
        (min_n, limit),
    ).fetchall()
    con.close()
    return [{"label": r["label"], "n": r["n"], "recurrence_rate": round(r["rate"], 4)} for r in rows]


def monthly_volume(path: str) -> list[dict]:
    con = db.connect(path)
    rows = con.execute("SELECT created_at FROM case_history").fetchall()
    con.close()
    buckets: dict[str, int] = {}
    for r in rows:
        m = _month_of(r["created_at"])
        if m != "unknown":
            buckets[m] = buckets.get(m, 0) + 1
    return [{"month": m, "n": n} for m, n in sorted(buckets.items())]


def recurrence_trend_by_month(path: str) -> list[dict]:
    con = db.connect(path)
    rows = con.execute("SELECT created_at, recurrence_flag FROM case_history").fetchall()
    con.close()
    buckets: dict[str, list[int]] = {}
    for r in rows:
        m = _month_of(r["created_at"])
        if m != "unknown":
            buckets.setdefault(m, []).append(r["recurrence_flag"] or 0)
    out = [{"month": m, "recurrence_rate": round(sum(v) / len(v), 4), "n": len(v)}
           for m, v in buckets.items()]
    out.sort(key=lambda x: x["month"])
    return out


def engineer_contribution(path: str) -> list[dict]:
    return top_labels(path, "engineer", limit=1000)


def total_cases(path: str) -> int:
    con = db.connect(path)
    n = con.execute("SELECT COUNT(*) AS n FROM case_history").fetchone()["n"]
    con.close()
    return n


def cases_this_month(path: str) -> int:
    current = datetime.now().strftime("%Y-%m")
    con = db.connect(path)
    rows = con.execute("SELECT created_at FROM case_history").fetchall()
    con.close()
    return sum(1 for r in rows if _month_of(r["created_at"]) == current)
