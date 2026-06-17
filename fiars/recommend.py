"""
recommend.py — Ranking & confidence engine.

Given a new fault's presenting text, retrieve similar verified cases and
aggregate their *outcomes* into confidence-scored root causes and resolutions.
Also checks the knowledge base (KB) for error-pattern matches.

    weight_i = similarity_i x recency_i x success_i
        similarity_i : rank-decay from BM25 retrieval        (in [0,1])
        recency_i    : exp(-age_days / TAU)                  (recent fixes weigh more)
        success_i    : 1.0 if the fix held, else RHO          (recurrence = failed fix)
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Any

from . import db

TAU_DAYS = 365.0
RHO = 0.25
ALPHA = 0.5


def _age_days(case_date: str) -> float:
    if not case_date:
        return 180.0
    for fmt in ("%Y-%m-%d", "%d %B %Y", "%Y-%m-%dT%H:%M:%S%z",
                "%d %B %Y", "%B %d, %Y"):
        try:
            dt = datetime.strptime(case_date.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return max(0.0, (datetime.now(timezone.utc) - dt).days)
        except ValueError:
            continue
    return 180.0


def _aggregate(cases: list[dict], key: str) -> tuple[list[dict], float, int]:
    """Weighted aggregation over `key` (root_cause_raw / resolution_raw)."""
    buckets: dict[str, dict[str, Any]] = {}
    total_w = 0.0
    for c in cases:
        label = (c.get(key) or "").strip()
        if not label:
            continue
        sim = c.get("similarity", 0.0)
        recency = math.exp(-_age_days(c.get("case_date", "")) / TAU_DAYS)
        success = 1.0 if int(c.get("recurrence_flag", 0)) == 0 else RHO
        w = sim * recency * success
        total_w += w
        b = buckets.setdefault(label, {"label": label, "weight": 0.0,
                                       "n": 0, "cases": []})
        b["weight"] += w
        b["n"] += 1
        b["cases"].append((w, c["case_id"]))

    n_buckets = len(buckets)
    denom = total_w + ALPHA * (n_buckets + 1)
    ranked = []
    for b in buckets.values():
        conf = (b["weight"] + ALPHA) / denom if denom else 0.0
        top_cases = [cid for _, cid in sorted(b["cases"], reverse=True)[:5]]
        ranked.append({"label": b["label"], "confidence": round(conf, 4),
                       "n": b["n"], "support": top_cases})
    ranked.sort(key=lambda x: x["confidence"], reverse=True)
    if denom:
        other = round(ALPHA / denom, 4)
        if other >= 0.005:
            ranked.append({"label": "Other", "confidence": other, "n": 0, "support": []})
    return ranked, total_w, len(cases)


def _evidence_label(n: int, mass: float) -> str:
    if n == 0:
        return "none"
    if n < 5:
        return "low"
    if n < 15:
        return "moderate"
    return "strong"


def _kb_lookup(path: str, raw_text: str) -> list[dict[str, Any]]:
    """Check raw fault text against KB error patterns."""
    if not raw_text:
        return []
    text_upper = raw_text.upper()
    con = db.connect(path)
    try:
        rows = con.execute(
            "SELECT * FROM kb_error_map"
        ).fetchall()
    except Exception:
        return []
    finally:
        con.close()
    matches = []
    for r in rows:
        pat = (r["error_pattern"] or "").strip().upper()
        if pat and pat in text_upper:
            suspects = []
            try:
                suspects = json.loads(r["suspect_components"] or "[]")
            except (json.JSONDecodeError, TypeError):
                suspects = [r["suspect_components"]] if r["suspect_components"] else []
            dimm_slots = []
            try:
                dimm_slots = json.loads(r["dimm_slots"] or "[]")
            except (json.JSONDecodeError, TypeError):
                pass
            # Get the parent KB article for context
            article = None
            try:
                con2 = db.connect(path)
                art_row = con2.execute(
                    "SELECT * FROM kb_articles WHERE kb_id=?", (r["kb_id"],)
                ).fetchone()
                if art_row:
                    article = {
                        "title": art_row["title"],
                        "solution": art_row["solution"],
                        "root_cause": art_row["root_cause"],
                        "suggestions": art_row["suggestions"],
                    }
                con2.close()
            except Exception:
                pass
            matches.append({
                "error_pattern": r["error_pattern"],
                "power_rail": r["power_rail"],
                "suspect_components": suspects,
                "dimm_slots": dimm_slots,
                "remark": r["remark"] or "",
                "article": article,
            })
    return matches


def diagnose(path: str, query_text: str, raw_text: str = "",
             k: int = 50, max_results: int = 5) -> dict[str, Any]:
    """Return ranked causes + resolutions + supporting evidence + KB matches."""
    # Case-based retrieval
    cases = db.search_similar(path, query_text, k=k)
    causes, resolutions, support = [], [], []
    found, evidence, notes_map = 0, "none", {}

    if cases:
        causes, mass, found = _aggregate(cases, "root_cause_raw")
        resolutions, _, _ = _aggregate(cases, "resolution_raw")
        evidence = _evidence_label(found, mass)
        support_ids = causes[0]["support"] if causes else []
        by_id = {c["case_id"]: c for c in cases}
        support = [{
            "case_id": cid,
            "fault_description": by_id[cid].get("fault_description", ""),
            "root_cause": by_id[cid].get("root_cause_raw", ""),
            "resolution": by_id[cid].get("resolution_raw", ""),
            "date": by_id[cid].get("case_date", ""),
            "recurred": int(by_id[cid].get("recurrence_flag", 0)),
        } for cid in support_ids if cid in by_id]
        notes_map = db.notes_for(path, support_ids)

    # KB pattern matching
    kb_matches = _kb_lookup(path, raw_text or query_text)

    return {
        "found": found,
        "evidence": evidence,
        "root_causes": causes[:max_results],
        "resolutions": resolutions[:max_results],
        "support": support,
        "notes": notes_map,
        "kb_matches": kb_matches,
    }
