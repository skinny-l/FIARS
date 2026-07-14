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

    # Title the primary Old/New block with the most specific name available:
    # 1) the matched dispatch row's own faulty-part label (most reliable —
    #    see parser_table.merge_dispatch, since the ticket's part_type can
    #    disagree with which dispatch row actually matched);
    # 2) the ticket's own part_type field;
    # 3) the inferred fault category (e.g. "GPU"), for jobs with no part_type
    #    and no dispatch row of their own (extra fault blocks on a ticket
    #    where only one dispatch row existed);
    # 4) generic "Part" if none of the above yield anything.
    if part.get("dispatch_label"):
        block_kind = _clean_part_title(part["dispatch_label"])
    elif part.get("type"):
        block_kind = ptype
    elif job.get("category") and job["category"] != "Other":
        block_kind = job["category"]
    else:
        block_kind = "Part"

    # Details is now a mandatory header field (Date/Ticket Number/Server
    # SN/Location/Details), always shown even when blank — the engineer
    # fills it with the real diagnostic narrative (there's no useful
    # auto-generated placeholder now that slot lives on the block title,
    # so it starts empty rather than "Replaced X. Issue resolved.").
    details = ""

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
        "slot": pos,
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


def _titled(kind: str, slot: str = "") -> str:
    """`"RAM", "P1_C3_D0"` -> `"RAM (slot P1_C3_D0)"`. No slot -> just kind."""
    return f"{kind} (slot {slot})" if slot else kind


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

    Header is Date / Ticket Number / Server SN / Location / Details — all
    five always shown, Details included even when blank, since it's where
    the engineer writes the real diagnostic narrative (the specific slot a
    part came from lives on that part's own Old/New block title instead,
    e.g. "Old RAM (slot P1_C3_D0)", not repeated in Details). Most tickets
    have just the primary part; tickets that touched more than one part
    (e.g. a motherboard swap that also required a RAM swap) get one extra
    Old/New block per additional part via draft["extra_parts"] — same
    ticket, same header, no duplicated report.
    """
    kind = draft.get("part_kind", "Part") or "Part"
    slot = draft.get("slot", "")

    lines = [
        f"Date: {draft.get('date','')}",
        f"Ticket Number: {draft.get('ticket_number','')}",
        f"Server SN: {draft.get('server_sn','')}",
        f"Location: {draft.get('location','')}",
        f"Details: {draft.get('details','')}",
        "",
        _part_block(f"Old {_titled(kind, slot)}", draft.get("old", {})),
        "",
        _part_block(f"New {_titled(kind, slot)}", draft.get("new", {})),
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


def _base_ticket(ticket_number: str) -> str:
    """`"SHGD0002034312#2"` -> `"SHGD0002034312"` (strip the #N sub-block suffix)."""
    return (ticket_number or "").split("#")[0]


def _segment(kind: str, slot: str, old: dict[str, str], new: dict[str, str]) -> list[str]:
    """One Old/New pair, as used inside build_combined_report. Slot is
    shown on the block title. Details is a header-level field now (see
    build_combined_report), not repeated per part block."""
    return [
        _part_block(f"Old {_titled(kind, slot)}", old),
        "",
        _part_block(f"New {_titled(kind, slot)}", new),
    ]


def build_combined_report(drafts: list[dict[str, Any]]) -> str:
    """
    Combine multiple drafts that belong to the same ticket + server SN
    (e.g. two separate 工单标签/tags fault blocks logged under one ticket,
    such as two distinct Xid events on the same GPU) into a single note:
    one shared header (Date/Ticket Number/Server SN/Location/Details —
    Details always shown, taken from the first block's draft, since that's
    normally where the engineer writes the narrative covering the whole
    ticket) followed by one Old/New segment per draft — each titled with
    its own slot ("Old RAM (slot P1_C3_D0)") — and a single Remark at the
    end.

    Drafts are grouped by (base ticket number, server SN); only drafts
    within the same group are combined. Groups are emitted in the order
    their first draft appears. Falls back to build_report for a lone draft.
    """
    if not drafts:
        return ""
    if len(drafts) == 1:
        return build_report(drafts[0])

    groups: list[tuple[str, str]] = []
    by_group: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for d in drafts:
        key = (_base_ticket(d.get("ticket_number", "")), d.get("server_sn", ""))
        if key not in by_group:
            groups.append(key)
            by_group[key] = []
        by_group[key].append(d)

    reports = []
    for key in groups:
        group = by_group[key]
        if len(group) == 1:
            reports.append(build_report(group[0]))
            continue

        head = group[0]
        lines = [
            f"Date: {head.get('date','')}",
            f"Ticket Number: {_base_ticket(head.get('ticket_number',''))}",
            f"Server SN: {head.get('server_sn','')}",
            f"Location: {head.get('location','')}",
            f"Details: {head.get('details','')}",
            "",
        ]
        for i, d in enumerate(group):
            kind = d.get("part_kind", "Part") or "Part"
            slot = d.get("slot", "")
            lines += _segment(kind, slot, d.get("old", {}), d.get("new", {}))
            for ep in d.get("extra_parts", []):
                ep_kind = ep.get("kind", "Part") or "Part"
                lines += ["", _part_block(f"Old {ep_kind}", ep.get("old", {})),
                          "", _part_block(f"New {ep_kind}", ep.get("new", {}))]
            if i < len(group) - 1:
                lines.append("")
        lines += ["", f"Remark: {head.get('remark','Done')}"]
        reports.append("\n".join(lines))

    return "\n\n".join(reports)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from fiars.parser import parse_ticket
    from tests.sample_tickets import HDD_TICKET, HDD_TICKET_NUMBER
    d = default_draft(parse_ticket(HDD_TICKET, HDD_TICKET_NUMBER))
    print(build_report(d))
