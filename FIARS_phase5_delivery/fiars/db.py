"""
db.py — Simplified FIARS database.

Three main tables:
  knowledge     — verified error→solution reference (the core)
  case_history  — work log of tickets processed (paginated)
  raw_dumps     — unprocessed uploads with extracted text

Plus kb_articles / kb_error_map for vendor pattern matching.
"""
from __future__ import annotations
import json, os, re, sqlite3
from datetime import datetime, timezone
from typing import Any

SCHEMA = """
-- Core knowledge base: error → solution reference
CREATE TABLE IF NOT EXISTS knowledge (
    id INTEGER PRIMARY KEY,
    category TEXT,
    error_code TEXT,
    fault_description TEXT NOT NULL,
    affected_parts TEXT,
    root_cause TEXT,
    solution TEXT NOT NULL,
    source TEXT,
    engineer TEXT,
    notes TEXT,
    created_at TEXT,
    updated_at TEXT
);
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
    id UNINDEXED, category, error_code, fault_description,
    affected_parts, root_cause, solution, notes,
    tokenize = 'unicode61'
);

-- Work log: tickets processed
CREATE TABLE IF NOT EXISTS case_history (
    id INTEGER PRIMARY KEY,
    ticket_number TEXT,
    date TEXT,
    server_sn TEXT,
    location TEXT,
    error_fault TEXT NOT NULL,
    parts TEXT,
    solution TEXT NOT NULL,
    root_cause TEXT,
    recurrence_flag INTEGER DEFAULT 0,
    engineer TEXT,
    notes TEXT,
    resolution_time_min INTEGER,
    report_text TEXT,
    raw_block TEXT,
    created_at TEXT
);
CREATE VIRTUAL TABLE IF NOT EXISTS case_history_fts USING fts5(
    id UNINDEXED, error_fault, parts, solution, root_cause, notes,
    tokenize = 'unicode61'
);

-- Raw fault dumps (unprocessed uploads)
CREATE TABLE IF NOT EXISTS raw_dumps (
    id INTEGER PRIMARY KEY,
    filename TEXT NOT NULL,
    file_type TEXT,
    file_path TEXT,
    extracted_text TEXT,
    status TEXT DEFAULT 'uploaded',
    uploaded_by TEXT,
    notes TEXT,
    created_at TEXT
);
CREATE VIRTUAL TABLE IF NOT EXISTS raw_dumps_fts USING fts5(
    id UNINDEXED, filename, extracted_text,
    tokenize = 'unicode61'
);

-- Vendor KB pattern matching (kept from before)
CREATE TABLE IF NOT EXISTS kb_articles (
    kb_id INTEGER PRIMARY KEY,
    title TEXT NOT NULL, scope TEXT, problem TEXT,
    solution TEXT, root_cause TEXT, suggestions TEXT,
    source_url TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS kb_error_map (
    id INTEGER PRIMARY KEY,
    kb_id INTEGER REFERENCES kb_articles(kb_id),
    error_pattern TEXT NOT NULL, power_rail TEXT,
    suspect_components TEXT, dimm_slots TEXT, remark TEXT
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_knowledge_cat ON knowledge(category);
CREATE INDEX IF NOT EXISTS idx_case_date ON case_history(date);
CREATE INDEX IF NOT EXISTS idx_raw_status ON raw_dumps(status);
CREATE INDEX IF NOT EXISTS idx_kb_pat ON kb_error_map(error_pattern);

-- Legacy cleanup
DROP TABLE IF EXISTS cases;
DROP TABLE IF EXISTS cases_fts;
DROP TABLE IF EXISTS case_components;
DROP TABLE IF EXISTS engineer_notes;
DROP TABLE IF EXISTS fault_categories;
DROP TABLE IF EXISTS root_cause_catalog;
DROP TABLE IF EXISTS resolution_catalog;
"""

def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def connect(path):
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def init_db(path):
    """Init or upgrade DB. Handles old schemas, purges SEED data."""
    is_new = not os.path.exists(path)
    try:
        con = connect(path)
        con.executescript(SCHEMA)
        # Migrate older case_history tables that predate root_cause/recurrence_flag.
        for stmt in ("ALTER TABLE case_history ADD COLUMN root_cause TEXT",
                     "ALTER TABLE case_history ADD COLUMN recurrence_flag INTEGER DEFAULT 0"):
            try:
                con.execute(stmt)
            except sqlite3.OperationalError:
                pass  # column already exists
        con.commit()
        con.close()
        return "created" if is_new else "ok"
    except sqlite3.OperationalError:
        # Incompatible — backup and recreate
        backup = path + f".bak_{datetime.now():%Y%m%d_%H%M%S}"
        try: os.rename(path, backup)
        except: pass
        con = connect(path)
        con.executescript(SCHEMA)
        con.commit(); con.close()
        return f"reset (old DB backed up: {backup})"

# ── Knowledge base ───────────────────────────────────────────────────────────
def add_knowledge(path, entry):
    """Add a verified knowledge entry. Returns id."""
    con = connect(path)
    now = _now()
    cur = con.execute("""INSERT INTO knowledge
        (category, error_code, fault_description, affected_parts,
         root_cause, solution, source, engineer, notes, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (entry.get("category",""), entry.get("error_code",""),
         entry["fault_description"], entry.get("affected_parts",""),
         entry.get("root_cause",""), entry["solution"],
         entry.get("source",""), entry.get("engineer",""),
         entry.get("notes",""), now, now))
    kid = cur.lastrowid
    con.execute("""INSERT INTO knowledge_fts
        (id, category, error_code, fault_description, affected_parts,
         root_cause, solution, notes)
        VALUES (?,?,?,?,?,?,?,?)""",
        (kid, entry.get("category",""), entry.get("error_code",""),
         entry["fault_description"], entry.get("affected_parts",""),
         entry.get("root_cause",""), entry["solution"],
         entry.get("notes","")))
    con.commit(); con.close()
    return kid

def search_knowledge(path, query, limit=20):
    """FTS5 search across knowledge base."""
    toks = [t for t in re.findall(r"[A-Za-z0-9_]+", query or "") if len(t) > 1]
    if not toks:
        con = connect(path)
        rows = con.execute("SELECT * FROM knowledge ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        con.close()
        return [dict(r) for r in rows]
    q = " OR ".join(dict.fromkeys(toks))
    con = connect(path)
    rows = con.execute("""SELECT k.* FROM knowledge_fts
        JOIN knowledge k ON k.id = knowledge_fts.id
        WHERE knowledge_fts MATCH ? ORDER BY rank LIMIT ?""", (q, limit)).fetchall()
    con.close()
    return [dict(r) for r in rows]

def count_knowledge(path):
    con = connect(path)
    n = con.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
    con.close()
    return n

def update_knowledge(path, kid, entry):
    """Update a knowledge entry by id."""
    con = connect(path)
    now = _now()
    con.execute("""UPDATE knowledge SET category=?, error_code=?, fault_description=?,
        affected_parts=?, root_cause=?, solution=?, source=?, engineer=?, notes=?, updated_at=?
        WHERE id=?""",
        (entry.get("category",""), entry.get("error_code",""),
         entry["fault_description"], entry.get("affected_parts",""),
         entry.get("root_cause",""), entry["solution"],
         entry.get("source",""), entry.get("engineer",""),
         entry.get("notes",""), now, kid))
    # Rebuild FTS entry
    con.execute("DELETE FROM knowledge_fts WHERE id=?", (kid,))
    con.execute("""INSERT INTO knowledge_fts
        (id, category, error_code, fault_description, affected_parts,
         root_cause, solution, notes) VALUES (?,?,?,?,?,?,?,?)""",
        (kid, entry.get("category",""), entry.get("error_code",""),
         entry["fault_description"], entry.get("affected_parts",""),
         entry.get("root_cause",""), entry["solution"], entry.get("notes","")))
    con.commit(); con.close()

def delete_knowledge(path, kid):
    """Delete a knowledge entry by id."""
    con = connect(path)
    con.execute("DELETE FROM knowledge_fts WHERE id=?", (kid,))
    con.execute("DELETE FROM knowledge WHERE id=?", (kid,))
    con.commit(); con.close()

# ── Case history (paginated) ────────────────────────────────────────────────
def add_case(path, entry):
    con = connect(path)
    now = _now()
    cur = con.execute("""INSERT INTO case_history
        (ticket_number, date, server_sn, location, error_fault, parts,
         solution, root_cause, recurrence_flag, engineer, notes,
         resolution_time_min, report_text, raw_block, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (entry.get("ticket_number",""), entry.get("date",""),
         entry.get("server_sn",""), entry.get("location",""),
         entry["error_fault"], entry.get("parts",""),
         entry["solution"], entry.get("root_cause",""),
         int(entry.get("recurrence_flag") or 0),
         entry.get("engineer",""), entry.get("notes",""),
         entry.get("resolution_time_min"),
         entry.get("report_text",""), entry.get("raw_block",""), now))
    cid = cur.lastrowid
    con.execute("""INSERT INTO case_history_fts
        (id, error_fault, parts, solution, root_cause, notes)
        VALUES (?,?,?,?,?,?)""",
        (cid, entry["error_fault"], entry.get("parts",""),
         entry["solution"], entry.get("root_cause",""), entry.get("notes","")))
    con.commit(); con.close()
    return cid

def search_similar(path, query, k=50, exclude_id=None):
    """
    FTS5 similarity search over case_history for recommend.py.
    Returns dicts in the field names recommend.diagnose() expects:
    case_id, case_date, fault_description, root_cause_raw, resolution_raw,
    recurrence_flag, similarity (rank-decayed, in [0,1]).

    exclude_id: optional case_id to omit from results (used by the leave-one-out
    eval harness so a held-out case can't match against itself).
    """
    toks = [t for t in re.findall(r"[A-Za-z0-9_]+", query or "") if len(t) > 1]
    if not toks:
        return []
    q = " OR ".join(dict.fromkeys(toks))
    # Fetch one extra row when excluding so the result count still hits k.
    fetch_k = k + 1 if exclude_id is not None else k
    con = connect(path)
    try:
        rows = con.execute("""SELECT c.*, case_history_fts.rank AS bm25
            FROM case_history_fts
            JOIN case_history c ON c.id = case_history_fts.id
            WHERE case_history_fts MATCH ? ORDER BY case_history_fts.rank LIMIT ?""",
            (q, fetch_k)).fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        con.close()
    if exclude_id is not None:
        rows = [r for r in rows if r["id"] != exclude_id][:k]
    out = []
    n = len(rows)
    for i, r in enumerate(rows):
        # BM25 rank in SQLite FTS5 is negative (more negative = better match);
        # decay by position since exact score scale isn't meaningfully comparable
        # to the similarity x recency x success weighting in recommend.py.
        similarity = 1.0 - (i / n) if n > 1 else 1.0
        out.append({
            "case_id": r["id"],
            "case_date": r["date"] or "",
            "fault_description": r["error_fault"] or "",
            "root_cause_raw": r["root_cause"] or "",
            "resolution_raw": r["solution"] or "",
            "recurrence_flag": r["recurrence_flag"] or 0,
            "similarity": similarity,
        })
    return out


def get_cases(path, case_ids):
    """
    Fetch full case_history rows by id, in the same field shape as
    search_similar (minus 'similarity', which callers set themselves).
    Used by retrieval/hybrid.py to hydrate a fused ranking back into
    the dict shape recommend.diagnose() expects.
    """
    if not case_ids:
        return {}
    con = connect(path)
    qmarks = ",".join("?" * len(case_ids))
    rows = con.execute(
        f"SELECT * FROM case_history WHERE id IN ({qmarks})", case_ids
    ).fetchall()
    con.close()
    return {
        r["id"]: {
            "case_id": r["id"],
            "case_date": r["date"] or "",
            "fault_description": r["error_fault"] or "",
            "root_cause_raw": r["root_cause"] or "",
            "resolution_raw": r["solution"] or "",
            "recurrence_flag": r["recurrence_flag"] or 0,
        }
        for r in rows
    }

def notes_for(path, case_ids):
    """Return {case_id: notes} for the given ids, for recommend.py's support snippets."""
    if not case_ids:
        return {}
    con = connect(path)
    qmarks = ",".join("?" * len(case_ids))
    rows = con.execute(
        f"SELECT id, notes FROM case_history WHERE id IN ({qmarks})", case_ids
    ).fetchall()
    con.close()
    return {r["id"]: r["notes"] or "" for r in rows}

def list_cases(path, page=1, per_page=25, search="", sort_col="id", sort_dir="DESC"):
    con = connect(path)
    allowed = {"id","ticket_number","date","error_fault","parts","solution","engineer"}
    col = sort_col if sort_col in allowed else "id"
    direction = "ASC" if sort_dir.upper() == "ASC" else "DESC"
    offset = (max(1, page) - 1) * per_page

    if search.strip():
        like = f"%{search.strip()}%"
        rows = con.execute(f"""SELECT * FROM case_history
            WHERE error_fault LIKE ? OR parts LIKE ? OR solution LIKE ?
                  OR ticket_number LIKE ? OR engineer LIKE ? OR notes LIKE ?
            ORDER BY {col} {direction} LIMIT ? OFFSET ?""",
            (like,like,like,like,like,like, per_page, offset)).fetchall()
        total = con.execute("""SELECT COUNT(*) FROM case_history
            WHERE error_fault LIKE ? OR parts LIKE ? OR solution LIKE ?
                  OR ticket_number LIKE ? OR engineer LIKE ? OR notes LIKE ?""",
            (like,like,like,like,like,like)).fetchone()[0]
    else:
        rows = con.execute(f"SELECT * FROM case_history ORDER BY {col} {direction} LIMIT ? OFFSET ?",
            (per_page, offset)).fetchall()
        total = con.execute("SELECT COUNT(*) FROM case_history").fetchone()[0]
    con.close()
    return [dict(r) for r in rows], total

# ── Raw dumps ────────────────────────────────────────────────────────────────
def add_raw_dump(path, filename, file_type, file_path, extracted_text="", uploaded_by=""):
    con = connect(path)
    now = _now()
    cur = con.execute("""INSERT INTO raw_dumps
        (filename, file_type, file_path, extracted_text, status, uploaded_by, created_at)
        VALUES (?,?,?,?,?,?,?)""",
        (filename, file_type, file_path, extracted_text,
         "extracted" if extracted_text else "uploaded", uploaded_by, now))
    did = cur.lastrowid
    if extracted_text:
        con.execute("INSERT INTO raw_dumps_fts (id, filename, extracted_text) VALUES (?,?,?)",
            (did, filename, extracted_text))
    con.commit(); con.close()
    return did

def list_raw_dumps(path, status=None, limit=50):
    con = connect(path)
    if status:
        rows = con.execute("SELECT * FROM raw_dumps WHERE status=? ORDER BY id DESC LIMIT ?",
            (status, limit)).fetchall()
    else:
        rows = con.execute("SELECT * FROM raw_dumps ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    con.close()
    return [dict(r) for r in rows]

def get_raw_dump(path, dump_id):
    con = connect(path)
    r = con.execute("SELECT * FROM raw_dumps WHERE id=?", (dump_id,)).fetchone()
    con.close()
    return dict(r) if r else None

def update_raw_dump_status(path, dump_id, status):
    con = connect(path)
    con.execute("UPDATE raw_dumps SET status=? WHERE id=?", (status, dump_id))
    con.commit(); con.close()

def search_raw_dumps(path, query, limit=20):
    toks = [t for t in re.findall(r"[A-Za-z0-9_]+", query or "") if len(t) > 1]
    if not toks: return list_raw_dumps(path, limit=limit)
    q = " OR ".join(dict.fromkeys(toks))
    con = connect(path)
    rows = con.execute("""SELECT r.* FROM raw_dumps_fts
        JOIN raw_dumps r ON r.id = raw_dumps_fts.id
        WHERE raw_dumps_fts MATCH ? ORDER BY rank LIMIT ?""", (q, limit)).fetchall()
    con.close()
    return [dict(r) for r in rows]

# ── KB (vendor articles + error map) ────────────────────────────────────────
def save_kb_article(path, article):
    con = connect(path)
    now = _now()
    cur = con.execute("""INSERT INTO kb_articles
        (title, scope, problem, solution, root_cause, suggestions, source_url, created_at)
        VALUES (?,?,?,?,?,?,?,?)""",
        (article["title"], article.get("scope",""), article.get("problem",""),
         article.get("solution",""), article.get("root_cause",""),
         article.get("suggestions",""), article.get("source_url",""), now))
    kb_id = cur.lastrowid
    for e in article.get("error_map", []):
        con.execute("""INSERT INTO kb_error_map
            (kb_id, error_pattern, power_rail, suspect_components, dimm_slots, remark)
            VALUES (?,?,?,?,?,?)""",
            (kb_id, e["error_pattern"], e.get("power_rail",""),
             json.dumps(e.get("suspect_components",[]),ensure_ascii=False),
             json.dumps(e.get("dimm_slots",[]),ensure_ascii=False),
             e.get("remark","")))
    con.commit(); con.close()
    return kb_id

def kb_pattern_lookup(path, text):
    """Match raw text against KB error patterns."""
    if not text: return []
    upper = text.upper()
    con = connect(path)
    try:
        rows = con.execute("SELECT * FROM kb_error_map").fetchall()
    except: return []
    finally: con.close()
    matches = []
    for r in rows:
        pat = (r["error_pattern"] or "").strip().upper()
        if pat and pat in upper:
            suspects = json.loads(r["suspect_components"] or "[]") if r["suspect_components"] else []
            dimms = json.loads(r["dimm_slots"] or "[]") if r["dimm_slots"] else []
            art = None
            try:
                c2 = connect(path)
                a = c2.execute("SELECT title,solution,suggestions FROM kb_articles WHERE kb_id=?",
                    (r["kb_id"],)).fetchone()
                if a: art = dict(a)
                c2.close()
            except: pass
            matches.append({"error_pattern": r["error_pattern"], "power_rail": r["power_rail"],
                "suspect_components": suspects, "dimm_slots": dimms, "article": art})
    return matches

# ── Stats ────────────────────────────────────────────────────────────────────
def stats(path):
    con = connect(path)
    kb_count = con.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
    case_count = con.execute("SELECT COUNT(*) FROM case_history").fetchone()[0]
    dump_count = con.execute("SELECT COUNT(*) FROM raw_dumps").fetchone()[0]
    kb_articles = con.execute("SELECT COUNT(*) FROM kb_articles").fetchone()[0]
    kb_patterns = con.execute("SELECT COUNT(*) FROM kb_error_map").fetchone()[0]
    con.close()
    return {"knowledge": kb_count, "cases": case_count, "raw_dumps": dump_count,
            "kb_articles": kb_articles, "kb_patterns": kb_patterns}

def kb_stats(path):
    """Backwards-compatible: return KB article/pattern counts."""
    con = connect(path)
    articles = con.execute("SELECT COUNT(*) FROM kb_articles").fetchone()[0]
    patterns = con.execute("SELECT COUNT(*) FROM kb_error_map").fetchone()[0]
    con.close()
    return {"kb_articles": articles, "kb_patterns": patterns}

def export_all(path, out_dir):
    con = connect(path)
    data = {}
    for t in ("knowledge","case_history","raw_dumps","kb_articles","kb_error_map"):
        try: data[t] = [dict(r) for r in con.execute(f"SELECT * FROM {t}").fetchall()]
        except: data[t] = []
    con.close()
    os.makedirs(out_dir, exist_ok=True)
    fn = os.path.join(out_dir, f"fiars_export_{datetime.now():%Y%m%d_%H%M%S}.json")
    with open(fn, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return fn
