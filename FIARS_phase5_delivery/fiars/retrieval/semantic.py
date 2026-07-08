"""
semantic.py — embedding-based retrieval (Phase 4, opt-in).

Design choices, and why:

- Uses sentence-transformers' all-MiniLM-L6-v2 (~80MB, downloads once, then
  fully offline) rather than a paid embedding API — keeps the project free
  and matches the existing "zero-dependency by default" philosophy: if
  sentence-transformers isn't installed, every function here degrades to a
  no-op and callers fall back to lexical-only search.

- Vectors are stored in a `case_embeddings` table in the same SQLite file as
  everything else, not a separate FAISS index file. At FIARS' actual scale
  (hundreds to low thousands of cases) a NumPy brute-force cosine search over
  a small in-memory matrix is well under 50ms and removes a second dependency
  and a second file that could drift out of sync with the DB. ARCHITECTURE.md
  explicitly allows this fallback; FAISS would only start to matter past
  roughly 10k+ cases.

- The encoder is injectable (the `encoder` param on build_index/search) so
  tests can run fully offline with a small fake embedding function instead of
  downloading the real model.
"""
from __future__ import annotations

import hashlib
import sqlite3
import struct
from datetime import datetime, timezone
from typing import Callable, Sequence

from .. import db

MODEL_NAME = "all-MiniLM-L6-v2"

_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS case_embeddings (
    case_id INTEGER PRIMARY KEY,
    vector BLOB NOT NULL,
    dim INTEGER NOT NULL,
    model TEXT NOT NULL,
    text_hash TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

_model_singleton = None


def available() -> bool:
    """True if sentence-transformers is importable (package installed)."""
    try:
        import sentence_transformers  # noqa: F401
        return True
    except ImportError:
        return False


def _get_model():
    global _model_singleton
    if _model_singleton is None:
        from sentence_transformers import SentenceTransformer
        _model_singleton = SentenceTransformer(MODEL_NAME)
    return _model_singleton


def _default_encoder(texts: Sequence[str]):
    """Real encoder: sentence-transformers, L2-normalized so dot product = cosine."""
    model = _get_model()
    return model.encode(list(texts), normalize_embeddings=True)


Encoder = Callable[[Sequence[str]], "Sequence[Sequence[float]]"]


def _ensure_table(con: sqlite3.Connection) -> None:
    con.execute(_TABLE_SQL)


def _text_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _pack(vec) -> bytes:
    return struct.pack(f"<{len(vec)}f", *[float(x) for x in vec])


def _unpack(blob: bytes, dim: int):
    return list(struct.unpack(f"<{dim}f", blob))


def index_ready(path: str) -> bool:
    """True if at least one embedding has been built."""
    con = db.connect(path)
    try:
        _ensure_table(con)
        row = con.execute("SELECT COUNT(*) AS n FROM case_embeddings").fetchone()
        return bool(row and row["n"] > 0)
    except sqlite3.OperationalError:
        return False
    finally:
        con.close()


def build_index(path: str, encoder: Encoder | None = None, batch_size: int = 64) -> int:
    """
    (Re)build embeddings for every case_history row whose text has changed
    since it was last embedded. Returns the number of rows (re)embedded.
    Safe to run repeatedly (e.g. from a scheduled task) — unchanged rows are
    skipped via a content hash, so re-running costs almost nothing.
    """
    encoder = encoder or _default_encoder
    con = db.connect(path)
    _ensure_table(con)
    rows = con.execute(
        "SELECT id, error_fault FROM case_history WHERE error_fault IS NOT NULL AND error_fault != ''"
    ).fetchall()
    existing = {
        r["case_id"]: r["text_hash"]
        for r in con.execute("SELECT case_id, text_hash FROM case_embeddings").fetchall()
    }

    todo = [
        (r["id"], r["error_fault"])
        for r in rows
        if existing.get(r["id"]) != _text_hash(r["error_fault"])
    ]
    embedded = 0
    now = datetime.now(timezone.utc).isoformat()
    for i in range(0, len(todo), batch_size):
        batch = todo[i:i + batch_size]
        vectors = encoder([text for _, text in batch])
        for (case_id, text), vec in zip(batch, vectors):
            con.execute(
                """INSERT INTO case_embeddings (case_id, vector, dim, model, text_hash, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(case_id) DO UPDATE SET
                       vector=excluded.vector, dim=excluded.dim, model=excluded.model,
                       text_hash=excluded.text_hash, updated_at=excluded.updated_at""",
                (case_id, _pack(vec), len(vec), MODEL_NAME, _text_hash(text), now),
            )
            embedded += 1
    # Drop embeddings for cases that no longer exist (deleted/edited away).
    live_ids = {r["id"] for r in rows}
    stale = [cid for cid in existing if cid not in live_ids]
    if stale:
        qmarks = ",".join("?" * len(stale))
        con.execute(f"DELETE FROM case_embeddings WHERE case_id IN ({qmarks})", stale)
    con.commit()
    con.close()
    return embedded


def search(
    path: str, query: str, k: int = 50, encoder: Encoder | None = None,
    exclude_id: int | None = None,
) -> list[tuple[int, float]]:
    """
    Return [(case_id, cosine_similarity), ...] sorted best-first.
    Empty list if the package isn't installed or the index hasn't been built.
    """
    con = db.connect(path)
    try:
        _ensure_table(con)
        rows = con.execute("SELECT case_id, vector, dim FROM case_embeddings").fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        con.close()
    if not rows or not (query or "").strip():
        return []

    encoder = encoder or _default_encoder
    qvec = list(encoder([query])[0])

    scored = []
    for r in rows:
        if exclude_id is not None and r["case_id"] == exclude_id:
            continue
        vec = _unpack(r["vector"], r["dim"])
        # Vectors are pre-normalized at index time, and the query vector is
        # normalized by the same encoder, so dot product == cosine similarity.
        sim = sum(a * b for a, b in zip(qvec, vec))
        scored.append((r["case_id"], sim))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]


def ranks(path: str, query: str, k: int = 50, encoder: Encoder | None = None,
          exclude_id: int | None = None) -> dict[int, int]:
    """Return {case_id: rank} (rank 1 = best) for RRF fusion."""
    results = search(path, query, k=k, encoder=encoder, exclude_id=exclude_id)
    return {cid: i + 1 for i, (cid, _score) in enumerate(results)}
