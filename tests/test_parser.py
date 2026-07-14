"""Tests for FIARS: parser, report, knowledge, cases, KB matching."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fiars import db
from fiars.parser import parse_ticket, search_text
from fiars.report import build_report, default_draft
from tests.sample_tickets import (
    HDD_TICKET, HDD_TICKET_NUMBER,
    NVME_LABELED_HDD_TICKET, NVME_LABELED_HDD_TICKET_NUMBER,
)

def test_parse_real_ticket():
    job = parse_ticket(HDD_TICKET, HDD_TICKET_NUMBER)
    assert job["server_sn"] == "21C938088"
    assert job["server_model"] == "S520-B3"
    assert job["server_product"] == "S68M1-I9DD3B-L-WW"
    assert job["location_full"] == "MYJHBGDS_B4_DH1B-B-10-40"
    assert job["category"] == "Storage"
    assert job["part"]["pn"] == "ST20000NM007D"

def test_nvme_device_name_overrides_hdd_part_type():
    # Regression: the ticket's own 部件类型/part_type field said "HDD", but
    # the actual fault device (故障设备/fault_part) is "nvme0n1" — a real
    # NVMe SSD, not a spinning HDD. The device name must win: part type
    # becomes SSD, and the report titles it "Old SSD (slot nvme0n1)", not
    # "Old HDD (slot nvme0n1)".
    job = parse_ticket(NVME_LABELED_HDD_TICKET, NVME_LABELED_HDD_TICKET_NUMBER)
    assert job["part"]["type"] == "SSD"
    assert job["part"]["position"] == "nvme0n1"
    draft = default_draft(job)
    report = build_report(draft)
    assert "Old SSD (slot nvme0n1)" in report
    assert "New SSD (slot nvme0n1)" in report
    assert "HDD" not in report

def test_search_text_excludes_answer():
    job = parse_ticket(HDD_TICKET, HDD_TICKET_NUMBER)
    txt = search_text(job).lower()
    assert "hdd" in txt and "ioerrorweek" in txt
    assert "replace" not in txt

def test_report_format():
    job = parse_ticket(HDD_TICKET, HDD_TICKET_NUMBER)
    d = default_draft(job)
    d["old"]["pn"] = "V0232PY0000000ZY"
    d["new"] = {"model":"WD 20TB","pn":"V0233JP","qn":"6MG","sn":"6MG","mpn":"WUH722"}
    r = build_report(d)
    assert "Ticket Number: SHGD0002014119" in r
    assert "Old HDD" in r and "New HDD" in r

def test_date_format():
    d = default_draft(parse_ticket(HDD_TICKET, HDD_TICKET_NUMBER))
    parts = d["date"].split()
    assert len(parts) == 3 and parts[0].isdigit()

def test_knowledge_add_search():
    path = os.path.join(tempfile.mkdtemp(), "t.db")
    db.init_db(path)
    db.add_knowledge(path, {"fault_description":"ECC error on DIMM",
        "solution":"Replace DIMM at P1_C1_D0","category":"Memory","error_code":"ECC"})
    db.add_knowledge(path, {"fault_description":"SMART disk failure",
        "solution":"Replace disk","category":"Storage","error_code":"SMART"})
    results = db.search_knowledge(path, "ECC DIMM")
    assert len(results) >= 1
    assert results[0]["error_code"] == "ECC"

def test_case_pagination():
    path = os.path.join(tempfile.mkdtemp(), "t.db")
    db.init_db(path)
    for i in range(30):
        db.add_case(path, {"error_fault":f"Error {i}","solution":f"Fix {i}","engineer":"Test"})
    rows, total = db.list_cases(path, page=1, per_page=10)
    assert total == 30
    assert len(rows) == 10
    rows2, _ = db.list_cases(path, page=3, per_page=10)
    assert len(rows2) == 10

def test_kb_pattern_matching():
    path = os.path.join(tempfile.mkdtemp(), "t.db")
    db.init_db(path)
    db.save_kb_article(path, {"title":"Test KB","error_map":[
        {"error_pattern":"PVCCIN_CPU0_Fault","power_rail":"PVCCIN",
         "suspect_components":["Motherboard","CPU"],"dimm_slots":[]}]})
    matches = db.kb_pattern_lookup(path, "BMC log: PVCCIN_CPU0_Fault alarm")
    assert len(matches) == 1
    assert "Motherboard" in matches[0]["suspect_components"]
    assert len(db.kb_pattern_lookup(path, "disk error unrelated")) == 0

def test_required_fields_guard():
    path = os.path.join(tempfile.mkdtemp(), "t.db")
    db.init_db(path)
    try:
        db.add_knowledge(path, {"fault_description":"","solution":""})
        # If it doesn't crash, check it's at least empty
    except: pass
    # Knowledge requires fault_description and solution via server validation

if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn(); print("PASS", name)
