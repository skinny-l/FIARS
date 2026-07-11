"""
report.py — Build the resolution note (the "report" lower-section format).

Auto-fills everything derivable from the parsed ticket; the engineer supplies
the replacement-part details, the free-text Details line, date and remark.
Output matches the established note layout exactly.
"""

from __future__ import annotations

from datetime import date
from typing import Any

# Normalises dispatch-table "Faulty Part" free text (e.g. "Memory",
# "Motherboard - high risk have bent pins") into a short block title
# matching the established report vocabulary (e.g. "RAM", "Motherboard").
_TITLE_KEYWORDS = [
    ("memory", "RAM"), ("ram", "RAM"), ("dimm", "RAM"),
    ("motherboard", "Motherboard"), ("board", "Motherboard"),
    ("cpu", "CPU"), ("processor", "CPU"),
    ("gpu", "GPU"),
    ("psu", "PSU"), ("power", "PSU"),
    ("nic", "NIC"), ("network", "NIC"),
    ("fan", "Fan"),
    ("hdd", "HDD"), ("hard drive", "HDD"), ("ssd", "SSD"), ("nvme", "NVMe"),
    ("backplane", "Backplane"),
    ("raid", "RAID Card"),
]


def _clean_part_title(raw_type: str) -> str:
    """`"Motherboard - high risk have bent pins"` -> `"Motherboard"`."""
    raw_type = (raw_type or "").strip()
    if not raw_type:
        return "Part"
    low = raw_type.lower()
    for kw, title in _TITLE_KEYWORDS:
        if kw in low:
            return title
    # Fall back to the first segment before a separator, title-cased.
    head = raw_type.split(" - ")[0].split(",")[0].strip()
    return head or "Part"


def default_draft(job: dict[str, Any]) -> dict[str, Any]:
    """The editable draft the UI presents after a parse."""
    part = job.get("part", {})
    ptype = part.get("type", "Part") or "Part"
    pos = part.get("position", "")
    details = f"Replaced {ptype} (slot {pos}). Issue resolved." if pos \
        else f"Replaced {ptype}. Issue resolved."

    # Title the primary Old/New block from the matched dispatch row's own
    # faulty-part label when available — more reliable than the ticket's
    # part_type field, which can disagree with which dispatch row actually
    # matched (see parser_table.merge_dispatch). Falls back to part_type.
    block_kind = _clean_part_title(part.get("dispatch_label", "")) if part.get("dispatch_label") else ptype

    # Extra parts (e.g. RAM swapped alongside the motherboard) come from
    # unconsumed dispatch-table rows on the same ticket/server SN — see
    # parser_table.merge_dispatch. Each becomes its own Old/New block below
    # the primary part, instead of being dropped or split into a separate
    # report.
    extra_parts = [
        {
            "kind": _clean_part_title(ep.get("type", "")),
            "old": {"model": "", "pn": ep.get("old_pn", ""), "qn": "", "sn": "", "mpn": ""},
            "new": {"model": "", "pn": ep.get("new_pn", ""), "qn": "", "sn": "", "mpn": ""},
        }
        for ep in job.get("extra_parts", [])
    ]

    return {
        "date": f"{date.today().day} {date.today().strftime('%B %Y')}",
        "ticket_number": job.get("ticket_number", ""),
        "server_sn": job.get("server_sn", ""),
        "location": job.get("location_full", ""),
        "details": details,
        "part_kind": block_kind,
        "old": {
            "model": job.get("part_model", ""),
            "pn": part.get("old_pn", ""),  # from dispatch table match, else blank
            "qn": part.get("sn", ""),
            "sn": part.get("sn", ""),
            "mpn": part.get("pn", ""),     # part_pn -> MPN
        },
        "new": {"model": "", "pn": part.get("new_pn", ""), "qn": "", "sn": "", "mpn": ""},
        "extra_parts": extra_parts,
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
    """
    Render the final report text from a (possibly engineer-edited) draft.

    A single header (Date/Ticket Number/Server SN/Location/Details) is
    always followed by one Old/New block per part. Most tickets have just
    the primary part; tickets that touched more than one part (e.g. a
    motherboard swap that also required a RAM swap) get one extra Old/New
    block per additional part via draft["extra_parts"] — same ticket, same
    header, no duplicated report.
    """
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
    ]
    for ep in draft.get("extra_parts", []):
        ep_kind = ep.get("kind", "Part") or "Part"
        lines += [
            "",
            _part_block(f"Old {ep_kind}", ep.get("old", {})),
            "",
            _part_block(f"New {ep_kind}", ep.get("new", {})),
        ]
    lines += [
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
