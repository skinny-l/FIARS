"""Tests for FIARS: recommend.py wiring (search_similar, notes_for, diagnose)."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fiars import db
from fiars.recommend import diagnose


def _fresh_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)  # init_db expects to create it
    db.init_db(path)
    return path


def test_search_similar_empty_db_returns_nothing():
    path = _fresh_db()
    assert db.search_similar(path, "memory fault DIMM") == []
    os.remove(path)


def test_add_case_then_search_similar_finds_it():
    path = _fresh_db()
    cid = db.add_case(path, {
        "ticket_number": "SHGD_TEST_1", "date": "2026-06-01",
        "server_sn": "TESTSN1", "location": "RACK-1",
        "error_fault": "Memory Device Disabled ECC error on DIMM slot",
        "parts": "DIMM", "solution": "Replaced DIMM at slot P0_C2_D0",
        "root_cause": "Faulty DIMM module", "recurrence_flag": 0,
    })
    results = db.search_similar(path, "memory ECC DIMM fault")
    assert any(r["case_id"] == cid for r in results)
    match = next(r for r in results if r["case_id"] == cid)
    assert match["root_cause_raw"] == "Faulty DIMM module"
    assert match["resolution_raw"] == "Replaced DIMM at slot P0_C2_D0"
    assert match["recurrence_flag"] == 0
    os.remove(path)


def test_notes_for_returns_requested_ids_only():
    path = _fresh_db()
    cid1 = db.add_case(path, {"error_fault": "Disk SMART fail", "solution": "Replaced HDD", "notes": "took 20 min"})
    cid2 = db.add_case(path, {"error_fault": "Fan failure", "solution": "Replaced fan", "notes": "loud before failure"})
    notes = db.notes_for(path, [cid1])
    assert notes == {cid1: "took 20 min"}
    assert cid2 not in notes
    os.remove(path)


def test_diagnose_end_to_end_surfaces_saved_case():
    path = _fresh_db()
    db.add_case(path, {
        "ticket_number": "SHGD_TEST_2", "date": "2026-06-15",
        "error_fault": "Memory Device Disabled ECC error",
        "solution": "Replaced DIMM", "root_cause": "Faulty DIMM module",
        "recurrence_flag": 0,
    })
    result = diagnose(path, "Memory Device Disabled ECC error", raw_text="")
    assert result["found"] >= 1
    assert result["evidence"] != "none"
    assert any(r["label"] == "Replaced DIMM" for r in result["resolutions"])
    assert any(c["label"] == "Faulty DIMM module" for c in result["root_causes"])
    os.remove(path)


def test_diagnose_no_data_returns_none_evidence_without_crashing():
    path = _fresh_db()
    result = diagnose(path, "some fault nobody has logged before", raw_text="")
    assert result["found"] == 0
    assert result["evidence"] == "none"
    assert result["root_causes"] == []
    assert result["resolutions"] == []
    os.remove(path)


def test_recurred_case_weighs_lower_than_clean_fix():
    path = _fresh_db()
    db.add_case(path, {"error_fault": "PSU fault power supply", "solution": "Fix A", "recurrence_flag": 0})
    db.add_case(path, {"error_fault": "PSU fault power supply", "solution": "Fix B", "recurrence_flag": 1})
    result = diagnose(path, "PSU fault power supply", raw_text="")
    by_label = {r["label"]: r["confidence"] for r in result["resolutions"] if r["label"] in ("Fix A", "Fix B")}
    assert by_label["Fix A"] > by_label["Fix B"]
    os.remove(path)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn(); print("PASS", name)
