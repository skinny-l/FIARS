"""
parser_table.py — Dispatch/assignment table -> structured rows, matched to jobs.

The dispatch table arrives by email (shift assignment list) and is pasted as
plain text. Outlook-style copy/paste puts one cell per line: the 11 header
cells first, then every subsequent group of 11 lines is one row, in this
fixed column order:

    Date, Ticket No#, Case ID#, Server SN, Rack Info, Faulty Part,
    OLD PN, NEW PN, Maker, Model, Engineer

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

from typing import Any

from fiars.parser import infer_category

HEADERS = [
    "date", "ticket_no", "case_id", "server_sn", "rack_info",
    "faulty_part", "old_pn", "new_pn", "maker", "model", "engineer",
]


def parse_dispatch_table(raw: str) -> list[dict[str, Any]]:
    """
    Parse a pasted dispatch table into row dicts.

    Tolerant of a preamble line before the header (e.g. a shift banner like
    "Fahrul | Isq | Aziz – BDC02 @ 9:30 am") and of trailing blank lines.
    Any leftover lines that don't form a complete row of 11 are returned
    under the '_unparsed' key of the last element's context so nothing is
    silently dropped — but in practice a well-formed paste divides evenly.
    """
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]

    # Find the header block: first line that reads exactly "Date".
    try:
        start = next(i for i, ln in enumerate(lines) if ln.lower() == "date")
    except StopIteration:
        return []

    body = lines[start + len(HEADERS):]
    rows: list[dict[str, Any]] = []
    for i in range(0, len(body) - len(HEADERS) + 1, len(HEADERS)):
        chunk = body[i:i + len(HEADERS)]
        row = dict(zip(HEADERS, chunk))
        row["category"] = infer_category(row.get("faulty_part", ""))
        rows.append(row)

    leftover = len(body) % len(HEADERS)
    if leftover:
        rows.append({"_unparsed": body[-leftover:]})

    return rows


def merge_dispatch(jobs: list[dict[str, Any]], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Match dispatch rows onto parsed jobs (in place) by Server SN, then
    category, then order of appearance. Returns the same job list.

    Jobs with no matching row are left untouched (ticket_number stays
    whatever was passed in manually; old_pn/new_pn stay blank) so nothing
    breaks when the table and the raw paste don't line up — the engineer
    fills the gap by hand as before.
    """
    by_sn: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        sn = row.get("server_sn")
        if sn:
            by_sn.setdefault(sn, []).append(row)

    for job in jobs:
        candidates = by_sn.get(job.get("server_sn", ""), [])
        if not candidates:
            job["dispatch_matched"] = False
            continue

        # Prefer same-category match; fall back to next unconsumed row.
        same_cat = [r for r in candidates if r.get("category") == job.get("category")]
        match = same_cat[0] if same_cat else candidates[0]
        candidates.remove(match)

        job["ticket_number"] = match.get("ticket_no", job.get("ticket_number", ""))
        job["server_model_code"] = " ".join(
            x for x in (match.get("maker", ""), match.get("model", "")) if x
        )
        job.setdefault("part", {})
        job["part"]["old_pn"] = match.get("old_pn", "")
        job["part"]["new_pn"] = match.get("new_pn", "")
        job["dispatch_matched"] = True

    return jobs


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(parse_dispatch_table(sys.stdin.read()), ensure_ascii=False, indent=2))
