"""
parser_table.py — Dispatch/assignment table -> structured rows, matched to jobs.

The dispatch table arrives by email (shift assignment list) and is pasted as
plain text. Outlook-style copy/paste puts one cell per line: the 11 header
cells first, then each row in this fixed column order:

    Date, Ticket No#, Case ID#, Server SN, Rack Info, Faulty Part,
    OLD PN, NEW PN, Maker, Model, Engineer

Rows are NOT assumed to be a fixed 11 lines each — some GPU rows carry an
extra trailing line after Engineer (a PCIe address/slot + serial note, e.g.
"GPU6 SN: 1323622026394" or "0000:9d:00.0 SN: 1323622026394"). Instead, each
row's start is detected by its Date cell matching a date-like pattern
(e.g. "6/7/2026" or "26/6/2026 - Priority"); everything from that line up to
the next detected date line belongs to that row. Any lines beyond the 11th
are folded into the engineer field rather than desyncing the next row.

Maker/Model describe the *server* (chassis SKU), not the replacement part —
kept as metadata only, never written into the part fields. Case ID# is
tracked but unused (no downstream purpose defined).

Rows are matched to parsed ticket jobs (from parser.py) by Server SN, then
disambiguated by category, then by order of appearance. This is the piece
that currently has to be typed by hand: Ticket Number, OLD/NEW PN.
Engineer is parsed (kept in the row dict) but deliberately not merged into
the job or report — not needed downstream.
"""
from __future__ import annotations

import re
from typing import Any

from fiars.parser import infer_category

HEADERS = [
    "date", "ticket_no", "case_id", "server_sn", "rack_info",
    "faulty_part", "old_pn", "new_pn", "maker", "model", "engineer",
]

_DATE_RE = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}\b")


def parse_dispatch_table(raw: str) -> list[dict[str, Any]]:
    """
    Parse a pasted dispatch table into row dicts.

    Tolerant of a preamble line before the header (e.g. a shift banner like
    "Fahrul | Isq | Aziz – BDC02 @ 9:30 am"), of trailing blank lines, and of
    rows with extra trailing lines beyond the 11 fixed columns. A row that
    comes up short (fewer than 11 cells before the next date line) is kept
    under '_unparsed' instead of silently guessing.
    """
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]

    # Find the header block: first line that reads exactly "Date".
    try:
        start = next(i for i, ln in enumerate(lines) if ln.lower() == "date")
    except StopIteration:
        return []

    body = lines[start + len(HEADERS):]

    # Each row starts where its Date cell looks like a date.
    row_starts = [i for i, ln in enumerate(body) if _DATE_RE.match(ln)]

    rows: list[dict[str, Any]] = []
    for idx, s in enumerate(row_starts):
        e = row_starts[idx + 1] if idx + 1 < len(row_starts) else len(body)
        chunk = body[s:e]
        if len(chunk) < len(HEADERS):
            rows.append({"_unparsed": chunk})
            continue
        row = dict(zip(HEADERS[:-1], chunk[:-1]))
        # Everything from the Engineer cell onward — normally just the name,
        # occasionally name + a GPU slot/serial note — folds in here so it
        # never bleeds into the next row.
        row["engineer"] = " | ".join(chunk[len(HEADERS) - 1:])
        row["category"] = infer_category(row.get("faulty_part", ""))
        rows.append(row)

    return rows


_MULTI_UNIT_RE = re.compile(r"[x×]\s*(\d+)\s*$", re.IGNORECASE)


def _unit_count(faulty_part: str) -> int:
    """`"Memory x2"` -> 2. `"Memory"` -> 1. Rows tagged with a unit count
    describe N identical physical parts collapsed into a single dispatch
    row (same PN for all of them) — so the row should match N same-category
    fault blocks instead of being exhausted after the first."""
    m = _MULTI_UNIT_RE.search((faulty_part or "").strip())
    return int(m.group(1)) if m else 1


def merge_dispatch(jobs: list[dict[str, Any]], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Match dispatch rows onto parsed jobs (in place) by Server SN, then
    category, then order of appearance. Returns the same job list.

    A single fault-description block (one job) commonly covers a whole
    ticket that touches more than one part — e.g. a bent-pin motherboard
    swap that also required a RAM swap. The dispatch table then carries one
    row per part, all under the same ticket/server SN. The first
    same-category (or first available) row becomes the job's primary part
    (job["part"]), same as before; any further rows left over for that same
    server SN are attached as job["extra_parts"] so their PN data isn't
    dropped. Jobs with no matching row are left untouched (ticket_number
    stays whatever was passed in manually; old_pn/new_pn stay blank) so
    nothing breaks when the table and the raw paste don't line up — the
    engineer fills the gap by hand as before.

    A row like "Memory x2" describes 2 identical physical parts (e.g. two
    DIMMs, same PN) collapsed into one row — when a ticket has two separate
    fault blocks for that category (two RAM jobs), both should match this
    same row rather than the row being exhausted after the first job,
    which would otherwise leave the second job with no same-category match
    and at risk of wrongly matching a different part's row instead.

    Matching NEVER crosses into a different category as a fallback: a job
    with no same-category dispatch row left is left unmatched (blank PN)
    rather than silently attached to another part's PN — a visibly blank
    field the engineer fills in beats a wrong PN that looks correct.
    """
    by_sn: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        sn = row.get("server_sn")
        if sn:
            by_sn.setdefault(sn, []).append(row)

    # Track, per server SN, which jobs reference it — so leftover dispatch
    # rows (extra parts on the same ticket) can be folded into the last job
    # for that SN rather than silently discarded.
    jobs_by_sn: dict[str, list[dict[str, Any]]] = {}
    for job in jobs:
        sn = job.get("server_sn", "")
        if sn:
            jobs_by_sn.setdefault(sn, []).append(job)

    # Remaining match-count per row (by id) — multi-unit rows ("x2") can
    # match more than once before being considered exhausted.
    remaining: dict[int, int] = {id(r): _unit_count(r.get("faulty_part", "")) for r in rows}

    for job in jobs:
        candidates = [r for r in by_sn.get(job.get("server_sn", ""), []) if remaining[id(r)] > 0]
        same_cat = [r for r in candidates if r.get("category") == job.get("category")]
        if not same_cat:
            # No same-category row left — do NOT fall back to a different
            # category (that's how a RAM job can end up wearing a
            # Motherboard PN). Leave unmatched; engineer fills by hand.
            job["dispatch_matched"] = False
            continue

        match = same_cat[0]
        remaining[id(match)] -= 1

        job["ticket_number"] = match.get("ticket_no", job.get("ticket_number", ""))
        job["server_model_code"] = " ".join(
            x for x in (match.get("maker", ""), match.get("model", "")) if x
        )
        job.setdefault("part", {})
        job["part"]["old_pn"] = match.get("old_pn", "")
        job["part"]["new_pn"] = match.get("new_pn", "")
        # The dispatch row's own faulty-part label is more reliable than the
        # ticket's part_type field for naming the block (e.g. a ticket whose
        # fault was logged under part_type "Motherboard" can still be
        # dispatched/matched against the "Memory" row by category) — kept
        # separately so report.py can prefer it without disturbing part.type.
        if match.get("faulty_part"):
            job["part"]["dispatch_label"] = match["faulty_part"]
        job["dispatch_matched"] = True

    # Second pass: any dispatch rows still unconsumed (remaining > 0) for a
    # server SN belong to a part not covered by its own fault-description
    # block (e.g. a motherboard swap dispatched alongside RAM, with only
    # the RAM block present in the raw paste). Attach them to the last job
    # for that SN as extra_parts so build_report can render an additional
    # Old/New block, instead of being dropped.
    for sn, sn_rows in by_sn.items():
        leftover = [r for r in sn_rows if remaining[id(r)] > 0]
        if not leftover:
            continue
        sn_jobs = jobs_by_sn.get(sn, [])
        if not sn_jobs:
            continue
        target = sn_jobs[-1]
        target.setdefault("extra_parts", [])
        for row in leftover:
            for _ in range(remaining[id(row)]):
                target["extra_parts"].append({
                    "type":   row.get("faulty_part", ""),
                    "old_pn": row.get("old_pn", ""),
                    "new_pn": row.get("new_pn", ""),
                })

    return jobs


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(parse_dispatch_table(sys.stdin.read()), ensure_ascii=False, indent=2))
