"""
metrics.py — derived/formatted metrics for the dashboard, built on queries.py.

confidence_distribution() is the one non-trivial piece: it's a genuine
calibration check, not a simulated number. For a sample of real cases it
hides each one from its own retrieval (same leave-one-out trick as
eval/leave_one_out.py) and records the confidence recommend.py actually
assigned its top root-cause prediction. A well-calibrated system should show
high confidences clustering where the prediction also tends to be correct —
this is the "Confidence distribution" dashboard page's histogram (§9, Module 5).
"""
from __future__ import annotations

import random

from .. import db
from ..recommend import diagnose
from . import queries


def overview(path: str) -> dict:
    mttr = queries.mttr_overall(path)
    recurrence = queries.recurrence_rate_overall(path)
    return {
        "total_cases": queries.total_cases(path),
        "cases_this_month": queries.cases_this_month(path),
        "mttr_minutes": mttr["mttr_minutes"],
        "mttr_n": mttr["n"],
        "recurrence_rate": recurrence["rate"],
        "recurrence_n": recurrence["n"],
    }


def confidence_distribution(path: str, sample_size: int = 200, seed: int = 42) -> dict:
    """
    Returns {"confidences": [...], "n_sampled": int, "n_total": int}.
    confidences[i] is the top predicted root-cause's confidence (0.0 if the
    system found no match at all) for the i-th sampled case, held out from
    its own retrieval. Capped at sample_size for dashboard responsiveness on
    large histories; uses a fixed seed so repeated dashboard loads agree.
    """
    con = db.connect(path)
    rows = con.execute(
        "SELECT id, error_fault FROM case_history "
        "WHERE error_fault IS NOT NULL AND TRIM(error_fault) != ''"
    ).fetchall()
    con.close()

    n_total = len(rows)
    if n_total > sample_size:
        rows = random.Random(seed).sample(rows, sample_size)

    confidences = []
    for r in rows:
        result = diagnose(path, r["error_fault"], exclude_id=r["id"])
        top = result["root_causes"][0]["confidence"] if result["root_causes"] else 0.0
        confidences.append(top)

    return {"confidences": confidences, "n_sampled": len(rows), "n_total": n_total}
