"""
smart_search.py — Intelligent fault-to-solution matching.

Strategies:
1. Error code extraction (SMART, ECC, IERR, Xid, PV*_FAULT, etc.)
2. Synonym expansion (disk→HDD→drive→storage, but NOT generic words)
3. Category inference + strong category bias
4. Multi-query FTS with dedup and ranked scoring
"""
from __future__ import annotations
import re
from typing import Any

# Synonym groups — ONLY component/hardware terms, NOT generic words
_SYNONYM_GROUPS = [
    {"disk", "drive", "hdd", "ssd", "nvme", "storage", "raid", "hard"},
    {"memory", "dimm", "ram", "ddr"},
    {"cpu", "processor", "socket"},
    {"fan", "cooling", "thermal", "temperature", "heat", "overheat"},
    {"power", "psu", "voltage"},
    {"network", "nic", "ethernet", "cable"},
    {"motherboard", "mainboard", "board", "backplane"},
    {"bios", "cmos", "firmware", "bmc", "uefi"},
    {"gpu", "cuda", "nvidia", "vbios", "xid", "retimer", "riser"},
]

_WORD_TO_SYNONYMS: dict[str, set[str]] = {}
for group in _SYNONYM_GROUPS:
    for word in group:
        _WORD_TO_SYNONYMS[word] = group

# Error code patterns
_ERROR_PATTERNS = [
    re.compile(r"\bSMART\b", re.I),
    re.compile(r"\bECC\b", re.I),
    re.compile(r"\bIERR\b", re.I),
    re.compile(r"\bMCE\b", re.I),
    re.compile(r"\bUCE\b", re.I),
    re.compile(r"\bUPI\b", re.I),
    re.compile(r"\bRAID\b", re.I),
    re.compile(r"\bNVMe\b", re.I),
    re.compile(r"\bBMC\b", re.I),
    re.compile(r"\bUEFI\b", re.I),
    re.compile(r"\bEDAC\b", re.I),
    re.compile(r"\bDPC\b", re.I),
    re.compile(r"\bXid\b", re.I),
    re.compile(r"PV[A-Z_]+_FAULT\b", re.I),
    re.compile(r"BAC\d+", re.I),
    re.compile(r"P3V_BAT", re.I),
    re.compile(r"IOError\w*", re.I),
    re.compile(r"BadSector\w*", re.I),
    re.compile(r"Reallocated\w*", re.I),
    re.compile(r"xid\s*\d+", re.I),
]

_CATEGORY_MAP = {
    "CPU": ["cpu", "processor", "ierr", "mce", "socket", "core", "throttl"],
    "Memory": ["memory", "dimm", "ram", "ecc", "uce", "ddr", "edac"],
    "Storage": ["disk", "drive", "hdd", "ssd", "nvme", "raid", "smart", "storage", "mdisk"],
    "Network": ["network", "nic", "ethernet", "link", "cable", "port", "latency", "pcie", "ocp"],
    "Power": ["power", "psu", "voltage", "watt"],
    "Thermal": ["fan", "thermal", "temperature", "heat", "cool", "overheat"],
    "BIOS": ["bios", "cmos", "post", "uefi", "gpt", "boot"],
    "Firmware": ["firmware", "bmc"],
    "Motherboard": ["motherboard", "board", "backplane"],
    "System": ["crash", "hang", "lockup", "reboot", "freeze"],
    "GPU": ["gpu", "cuda", "nvidia", "xid", "vbios", "retimer", "riser"],
}

# Stop words — never expand or search these
_STOP = {"the", "is", "has", "was", "are", "been", "have", "had", "off", "on", "of",
         "and", "or", "not", "for", "from", "with", "this", "that", "in", "to", "it",
         "at", "by", "an", "be", "as", "do", "if", "no", "so", "up", "log", "status",
         "diff", "pid", "name", "none", "tags"}


def extract_error_codes(text: str) -> list[str]:
    codes = []
    for pat in _ERROR_PATTERNS:
        for m in pat.finditer(text):
            codes.append(m.group(0))
    return list(dict.fromkeys(codes))


def expand_synonyms(words: list[str]) -> list[str]:
    expanded = set(words)
    for w in words:
        wl = w.lower()
        if wl in _STOP:
            continue
        if wl in _WORD_TO_SYNONYMS:
            expanded.update(_WORD_TO_SYNONYMS[wl])
    return list(expanded)


def infer_categories(text: str) -> list[str]:
    tl = text.lower()
    cats = []
    for cat, keywords in _CATEGORY_MAP.items():
        if any(kw in tl for kw in keywords):
            cats.append(cat)
    return cats


def build_search_queries(text: str, parsed_category: str = "") -> list[str]:
    queries = []
    codes = extract_error_codes(text)
    if codes:
        queries.append(" ".join(codes))

    # Category-specific query (strongest signal)
    if parsed_category and parsed_category != "Other":
        queries.append(parsed_category)

    # Clean words (no stop words, no short tokens)
    words = [w for w in re.findall(r"[A-Za-z0-9_]+", text)
             if len(w) > 2 and w.lower() not in _STOP]
    if words:
        expanded = expand_synonyms(words)
        # Remove stop words from expanded set too
        expanded = [w for w in expanded if w.lower() not in _STOP and len(w) > 2]
        queries.append(" ".join(expanded[:30]))  # cap to avoid massive queries

    cats = infer_categories(text)
    if cats:
        queries.append(" ".join(cats))

    if words:
        queries.append(" ".join(words[:20]))

    return queries


def smart_search(db_module, db_path: str, text: str, limit: int = 10,
                 parsed_category: str = "") -> list[dict[str, Any]]:
    """Multi-strategy search with category bias."""
    queries = build_search_queries(text, parsed_category)
    if not queries:
        return db_module.search_knowledge(db_path, "", limit=limit)

    seen: dict[int, dict] = {}
    scores: dict[int, float] = {}

    for priority, query in enumerate(queries):
        weight = 1.0 / (1 + priority)
        results = db_module.search_knowledge(db_path, query, limit=limit * 2)
        for rank, entry in enumerate(results):
            eid = entry["id"]
            if eid not in seen:
                seen[eid] = entry
                scores[eid] = 0.0
            scores[eid] += weight / (1 + rank)

    # Category bias: boost entries matching the parsed category
    if parsed_category and parsed_category != "Other":
        cat_lower = parsed_category.lower()
        for eid, entry in seen.items():
            if (entry.get("category") or "").lower() == cat_lower:
                scores[eid] *= 3.0  # Strong boost for exact category match

    ranked = sorted(seen.keys(), key=lambda x: scores[x], reverse=True)
    return [seen[eid] for eid in ranked[:limit]]
