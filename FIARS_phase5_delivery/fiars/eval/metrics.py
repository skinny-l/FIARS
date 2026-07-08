"""
metrics.py — scoring for the leave-one-out retrieval eval.

Each query contributes one `rank` (1-indexed position of the correct label
in the predicted ranking, or None if it never appears in the top-k candidates
at all). These three numbers are the standard, easy-to-defend trio for a
ranked-retrieval task:

  top_1  — fraction of queries where the correct label was ranked #1
  top_3  — fraction where it was ranked in the top 3
  mrr    — mean reciprocal rank (1/rank, 0 if not found) — rewards "close" misses
           more than top_1 alone does, without needing a fixed cutoff.
"""
from __future__ import annotations


def score(ranks: list[int | None]) -> dict[str, float]:
    n = len(ranks)
    if n == 0:
        return {"n": 0, "top_1": 0.0, "top_3": 0.0, "mrr": 0.0}
    top_1 = sum(1 for r in ranks if r == 1)
    top_3 = sum(1 for r in ranks if r is not None and r <= 3)
    mrr = sum((1.0 / r) if r else 0.0 for r in ranks)
    return {
        "n": n,
        "top_1": round(top_1 / n, 4),
        "top_3": round(top_3 / n, 4),
        "mrr": round(mrr / n, 4),
    }
