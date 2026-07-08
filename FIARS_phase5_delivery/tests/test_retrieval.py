"""
Tests for FIARS Phase 4 retrieval: semantic embeddings + hybrid RRF fusion.

Uses a small deterministic fake encoder instead of the real sentence-transformers
model, so these run fully offline and fast (no model download, no torch needed).
`semantic.available` is temporarily patched to True for the hybrid-fusion tests
since those test our own fusion logic, not whether sentence-transformers happens
to be pip-installed on this machine.
"""
import math
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fiars import db
from fiars.retrieval import hybrid, lexical, semantic


def _fresh_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)  # init_db expects to create it
    db.init_db(path)
    return path


def _fake_encoder(texts):
    """Deterministic bag-of-words 'embedding' — enough to test plumbing and
    fusion order, not a stand-in for real semantic quality."""
    dim = 32
    vectors = []
    for t in texts:
        vec = [0.0] * dim
        for word in (t or "").lower().split():
            vec[hash(word) % dim] += 1.0
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        vectors.append([x / norm for x in vec])
    return vectors


def test_index_not_ready_on_fresh_db():
    path = _fresh_db()
    assert semantic.index_ready(path) is False
    os.remove(path)


def test_build_index_embeds_all_cases_with_text():
    path = _fresh_db()
    db.add_case(path, {"error_fault": "CPU IERR detected", "solution": "Replace CPU"})
    db.add_case(path, {"error_fault": "Memory ECC fault DIMM", "solution": "Replace DIMM"})
    n = semantic.build_index(path, encoder=_fake_encoder)
    assert n == 2
    assert semantic.index_ready(path) is True
    os.remove(path)


def test_build_index_skips_unchanged_rows_on_rerun():
    path = _fresh_db()
    db.add_case(path, {"error_fault": "CPU IERR detected", "solution": "Replace CPU"})
    first = semantic.build_index(path, encoder=_fake_encoder)
    second = semantic.build_index(path, encoder=_fake_encoder)  # nothing changed
    assert first == 1
    assert second == 0
    os.remove(path)


def test_semantic_search_ranks_closer_meaning_higher():
    path = _fresh_db()
    cid_cpu = db.add_case(path, {"error_fault": "CPU internal error IERR fault", "solution": "Replace CPU"})
    cid_fan = db.add_case(path, {"error_fault": "Fan failure high RPM alarm", "solution": "Replace fan"})
    semantic.build_index(path, encoder=_fake_encoder)
    results = semantic.search(path, "CPU IERR internal error", encoder=_fake_encoder)
    ids = [cid for cid, _score in results]
    assert ids.index(cid_cpu) < ids.index(cid_fan)
    os.remove(path)


def test_semantic_search_excludes_given_id():
    path = _fresh_db()
    cid = db.add_case(path, {"error_fault": "CPU IERR fault", "solution": "Replace CPU"})
    semantic.build_index(path, encoder=_fake_encoder)
    results = semantic.search(path, "CPU IERR fault", encoder=_fake_encoder, exclude_id=cid)
    assert all(c != cid for c, _score in results)
    os.remove(path)


def test_hybrid_falls_back_to_lexical_when_index_not_built():
    path = _fresh_db()
    db.add_case(path, {"error_fault": "Disk SMART failure predictive", "solution": "Replace HDD"})
    lex = lexical.search(path, "Disk SMART failure")
    hyb = hybrid.retrieve(path, "Disk SMART failure")
    assert [c["case_id"] for c in lex] == [c["case_id"] for c in hyb]
    os.remove(path)


def test_hybrid_falls_back_to_lexical_when_ml_package_missing():
    # Default environment: sentence-transformers not installed / not patched.
    path = _fresh_db()
    db.add_case(path, {"error_fault": "PSU fault power rail", "solution": "Replace PSU"})
    semantic.build_index(path, encoder=_fake_encoder)  # index exists...
    lex = lexical.search(path, "PSU fault power rail")
    hyb = hybrid.retrieve(path, "PSU fault power rail")  # ...but package "unavailable"
    assert [c["case_id"] for c in lex] == [c["case_id"] for c in hyb]
    os.remove(path)


def test_hybrid_fuses_lexical_and_semantic_when_both_available():
    path = _fresh_db()
    cid_exact = db.add_case(path, {"error_fault": "CPU IERR internal error", "solution": "Replace CPU"})
    db.add_case(path, {"error_fault": "totally unrelated fan noise complaint", "solution": "Replace fan"})
    semantic.build_index(path, encoder=_fake_encoder)

    original_available = semantic.available
    semantic.available = lambda: True
    try:
        results = hybrid.retrieve(path, "CPU IERR internal error", encoder=_fake_encoder)
    finally:
        semantic.available = original_available

    assert results, "hybrid retrieval returned no results"
    assert results[0]["case_id"] == cid_exact
    assert 0.0 < results[0]["similarity"] <= 1.0
    os.remove(path)


def test_hybrid_still_finds_case_missing_from_semantic_index():
    # Case exists in FTS but was added after the last build_index() run —
    # hybrid should still surface it via the lexical signal, not silently drop it.
    path = _fresh_db()
    cid_indexed = db.add_case(path, {"error_fault": "GPU Xid 79 fallen off bus", "solution": "Reseat GPU"})
    semantic.build_index(path, encoder=_fake_encoder)
    cid_new = db.add_case(path, {"error_fault": "GPU Xid 79 fallen off bus again", "solution": "Replace GPU"})

    original_available = semantic.available
    semantic.available = lambda: True
    try:
        results = hybrid.retrieve(path, "GPU Xid 79 fallen off bus", encoder=_fake_encoder)
    finally:
        semantic.available = original_available

    ids = [c["case_id"] for c in results]
    assert cid_indexed in ids
    assert cid_new in ids
    os.remove(path)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn(); print("PASS", name)
