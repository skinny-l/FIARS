"""
hybrid.py — Reciprocal Rank Fusion of lexical + semantic retrieval.

RRF (Cormack et al., 2009) combines two independently-scaled rankings by
summing 1/(K + rank) per source, rather than trying to normalize BM25 scores
against cosine similarities (which live on incomparable scales). K=60 is the
standard default from the original paper and needs no tuning.

Falls back to lexical-only, unchanged, whenever:
  - sentence-transformers isn't installed, or
  - `scripts/build_index.py` hasn't been run yet (no embeddings in the DB)
so installs that never opt into the ML extra see identical behavior to
Phase 3.
"""
from __future__ import annotations

from .. import db
from . import lexical, semantic

RRF_K = 60


def retrieve(path: str, query: str, k: int = 50, exclude_id: int | None = None,
             encoder=None) -> list[dict]:
    """
    Return case dicts in the same shape as db.search_similar, ordered
    best-first, with 'similarity' replaced by a fused RRF-derived score
    normalized to [0, 1] when both signals are available.

    encoder: only used for tests (injects a fake embedder instead of
    downloading the real sentence-transformers model). Production callers
    never pass this.
    """
    lex_ranks = lexical.ranks(path, query, k=k, exclude_id=exclude_id)

    use_semantic = semantic.available() and semantic.index_ready(path)
    if not use_semantic:
        # No opt-in ML extra / no index built yet: behave exactly like Phase 3.
        return lexical.search(path, query, k=k, exclude_id=exclude_id)

    sem_ranks = semantic.ranks(path, query, k=k, exclude_id=exclude_id, encoder=encoder)
    if not sem_ranks:
        return lexical.search(path, query, k=k, exclude_id=exclude_id)

    fused: dict[int, float] = {}
    for cid, r in lex_ranks.items():
        fused[cid] = fused.get(cid, 0.0) + 1.0 / (RRF_K + r)
    for cid, r in sem_ranks.items():
        fused[cid] = fused.get(cid, 0.0) + 1.0 / (RRF_K + r)

    ordered = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[:k]
    if not ordered:
        return []

    cases = db.get_cases(path, [cid for cid, _ in ordered])
    max_score = ordered[0][1] or 1.0
    out = []
    for cid, score in ordered:
        c = cases.get(cid)
        if not c:
            continue
        c = dict(c)
        c["similarity"] = round(score / max_score, 4)
        out.append(c)
    return out
