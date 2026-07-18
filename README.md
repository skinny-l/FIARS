# FIARS — Fault Resolution Intelligence Platform

Local, offline fault-diagnosis tool for data-centre maintenance teams.

**Core features:**
1. **Ticket parser** — paste a raw fault block (single fault, multiple fault blocks, or a full
   dispatch table), get parsed structured fields, an auto-generated OneNote-format report,
   on-site diagnostic commands/log-collection steps for the fault category, and a "similar past
   cases" panel ranked by similarity × recency × fix-success.
2. **Checklist** — auto-fills an inspection checklist from the parsed ticket (server info,
   category-aware pre-checked items, hot-swap vs. power-off guidance) and prints cleanly to PDF.
3. **Searchable knowledge base** — error codes, solutions, affected parts. FTS5 search with
   synonym expansion (e.g. a query for "PSU" also matches cases worded as "power supply").
4. **Quick add** — new knowledge entry in 30 seconds. Three required fields.
5. **Paginated case history** — server-side pagination, search, sort. Scales to thousands.
6. **Raw dump repository** — upload fault logs/PDFs/emails/screenshots. Auto-extract text,
   synonym-aware search, convertible to KB entries.

> No paid services. No cloud. Pure Python stdlib. Offline from first launch.

## Quick start

    python server.py        (or double-click start.bat on Windows)

The server auto-initialises the database, loads the pre-loaded knowledge base, runs a self-test,
then opens http://127.0.0.1:5000.

## Pre-loaded knowledge

107 knowledge entries + 36 BMC error patterns, made up of:

- 17 confirmed solutions (Fan, PSU, Motherboard, CPU, Memory, Storage, Battery, BIOS, Firmware)
- 29 general server fault KB entries
- 14 SA5212D6-specific fault codes
- 10 GPU fault codes
- 37 reference entries (SEL, SMART, Xid, CPU)
- 36 Power_Fault BMC error patterns with suspect components and DIMM slot locations
  (SA5212D6/SA5326D6)

## Raw dump file support

Native (no install): .txt .log .csv .tsv .md .json .eml .html .htm .ini .cfg
Optional (pip install pymupdf): .pdf
Optional (Tesseract + pip install pytesseract Pillow): .png .jpg .jpeg .tiff .bmp scanned images

## Configuration

Copy `config.json.example` to `config.json` to override defaults (db path, backup dir, engineer
name, host, port). Safe to skip — sensible local defaults are used if it's missing.

## Verify

    python tests/test_parser.py         (11 tests)
    python tests/test_parser_table.py   (24 tests)
    python tests/test_recommend.py      (9 tests)

## Design doc

See `ARCHITECTURE.md` for the original design/roadmap doc. Note: it describes an optional
sentence-transformers/FAISS semantic-search layer that was evaluated and deliberately *not*
adopted (see commit `a9c54ed`) in favor of the lighter synonym-expansion approach that ships
today, to keep the app dependency-free. Treat the "Guiding principles" and schema sections as
current; treat the semantic-search tech-stack section as a rejected alternative, not the
implemented design.
