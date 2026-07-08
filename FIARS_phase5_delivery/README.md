# FIARS — Fault Resolution Intelligence Platform

Local, offline fault-diagnosis tool for data-centre maintenance teams.

**Seven core features:**
1. **Searchable knowledge base** — error codes, solutions, affected parts. FTS5 instant search.
2. **Quick add** — new knowledge entry in 30 seconds. Three required fields.
3. **Ticket parser** — paste raw fault block, get parsed details + report + KB matches.
4. **Paginated case history** — server-side pagination, search, sort. Scales to thousands.
5. **Raw dump repository** — upload fault logs/PDFs/emails. Auto-extract text, searchable, convertible to KB entries.
6. **Recommendation engine** — on parse, ranks likely root causes and resolutions from real case
   history (similarity × recency × fix-success weighting), with confidence scores and supporting
   case IDs. Lexical (FTS5) by default; optional semantic/hybrid search — see below.
7. **Analytics dashboard** — read-only Streamlit app: MTTR, recurrence/resolution-effectiveness,
   fault trends, confidence calibration, engineer contribution. Separate optional process — see below.

> No paid services. No cloud. Pure Python stdlib by default. Offline from first launch.

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

## Semantic / hybrid search (optional)

The recommendation engine uses lexical (FTS5) search by default — nothing to install. To add
semantic search on top of it (catches paraphrased faults that share no exact words):

    pip install -r requirements-ml.txt
    python scripts/build_index.py

First run downloads the ~80MB `all-MiniLM-L6-v2` model once (needs internet); fully offline
after that. Re-run `build_index.py` any time — unchanged cases are skipped automatically.
`diagnose()` automatically switches from lexical-only to hybrid (Reciprocal Rank Fusion of
lexical + semantic) once the index exists; nothing else changes.

**Measuring retrieval quality:** the eval harness runs leave-one-out testing — for every past
case, it's hidden from its own search, then checked whether the system still recovers its
correct root cause from the rest of the history.

    python -m fiars.eval.leave_one_out fiars.db --mode lexical
    python -m fiars.eval.leave_one_out fiars.db --mode hybrid   # after build_index.py

Each prints `top-1` / `top-3` / mean-reciprocal-rank. *(Numbers here reflect your own real case
history when you run it — worth pasting into this README once you have them.)*

## Analytics dashboard (optional)

Read-only Streamlit app over the same `fiars.db` — six pages: Overview, Faults & Causes, Trends,
Resolution Effectiveness, Confidence Distribution, Engineer Contribution.

    pip install -r requirements-dashboard.txt
    streamlit run dashboard/streamlit_app.py     (or double-click start_dashboard.bat on Windows)

Never writes to the database — safe to run alongside the Flask app. The Confidence Distribution
page runs a live leave-one-out sample through the real recommendation engine, so it can take a
few seconds on a large case history (there's a sample-size slider to control this).

## Verify

    python tests/test_parser.py         (8 tests)
    python tests/test_parser_table.py   (11 tests)
    python tests/test_recommend.py      (6 tests)
    python tests/test_retrieval.py      (9 tests)
    python tests/test_eval.py           (6 tests)
    python tests/test_analytics.py      (11 tests)
