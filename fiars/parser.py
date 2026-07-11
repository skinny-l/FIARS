"""
parser.py — Raw fault block -> structured job.

The raw block is a list of lines, each usually `中文标签/english_key：value`.
Separators may be the full-width colon `：` (U+FF1A) or the ASCII `:`.
Keys may be `中文/english_key`, just `english_key`, or just `中文`.
Values may be missing. There may be a trailing `From <url>` line.

The parser is intentionally tolerant: anything it doesn't recognise is still
kept under `fields`, so no information is silently lost.
"""

from __future__ import annotations

import re
from typing import Any

# full-width and ASCII colons both act as key/value separators
_COLON = re.compile(r"[:：]")
_URL = re.compile(r"https?://[^\s<>]+")

# Known english field keys. Used to (a) recognise fields and (b) split lines
# that pack two fields together, e.g. `server_model：X server_product：Y`.
KNOWN_KEYS = {
    "tags", "fault_60day_rt", "idc_kind", "priority", "server_model",
    "server_product", "server_sn", "location", "unit_no", "server_po",
    "server_ip", "asset_no", "part_position", "backplane_number",
    "manufacturer", "part_manufacturer", "firmware_version", "part_sn",
    "part_size", "part_type", "part_pn", "fault_log_dir", "fault_detail",
    "fault_part", "fault_type", "fault_description", "fault_30day_rt",
    "manufacturer_id", "disk_virtual_return_status",
    "manufacturer_id",
}
# Only underscore-style keys are safe to split on mid-line: plain words like
# "manufacturer" could occur inside free text, but "server_product" never does.
_INLINE_KEYS = sorted((k for k in KNOWN_KEYS if "_" in k), key=len, reverse=True)
_INLINE = re.compile(r"(?<=\s)(" + "|".join(_INLINE_KEYS) + r")\s*[:：]", re.I)


def _explode_inline(line: str) -> list[str]:
    """Split a line into `key:value` chunks at any known inline secondary key."""
    cuts = [m.start() for m in _INLINE.finditer(line)]
    if not cuts:
        return [line]
    bounds = [0] + cuts + [len(line)]
    return [line[bounds[i]:bounds[i + 1]].strip()
            for i in range(len(bounds) - 1) if line[bounds[i]:bounds[i + 1]].strip()]


def _split_kv(line: str):
    """Return (key, value) for a line, or None if it has no colon."""
    m = _COLON.search(line)
    if not m:
        return None
    key = line[: m.start()].strip()
    value = line[m.end():].strip()
    return key, value


def _canon_key(key: str) -> str:
    """`起始U位/ unit_no` -> `unit_no`; `Priority` -> `priority`."""
    if "/" in key:
        key = key.split("/")[-1]
    return key.strip().lower()


# fault_type / part_type -> coarse category used by the similarity engine
_CATEGORY_KEYWORDS = {
    "Storage": ["disk", "hdd", "ssd", "drive", "raid", "sas", "sata", "nvme"],
    "Memory":  ["memory", "dimm", "ram", "ecc", "edac"],
    "CPU":     ["cpu", "processor", "socket"],
    "Power":   ["power", "psu", "supply"],
    "GPU":     ["gpu", "cuda", "nvidia", "xid", "vbios"],
    "Network": ["nic", "network", "link", "ethernet", "port", "pcie"],
    "Thermal": ["fan", "temp", "thermal", "overheat", "heat"],
    "Board":   ["board", "motherboard", "system board", "backplane"],
}

# Word-boundary matchers per category, built once. Short/ambiguous keywords
# (e.g. "ram", "port") must not match as a bare substring inside unrelated
# words — e.g. "ram" inside "DRAM"/"VRAM" (GPU on-die memory, not a DIMM) or
# "program"; "port" inside "important". \b works fine here since keywords
# are plain alphanumerics.
_CATEGORY_PATTERNS = {
    cat: re.compile(r"\b(?:" + "|".join(re.escape(k) for k in kws) + r")\b")
    for cat, kws in _CATEGORY_KEYWORDS.items()
}


def infer_category(*texts: str) -> str:
    blob = " ".join(t for t in texts if t).lower()
    for cat, pattern in _CATEGORY_PATTERNS.items():
        if pattern.search(blob):
            return cat
    return "Other"


def _to_int(v: str, default: int = 0) -> int:
    try:
        return int(re.sub(r"[^\d-]", "", str(v)) or default)
    except (ValueError, TypeError):
        return default


def parse_ticket(raw: str, ticket_number: str = "") -> dict[str, Any]:
    """
    Parse one raw fault block.

    `ticket_number` is supplied by the engineer (it is not reliably inside the
    block) and becomes the case id.
    """
    fields: dict[str, str] = {}
    flags: list[str] = []        # colon-less lines, e.g. 可以直接维修
    url = ""

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith("from") and _URL.search(line):
            url = _URL.search(line).group(0)
            continue
        for chunk in _explode_inline(line):
            kv = _split_kv(chunk)
            if kv is None:
                m = _URL.search(chunk)
                if m:
                    url = m.group(0)
                else:
                    flags.append(chunk)
                continue
            key, value = kv
            ckey = _canon_key(key)
            if ckey:
                fields[ckey] = value

    g = fields.get  # shorthand

    location = g("location", "")
    unit_no = g("unit_no", "")
    location_full = f"{location}-{unit_no}" if location and unit_no else location

    part = {
        "type":         g("part_type", ""),
        "manufacturer": g("part_manufacturer", ""),
        "size":         g("part_size", ""),
        "pn":           g("part_pn", ""),     # -> becomes MPN in the report
        "sn":           g("part_sn", ""),     # -> SN and QN in the report
        "position":     g("part_position", ""),
        "firmware":     g("firmware_version", ""),
        "backplane":    g("backplane_number", ""),
    }

    # NVMe location logic: fault_part (e.g. "nvme8n2") is the physical
    # identifier, not part_position (which is the PCIe address).
    fault_part = g("fault_part", "")
    if part["type"].upper() in ("NVME", "SSD") and fault_part:
        part["pcie_address"] = part["position"]  # keep PCIe addr for reference
        part["position"] = fault_part             # use device name as location

    part_model = " ".join(x for x in (part["manufacturer"], part["size"]) if x)

    fault_description = g("fault description", "") or g("fault_description", "")
    fault_detail = g("fault_detail", "")
    fault_type = g("fault_type", "")

    # If fault_description is empty or just "-", use fault_detail
    if not fault_description or fault_description.strip() == "-":
        fault_description = fault_detail

    r30 = _to_int(g("fault_30day_rt", "0"))
    r60 = _to_int(g("fault_60day_rt", "0"))

    job = {
        "ticket_number":   ticket_number.strip(),
        "raw":             raw,
        "fields":          fields,
        "flags":           flags,
        "url":             url,

        "server_sn":       g("server sn", "") or g("server_sn", ""),
        "server_model":    g("server_model", ""),
        "server_product":  g("server_product", ""),
        "manufacturer":    g("manufacturer", ""),     # server vendor, e.g. Inspur
        "idc_kind":        g("idc_kind", ""),
        "priority":        g("priority", ""),
        "asset_no":        g("asset_no", ""),
        "server_ip":       g("server_ip", ""),

        "location":        location,
        "unit_no":         unit_no,
        "location_full":   location_full,

        "fault_type":      fault_type,
        "fault_description": fault_description,
        "fault_detail":    fault_detail,
        "fault_part":      g("fault_part", ""),
        "category":        infer_category(fault_type, part["type"],
                                          fault_description, fault_detail),

        "part":            part,
        "part_model":      part_model,

        "prior_repeat_30d": r30,
        "prior_repeat_60d": r60,
        "recurrence_on_intake": 1 if (r30 > 0 or r60 > 0) else 0,
    }
    return job


def search_text(job: dict[str, Any]) -> str:
    """
    The presenting-side text used for similarity search.
    Deliberately excludes root cause / resolution (those are the *answers*).
    """
    parts = [
        job.get("fault_description", ""),
        job.get("fault_detail", ""),
        job.get("fault_type", ""),
        job.get("category", ""),
        job.get("part", {}).get("type", ""),
        job.get("part_model", ""),
    ]
    return " ".join(p for p in parts if p).strip()


def parse_multi_ticket(raw: str, ticket_number: str = "") -> list[dict[str, Any]]:
    """
    Detect multi-block tickets (multiple 工单标签/tags: sections).
    Returns a list of jobs.
    """
    marker = "工单标签/tags"
    if raw.count(marker) > 1:
        parts = raw.split(marker)
        blocks = [marker + ":" + p for p in parts[1:] if p.strip()]
    else:
        blocks = [raw]
    jobs = []
    for i, block in enumerate(blocks):
        tid = f"{ticket_number}#{i+1}" if len(blocks) > 1 else ticket_number
        jobs.append(parse_ticket(block.strip(), tid))
    return jobs


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(parse_ticket(sys.stdin.read(), "DEMO"), ensure_ascii=False, indent=2))
