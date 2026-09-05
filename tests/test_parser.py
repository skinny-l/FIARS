"""Tests for FIARS: parser, report, knowledge, cases, KB matching."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fiars import db
from fiars.parser import parse_ticket, parse_multi_ticket, search_text
from fiars.report import build_report, default_draft
from tests.sample_tickets import (
    HDD_TICKET, HDD_TICKET_NUMBER,
    NVME_LABELED_HDD_TICKET, NVME_LABELED_HDD_TICKET_NUMBER,
    BOILERPLATE_POSITION_TICKET, BOILERPLATE_POSITION_TICKET_NUMBER,
)

def test_parse_real_ticket():
    job = parse_ticket(HDD_TICKET, HDD_TICKET_NUMBER)
    assert job["server_sn"] == "21X100001"
    assert job["server_model"] == "S520-B3"
    assert job["server_product"] == "S68M1-I9DD3B-L-WW"
    assert job["location_full"] == "TESTDC1_B4_DH1B-B-10-40"
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
    assert "Ticket Number: SHGD0009000001" in r
    assert "Old HDD" in r and "New HDD" in r

def test_report_starts_with_quick_reference_line():
    # First line of every report is "{server_sn}_{location minus site code}",
    # e.g. "21X100001_B4_DH1B-B-10-40" — lets the engineer see which
    # block/rack/unit to go to without hunting through the raw ticket dump
    # or scrolling down to the Location: field. Site code (TESTDC1,
    # TESTDC2, ...) is dropped to keep the line short.
    job = parse_ticket(HDD_TICKET, HDD_TICKET_NUMBER)
    d = default_draft(job)
    r = build_report(d)
    lines = r.split("\n")
    assert lines[0] == "21X100001_B4_DH1B-B-10-40"
    assert lines[1] == ""  # blank line separates it from Date:
    assert lines[2] == f"Date: {d['date']}"
    # Full, untouched location is still present further down for the record
    assert "Location: TESTDC1_B4_DH1B-B-10-40" in r


def test_quick_reference_line_handles_missing_location_gracefully():
    # No location data at all (e.g. a manually-built draft) -> quick-ref
    # line falls back to just the server SN, no stray underscore.
    from fiars.report import build_report
    d = default_draft({"ticket_number": "SHGD0009000006", "server_sn": "TESTSN"})
    r = build_report(d)
    assert r.split("\n")[0] == "TESTSN"


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

def test_part_position_strips_vendor_boilerplate_note():
    # Regression: 部件位置/part_position on this ticket type always carries
    # a fixed Chinese instructional note glued onto the value with no
    # separator, e.g. "P1_C1_D0 （如果报修为硬盘故障，...）". Only the real
    # slot value should survive parsing and reach the report's slot title.
    job = parse_ticket(BOILERPLATE_POSITION_TICKET, BOILERPLATE_POSITION_TICKET_NUMBER)
    assert job["part"]["position"] == "P1_C1_D0"

    draft = default_draft(job)
    r = build_report(draft)
    assert "如果报修为硬盘故障" not in r
    assert "Old Memory (slot P1_C1_D0)" in r


def test_parse_ticket_tab_delimited_format():
    # Some vendor exports (e.g. a table copied straight out of a browser)
    # use a literal tab between label and value instead of a colon -- was
    # previously only implemented in a stray, never-imported parser.py at
    # the repo root and never actually active; now merged into the real
    # fiars/parser.py that server.py imports.
    raw = (
        "TikTok Inc Server Fault Report\n"
        "Server SN\t21X999001\n"
        "IP\t10.0.0.5\n"
        "Product_Manufacturer\tInspur\n"
        "Server_Suite\tS520-B3\n"
        "Suite_Name\tS68M1-I9DD3B-L-WW\n"
        "Asset_Number\tAB12345\n"
        "Fault Type\tDisk\n"
        "Part_Capacity\t2TB\n"
    )
    job = parse_ticket(raw, "TICKET-TAB-1")
    assert job["server_sn"] == "21X999001"
    assert job["server_ip"] == "10.0.0.5"
    assert job["manufacturer"] == "Inspur"
    assert job["server_model"] == "S520-B3"
    assert job["server_product"] == "S68M1-I9DD3B-L-WW"
    assert job["asset_no"] == "AB12345"
    assert job["fault_type"] == "Disk"
    assert job["part"]["size"] == "2TB"
    # The repeating banner line must not leak into fields or flags.
    assert "TikTok Inc Server Fault Report" not in job["fields"]
    assert not any("TikTok" in f for f in job["flags"])


def test_parse_multi_ticket_tab_delimited_marker():
    # The tab-delimited export repeats "TikTok Inc Server Fault Report" as
    # its block boundary instead of "工单标签/tags" -- parse_multi_ticket
    # must detect whichever marker actually repeats in this particular paste.
    raw = (
        "TikTok Inc Server Fault Report\n"
        "Server SN\t21X001\n"
        "Fault Type\tDisk\n"
        "TikTok Inc Server Fault Report\n"
        "Server SN\t21X002\n"
        "Fault Type\tMemory\n"
    )
    jobs = parse_multi_ticket(raw, "MULTI-TAB-1")
    assert len(jobs) == 2
    assert jobs[0]["server_sn"] == "21X001"
    assert jobs[0]["fault_type"] == "Disk"
    assert jobs[1]["server_sn"] == "21X002"
    assert jobs[1]["fault_type"] == "Memory"
