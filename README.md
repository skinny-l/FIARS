# FIARS — Fault Resolution Intelligence Platform

Local, offline fault-diagnosis tool for data-centre maintenance teams.

**Five core features:**
1. **Searchable knowledge base** — error codes, solutions, affected parts. FTS5 instant search.
2. **Quick add** — new knowledge entry in 30 seconds. Three required fields.
3. **Ticket parser** — paste raw fault block, get parsed details + report + KB matches.
4. **Paginated case history** — server-side pagination, search, sort. Scales to thousands.
5. **Raw dump repository** — upload fault logs/PDFs/emails. Auto-extract text, searchable, convertible to KB entries.

> No paid services. No cloud. Pure Python stdlib. Offline from first launch.

## Quick start

    python server.py        (or double-click start.bat on Windows)

The server auto-initialises the database, loads 17 confirmed solutions + 36 BMC error patterns,
runs a self-test, then opens http://127.0.0.1:5000.

## Pre-loaded knowledge

- **17 confirmed solutions** (Fan, PSU, Motherboard, CPU, Memory, Storage, Battery, BIOS, Firmware)
- **36 Power_Fault BMC error patterns** with suspect components and DIMM slot locations (SA5212D6/SA5326D6)

## Raw dump file support

Native (no install): .txt .log .csv .json .eml .html
Optional (pip install pymupdf): .pdf
Optional (Tesseract + pip install pytesseract Pillow): .png .jpg scanned images

## Verify

    python tests/test_parser.py    (8 tests)
