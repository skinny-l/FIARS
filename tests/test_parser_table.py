"""Tests for FIARS: dispatch table parsing and merge into parsed jobs."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fiars.parser import parse_ticket, infer_category
from fiars.parser_table import parse_dispatch_table, merge_dispatch
from fiars.report import default_draft, build_report
from tests.sample_tickets import (
    HDD_TICKET, HDD_TICKET_NUMBER,
    DISPATCH_ROW_HDD, DISPATCH_TABLE_TWO_PARTS,
)

# Real dispatch table sample where two rows carry an extra trailing line
# after Engineer (PCIe address/slot + serial), which used to desync every
# row parsed after them under fixed-width chunking.
DISPATCH_TABLE_GPU_VARIABLE_ROWS = """Date
Ticket No#
Case ID#
Server SN
Rack Info
Faulty Part
OLD PN
NEW PN
Maker
Model
Engineer
26/6/2026
SHGD0002021353
SHSJ0004146414
2KB700011
MYJHBGDS_B1_DH2A-B-10-1
GPU A100 PCIE - SPEX2026062500003
X0170AD0000004ZY
Onsite run test to confirm
A
NF5468M6
Sahir
GPU6 SN: 1323622026394
6/7/2026
SHGD0002029073
SHSJ0004162020
2KB700062
MYJHBGDS_B1_DH2A-A-10-11
GPU A100 PCIE - SPEX2026070500043
0000:9b:00.0 SN:1323622026318
customer provide parts
A
NF5468M6
Haikal | Xianyao | Aziz"""


def test_infer_category_gpu_beats_pcie_network_collision():
    # "PCIE" is also a Network keyword — GPU must win for GPU faults.
    assert infer_category("GPU A100 PCIE - SPEX2026062500003") == "GPU"


def test_parse_row_with_extra_trailing_line_does_not_desync_next_row():
    rows = parse_dispatch_table(DISPATCH_TABLE_GPU_VARIABLE_ROWS)
    assert len(rows) == 2
    assert rows[0]["ticket_no"] == "SHGD0002021353"
    assert rows[0]["server_sn"] == "2KB700011"
    assert rows[0]["category"] == "GPU"
    assert "GPU6 SN" in rows[0]["engineer"]
    # Second row must start clean — this is what broke before the fix.
    assert rows[1]["ticket_no"] == "SHGD0002029073"
    assert rows[1]["server_sn"] == "2KB700062"
    assert rows[1]["old_pn"] == "0000:9b:00.0 SN:1323622026318"


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
