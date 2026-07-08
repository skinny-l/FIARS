"""Tests for FIARS Phase 5 analytics: fiars.analytics.queries / metrics."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fiars import db
from fiars.analytics import metrics, queries


def _fresh_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    db.init_db(path)
    return path


def _set_created_at(path, case_id, iso_ts):
    con = db.connect(path)
    con.execute("UPDATE case_history SET created_at=? WHERE id=?", (iso_ts, case_id))
    con.commit()
    con.close()


def test_top_labels_counts_and_orders_descending():
    path = _fresh_db()
    db.add_case(path, {"error_fault": "a", "solution": "Replace DIMM", "root_cause": "Faulty DIMM"})
    db.add_case(path, {"error_fault": "b", "solution": "Replace DIMM", "root_cause": "Faulty DIMM"})
    db.add_case(path, {"error_fault": "c", "solution": "Replace fan", "root_cause": "Worn bearing"})
    top = queries.top_labels(path, "root_cause", limit=10)
    assert top[0] == {"label": "Faulty DIMM", "n": 2}
    assert {"label": "Worn bearing", "n": 1} in top
    os.remove(path)


def test_top_labels_rejects_unknown_column():
    path = _fresh_db()
    try:
        queries.top_labels(path, "not_a_real_column")
        assert False, "expected ValueError"
    except ValueError:
        pass
    os.remove(path)


def test_mttr_overall_ignores_null_resolution_time():
    path = _fresh_db()
    db.add_case(path, {"error_fault": "a", "solution": "s", "resolution_time_min": 30})
    db.add_case(path, {"error_fault": "b", "solution": "s", "resolution_time_min": 90})
    db.add_case(path, {"error_fault": "c", "solution": "s"})  # no resolution_time_min
    result = queries.mttr_overall(path)
    assert result == {"mttr_minutes": 60.0, "n": 2}
    os.remove(path)


def test_recurrence_rate_overall():
    path = _fresh_db()
    db.add_case(path, {"error_fault": "a", "solution": "s", "recurrence_flag": 0})
    db.add_case(path, {"error_fault": "b", "solution": "s", "recurrence_flag": 1})
    db.add_case(path, {"error_fault": "c", "solution": "s", "recurrence_flag": 1})
    result = queries.recurrence_rate_overall(path)
    assert result["n"] == 3
    assert result["rate"] == round(2 / 3, 4)
    os.remove(path)


def test_recurrence_by_resolution_filters_by_min_n():
    path = _fresh_db()
    db.add_case(path, {"error_fault": "a", "solution": "Fix A", "recurrence_flag": 0})
    # "Fix B" only appears once -> excluded by default min_n=2
    db.add_case(path, {"error_fault": "b", "solution": "Fix B", "recurrence_flag": 1})
    db.add_case(path, {"error_fault": "c", "solution": "Fix A", "recurrence_flag": 1})
    result = queries.recurrence_by_resolution(path, min_n=2)
    labels = [r["label"] for r in result]
    assert labels == ["Fix A"]
    assert result[0]["n"] == 2
    os.remove(path)


def test_monthly_volume_buckets_by_created_at():
    path = _fresh_db()
    c1 = db.add_case(path, {"error_fault": "a", "solution": "s"})
    c2 = db.add_case(path, {"error_fault": "b", "solution": "s"})
    c3 = db.add_case(path, {"error_fault": "c", "solution": "s"})
    _set_created_at(path, c1, "2026-05-01T10:00:00+00:00")
    _set_created_at(path, c2, "2026-05-15T10:00:00+00:00")
    _set_created_at(path, c3, "2026-06-01T10:00:00+00:00")
    result = queries.monthly_volume(path)
    assert result == [{"month": "2026-05", "n": 2}, {"month": "2026-06", "n": 1}]
    os.remove(path)


def test_mttr_by_month_averages_within_bucket():
    path = _fresh_db()
    c1 = db.add_case(path, {"error_fault": "a", "solution": "s", "resolution_time_min": 20})
    c2 = db.add_case(path, {"error_fault": "b", "solution": "s", "resolution_time_min": 40})
    _set_created_at(path, c1, "2026-05-01T10:00:00+00:00")
    _set_created_at(path, c2, "2026-05-15T10:00:00+00:00")
    result = queries.mttr_by_month(path)
    assert result == [{"month": "2026-05", "mttr_minutes": 30.0, "n": 2}]
    os.remove(path)


def test_engineer_contribution_skips_blank_engineer():
    path = _fresh_db()
    db.add_case(path, {"error_fault": "a", "solution": "s", "engineer": "King"})
    db.add_case(path, {"error_fault": "b", "solution": "s", "engineer": ""})
    result = queries.engineer_contribution(path)
    assert result == [{"label": "King", "n": 1}]
    os.remove(path)


def test_overview_combines_counts_correctly():
    path = _fresh_db()
    db.add_case(path, {"error_fault": "a", "solution": "s", "resolution_time_min": 50, "recurrence_flag": 0})
    db.add_case(path, {"error_fault": "b", "solution": "s", "resolution_time_min": 70, "recurrence_flag": 1})
    result = metrics.overview(path)
    assert result["total_cases"] == 2
    assert result["mttr_minutes"] == 60.0
    assert result["recurrence_rate"] == 0.5
    os.remove(path)


def test_confidence_distribution_returns_one_value_per_sampled_case():
    path = _fresh_db()
    for i in range(4):
        db.add_case(path, {
            "error_fault": "Memory ECC fault DIMM slot",
            "solution": "Replaced DIMM", "root_cause": "Faulty DIMM module",
        })
    result = metrics.confidence_distribution(path, sample_size=200)
    assert result["n_total"] == 4
    assert result["n_sampled"] == 4
    assert len(result["confidences"]) == 4
    assert all(0.0 <= c <= 1.0 for c in result["confidences"])
    os.remove(path)


def test_confidence_distribution_respects_sample_cap():
    path = _fresh_db()
    for i in range(10):
        db.add_case(path, {"error_fault": f"unique fault number {i}", "solution": "s", "root_cause": "r"})
    result = metrics.confidence_distribution(path, sample_size=3)
    assert result["n_total"] == 10
    assert result["n_sampled"] == 3
    assert len(result["confidences"]) == 3
    os.remove(path)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn(); print("PASS", name)
