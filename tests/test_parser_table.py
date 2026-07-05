"""Tests for FIARS: dispatch table parsing and merge into parsed jobs."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fiars.parser import parse_ticket
from fiars.parser_table import parse_dispatch_table, merge_dispatch
from fiars.report import default_draft, build_report
from tests.sample_tickets import (
    HDD_TICKET, HDD_TICKET_NUMBER,
    DISPATCH_ROW_HDD, DISPATCH_TABLE_TWO_PARTS,
)


def test_parse_single_row():
    rows = parse_dispatch_table(DISPATCH_ROW_HDD)
    assert len(rows) == 1
    row = rows[0]
    assert row["ticket_no"] == "SHGD0002019999"
    assert row["server_sn"] == "21C938088"
    assert row["old_pn"] == "V0232PY0000000ZY"
    assert row["new_pn"] == "V0233JP0000000ZY"
    assert row["category"] == "Storage"


def test_parse_multi_row_same_ticket():
    rows = parse_dispatch_table(DISPATCH_TABLE_TWO_PARTS)
    assert len(rows) == 2
    assert all(r["ticket_no"] == "SHGD0002025775" for r in rows)
    assert all(r["server_sn"] == "21D738325" for r in rows)
    cats = {r["category"] for r in rows}
    assert cats == {"Board", "Memory"}


def test_parse_ignores_shift_banner_preamble():
    banner = "Fahrul | Isq | Aziz – BDC02 @ 9:30 am\n" + DISPATCH_ROW_HDD
    rows = parse_dispatch_table(banner)
    assert len(rows) == 1
    assert rows[0]["server_sn"] == "21C938088"


def test_merge_overrides_ticket_number_and_fills_pn():
    job = parse_ticket(HDD_TICKET, HDD_TICKET_NUMBER)
    assert job["ticket_number"] == HDD_TICKET_NUMBER  # manually-typed, before merge
    rows = parse_dispatch_table(DISPATCH_ROW_HDD)
    merge_dispatch([job], rows)
    assert job["ticket_number"] == "SHGD0002019999"   # dispatch table wins
    assert job["part"]["old_pn"] == "V0232PY0000000ZY"
    assert job["part"]["new_pn"] == "V0233JP0000000ZY"
    assert job["dispatch_matched"] is True


def test_merge_disambiguates_two_parts_by_category():
    # Same server SN, two categories — must not cross-match.
    board_job = {"server_sn": "21D738325", "category": "Board", "part": {}}
    memory_job = {"server_sn": "21D738325", "category": "Memory", "part": {}}
    rows = parse_dispatch_table(DISPATCH_TABLE_TWO_PARTS)
    merge_dispatch([board_job, memory_job], rows)
    assert board_job["part"]["old_pn"] == "YZMB-02666-106"
    assert board_job["part"]["new_pn"] == "YZMB-02666-106 borrow"
    assert memory_job["part"]["old_pn"] == "V0040NM0000000ZY"
    assert memory_job["part"]["new_pn"] == "V0040NM0000000ZY"


def test_merge_no_match_leaves_job_untouched():
    job = parse_ticket(HDD_TICKET, HDD_TICKET_NUMBER)
    rows = parse_dispatch_table(DISPATCH_TABLE_TWO_PARTS)  # different SN entirely
    merge_dispatch([job], rows)
    assert job["ticket_number"] == HDD_TICKET_NUMBER  # untouched, no fabricated match
    assert job["dispatch_matched"] is False


def test_engineer_and_case_id_not_merged_into_job():
    job = parse_ticket(HDD_TICKET, HDD_TICKET_NUMBER)
    rows = parse_dispatch_table(DISPATCH_ROW_HDD)
    merge_dispatch([job], rows)
    assert "engineer" not in job
    assert "case_id" not in job


def test_maker_model_stored_as_metadata_not_part_fields():
    job = parse_ticket(HDD_TICKET, HDD_TICKET_NUMBER)
    rows = parse_dispatch_table(DISPATCH_ROW_HDD)
    merge_dispatch([job], rows)
    assert job["server_model_code"] == "Q QC5476M6D"
    assert job["part"].get("model") != "Q QC5476M6D"


def test_end_to_end_report_reflects_dispatch_merge():
    job = parse_ticket(HDD_TICKET, HDD_TICKET_NUMBER)
    rows = parse_dispatch_table(DISPATCH_ROW_HDD)
    merge_dispatch([job], rows)
    draft = default_draft(job)
    report = build_report(draft)
    assert "Ticket Number: SHGD0002019999" in report
    assert "PN: V0232PY0000000ZY" in report
    assert "PN: V0233JP0000000ZY" in report


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn(); print("PASS", name)
