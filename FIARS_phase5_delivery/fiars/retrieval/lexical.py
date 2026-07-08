"""
lexical.py — thin wrapper around db.search_similar.

Kept as its own module (rather than calling db.search_similar directly from
hybrid.py) so the retrieval layer has one clean seam per signal, matching the
structure in ARCHITECTURE.md Phase 4. Behavior is identical to the existing
Phase 3 lexical search; this is a no-op refactor from the caller's point of view.
"""
from __future__ import annotations

from .. import db


def search(path: str, query: str, k: int = 50, exclude_id: int | None = None) -> list[dict]:
    """Return the same dict shape as db.search_similar, ordered best-first."""
    return db.search_similar(path, query, k=k, exclude_id=exclude_id)


def ranks(path: str, query: str, k: int = 50, exclude_id: int | None = None) -> dict[int, int]:
    """Return {case_id: rank} (rank 1 = best) for RRF fusion."""
    results = search(path, query, k=k, exclude_id=exclude_id)
    return {r["case_id"]: i + 1 for i, r in enumerate(results)}
