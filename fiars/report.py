"""
report.py — Build the resolution note (the "report" lower-section format).

Auto-fills everything derivable from the parsed ticket; the engineer supplies
the replacement-part details, the free-text Details line, date and remark.
Output matches the established note layout exactly.
"""

from __future__ import annotations

from datetime import date
from typing import Any


def default_draft(job: dict[str, Any]) -> dict[str, Any]:
    """The editable draft the UI presents after a parse."""
    part = job.get("part", {})
    ptype = part.get("type", "Part") or "Part"
    pos = part.get("position", "")
    details = f"Replaced {ptype} (slot {pos}). Issue resolved." if pos \
        else f"Replaced {ptype}. Issue resolved."
    return {
        "date": f"{date.today().day} {date.today().strftime('%B %Y')}",
        "ticket_number": job.get("ticket_number", ""),
        "server_sn": job.get("server_sn", ""),
        "location": job.get("location_full", ""),
        "details": details,
        "part_kind": ptype,
        "old": {
            "model": job.get("part_model", ""),
            "pn": part.get("old_pn", ""),  # from dispatch table match, else blank
            "qn": part.get("sn", ""),
            "sn": part.get("sn", ""),
            "mpn": part.get("pn", ""),     # part_pn -> MPN
        },
        "new": {"model": "", "pn": part.get("new_pn", ""), "qn": "", "sn": "", "mpn": ""},
        "remark": "Done",
    }


def _part_block(title: str, p: dict[str, str]) -> str:
    return (
        f"{title}\n"
        f"Model: {p.get('model','')}\n"
        f"PN: {p.get('pn','')}\n"
        f"QN: {p.get('qn','')}\n"
        f"SN: {p.get('sn','')}\n"
        f"MPN: {p.get('mpn','')}"
    )


def build_report(draft: dict[str, Any]) -> str:
    """Render the final report text from a (possibly engineer-edited) draft."""
    kind = draft.get("part_kind", "Part") or "Part"
    lines = [
        f"Date: {draft.get('date','')}",
        f"Ticket Number: {draft.get('ticket_number','')}",
        f"Server SN: {draft.get('server_sn','')}",
        f"Location: {draft.get('location','')}",
        f"Details: {draft.get('details','')}",
        "",
        _part_block(f"Old {kind}", draft.get("old", {})),
        "",
        _part_block(f"New {kind}", draft.get("new", {})),
        "",
        f"Remark: {draft.get('remark','')}",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from fiars.parser import parse_ticket
    from tests.sample_tickets import HDD_TICKET, HDD_TICKET_NUMBER
    d = default_draft(parse_ticket(HDD_TICKET, HDD_TICKET_NUMBER))
    print(build_report(d))
