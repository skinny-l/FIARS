"""
fiars.retrieval — Phase 4 retrieval layer.

Three modules:
  lexical.py   — thin wrapper around db.search_similar (FTS5/BM25, always available)
  semantic.py  — embedding-based retrieval (opt-in; needs sentence-transformers)
  hybrid.py    — Reciprocal Rank Fusion of lexical + semantic

If sentence-transformers isn't installed, or the embedding index hasn't been
built yet, hybrid.retrieve() transparently falls back to lexical-only results.
Nothing here changes behavior for installs that never run `scripts/build_index.py`.
"""
