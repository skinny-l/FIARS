"""
smart_search.py — Intelligent fault-to-solution matching.

Given a free-text problem description (like an engineer would describe it),
finds the most relevant knowledge entries using multiple strategies:

1. Error code extraction — regex pulls known patterns (SMART, ECC, IERR, etc.)
2. Synonym expansion — "disk making noise" → also searches "HDD", "drive", "storage"
3. Category inference — keywords map to fault categories
4. Multi-query FTS — runs expanded queries, deduplicates, ranks by match count
"""

from __future__ import annotations
import re
from typing import Any

# ── Synonym groups: any word in a group matches all others ──────────────
_SYNONYM_GROUPS = [
    {"disk", "drive", "hdd", "ssd", "nvme", "storage", "raid", "hard"},
    {"memory", "dimm", "ram", "ecc", "ddr"},
    {"cpu", "processor", "socket", "core"},
    {"fan", "cooling", "thermal", "temperature", "heat", "overheat"},
    {"power", "psu", "voltage", "watt"},
    {"network", "nic", "ethernet", "link", "port", "cable"},
    {"motherboard", "mainboard", "board", "backplane"},
    {"bios", "cmos", "firmware", "bmc", "post", "uefi"},
    {"error", "fault", "failure", "failed", "broken", "bad", "dead"},
    {"slow", "degraded", "reduced", "performance", "latency"},
    {"crash", "hang", "freeze", "lockup", "reboot", "restart"},
    {"noise", "vibration", "clicking", "grinding"},
    {"replace", "swap", "reseat", "reinstall"},
    {"missing", "not detected", "unrecognized", "disappeared"},
]

_WORD_TO_SYNONYMS: dict[str, set[str]] = {}
for group in _SYNONYM_GROUPS:
    for word in group:
        _WORD_TO_SYNONYMS[word] = group

# ── Error code patterns (regex) ─────────────────────────────────────────
_ERROR_PATTERNS = [
    re.compile(r"\bSMART\b", re.I),
    re.compile(r"\bECC\b", re.I),
    re.compile(r"\bIERR\b", re.I),
    re.compile(r"\bMCE\b", re.I),
    re.compile(r"\bUCE\b", re.I),
    re.compile(r"\bFRB2\b", re.I),
    re.compile(r"\bUPI\b", re.I),
    re.compile(r"\bPOST\b", re.I),
    re.compile(r"\bRAID\b", re.I),
    re.compile(r"\bNVMe\b", re.I),
    re.compile(r"\bBMC\b", re.I),
    re.compile(r"\bUEFI\b", re.I),
    re.compile(r"\bGPT\b", re.I),
    re.compile(r"PV[A-Z_]+_FAULT\b", re.I),      # Power_Fault patterns
    re.compile(r"BAC\d+", re.I),                    # Fan error codes
    re.compile(r"P3V_BAT", re.I),                   # Battery
    re.compile(r"IOError\w*", re.I),                 # Disk IO errors
    re.compile(r"BadSector\w*", re.I),               # Disk sector errors
    re.compile(r"Reallocated\w*", re.I),             # Disk SMART
]

# ── Category keywords ───────────────────────────────────────────────────
_CATEGORY_MAP = {
    "CPU": ["cpu", "processor", "ierr", "mce", "socket", "core", "throttl"],
    "Memory": ["memory", "dimm", "ram", "ecc", "uce", "ddr"],
    "Storage": ["disk", "drive", "hdd", "ssd", "nvme", "raid", "smart", "storage", "mdisk"],
    "Network": ["network", "nic", "ethernet", "link", "cable", "port", "latency"],
    "Power": ["power", "psu", "voltage", "watt", "supply"],
    "Thermal": ["fan", "thermal", "temperature", "heat", "cool", "overheat"],
    "BIOS": ["bios", "cmos", "post", "uefi", "gpt", "boot"],
    "Firmware": ["firmware", "bmc", "update"],
    "Motherboard": ["motherboard", "board", "backplane"],
    "System": ["crash", "hang", "lockup", "reboot", "freeze"],
}


def extract_error_codes(text: str) -> list[str]:
    """Pull recognizable error codes/patterns from free text."""
    codes = []
    for pat in _ERROR_PATTERNS:
        for m in pat.finditer(text):
            codes.append(m.group(0))
    return list(dict.fromkeys(codes))  # dedupe, keep order


def expand_synonyms(words: list[str]) -> list[str]:
    """Given a list of words, add synonyms from known groups."""
    expanded = set(words)
    for w in words:
        wl = w.lower()
        if wl in _WORD_TO_SYNONYMS:
            expanded.update(_WORD_TO_SYNONYMS[wl])
    return list(expanded)


def infer_categories(text: str) -> list[str]:
    """Guess which fault categories a description relates to."""
    tl = text.lower()
    cats = []
    for cat, keywords in _CATEGORY_MAP.items():
        if any(kw in tl for kw in keywords):
            cats.append(cat)
    return cats


def build_search_queries(text: str) -> list[str]:
    """
    Turn a free-text problem description into multiple search queries.
    Returns a list of queries ordered from most specific to most general.
    """
    queries = []

    # 1. Error codes (most specific)
    codes = extract_error_codes(text)
    if codes:
        queries.append(" ".join(codes))

    # 2. Original words + synonyms
    words = [w for w in re.findall(r"[A-Za-z0-9_]+", text) if len(w) > 1]
    if words:
        expanded = expand_synonyms(words)
        queries.append(" ".join(expanded))

    # 3. Category-based
    cats = infer_categories(text)
    if cats:
        queries.append(" ".join(cats))

    # 4. Original text as fallback
    if words:
        queries.append(" ".join(words))

    return queries


def smart_search(db_module, db_path: str, text: str, limit: int = 10) -> list[dict[str, Any]]:
    """
    Multi-strategy search: run multiple queries, deduplicate, rank by
    how many strategies matched each result.
    """
    queries = build_search_queries(text)
    if not queries:
        return db_module.search_knowledge(db_path, "", limit=limit)

    seen: dict[int, dict] = {}      # id → entry
    scores: dict[int, float] = {}   # id → score

    for priority, query in enumerate(queries):
        weight = 1.0 / (1 + priority)  # earlier queries are more specific
        results = db_module.search_knowledge(db_path, query, limit=limit * 2)
        for rank, entry in enumerate(results):
            eid = entry["id"]
            if eid not in seen:
                seen[eid] = entry
                scores[eid] = 0.0
            scores[eid] += weight / (1 + rank)

    # Sort by combined score
    ranked = sorted(seen.keys(), key=lambda x: scores[x], reverse=True)
    return [seen[eid] for eid in ranked[:limit]]
