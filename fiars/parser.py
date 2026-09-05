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

# Some vendor ticket fields always carry a fixed Chinese instructional note
# glued directly onto the value on the same line, with no separator — e.g.
# `部件位置/part_position:P1_C1_D0 （如果报修为硬盘故障，此位置信息不做参考，...）`.
# The note is boilerplate the vendor template always includes on that line
# (present even when a real value like "P1_C1_D0" precedes it), not
# engineer-entered data, so it must be stripped or it ends up baked into the
# report's slot title, e.g. "Old RAM (slot P1_C1_D0 （如果报修为硬盘故障...）)".
# Keyed by canonical field key -> the boilerplate's distinctive opening
# substring; everything from that point onward is dropped.
_FIELD_BOILERPLATE = {
    "part_position": "（如果报修为硬盘故障",
    "part_position_bmc": "（严格按照近期发布的",
}


def _strip_boilerplate(ckey: str, value: str) -> str:
    marker = _FIELD_BOILERPLATE.get(ckey)
    if marker:
        idx = value.find(marker)
        if idx != -1:
            value = value[:idx].strip()
    return value

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
    """Return (key, value) for a line, or None if it has no separator.

    Some vendor ticket exports (e.g. a table copy-pasted from a browser)
    use a literal tab between the `中文/English Key` label and its value
    instead of a colon — there is no colon anywhere on the line at all.
    Tab takes priority when present, since a colon-based split would
    either miss the field entirely or, worse, mis-split on a colon that
    happens to appear inside the *value* (e.g. an IPv6 address).
    """
    if "\t" in line:
        key, _, value = line.partition("\t")
        return key.strip(), value.strip()
    m = _COLON.search(line)
    if not m:
        return None
    key = line[: m.start()].strip()
    value = line[m.end():].strip()
    return key, value


# Some vendor templates label a field in English differently from the
# snake_case name used internally (and in other vendors' templates) for
# the same concept. Map those after normalisation so both spellings land
# on the same canonical key.
_KEY_ALIASES = {
    "ip": "server_ip",
    "product_manufacturer": "manufacturer",       # server vendor, e.g. Inspur
    "server_suite": "server_model",               # short model code
    "suite_name": "server_product",                # long SKU code
    "asset_number": "asset_no",
    "part_capacity": "part_size",
    "number_of_repairs_in_past_30_days": "fault_30day_rt",
    "number_of_repairs_in_past_60_days": "fault_60day_rt",
}


def _canon_key(key: str) -> str:
    """`起始U位/ unit_no` -> `unit_no`; `Priority` -> `priority`;
    `Fault Type` -> `fault_type` (spaced English labels get underscored
    so they line up with the snake_case keys used elsewhere)."""
    if "/" in key:
        key = key.split("/")[-1]
    key = re.sub(r"\s+", "_", key.strip().lower())
    return _KEY_ALIASES.get(key, key)


# fault_type / part_type -> coarse category used by the similarity engine.
# Keywords are split into "strong" (specific enough to one category that
# they should win outright) and "weak" (genuinely ambiguous across
# categories — e.g. "ecc"/"edac" errors happen on RAM DIMMs AND on GPU
# on-die memory, so they shouldn't unilaterally decide the category).
_CATEGORY_KEYWORDS_STRONG = {
    "Storage": ["disk", "hdd", "ssd", "drive", "raid", "sas", "sata", "nvme"],
    "Memory":  ["memory", "dimm"],
    "CPU":     ["cpu", "processor", "socket"],
    "Power":   ["power", "psu", "supply"],
    "GPU":     ["gpu", "cuda", "nvidia", "xid", "vbios"],
    "Network": ["nic", "network", "link", "ethernet", "port", "pcie"],
    "Thermal": ["fan", "temp", "thermal", "overheat", "heat"],
    "Board":   ["board", "motherboard", "system board", "backplane"],
}
_CATEGORY_KEYWORDS_WEAK = {
    "Memory": ["ram", "ecc", "edac"],
}


def _compile(keyword_map: dict[str, list[str]]) -> dict[str, re.Pattern]:
    return {
        cat: re.compile(r"\b(?:" + "|".join(re.escape(k) for k in kws) + r")\b")
        for cat, kws in keyword_map.items()
    }


# Word-boundary matchers per category, built once. Short/ambiguous keywords
# (e.g. "ram", "port") must not match as a bare substring inside unrelated
# words — e.g. "ram" inside "DRAM"/"VRAM" (GPU on-die memory, not a DIMM) or
# "program"; "port" inside "important". \b works fine here since keywords
# are plain alphanumerics.
_CATEGORY_PATTERNS_STRONG = _compile(_CATEGORY_KEYWORDS_STRONG)
_CATEGORY_PATTERNS_WEAK = _compile(_CATEGORY_KEYWORDS_WEAK)


def infer_category(*texts: str) -> str:
    blob = " ".join(t for t in texts if t).lower()
    # All strong (unambiguous) signals are checked first, across every
    # category, before any weak/ambiguous keyword is allowed to decide —
    # so e.g. a GPU fault mentioning "Xid" and "ECC" in the same text
    # correctly stays GPU instead of "ecc" (shared with Memory) winning
    # just because Memory happened to be checked first.
    for cat, pattern in _CATEGORY_PATTERNS_STRONG.items():
        if pattern.search(blob):
            return cat
    for cat, pattern in _CATEGORY_PATTERNS_WEAK.items():
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
        if line.startswith("TikTok Inc Server Fault Report"):
            # Block-boundary banner, not a real field — skip so it doesn't
            # land in `fields` as noise.
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
                fields[ckey] = _strip_boilerplate(ckey, value)

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
    # identifier, not part_position (which is the PCIe address). The
    # ticket's own part_type field can still say "HDD" even when the fault
    # device is clearly an NVMe SSD (nvmeXnY naming) — the device name is
    # the more reliable signal, so it overrides part_type in that case.
    fault_part = g("fault_part", "")
    if re.match(r"nvme\d+n\d+", fault_part, re.IGNORECASE):
        part["type"] = "SSD"
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



# Different vendor templates mark the start of a new fault block
# differently. `工单标签/tags` repeats for each block in the old
# colon-delimited format; `TikTok Inc Server Fault Report` repeats for
# each block in the tab-delimited table export. Whichever one actually
# repeats (>1 occurrence) in this particular paste is the splitter.
_MULTI_BLOCK_MARKERS = ["工单标签/tags", "TikTok Inc Server Fault Report"]


def parse_multi_ticket(raw: str, ticket_number: str = "") -> list[dict[str, Any]]:
    """
    Detect multi-block tickets (multiple fault-report sections pasted
    together as one). Returns a list of jobs.
    """
    marker = next((m for m in _MULTI_BLOCK_MARKERS if raw.count(m) > 1), None)
    if marker:
        parts = raw.split(marker)
        sep = ":" if marker == "工单标签/tags" else ""
        blocks = [marker + sep + p for p in parts[1:] if p.strip()]
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
