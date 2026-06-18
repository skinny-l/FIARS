"""
bulk_parse.py — Parse pasted knowledge data in multiple formats.

Supports:
  1. Pipe-delimited: ERROR | DESCRIPTION | PARTS | ROOT_CAUSE | SOLUTION
  2. Markdown tables (auto-detects column headers)
  3. JSON arrays

Returns a list of knowledge-entry dicts ready for db.add_knowledge.
"""
from __future__ import annotations
import json
import re


# Map common column header names to our field names
_HEADER_MAP = {
    "error": "error_code", "error code": "error_code", "code": "error_code",
    "event code": "error_code", "fault code": "error_code", "xid number": "error_code",
    "smart attribute": "error_code", "log type": "error_code", "attribute": "error_code",
    "fault": "fault_description", "fault description": "fault_description",
    "description": "fault_description", "meaning": "fault_description",
    "symptom": "fault_description", "symptoms": "fault_description",
    "parts": "affected_parts", "affected parts": "affected_parts",
    "suspect components": "affected_parts", "component": "affected_parts",
    "components": "affected_parts", "affected": "affected_parts",
    "root cause": "root_cause", "cause": "root_cause",
    "solution": "solution", "fix": "solution", "action": "solution",
    "recommended action": "solution", "remediation": "solution", "usage": "solution",
    "category": "category", "fault category": "category",
    "threshold": "threshold", "path": "path",
    "source": "source", "reference": "source", "remark": "notes", "remarks": "notes",
}


def _clean(s: str) -> str:
    s = (s or "").strip()
    # Strip reference markers like [1], [5, 9] anywhere in the text
    s = re.sub(r"\s*\[\d+(?:,\s*\d+)*\]", "", s).strip()
    return s


def _parse_pipe(text: str, default_category: str = "") -> list[dict]:
    """Pipe-delimited: ERROR | DESC | PARTS | ROOT_CAUSE | SOLUTION"""
    entries = []
    for line in text.splitlines():
        line = line.strip()
        if not line or "|" not in line:
            continue
        # Skip markdown table separators
        if re.match(r"^[\s|:-]+$", line):
            continue
        cols = [_clean(c) for c in line.split("|")]
        # Drop leading/trailing empty cells (markdown tables have them)
        while cols and cols[0] == "":
            cols.pop(0)
        while cols and cols[-1] == "":
            cols.pop()
        if len(cols) < 2:
            continue
        # Skip header rows
        if cols[0].lower() in _HEADER_MAP and cols[0].lower() in (
                "error", "error code", "code", "event code", "fault code"):
            continue

        # 5-column: error, desc, parts, root_cause, solution
        if len(cols) >= 5:
            entries.append({
                "error_code": cols[0], "fault_description": cols[1],
                "affected_parts": cols[2], "root_cause": cols[3],
                "solution": cols[4], "category": default_category,
            })
        # 4-column: error, category, parts, action  (BMC SEL style)
        elif len(cols) == 4:
            entries.append({
                "error_code": cols[0], "fault_description": cols[1],
                "affected_parts": cols[2], "solution": cols[3],
                "category": default_category,
            })
        # 3-column: code, meaning/threshold, action
        elif len(cols) == 3:
            entries.append({
                "error_code": cols[0], "fault_description": cols[1],
                "solution": cols[2], "category": default_category,
            })
        # 2-column: term, value
        elif len(cols) == 2:
            entries.append({
                "error_code": cols[0], "fault_description": cols[1],
                "solution": cols[1], "category": default_category,
            })
    return entries


def _parse_markdown_table(text: str, default_category: str = "") -> list[dict]:
    """Parse a markdown table with a header row, mapping columns by name."""
    lines = [l.strip() for l in text.splitlines() if l.strip() and "|" in l]
    if len(lines) < 2:
        return []

    # First non-separator line is the header
    header_line = None
    data_start = 0
    for i, line in enumerate(lines):
        if re.match(r"^[\s|:-]+$", line):
            continue
        if header_line is None:
            header_line = line
            data_start = i + 1
            break

    if not header_line:
        return []

    headers = [_clean(h).lower() for h in header_line.split("|") if _clean(h)]
    field_names = [_HEADER_MAP.get(h, None) for h in headers]

    # If no recognizable headers, fall back to positional pipe parse
    if not any(field_names):
        return _parse_pipe(text, default_category)

    entries = []
    for line in lines[data_start:]:
        if re.match(r"^[\s|:-]+$", line):
            continue
        cols = [_clean(c) for c in line.split("|")]
        while cols and cols[0] == "":
            cols.pop(0)
        while cols and cols[-1] == "":
            cols.pop()
        if not cols or all(c == "" for c in cols):
            continue

        entry = {"category": default_category}
        threshold = ""
        path = ""
        for idx, field in enumerate(field_names):
            if idx >= len(cols) or not field:
                continue
            val = cols[idx]
            if field == "threshold":
                threshold = val
            elif field == "path":
                path = val
            else:
                entry[field] = val

        # Fold threshold into description, path into solution
        if threshold and entry.get("fault_description"):
            entry["fault_description"] += f" (threshold: {threshold})"
        elif threshold:
            entry["fault_description"] = f"Threshold: {threshold}"
        if path:
            entry["solution"] = (entry.get("solution", "") + f" Path: {path}").strip()

        # Need at least error_code and (description or solution)
        if entry.get("error_code") and (entry.get("fault_description") or entry.get("solution")):
            if not entry.get("solution"):
                entry["solution"] = entry.get("fault_description", "")
            if not entry.get("fault_description"):
                entry["fault_description"] = entry.get("error_code", "")
            entries.append(entry)
    return entries


def parse_bulk(text: str, default_category: str = "", fmt: str = "auto") -> list[dict]:
    """
    Parse bulk knowledge text. fmt: 'auto', 'pipe', 'markdown', 'json'.
    Returns list of entry dicts.
    """
    text = text.strip()
    if not text:
        return []

    # JSON
    if fmt == "json" or (fmt == "auto" and text.lstrip().startswith(("[", "{"))):
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                data = data.get("knowledge", [data])
            return [e for e in data if isinstance(e, dict)]
        except json.JSONDecodeError:
            pass

    # Markdown table (has a header row with recognizable names)
    if fmt == "markdown" or (fmt == "auto" and _looks_like_md_table(text)):
        return _parse_markdown_table(text, default_category)

    # Default: pipe-delimited
    return _parse_pipe(text, default_category)


def _looks_like_md_table(text: str) -> bool:
    """Detect if text has a markdown table header + separator row."""
    lines = [l for l in text.splitlines() if "|" in l]
    if len(lines) < 2:
        return False
    # Look for a separator row (---|---|---)
    for line in lines[:3]:
        if re.match(r"^[\s|:-]+$", line.strip()) and "-" in line:
            return True
    return False
