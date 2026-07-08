"""Tests for FIARS Phase 4 eval: fiars.eval.leave_one_out / metrics."""
import math
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fiars import db
from fiars.eval import leave_one_out, metrics
from fiars.retrieval import semantic


def _fresh_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    db.init_db(path)
    return path


def _fake_encoder(texts):
    dim = 32
    vectors = []
    for t in texts:
        vec = [0.0] * dim
        for word in (t or "").lower().split():
            vec[hash(word) % dim] += 1.0
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        vectors.append([x / norm for x in vec])
    return vectors


# ── metrics.score ────────────────────────────────────────────────────────

def test_metrics_score_empty():
    assert metrics.score([]) == {"n": 0, "top_1": 0.0, "top_3": 0.0, "mrr": 0.0}


def test_metrics_score_mix_of_hits_and_misses():
    result = metrics.score([1, 2, None, 5])
    assert result["n"] == 4
    assert result["top_1"] == 0.25          # only rank==1
    assert result["top_3"] == 0.5           # ranks 1 and 2
    assert result["mrr"] == round((1 + 0.5 + 0 + 0.2) / 4, 4)


# ── leave_one_out.run ────────────────────────────────────────────────────

def test_lexical_mode_recovers_repeated_root_cause():
    path = _fresh_db()
    # Three cases share wording and root cause -> each held-out case should
    # find the same label as its #1 ranked prediction from the other two.
    for i in range(3):
        db.add_case(path, {
            "error_fault": "Memory Device Disabled ECC error on DIMM slot",
            "solution": "Replaced DIMM",
            "root_cause": "Faulty DIMM module",
            "recurrence_flag": 0,
        })
    result = leave_one_out.run(path, mode="lexical")
    assert result["n"] == 3
    assert result["top_1"] == 1.0
    assert result["mrr"] == 1.0
    os.remove(path)


def test_lexical_mode_records_miss_for_unique_fault():
    path = _fresh_db()
    db.add_case(path, {
        "error_fault": "Extremely one-of-a-kind fault nobody else has",
        "solution": "Escalated to vendor", "root_cause": "Unknown silicon defect",
    })
    result = leave_one_out.run(path, mode="lexical")
    assert result["n"] == 1
    assert result["top_1"] == 0.0
    assert result["mrr"] == 0.0
    os.remove(path)


def test_hybrid_mode_without_index_raises_clear_error():
    path = _fresh_db()
    db.add_case(path, {"error_fault": "CPU IERR", "solution": "Replace CPU", "root_cause": "Bad CPU"})
    try:
        leave_one_out.run(path, mode="hybrid")
        assert False, "expected RuntimeError when no embedding index exists"
    except RuntimeError as e:
        assert "build_index.py" in str(e)
    os.remove(path)


def test_hybrid_mode_runs_once_index_is_built():
    path = _fresh_db()
    for i in range(3):
        db.add_case(path, {
            "error_fault": "GPU Xid 79 fallen off the bus",
            "solution": "Reseat GPU", "root_cause": "Loose GPU riser card",
        })
    semantic.build_index(path, encoder=_fake_encoder)

    # Force the fusion branch (rather than the lexical-fallback branch) so
    # this actually exercises hybrid RRF, not just "didn't crash."
    original_available = semantic.available
    semantic.available = lambda: True
    try:
        result = leave_one_out.run(path, mode="hybrid", encoder=_fake_encoder)
    finally:
        semantic.available = original_available

    assert result["n"] == 3
    assert result["mode"] == "hybrid"
    os.remove(path)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn(); print("PASS", name)
