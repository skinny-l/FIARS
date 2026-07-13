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
    RAM_X2_TICKET, RAM_X2_TICKET_NUMBER, DISPATCH_TABLE_RAM_X2_PLUS_MB_NIC,
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

    # Slot lives on the block title now, not a repeated "Details: Replaced
    # X (slot Y). Issue resolved." sentence per block. Both blocks here
    # still have auto-generated placeholder Details (no engineer edit), so
    # no Details: line should appear at all.
    assert "Details:" not in report
    assert "(slot 37:00)" in report
    assert "(slot 0000:37:00.0)" in report

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


def test_multi_unit_row_matches_each_same_category_job_without_being_exhausted():
    # "Memory x2" is one dispatch row describing 2 identical DIMMs. Two
    # separate RAM fault blocks on the same ticket must BOTH match this row
    # (same PN) rather than the row being consumed after the first match.
    jobs = parse_multi_ticket(RAM_X2_TICKET, RAM_X2_TICKET_NUMBER)
    assert len(jobs) == 2
    rows = parse_dispatch_table(DISPATCH_TABLE_RAM_X2_PLUS_MB_NIC)
    merge_dispatch(jobs, rows)

    for j in jobs:
        assert j["dispatch_matched"] is True
        assert j["part"]["dispatch_label"] == "Memory x2"
        assert j["part"]["old_pn"] == "V0040J30000000ZY"
        assert j["part"]["new_pn"] == "V0040J30000000ZY"

    # Distinct physical DIMMs — their own SNs must NOT be mixed up between
    # jobs (this was the actual reported bug: job 2's SN ended up paired
    # with the Motherboard row's PN under a wrong "Motherboard" title).
    sns = {j["part"]["sn"] for j in jobs}
    assert sns == {"802C0F24444BC656AC", "802C0F24444BC654AE"}

    # Motherboard + NIC had no fault-description block of their own, so
    # both leftover rows land on the last job as extra_parts — not
    # swallowed into job 2's own (RAM) primary block.
    assert len(jobs[-1]["extra_parts"]) == 2
    extra_pns = {ep["old_pn"] for ep in jobs[-1]["extra_parts"]}
    assert extra_pns == {"YZMB-02666-106", "V0220A90000004ZY"}


def test_multi_unit_row_report_never_mixes_ram_and_motherboard_fields():
    jobs = parse_multi_ticket(RAM_X2_TICKET, RAM_X2_TICKET_NUMBER)
    rows = parse_dispatch_table(DISPATCH_TABLE_RAM_X2_PLUS_MB_NIC)
    merge_dispatch(jobs, rows)
    drafts = [default_draft(j) for j in jobs]
    report = build_combined_report(drafts)

    # Both RAM blocks titled RAM, with RAM's own PN — never "Old Motherboard"
    # wearing a RAM model/SN/MPN, which was the reported bug.
    assert report.count("Old RAM") == 2
    assert report.count("New RAM") == 2
    assert "Old Motherboard" in report  # from extra_parts, correctly separate
    assert "Old NIC" in report

    # The Motherboard block (from extra_parts) must carry ONLY the
    # motherboard PN — no RAM model/MPN/SN leaking into it.
    mb_idx = report.index("Old Motherboard")
    mb_block = report[mb_idx:mb_idx + 200]
    assert "MTC40F2046S1RC56BD1" not in mb_block  # RAM's MPN
    assert "Micron 64GB" not in mb_block           # RAM's model
    assert "YZMB-02666-106" in mb_block


def test_unit_count_never_matches_inside_unrelated_tokens():
    # Regression: "GPU A100 PCIE - SPEX2026071100090" was misread as a
    # unit-count marker ("x2026071100090" — the X in SPEX + the digits
    # after it), which made merge_dispatch attempt a multi-trillion
    # iteration loop and hang the whole process. A "X" immediately
    # followed by digits must NOT count as "xN" unless it's a genuine
    # standalone marker (word boundary before it, at most 2 digits).
    from fiars.parser_table import _unit_count
    assert _unit_count("GPU A100 PCIE - SPEX2026071100090") == 1
    assert _unit_count("GPU H100 - SPEX2026071100080") == 1
    assert _unit_count("Memory x2") == 2
    assert _unit_count("Memory x10") == 10
    assert _unit_count("Memory X3") == 3
    assert _unit_count("Motherboard - high risk have bent pins") == 1


def test_gpu_spex_dispatch_rows_do_not_hang_merge_dispatch():
    # End-to-end regression for the SPEX-code hang: two GPU fault blocks
    # (real Xid ECC report, same ticket) matched against a single-row
    # dispatch table whose Faulty Part text contains a SPEX code. Must
    # complete (and correctly categorize both blocks as GPU) instead of
    # hanging on a runaway range() loop.
    jobs = parse_multi_ticket(GPU_TWO_BLOCK_TICKET, GPU_TICKET_NUMBER)
    rows = parse_dispatch_table(DISPATCH_ROW_GPU_SINGLE)
    merge_dispatch(jobs, rows)  # must return promptly, not hang
    assert jobs[0]["category"] == "GPU"
    assert jobs[1]["category"] == "GPU"
    drafts = [default_draft(j) for j in jobs]
    report = build_combined_report(drafts)
    assert report.count("Old GPU") == 2
    assert "(slot 37:00)" in report
    assert "(slot 0000:37:00.0)" in report


def test_infer_category_gpu_ecc_outranks_ambiguous_memory_keyword():
    # Regression: a GPU fault whose text contains both "ECC" (ambiguous —
    # shared with Memory/DIMM errors) and "Xid"/"GPU" (unambiguous GPU
    # signals) must resolve to GPU, not Memory. Previously Memory's "ecc"
    # keyword won just because Memory was checked before GPU.
    text_desc = ("diff:371;NVRM: Xid (PCI:0000:37:00): 95, pid=5171, "
                 "Uncontained: FBHUB. RST: Yes, D-RST: No")
    text_detail = "xid 95 Uncontained ECC error occurred"
    assert infer_category("GPU", "", text_desc, text_detail) == "GPU"

    # A genuine DIMM ECC error with no GPU signal must still be Memory.
    assert infer_category("Memory", "", "Memory CE (Count) > Max (Kernel)",
                           "ECC error on DIMM P1_C1_D0") == "Memory"


def test_slot_appears_on_block_title_not_details_sentence():
    # New format: "Old RAM (slot X)" / "New RAM (slot X)" instead of a
    # "Details: Replaced RAM (slot X). Issue resolved." sentence. When the
    # engineer hasn't written a real Details line, no Details: line should
    # appear at all — the slot alone on the title carries that information.
    job = parse_ticket(HDD_TICKET, HDD_TICKET_NUMBER)
    rows = parse_dispatch_table(DISPATCH_ROW_HDD)
    merge_dispatch([job], rows)
    draft = default_draft(job)
    assert draft["slot"] == "22"
    report = build_report(draft)
    assert "(slot 22)" in report
    assert "Old HDD (slot 22)" in report
    assert "New HDD (slot 22)" in report
    assert "Details:" not in report  # placeholder text, correctly suppressed


def test_engineer_written_details_still_shown_without_slot_duplication():
    job = parse_ticket(HDD_TICKET, HDD_TICKET_NUMBER)
    rows = parse_dispatch_table(DISPATCH_ROW_HDD)
    merge_dispatch([job], rows)
    draft = default_draft(job)
    draft["details"] = "Found bad sectors, replaced disk, rebuilt RAID. Issue resolved."
    report = build_report(draft)
    assert report.count("Details:") == 1
    assert "Found bad sectors" in report
    assert "Old HDD (slot 22)" in report  # slot still on title, not duplicated in Details


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn(); print("PASS", name)
