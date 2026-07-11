"""Tests for FIARS: dispatch table parsing and merge into parsed jobs."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fiars.parser import parse_ticket, parse_multi_ticket, infer_category
from fiars.parser_table import parse_dispatch_table, merge_dispatch
from fiars.report import default_draft, build_report, build_combined_report
from tests.sample_tickets import (
    HDD_TICKET, HDD_TICKET_NUMBER,
    DISPATCH_ROW_HDD, DISPATCH_TABLE_TWO_PARTS,
    MB_TICKET, MB_TICKET_NUMBER, DISPATCH_TABLE_MB_PLUS_MEMORY,
    GPU_TWO_BLOCK_TICKET, GPU_TICKET_NUMBER, DISPATCH_ROW_GPU_SINGLE,
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


def test_merge_attaches_unconsumed_row_as_extra_part():
    # ONE job (one fault block), but TWO dispatch rows for the same ticket
    # (Memory + Motherboard) — the leftover row must not be dropped.
    job = parse_ticket(MB_TICKET, MB_TICKET_NUMBER)
    rows = parse_dispatch_table(DISPATCH_TABLE_MB_PLUS_MEMORY)
    merge_dispatch([job], rows)
    assert job["dispatch_matched"] is True
    # Primary part (matched by category = Memory, since fault_type is Memory)
    assert job["part"]["old_pn"] == "V0040E20000000ZY"
    assert job["part"]["new_pn"] == "V0040E20000000ZY"
    # Leftover Motherboard row preserved, not discarded
    assert len(job["extra_parts"]) == 1
    assert job["extra_parts"][0]["old_pn"] == "YZMB-03296-10F"
    assert job["extra_parts"][0]["new_pn"] == "YZMB-03296-10F"


def test_draft_and_report_combine_both_parts_into_one_report():
    job = parse_ticket(MB_TICKET, MB_TICKET_NUMBER)
    rows = parse_dispatch_table(DISPATCH_TABLE_MB_PLUS_MEMORY)
    merge_dispatch([job], rows)
    draft = default_draft(job)
    report = build_report(draft)

    # Single header, not duplicated
    assert report.count("Ticket Number:") == 1
    assert report.count("Server SN:") == 1
    assert report.count("Location:") == 1
    assert "Ticket Number: SHGD0002032731" in report

    # Both PNs present in the one report
    assert "V0040E20000000ZY" in report
    assert "YZMB-03296-10F" in report

    # Extra block titled by its own part type, not the primary "part_kind"
    assert "Old Motherboard" in report
    assert "New Motherboard" in report

    # Single Remark at the end, not one per part
    assert report.count("Remark:") == 1


def test_infer_category_dram_does_not_false_match_ram():
    # "DRAM"/"DRAMUncorrectable" must not trip the Memory "ram" keyword —
    # this is GPU on-die memory, not a DIMM. Regression for a substring
    # match bug ("ram" matching inside "dram").
    text = ("RemappedRows Pending:Yes,Volatile DRAMUncorrectable:2, "
            "need to reset GPU or server.")
    assert infer_category(text) == "GPU"


def test_two_tags_blocks_same_ticket_combine_into_one_report():
    # Two 工单标签/tags blocks (two distinct GPU Xid events), same ticket,
    # same server SN, but only one dispatch row for that SN — must combine
    # into a single note, not two fully separate block reports.
    jobs = parse_multi_ticket(GPU_TWO_BLOCK_TICKET, GPU_TICKET_NUMBER)
    assert len(jobs) == 2
    rows = parse_dispatch_table(DISPATCH_ROW_GPU_SINGLE)
    merge_dispatch(jobs, rows)
    drafts = [default_draft(j) for j in jobs]
    report = build_combined_report(drafts)

    # Single shared header
    assert report.count("Ticket Number:") == 1
    assert report.count("Server SN:") == 1
    assert report.count("Location:") == 1
    assert "Ticket Number: SHGD0002034312" in report

    # Both blocks' own Details lines preserved, each with its own slot
    assert report.count("Details:") == 2
    assert "slot 37:00" in report
    assert "slot 0000:37:00.0" in report

    # Both blocks' part data present
    assert "0000:37:00.0 SN: 1323622028016" in report          # block 1, from dispatch
    assert "900-21001-0020-100" in report                        # block 2, from ticket text

    # Both blocks correctly titled GPU, not generic "Part" or wrong category
    assert report.count("Old GPU") == 2
    assert report.count("New GPU") == 2

    # Single Remark at the end
    assert report.count("Remark:") == 1


def test_combined_report_does_not_merge_different_tickets():
    # Different ticket numbers / server SNs must stay as separate reports
    # even when passed through build_combined_report together.
    job_a = parse_ticket(HDD_TICKET, HDD_TICKET_NUMBER)
    rows = parse_dispatch_table(DISPATCH_ROW_HDD)
    merge_dispatch([job_a], rows)
    draft_a = default_draft(job_a)

    board_job = {"server_sn": "21D738325", "category": "Board", "part": {},
                 "ticket_number": "SHGD0002025775", "location_full": "SOMEWHERE"}
    draft_b = default_draft(board_job)

    combined = build_combined_report([draft_a, draft_b])
    assert combined.count("Ticket Number:") == 2
    assert "SHGD0002019999" in combined
    assert "SHGD0002025775" in combined


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn(); print("PASS", name)
